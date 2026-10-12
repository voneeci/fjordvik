# Intake rules

Every site file passes through the same ten rules. The flow applies them with Power
Automate actions; `intake_rules.py` holds the same rules in plain Python, and the tests
check that they give the expected result for every file in `intake/`. A file that fails
any rule is rejected whole: no row from it is loaded.

| Rule | Checks | Why | Planted example |
| --- | --- | --- | --- |
| R1 | The table has the columns `site_id`, `month`, `source_id`, `activity_amount` and `unit` | Nothing else can be read reliably if the layout changed, so the other rules are skipped | |
| R2 | Every row's `site_id` is the site the file belongs to (from the file name) | Stops one site's numbers landing under another site | |
| R3 | Every row is for the reporting month | Stops last month's file being loaded again as this month | |
| R4 | Every `source_id` is one this site reported last month | A head office has no natural gas; a new source needs a decision first | |
| R5 | Every `unit` is the unit for that source | A factor per kWh applied to MWh is wrong by a factor of 1,000 | Tampere: electricity in MWh |
| R6 | Every `activity_amount` is a number of zero or more | Text and negative amounts can't be summed | |
| R7 | No source appears twice | A duplicate row double-counts emissions | Gothenburg: diesel twice |
| R8 | Every source the site reported last month is present | A missing row looks like zero emissions | Oulu: no district heating |
| R9 | Each amount is between half and double the same month last year (refrigerant exempt) | Catches slips such as wrong units or extra zeros that pass the other rules | Tampere: 0.001 times last year |
| R10 | This site and month are not already in the central list | Makes the flow safe to rerun: a month is never loaded twice | |

**Missing submissions** (the reminder flow): a site with no accepted file for the month
by day 5. In the problem set, Tartu sends nothing, and the three rejected sites also count
until they send a corrected file.

## The R9 range is a business rule

Half to double is a design choice, not a published figure. It is wide enough for normal
seasonal change and growth, and narrow enough to catch a unit slip. Refrigerant is exempt
because top-ups are zero in most months. A real deployment would tune the range per source
with the people who know the sites.

## Expected results

`expected/expected_results.json` lists, for every file in `intake/clean` and
`intake/problems`, the status, the rules that fail, the failure details, the rows to load
and their tCO2e. When the flows run in the tenant, their run log must match it.
