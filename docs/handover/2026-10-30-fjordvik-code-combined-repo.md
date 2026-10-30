# Handover: Fjordvik, new laptop and combined repository
Date: 2026-10-30   Chat: Fjordvik code chat   Read from: git 9ca72bc (voneeci/fjordvik, main)

## Done
- 25 October 2026, new laptop (BIGRIG): rebuilt each project's virtual environment,
  fixed the old user-folder paths, and let `powerbi/scripts/run_dax_table.ps1` find
  Power BI Desktop's Program Files install. Raw test output is in each folder's
  `evidence/pytest-new-laptop-2026-10-25.txt`.
- 30 October 2026: combined the four repositories into private
  https://github.com/voneeci/fjordvik with `git subtree` (no squash), so all 15 original
  commit hashes still resolve. The folders are `data`, `mcp`, `powerbi` and
  `power-automate`.
- 9ca72bc:
  - `sync_data.py` in mcp, powerbi and power-automate defaults to `..\data`;
  - the Power BI `DataFolder` parameter points at
    `C:\Users\reece\Projects\fjordvik\powerbi\data`;
  - the READMEs, CLAUDE.md files and example configs name the new folders;
  - new root `README.md` and `CLAUDE.md`;
  - `powerbi/.gitattributes` pins `docs/data-dictionary.md` to Unix line endings (LF).
    Git for Windows checks text out with Windows line endings (CRLF), and the
    data-dictionary test compares bytes, so every fresh Windows clone failed it before.
    The test is unchanged.
- The four old GitHub repositories have a "moved" line in their READMEs and are archived.
  The old local clones are in `C:\Users\reece\Projects\done\`.
- Knowledge inbox note: `raw/inbox/2026-10-30-fjordvik-combined-repo.md` (not yet
  processed).

## Checked
- `python -m pytest -q` in each folder's own virtual environment, 30 October 2026. Raw
  output is in `<folder>/evidence/pytest-combined-repo-2026-10-30.txt`:
  - data: 24 passed;
  - mcp: 48 passed;
  - powerbi: 69 passed, 31 skipped (Power BI Desktop closed);
  - power-automate: 26 passed.
- `git status` is clean, and local and origin are both at 9ca72bc.
- `gh repo view` showed all four old repositories archived and private.
- Not checked: the 31 live Power BI tests, and whether the new `DataFolder` path loads
  in Desktop.

## Decisions (Reece, in the question box)
- One repository, `voneeci/fjordvik`, private, with folders data, mcp, powerbi and
  power-automate (30 October 2026).
- Each consumer keeps its own checksum-verified data copy for now (30 October 2026).
- Old repositories archived with a pointer, and their local clones moved to `done`
  (30 October 2026).
- Power Automate: wait for a role that asks for it, then build in a 30-day trial tenant
  (25 October 2026).

## Open
- Reece, by hand: register the Claude Desktop connector from
  `C:\Users\reece\Projects\fjordvik\mcp` (Claude Desktop fully quit, then
  `C:\Users\reece\AppData\Local\Python\pythoncore-3.14-64\python.exe scripts\add_to_claude_desktop.py`).
- Three READMEs say "re-pin to the fjordvik-data `v1.0.0` tag", but no tag exists
  (`git tag -l` is empty). In one repository, a tag versus one shared data copy is
  Reece's call.
- The wiki page `wiki/projects/fjordvik-portfolio.md` (26 October 2026) still describes
  four repositories. The inbox note covers this for the curator.
- Rule files changed: the CLAUDE.md files changed in 9ca72bc. This chat must be replaced
  by a fresh one, which this note is for.

## Project next steps (tell Reece these first)
1. Run the 31 live Power BI tests with Desktop open. This also proves that the new
   `DataFolder` path loads.
2. Reece registers the Claude Desktop connector from the new `mcp` folder.
3. Reece decides how the folders share data: tag `v1.0.0` and pin to it, or one shared
   copy, or leave the copies as they are.
4. Power Automate: build in a trial tenant when a role asks for it (Reece's decision of
   25 October).
5. Later, from the READMEs:
   - powerbi: publish to a workspace with row-level security (RLS) and run the live tests
     over the XML for Analysis (XMLA) endpoint;
   - mcp: a remote Model Context Protocol (MCP) server with OAuth sign-in, and a tool
     that runs Data Analysis Expressions (DAX) queries;
   - data: market-based scope 2, and yearly factor versions.

## Next step
With Reece:
1. He opens `C:\Users\reece\Projects\fjordvik\powerbi\FjordvikEmissions.pbip` in Power BI
   Desktop and clicks **Refresh now** on the yellow bar.
2. From `powerbi`, run `.venv\Scripts\python -m pytest -v tests\test_measures_live.py`.
   The runner finds the engine's port by itself.
3. Save the raw output as `powerbi/evidence/live-measures-<date>.txt`.
4. Reece closes Desktop without saving.

## Log
Task: new laptop setup and combined repository   Minutes (Reece's time): under 15   Rework needed: no (one folder move needed Reece's hand, because this chat's process held the folder open)
