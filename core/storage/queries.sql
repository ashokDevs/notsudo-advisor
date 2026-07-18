-- name: get_advisory_by_id
SELECT * FROM advisories WHERE id = $1;

-- name: insert_advisory
INSERT INTO advisories (id, source_id, package_name, affected_ranges, summary, details, embedding)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (source_id) DO UPDATE SET
    package_name = EXCLUDED.package_name,
    affected_ranges = EXCLUDED.affected_ranges,
    summary = EXCLUDED.summary,
    details = EXCLUDED.details,
    embedding = EXCLUDED.embedding;
