# Dataset certification checklist

In the Power BI Service, a **certified** semantic model is one the organisation has
checked and recommends. Certification is granted by people the tenant administrator
nominates; this checklist is what they would review first. Fjordvik is a portfolio
model, so it is not published or certified; the checklist shows what certification
would require and where the evidence for each item is.

| # | Requirement | Evidence in this repository | Status |
| --- | --- | --- | --- |
| 1 | A named business owner and a named technical owner | README, "Ownership" | Fictional owners named |
| 2 | Source data is identified and pinned to a version | The shared `data/tables` folder of the repository, at a known git commit; SHA-256 checksums in `data/tables/manifest.json`, checked by `tests/test_data.py` | Done |
| 3 | Every measure reconciles with an independent calculation | `tests/test_measures_live.py`: 68 cases against plain Python sums | Run before each release |
| 4 | Totals reconcile across routes inside the model | `Reconciliation Difference (tCO2e)` measure: stored tCO2e against activity times factor | Shown on the Data quality page |
| 5 | Naming conventions followed | `docs/naming-conventions.md`, checked by `tests/test_model_files.py` | Done |
| 6 | Every measure has a description, format string and display folder | `tests/test_model_files.py` | Done |
| 7 | Row-level security defined and tested | Three country roles; RLS cases in `tests/test_measures_live.py` | Done |
| 8 | No hard-coded rates or factors in DAX | `tests/test_model_files.py` | Done |
| 9 | Model is under version control as text | Power BI Project (PBIP) with Tabular Model Definition Language (TMDL) files in git | Done |
| 10 | Refresh works from source with no manual steps | Refresh in Power BI Desktop after setting the `DataFolder` parameter | Check after each data release |
| 11 | Known limitations documented | README, "Limitations" | Done |
| 12 | Data is synthetic and factors are illustrative | README banner, report footer | Done |

## How to certify in the Power BI Service (for reference)

Source: Microsoft Learn, [Endorse Fabric and Power BI items](https://learn.microsoft.com/en-us/fabric/fundamentals/endorsement-promote-certify)
(page last updated 26 January 2025, read 12 October 2026).

1. Publish the model to a workspace.
2. Only reviewers authorised by the Fabric administrator can certify, and they also need
   write permission on the model. Anyone else requests certification through the link
   in the model's endorsement settings.
3. The reviewer checks the evidence above, opens the semantic model's settings, expands
   **Endorsement**, selects **Certified** and applies.
4. Re-review after any change to measures, roles or sources.

Promotion is the lighter step: any owner, or anyone with write permission, can mark a
model **Promoted** to say it is worth reusing, without a formal review.
