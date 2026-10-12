# SharePoint lists and folders

Everything lives in one SharePoint site, **Fjordvik Sustainability**. The column names
match the shared Fjordvik schema, so the same names run through the CSV files, the Power BI
model, the MCP connector and these lists.

## Document library: Site submissions

| Folder | Holds | Who writes it |
| --- | --- | --- |
| `Incoming` | New monthly files from the sites, named `<site_id>_<yyyy-mm>.xlsx` | Site contacts |
| `Processed` | Files the intake flow accepted | The intake flow |
| `Rejected` | Files the intake flow rejected | The intake flow |

Each file holds one Excel table named `Submission` with the columns `site_id`, `month`,
`source_id`, `activity_amount`, `unit` (see [intake-rules.md](intake-rules.md)).

## Lists

**Reference lists** (read by the flows, changed only by the data owner):

| List | Columns (type) | Rows | Seed workbook |
| --- | --- | --- | --- |
| Sites | site_id (text, unique), site_name (text), country (text), site_type (text), contact_email (text) | 6 | `sharepoint/seed/Sites.xlsx` |
| Sources | source_id (text, unique), source_name (text), scope (number), category (text), unit (text) | 8 | `sharepoint/seed/Sources.xlsx` |
| EmissionFactors | source_id (text), country (text), emission_factor (number, kg CO2e per unit, illustrative) | 24 (8 sources, 3 countries) | `sharepoint/seed/EmissionFactors.xlsx` |

`contact_email` is left blank in the seed. In the demo, fill it with your own trial
account's address so every email comes to you; a real deployment holds each site's
contact.

**Data lists** (written by the intake flow):

| List | Columns (type) | Rows at start | Seed workbook |
| --- | --- | --- | --- |
| Emissions | date_key (number), site_id (text), source_id (text), activity_amount (number), unit (text), emission_factor (number), tco2e (number), submitted_file (text), run_id (text) | 1,379 (January 2023 to November 2025) | `sharepoint/seed/Emissions.xlsx` |
| IntakeLog | run_id (text), file_name (text), site_id (text), month (text), status (choice: Accepted, Rejected, Failed), rows_loaded (number), tco2e_loaded (number), errors (multiple lines of text), processed_at (date and time) | 0 | none |

What the IntakeLog statuses do, and why changing one by hand does nothing, is in
[run-statuses.md](run-statuses.md).

## Why lists, not an Excel workbook

A SharePoint list takes one row at a time from several flow runs without locking a file,
keeps version history per row, and can be read by Power BI. An Excel workbook would lock
while a flow writes to it, and two sites uploading at once would collide.
