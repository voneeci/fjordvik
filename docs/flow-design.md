# Flow design

Two Power Automate cloud flows replace the manual monthly routine of collecting site
spreadsheets, checking them by eye and copying numbers into a central file.

| Flow | Trigger | Does |
| --- | --- | --- |
| **Fjordvik - Site file intake** | A file is uploaded to `Site submissions/Incoming` | Checks rules R1 to R10; loads accepted rows with tCO2e worked out; rejects the rest with an email; logs every run |
| **Fjordvik - Monthly submission reminder** | Day 5 of each month, 09:00 Helsinki time | Emails every site with no accepted file for the previous month, and sends the data owner a summary |

Every action is renamed to say what it does (for example "Get last year's rows" rather
than "Get items 2"), so the run history reads like a checklist. The rules themselves are in
[intake-rules.md](intake-rules.md); the lists and folders in
[sharepoint-lists.md](sharepoint-lists.md); the statuses in [run-statuses.md](run-statuses.md).

## Flow 1: Site file intake

### Trigger

**SharePoint: When a file is created (properties only)**, site *Fjordvik Sustainability*,
library *Site submissions*, folder `/Incoming`.

Not "When a file is created in a folder": Microsoft now marks that trigger deprecated and
says it "may not work as expected". Files **moved** into the folder do not fire the
trigger, because moving keeps the file's created and modified times, so test files must be
**uploaded**. Sources: [SharePoint connector reference](https://learn.microsoft.com/en-us/connectors/sharepointonline/)
and [SharePoint triggers guidance](https://learn.microsoft.com/en-us/sharepoint/dev/business-apps/power-automate/sharepoint-connector-actions-triggers),
read 12 October 2026.

### Steps

| # | Action (renamed) | Connector action | What it does |
| --- | --- | --- | --- |
| 1 | Initialise errors | Initialize variable (array) | Collects failed rules. Variables can only be created at the top level, so this comes first |
| 2 | Read file name parts | Compose ×3 | `site_id` = the text before `_`; `month` = the text after it, without `.xlsx`; month keys for this month, last month and last year |
| 3 | **Try** | Scope | Everything below runs inside it, so any technical failure is caught |
| 3.1 | Read the submission | Excel Online (Business): List rows present in a table | Reads table `Submission` from the uploaded file |
| 3.2 | Get the site | SharePoint: Get items (Sites, filter `site_id eq '<site>'`) | Unknown site: R2. Gives the country and contact email |
| 3.3 | Get sources | SharePoint: Get items (Sources) | Units for R5 |
| 3.4 | Get factors | SharePoint: Get items (EmissionFactors, filter `country eq '<country>'`) | Factor for each source |
| 3.5 | Check not already loaded | SharePoint: Get items (Emissions, filter on `date_key` and `site_id`) | Any rows: R10 |
| 3.6 | Get last month's rows | SharePoint: Get items (Emissions, last month's key) | The sources the site reports: R4 and R8 |
| 3.7 | Get last year's rows | SharePoint: Get items (Emissions, same month last year) | Amounts for R9 |
| 3.8 | Check columns | Condition | R1: all five columns present in the first row |
| 3.9 | Check each row | Apply to each (sequential) | Per row: R2, R3, R4, R5, R6 (`isFloat`, then not negative), R9 (ratio to last year, refrigerant exempt). Each failure is appended to `errors` |
| 3.10 | Check duplicates and gaps | Select + Compose + Filter array | R7: `length(sourceIds)` against `length(union(sourceIds, sourceIds))`; R8: last month's sources missing from the file |
| 3.11 | Accept or reject | Condition on `length(variables('errors'))` | See the two branches below |
| 4 | **Catch** | Scope, run after Try *has failed* or *has timed out* | Deletes any Emissions rows this run created (by `run_id`), logs **Failed**, emails the data owner. The file stays in `Incoming` |

**Accepted branch:** Apply to each row: Create item in **Emissions** with the factor from
step 3.4 and `tco2e` = amount × factor ÷ 1,000, rounded to 6 decimals with
`formatNumber`; Create item in **IntakeLog** (Accepted, rows, tCO2e); Move file to
`/Processed`.

**Rejected branch:** Create item in **IntakeLog** (Rejected, the errors joined one per
line); Send an email (V2) to the site contact with the same list; Move file to `/Rejected`.

### Design decisions

- **Whole file or nothing.** No rows are written until every rule has passed, and the Catch
  scope removes rows a failed run created. A site-month is complete or absent, never half
  loaded.
- **Safe to rerun.** R10 refuses a site-month that is already loaded.
- **Sequential loop.** Apply to each runs one item at a time by default, and Microsoft says
  variables inside it give predictable results only when it runs sequentially, so
  concurrency stays off ([Apply to each](https://learn.microsoft.com/en-us/power-automate/apply-to-each)).
- **Excel file lock.** Microsoft notes that "An Excel file may be locked for an update or
  delete up to 6 minutes since the last use of the connector"
  ([Excel Online (Business) connector](https://learn.microsoft.com/en-us/connectors/excelonlinebusiness/)).
  The Move file actions therefore get a retry policy (exponential, 4 retries). If moves
  still fail in testing, the fallback is to tag the file with a status column instead of
  moving it.
- **Small numbers of rows.** A file has at most 8 rows, well under the Excel connector's
  default of 256 returned rows. The Emissions list starts at 1,379 rows and grows by 43 a
  month, under the 5,000-item limit for Get items on Microsoft 365 plans; index the
  `date_key` and `site_id` columns before it grows.
- **Standard connectors only.** SharePoint, Excel Online (Business) and Office 365
  Outlook are standard connectors, included with Microsoft 365 licences, so no premium
  licence is needed.

### To check during the first build

These could not be confirmed from Microsoft's documentation, so the first test run checks
them with a Compose action and the run history:

1. Whether List rows returns `activity_amount` as text or a number, and with which decimal
   mark. The flow converts with `float()`; if the tenant's locale returns a comma, use
   `float(value, 'fi-FI')` or set the workbook's number format.
2. Whether the trigger fires for a file uploaded straight into `Incoming` from a browser
   (expected) and for a copied file (unconfirmed).
3. That `isFloat()` is available in the expression editor for rule R6. If not, R6 uses
   `float()` inside its own Scope and treats a failure as a non-number.

## Flow 2: Monthly submission reminder

| # | Action (renamed) | Connector action | What it does |
| --- | --- | --- | --- |
| 1 | Every month on day 5 | Recurrence (monthly, day 5, 09:00, time zone FLE Standard Time) | Starts the run |
| 2 | Month to check | Compose | Previous month as `yyyy-MM`, from `addDays(startOfMonth(utcNow()), -1)`. For the December 2025 demo, a manual run sets it to `2025-12` |
| 3 | Get sites | SharePoint: Get items (Sites) | All six sites and contacts |
| 4 | Get accepted files | SharePoint: Get items (IntakeLog, filter `month eq '<month>' and status eq 'Accepted'`) | Sites that are done |
| 5 | Sites still missing | Filter array (sites whose `site_id` is not among the accepted ones) | The list to chase |
| 6 | Email each missing site | Apply to each + Send an email (V2) | Asks for the file, naming the month and the upload folder |
| 7 | Summary to the data owner | Send an email (V2) | One email: which sites are missing, or that all six are in |

Expected results for the demo, from `expected/expected_results.json`: with the clean files
loaded, no site is missing; with the problem files, Tartu (sent nothing) and the three
rejected sites (Tampere, Oulu, Gothenburg) are chased.

## Source control

Microsoft recommends putting flows in a **solution** and exporting the solution, rather
than the older "Export package (.zip)", which it now labels legacy. A solution export
stores each flow as JSON, and `pac solution unpack` turns the export into readable files
for git ([Export a solution](https://learn.microsoft.com/en-us/power-automate/export-flow-solution),
[pac solution](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/solution)).
Solutions need a Dataverse database in the environment; if the trial's default environment
has none, the legacy package export is the fallback. The exported flows go in `flows/`.
