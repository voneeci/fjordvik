# Run statuses: what each one does

The intake flow writes one row to the **IntakeLog** SharePoint list for every file it
handles. This page explains what each status means, what the flow has already done when it
sets it, and what happens if someone changes it by hand. It is written for the IT team and
the data owner.

## The statuses

| Status | Set when | What the flow has done | What the site has to do |
| --- | --- | --- | --- |
| **Accepted** | Every rule (R1 to R10) passed | Added one row per source to the **Emissions** list, with the emission factor looked up and tCO2e worked out; moved the file to the **Processed** folder | Nothing |
| **Rejected** | One or more rules failed | Added **nothing** to the Emissions list; moved the file to the **Rejected** folder; emailed the site contact the failed rules and row details | Fix the file and upload it to **Incoming** again |

There is no partial load: a file is accepted whole or rejected whole. That keeps every
site-month either complete or absent, never half there.

## What changing a status by hand does

**Nothing.** The IntakeLog is a record of what happened, not a switch. Changing
**Rejected** to **Accepted** does not load any rows, and changing **Accepted** to
**Rejected** does not remove any. Change the data, not the log:

| You want to | Do this | Why |
| --- | --- | --- |
| Load a rejected file | Correct the file and upload it to **Incoming** again | The flow checks it again from the start; a new log row records the result |
| Correct a month that was already accepted | A data owner deletes that site-month's rows from the Emissions list, then the corrected file is uploaded to **Incoming** | Rule R10 refuses a site-month that is already loaded, so a month can never be loaded twice by accident |
| Stop the reminder email for a site | Upload an accepted file for the month | The reminder flow looks for an **Accepted** log row for the site and month |

## Reading the log

- One site and month can have several rows: for example a **Rejected** row, then an
  **Accepted** row after the fix. The latest **Accepted** row is the one that loaded data.
- The `errors` column lists each failed rule with its detail, in the same words as the
  email to the site.
- The `run_id` column links the log row to the flow run, for checking the run history in
  Power Automate.
