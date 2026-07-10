"""
Gemini pipeline for daily marketing report generation.

Reporter: drafts the report from raw BQ data.
Verifier: audits the draft for accuracy and returns a JSON verdict.
  If it requests revision, the Reporter is called again (max 2 passes).
  If blockers remain after 2 passes, the last draft is returned with a warning.
Trends: streaming path only — analyses KPI history and appends a trends section.
"""

import concurrent.futures
import json
import logging
import time
from pathlib import Path

import pandas as pd
from google import genai
from google.genai import types

from src.config import LLM

log = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_MAX_VERIFIER_PASSES = 2


def _load_prompt(client_id: str, filename: str) -> str:
    client_path = _PROMPTS_DIR / client_id / filename
    if client_path.exists():
        return client_path.read_text()
    return (_PROMPTS_DIR / "default" / filename).read_text()


def _dataframe_to_text(df: pd.DataFrame) -> str:
    if "date" in df.columns:
        df = df.sort_values("date", ascending=False).head(LLM.max_rows_per_table)
    elif len(df) > LLM.max_rows_per_table:
        df = df.head(LLM.max_rows_per_table)
    return df.to_csv(index=False)


def _make_client() -> genai.Client:
    return genai.Client(vertexai=True, project=LLM.project, location=LLM.location)


def _reporter_config(client_id: str, client_name: str) -> types.GenerateContentConfig:
    system_prompt = _load_prompt(client_id, "reporter.md").replace("{{client_name}}", client_name)
    return types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=LLM.max_output_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=LLM.thinking_budget),
    )


def _verifier_config(client_id: str, client_name: str) -> types.GenerateContentConfig:
    system_prompt = _load_prompt(client_id, "verifier.md").replace("{{client_name}}", client_name)
    return types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=LLM.max_output_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=LLM.thinking_budget),
        tools=[types.Tool(code_execution=types.ToolCodeExecution())],
    )


def _reporter_message(client_name: str, data_section: str, issues: list | None = None) -> str:
    msg = f"Client: {client_name}\n\n## Data\n{data_section}"
    if issues:
        issues_text = "\n".join(
            f"- [{i['severity'].upper()}] {i['section']}: {i['problem']} → {i['fix']}"
            for i in issues
        )
        msg += f"\n\n## Issues to Address\n{issues_text}\n\nPlease revise the report addressing all issues above."
    return msg


def _verifier_message(client_name: str, data_section: str, draft: str) -> str:
    return f"## Draft Report\n{draft}\n\n## Raw Data Snapshot\nClient: {client_name}\n\n{data_section}"


def _generate_with_retry(
    client: genai.Client,
    contents: str,
    config: types.GenerateContentConfig,
    max_attempts: int = 3,
    timeout_seconds: int = 240,
) -> any:
    """Calls generate_content with per-call timeout and retry on 429 to avoid rate limiting."""
    delay = 30
    for attempt in range(1, max_attempts + 1):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                client.models.generate_content,
                model=LLM.model, contents=contents, config=config,
            )
            try:
                return future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                log.error("LLM call timed out after %ds (attempt %d/%d)", timeout_seconds, attempt, max_attempts)
                if attempt >= max_attempts:
                    raise TimeoutError(f"LLM call timed out after {timeout_seconds}s — check Vertex AI quota")
            except Exception as e:
                if "429" in str(e) and attempt < max_attempts:
                    log.warning("Rate limit hit — retrying in %ds (attempt %d/%d)", delay, attempt, max_attempts)
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise


def _call_reporter(
    client: genai.Client,
    client_id: str,
    client_name: str,
    data_section: str,
    issues: list | None = None,
) -> str:
    response = _generate_with_retry(
        client,
        contents=_reporter_message(client_name, data_section, issues),
        config=_reporter_config(client_id, client_name),
    )

    _log_usage(response.usage_metadata, agent="Reporter")
    return response.text


def _call_verifier(
    client: genai.Client,
    client_id: str,
    client_name: str,
    data_section: str,
    draft: str,
) -> dict:
    response = _generate_with_retry(
        client,
        contents=_verifier_message(client_name, data_section, draft),
        config=_verifier_config(client_id, client_name),
    )
    _log_usage(response.usage_metadata, agent="Verifier")
    _log_code_execution(response, agent="Verifier")
    try:
        return _extract_json(response.text)
    except (json.JSONDecodeError, AttributeError, ValueError) as e:
        log.warning("Verifier returned invalid JSON: %s — treating as approve", e)
        return {"verdict": "approve", "issues": []}


def _log_code_execution(response, agent: str = "") -> None:
    try:
        parts = response.candidates[0].content.parts
        code_blocks = [p for p in parts if getattr(p, "executable_code", None)]
        if code_blocks:
            log.info("[%s] Code execution used: %d block(s)", agent, len(code_blocks))
            for i, block in enumerate(code_blocks, 1):
                log.info("[%s] Code block %d:\n%s", agent, i, block.executable_code.code[:500])
        else:
            log.info("[%s] Code execution not used", agent)
    except Exception as e:
        log.debug("[%s] Could not inspect code execution parts: %s", agent, e)


def _extract_json(text: str) -> dict:
    """Extract the first valid JSON object from text, handling code-execution preamble."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Verifier response")
    depth = 0
    for i, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("No complete JSON object found in Verifier response")


def _log_input_tokens(client: genai.Client, contents: str) -> None:
    try:
        result = client.models.count_tokens(model=LLM.model, contents=contents)
        log.info("Input tokens (pre-call): %d / 1,048,576 limit", result.total_tokens)
    except Exception as e:
        log.warning("Could not count input tokens: %s", e)


def _log_usage(usage, agent: str = "") -> None:
    if not usage:
        return
    prefix = f"[{agent}] " if agent else ""
    log.info(
        "\n\n%sTokens used — input: %d, thinking: %d, output: %d, total: %d",
        prefix,
        usage.prompt_token_count or 0,
        usage.thoughts_token_count or 0,
        usage.candidates_token_count or 0,
        usage.total_token_count or 0,
    )


def analyse(client_id: str, client_name: str, tables: dict[str, pd.DataFrame]) -> str:
    """
    Run the Reporter + Verifier loop over the provided DataFrames.
    (Trends agent doesn't run here — see analyse_stream.)
    Agent 1: Reporter. It creates a draft with the context provided from BQ
    Agent 2: Verifier. 2.1 Receives the draft + initial context.
                       2.2 It has access to a Tool of python to verify that the
                       numbers provided by the reporter are correct.
                       2.3 Returns {"verdict": "approve/revise", "issues": [...], "rewritten_report": "..."}
                       2.4 If the verdict is approved, returns de report.
                       2.5 If the verdict is revised, returns the needed corrections and calls the
                       Reporter agent again, adding the corrections as context. Max 2 loops.

    Args:
        client_id: Used to resolve client-specific prompts (falls back to default).
        client_name: Human-readable client name injected into prompts.
        tables: dict mapping table name to its DataFrame.

    Returns:
        Verified markdown report ready for PDF rendering.
    """
    # Creates client to Vertex AI
    client = _make_client()
    log.info("LLM: model=%s location=%s thinking_budget=%d max_output_tokens=%d",
             LLM.model, LLM.location, LLM.thinking_budget, LLM.max_output_tokens)

    # Convert tables to text — history is handled separately via analyse_trends()
    data_section = _build_data_section(tables)
    _log_input_tokens(client, _reporter_message(client_name, data_section))

    # 1st Agent call: Reporter
    log.info("Reporter: drafting report (pass 1)")
    draft = _call_reporter(client, client_id, client_name, data_section)

    for attempt in range(1, _MAX_VERIFIER_PASSES + 1):
        # 2nd agent call: Validator
        log.info("Verifier: auditing draft (pass %d)", attempt)
        verdict = _call_verifier(client, client_id, client_name, data_section, draft)

        blockers = [i for i in verdict.get("issues", []) if i.get("severity") == "blocker"]
        log.info("Verifier verdict: %s | issues: %d | blockers: %d",
                 verdict["verdict"], len(verdict.get("issues", [])), len(blockers))

        if verdict["verdict"] == "approve":
            return verdict.get("rewritten_report") or draft

        if "rewritten_report" in verdict:
            log.info("Verifier provided inline rewrite — using it")
            return verdict["rewritten_report"]

        if attempt < _MAX_VERIFIER_PASSES:
            log.info("Reporter: revising report (pass %d)", attempt + 1)
            draft = _call_reporter(client, client_id, client_name, data_section,
                                   issues=verdict.get("issues", []))
        else:
            log.warning("Verifier still flagging after %d passes. Manual review required", _MAX_VERIFIER_PASSES)

    return draft


def analyse_stream(client_id: str, client_name: str, tables: dict[str, pd.DataFrame], kpi_history: list | None = None):
    """
    Streaming variant of analyse(). Streams the Reporter first pass in real time,
    then runs the Verifier loop non-streaming. Useful for local testing and for future chat AI assistant.
    """
    client = _make_client()
    log.info("LLM: model=%s location=%s thinking_budget=%d max_output_tokens=%d",
             LLM.model, LLM.location, LLM.thinking_budget, LLM.max_output_tokens)

    data_section = _build_data_section(tables)
    _log_input_tokens(client, _reporter_message(client_name, data_section))

    # Stream Reporter first pass
    log.info("Reporter: drafting report (pass 1, streaming)")
    chunks = []
    last_chunk = None
    for chunk in client.models.generate_content_stream(
        model=LLM.model,
        contents=_reporter_message(client_name, data_section),
        config=_reporter_config(client_id, client_name),
    ):
        if chunk.text:
            yield chunk.text
            chunks.append(chunk.text)
        last_chunk = chunk

    if last_chunk:
        _log_usage(last_chunk.usage_metadata, agent="Reporter")

    draft = "".join(chunks)

    # Verifier loop (non-streaming)
    for attempt in range(1, _MAX_VERIFIER_PASSES + 1):
        log.info("Verifier: auditing draft (pass %d)", attempt)
        verdict = _call_verifier(client, client_id, client_name, data_section, draft)

        blockers = [i for i in verdict.get("issues", []) if i.get("severity") == "blocker"]
        log.info("Verifier verdict: %s | issues: %d | blockers: %d",
                 verdict["verdict"], len(verdict.get("issues", [])), len(blockers))

        if verdict["verdict"] == "approve":
            rewritten = verdict.get("rewritten_report")
            if rewritten:
                yield "\n\n---\n* Verifier applied minor corrections*\n\n"
                yield rewritten
            return

        if "rewritten_report" in verdict:
            yield "\n\n---\n*[Verifier provided inline rewrite]*\n\n"
            yield verdict["rewritten_report"]
            return

        if attempt < _MAX_VERIFIER_PASSES:
            log.info("Reporter: revising report (pass %d)", attempt + 1)
            draft = _call_reporter(client, client_id, client_name, data_section,
                                   issues=verdict.get("issues", []))
            yield f"\n\n---\n*[Verifier requested revision - pass {attempt + 1}]*\n\n"
            yield draft
        else:
            log.warning("Verifier still flagging after %d passes - human review required", _MAX_VERIFIER_PASSES)

    # Trends section (non-streaming, appended after verifier)
    if kpi_history:
        log.info("Trends agent: running after verifier")
        trends = analyse_trends(client_id, client_name, kpi_history, draft)
        if trends:
            yield f"\n\n7. Trends\n{trends}"


def analyse_trends(
    client_id: str,
    client_name: str,
    kpi_history: list,
    today_report_markdown: str,
) -> str | None:
    """
    Call the Trends agent with historical KPI data and today's report.
    Returns a markdown bullet list (2-4 bullets) or None if history is too short.
    """
    if len(kpi_history) < 2:
        log.info("Trend analysis skipped: only %d day(s) of history", len(kpi_history))
        return None

    from src.history_manager import format_history_for_llm
    history_table = format_history_for_llm(kpi_history)
    if not history_table:
        return None

    system_prompt = _load_prompt(client_id, "trends.md").replace("{{client_name}}", client_name)
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=512,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    contents = f"{history_table}\n\n## Today's KPIs (for reference)\n{today_report_markdown[:1500]}"

    client = _make_client()
    log.info("Trends agent: analysing %d day(s) of history for %s", len(kpi_history), client_id)
    try:
        response = _generate_with_retry(client, contents=contents, config=config)
        _log_usage(response.usage_metadata, agent="Trends")
        return response.text.strip()
    except Exception as e:
        log.warning("Trend analysis failed: %s — skipping section", e)
        return None


def _build_data_section(tables: dict[str, pd.DataFrame]) -> str:
    sections = []
    for table_name, df in tables.items():
        sections.append(f"### {table_name}\n{_dataframe_to_text(df)}")
    return "\n\n".join(sections)
