-- raw_table.sql
-- Generic full-table read. No aggregations, filters, LIMIT, or transforms.
-- Placeholders are validated against CLIENT_CONFIG before interpolation —
-- never populated from external input directly.
--
-- Usage: format(project=..., dataset=..., table=...)

SELECT *
FROM `{project}.{dataset}.{table}`
