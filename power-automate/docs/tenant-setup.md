# Building the flows in a trial tenant

A step-by-step guide for building and testing the two flows in a Microsoft 365 trial.
Screen labels change between releases: where a button has moved, look for the nearest
match and note the difference in the run log at the end of this page.

## Part A: the trial (you do this)

A personal Microsoft account (Hotmail, Outlook.com) **cannot** run Power Automate cloud
flows: Microsoft's FAQ says sign-in needs a work or school address and "will no longer
support personal email accounts, such as gmail.com or outlook.com"
([Power Automate FAQ](https://learn.microsoft.com/en-us/power-automate/frequently-asked-questions),
read 12 October 2026). A new trial creates a work account for you.

**Use the Microsoft 365 Business Basic one-month trial.** It includes SharePoint, Exchange
mail and Power Automate for Microsoft 365 (cloud flows)
([plans and pricing, Finland](https://www.microsoft.com/fi-fi/microsoft-365/business/microsoft-365-plans-and-pricing),
read 12 October 2026).

> **Card and billing.** The trial asks for a payment card and turns into a paid
> subscription (about 6,07 € per user per month, excluding VAT, on the Finnish page) unless
> recurring billing is switched off. Switch it off on the day you sign up, in the billing
> section of the Microsoft 365 admin centre, following Microsoft's
> [Try or buy a Microsoft 365 subscription](https://learn.microsoft.com/en-us/microsoft-365/commerce/try-or-buy-microsoft-365)
> page (the menu path was not checked for this guide).
> The trial lasts 30 days: plan the build and the export inside that window.

1. Start the Business Basic trial from the Finnish plans page ("Kokeile maksutta").
2. Choose a company name such as *Fjordvik Demo*; the account becomes
   `you@<name>.onmicrosoft.com`. Store the password in your password manager, never in the
   repository.
3. Switch off recurring billing straight away.
4. Sign in at `make.powerautomate.com` and `<name>.sharepoint.com` to check both open.

## Part B: SharePoint (about 30 minutes)

1. Create a team site named **Fjordvik Sustainability**.
2. In **Documents**, or a new library named **Site submissions**, create the folders
   `Incoming`, `Processed` and `Rejected`.
3. Create each list **from Excel** using the workbooks in `sharepoint/seed/`: **Sites**,
   **Sources**, **EmissionFactors** and **Emissions** (1,379 rows, under the 5,000 rows
   Microsoft's "from Excel" page states). Check each column type after import: numbers as
   *Number*, ids as *Single line of text*
   ([Create a list based on a spreadsheet](https://support.microsoft.com/en-us/office/create-a-list-based-on-a-spreadsheet-380cfeb5-6e14-438e-988a-c2b9bea574fa)).
4. Create the **IntakeLog** list by hand with the columns in
   [sharepoint-lists.md](sharepoint-lists.md); `status` is a Choice column with
   Accepted, Rejected and Failed.
5. In **Sites**, fill `contact_email` with your own trial address for all six sites.
6. In **Emissions** list settings, index the `date_key` and `site_id` columns.

## Part C: the intake flow (about 2 hours the first time)

Build **Fjordvik - Site file intake** in Power Automate, following the step table in
[flow-design.md](flow-design.md). Rename every action as you add it.

Two expressions worth copying exactly:

```text
site id:   first(split(triggerOutputs()?['body/{FilenameWithExtension}'], '_'))
month:     replace(last(split(triggerOutputs()?['body/{FilenameWithExtension}'], '_')), '.xlsx', '')
```

Before building the rules, run the flow once with a single **Compose** after
"Read the submission" and upload `intake/clean/FI02_2025-12.xlsx`. In the run history,
check how `activity_amount` comes back (text or number, which decimal mark). This settles
the open points listed in flow-design.md.

## Part D: test runs

Run these in order and record each result in the table below. Upload files from your
computer into `Incoming`; do not move them in from another folder (moved files don't start
the flow).

| # | Upload | Expected (from `expected/expected_results.json`) |
| --- | --- | --- |
| 1 | `intake/problems/FI01_2025-12.xlsx` | Rejected: R5, R9. Email lists both. File in Rejected |
| 2 | `intake/problems/FI03_2025-12.xlsx` | Rejected: R8 |
| 3 | `intake/problems/SE01_2025-12.xlsx` | Rejected: R7 |
| 4 | `intake/problems/FI02_2025-12.xlsx` | Accepted: 5 rows |
| 5 | `intake/problems/EE01_2025-12.xlsx` | Accepted: 8 rows |
| 6 | Run the reminder flow by hand for `2025-12` | Chases EE02, FI01, FI03, SE01 |
| 7 | `intake/clean/FI01`, `FI03`, `SE01`, `EE02` (the fixed files) | Accepted |
| 8 | `intake/clean/FI02_2025-12.xlsx` again | Rejected: R10 (already loaded) |
| 9 | Run the reminder flow again | Nobody missing |

After run 9, export the Emissions list to Excel and save it as
`evidence/emissions_after_december.xlsx`. The test
`tests/test_evidence.py` (added with the evidence) compares it with fjordvik-data: all
1,422 rows must match.

## Part E: the reminder flow

Build **Fjordvik - Monthly submission reminder** from the second table in
[flow-design.md](flow-design.md). Set the Recurrence time zone to Helsinki (FLE Standard
Time). For the demo, give the "Month to check" Compose a manual value of `2025-12`.

## Part F: export into this repository

1. Add both flows to a solution named **Fjordvik Intake** and export it (unmanaged).
   If solutions are unavailable in the trial environment, use the legacy **Export >
   Package (.zip)** instead.
2. Put the zip in `flows/` and, if you have the Power Platform CLI, unpack it:
   `pac solution unpack --zipfile flows/FjordvikIntake.zip --folder flows/src`.
3. Take screenshots of each flow's designer view and of one Accepted and one Rejected run;
   save them in `docs/images/`.
4. Check the export contains no passwords, keys or personal addresses before committing.
   Connection references in a solution hold no secrets, but email addresses in the flow
   steps do.

## Run log

| Date | Step | Result | Note |
| --- | --- | --- | --- |
| | | | |
