-- 02 Remove duplicate lines.
-- A line is identified by its business unit and line id. When an extract is
-- re-sent, the same lines arrive twice; the copy from the earlier file is kept.

CREATE TABLE stg_ranked AS
SELECT *, row_number() OVER (PARTITION BY business_unit, line_id ORDER BY source_file) AS copy_no
FROM stg_lines;

CREATE TABLE lines_unique AS SELECT * EXCLUDE (copy_no) FROM stg_ranked WHERE copy_no = 1;
CREATE TABLE lines_duplicate AS SELECT * EXCLUDE (copy_no) FROM stg_ranked WHERE copy_no > 1;

-- A duplicate is only safe to drop if it is an exact copy. Two different lines
-- with one id is a conflict for the ERP team, not something to resolve here.
INSERT INTO check_results
SELECT 'duplicates_are_exact_copies', count(*) = 0, count(*) || ' conflicting line ids'
FROM lines_duplicate d
JOIN lines_unique u USING (business_unit, line_id)
WHERE (d.item_number, d.customer_region, d.quantity, d.amount, d.cost, d.period_name)
   IS DISTINCT FROM (u.item_number, u.customer_region, u.quantity, u.amount, u.cost, u.period_name);
