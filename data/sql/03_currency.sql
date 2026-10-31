-- 03 Convert every line to euros.
-- A missing currency code falls back to the business unit's ledger currency and
-- is logged (04). Kronor convert at the ECB monthly average rate, rounded to the cent.

CREATE TABLE lines_eur AS
SELECT
    l.*,
    b.site_id,
    coalesce(l.currency_code, b.ledger_currency) AS currency,
    l.currency_code IS NULL AS currency_defaulted,
    CASE WHEN coalesce(l.currency_code, b.ledger_currency) = 'EUR' THEN l.amount
         ELSE CAST(round(CAST(l.amount AS DOUBLE) / r.rate, 2) AS DECIMAL(18, 2)) END AS amount_eur,
    CASE WHEN coalesce(l.currency_code, b.ledger_currency) = 'EUR' THEN l.cost
         ELSE CAST(round(CAST(l.cost AS DOUBLE) / r.rate, 2) AS DECIMAL(18, 2)) END AS cost_eur,
    r.rate
FROM lines_unique l
LEFT JOIN ref_bu b USING (business_unit)
LEFT JOIN ref_rates r
       ON r.date_key = l.date_key AND r.currency = coalesce(l.currency_code, b.ledger_currency);

INSERT INTO check_results
SELECT 'business_units_known', count(*) = 0, count(*) || ' lines from unknown business units'
FROM lines_eur WHERE site_id IS NULL;

INSERT INTO check_results
SELECT 'exchange_rates_found', count(*) = 0, count(*) || ' non-euro lines with no ECB rate'
FROM lines_eur WHERE currency <> 'EUR' AND rate IS NULL;

INSERT INTO check_results
SELECT 'currency_matches_ledger', count(*) = 0, count(*) || ' lines in a currency other than the ledger currency'
FROM lines_eur e JOIN ref_bu b USING (business_unit)
WHERE e.currency <> b.ledger_currency;
