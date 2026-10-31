-- 04 Map local item numbers to the global product classification, and region
-- codes to sales regions. A line whose item number is not in the map is held in
-- quarantine, never guessed: portfolio governance must map it first.

CREATE TABLE lines_mapped AS
SELECT e.*, m.product_id, rc.region_id
FROM lines_eur e
LEFT JOIN ref_code_map m
       ON m.business_unit = e.business_unit AND m.local_item_number = e.item_number
LEFT JOIN ref_region_codes rc ON rc.erp_region_code = e.customer_region;

INSERT INTO check_results
SELECT 'regions_known', count(*) = 0, count(*) || ' lines with an unknown region code'
FROM lines_mapped WHERE region_id IS NULL;

INSERT INTO check_results
SELECT 'quantities_positive', count(*) = 0, count(*) || ' lines with a quantity of zero or less'
FROM lines_mapped WHERE quantity <= 0;

INSERT INTO check_results
SELECT 'amounts_not_negative', count(*) = 0, count(*) || ' lines with a negative amount or cost'
FROM lines_mapped WHERE amount_eur < 0 OR cost_eur < 0;

INSERT INTO check_results
SELECT 'products_known', count(*) = 0, count(*) || ' mapped lines whose product is not in dim_product'
FROM lines_mapped l
LEFT JOIN read_csv('{products}', header = true, all_varchar = true) p USING (product_id)
WHERE l.product_id IS NOT NULL AND p.product_id IS NULL;
