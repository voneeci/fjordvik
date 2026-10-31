-- 05 Publish the clean sales, the classification and the issue list.

CREATE TABLE fact_sales AS
SELECT date_key, site_id, product_id, region_id,
       sum(quantity) AS units,
       sum(amount_eur) AS net_sales_eur,
       sum(cost_eur) AS cost_of_sales_eur,
       sum(amount_eur) - sum(cost_eur) AS margin_eur
FROM lines_mapped
WHERE product_id IS NOT NULL
GROUP BY ALL
ORDER BY date_key, site_id, product_id, region_id;

CREATE TABLE dim_product_code AS
SELECT business_unit, local_item_number, product_id
FROM ref_code_map
ORDER BY business_unit, local_item_number;

-- One row per issue for the data owner: what happened, how much, what to do.
CREATE TABLE issues_raw AS
SELECT d.date_key, b.site_id, d.business_unit, 'Duplicate lines' AS issue_type,
       'File ' || min(d.source_file) || ' repeats lines already received' AS detail,
       count(*) AS line_count,
       sum(CASE WHEN b.ledger_currency = 'EUR' THEN d.amount
                ELSE CAST(round(CAST(d.amount AS DOUBLE) / r.rate, 2) AS DECIMAL(18, 2)) END) AS amount_eur,
       'Removed by rule' AS status,
       'Ask the ERP team why the extract was sent twice' AS action
FROM lines_duplicate d
JOIN ref_bu b USING (business_unit)
LEFT JOIN ref_rates r ON r.date_key = d.date_key AND r.currency = b.ledger_currency
GROUP BY d.date_key, b.site_id, d.business_unit
UNION ALL
SELECT date_key, site_id, business_unit, 'Missing currency code',
       'Lines had no currency code; the ledger currency ' || min(currency) || ' was applied',
       count(*), sum(amount_eur), 'Corrected by rule',
       'Ask the business unit to fix the currency code at source'
FROM lines_mapped WHERE currency_defaulted
GROUP BY date_key, site_id, business_unit
UNION ALL
SELECT date_key, site_id, business_unit, 'Unmapped item number',
       'Local item number ' || item_number || ' is not in the global product classification',
       count(*), sum(amount_eur), 'Quarantined',
       'Portfolio governance to map ' || item_number || ' to a global product'
FROM lines_mapped WHERE product_id IS NULL
GROUP BY date_key, site_id, business_unit, item_number;

CREATE TABLE fact_data_issue AS
SELECT row_number() OVER (ORDER BY date_key, site_id, issue_type, detail) AS issue_id, *
FROM issues_raw
ORDER BY issue_id;
