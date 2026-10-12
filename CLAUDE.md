# fjordvik-mcp

Model Context Protocol (MCP) server over the synthetic Fjordvik dataset, for Claude
Desktop. Part of four repos: fjordvik-data (source of the data), fjordvik-mcp,
fjordvik-powerbi, fjordvik-power-automate. Permanent rules in
`C:\Users\Vihree Nelonen\Projects\knowledge\RULES.md` override this file.

## Rules for this repo

- Synthetic data only. No secrets: `.env.example` holds the only setting, and `.env`
  is git-ignored.
- Emission factors are illustrative, not cited (Reece's one-off exception for the
  Fjordvik project, 12 October 2026). Every doc says so.
- Never edit `data/` by hand. Refresh it with `python scripts/sync_data.py`, which
  verifies checksums and records the source commit.
- Every tool stays read-only. `run_sql` keeps all three guards: one SELECT only,
  locked external access, capped rows. Removing a guard needs Reece's yes.
- MCP SDK is 2.x: `from mcp.server.mcpserver import MCPServer` (FastMCP was renamed),
  in-process tests via `mcp.Client(server)`. Raise `ToolError` for messages Claude
  should see; other exceptions are hidden by design.
- Writing: no em dashes, Australian spelling, spell out acronyms on first use.

## Commands

```bash
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q        # 48 tests
.venv\Scripts\python -m fjordvik_mcp     # run over stdio (Claude Desktop does this)
```
