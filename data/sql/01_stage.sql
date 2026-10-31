-- 01 Stage the extract and the reference lists.
-- The runner has already checked every ZIP against its manifest (SHA-256) and
-- unpacked the CSV files into the staging folder. Everything is read as text,
-- then typed here, so a malformed number fails loudly instead of being guessed.

CREATE TABLE stg_lines AS
SELECT
    BUSINESS_UNIT AS business_unit,
    PERIOD_NAME AS period_name,
    CAST(replace(PERIOD_NAME, '-', '') || '01' AS INTEGER) AS date_key,
    ORDER_NUMBER AS order_number,
    LINE_ID AS line_id,
    ITEM_NUMBER AS item_number,
    CUSTOMER_REGION AS customer_region,
    CAST(QUANTITY AS INTEGER) AS quantity,
    NULLIF(CURRENCY_CODE, '') AS currency_code,
    CAST(EXTENDED_AMOUNT AS DECIMAL(18, 2)) AS amount,
    CAST(EXTENDED_COST AS DECIMAL(18, 2)) AS cost,
    parse_filename(filename) AS source_file
FROM read_csv('{staging}', header = true, all_varchar = true, filename = true);

CREATE TABLE ref_code_map AS
SELECT * FROM read_csv('{code_map}', header = true, all_varchar = true);

CREATE TABLE ref_region_codes AS
SELECT * FROM read_csv('{region_codes}', header = true, all_varchar = true);

CREATE TABLE ref_bu AS
SELECT * FROM read_csv('{business_units}', header = true, all_varchar = true);

-- ECB monthly average reference rates, kronor per euro (cited in data/reference).
CREATE TABLE ref_rates AS
SELECT CAST(date_key AS INTEGER) AS date_key, currency, CAST(sek_per_eur AS DOUBLE) AS rate
FROM read_csv('{rates}', header = true, all_varchar = true);

CREATE TABLE check_results (check_name VARCHAR, passed BOOLEAN, detail VARCHAR);
