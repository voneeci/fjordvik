-- 06 Reconcile to finance. For every site-month, clean sales plus quarantined
-- lines must equal the revenue finance booked, to the cent. A difference means
-- lines are missing or counted twice, and nothing is published.

CREATE TABLE reconciliation AS
WITH finance AS (
    SELECT CAST(date_key AS INTEGER) AS date_key, site_id,
           CAST(revenue_eur AS DECIMAL(18, 2)) AS revenue_eur
    FROM read_csv('{finance}', header = true, all_varchar = true)
    WHERE CAST(revenue_eur AS DECIMAL(18, 2)) > 0
),
sales AS (SELECT date_key, site_id, sum(net_sales_eur) AS sales_eur FROM fact_sales GROUP BY ALL),
held AS (
    SELECT date_key, site_id, sum(amount_eur) AS quarantined_eur
    FROM fact_data_issue WHERE status = 'Quarantined' GROUP BY ALL
)
SELECT coalesce(f.date_key, s.date_key) AS date_key,
       coalesce(f.site_id, s.site_id) AS site_id,
       coalesce(f.revenue_eur, 0) AS revenue_eur,
       coalesce(s.sales_eur, 0) AS sales_eur,
       coalesce(h.quarantined_eur, 0) AS quarantined_eur,
       coalesce(f.revenue_eur, 0) - coalesce(s.sales_eur, 0) - coalesce(h.quarantined_eur, 0)
           AS difference_eur
FROM finance f
FULL OUTER JOIN sales s USING (date_key, site_id)
LEFT JOIN held h ON h.date_key = coalesce(f.date_key, s.date_key)
                AND h.site_id = coalesce(f.site_id, s.site_id);

INSERT INTO check_results
SELECT 'reconciles_to_finance', count(*) = 0, count(*) || ' site-months that do not reconcile'
FROM reconciliation WHERE difference_eur <> 0;
