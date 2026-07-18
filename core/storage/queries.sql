-- name: get_advisory_by_id
SELECT * FROM advisories WHERE id = $1;

-- name: insert_advisory
INSERT INTO advisories (id, source_id, package_name, affected_ranges, summary, details)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (id) DO UPDATE SET
    affected_ranges = EXCLUDED.affected_ranges,
    summary = EXCLUDED.summary,
    details = EXCLUDED.details;
