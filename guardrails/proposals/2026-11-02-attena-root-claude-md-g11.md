# Point the root CLAUDE.md to rule G11

From Attena, 2 November 2026. For the chat that maintains the repository's root
`CLAUDE.md`. Attena does not edit that file.

1. **Rule:** G11 (new in `GUARDRAILS.md`, 2 November 2026).
2. **Wording:** add one line under "Rules for this repo" in the root `CLAUDE.md`:

   > - Start every Claude Code chat in this repository with the repository root as its
   >   folder, and `cd` into a part to work there (GUARDRAILS.md rule G11). A chat started
   >   in a part folder runs with no guardrail hook.

3. **Why:** Claude Code loads `.claude/settings.json` only from the folder a chat starts
   in, with no parent-folder fallback. A chat started in `service-ai`, `mcp` or any other
   part runs without the guardrail hook, so none of the hook rules (D2, D3, D8, G1 to G3,
   G9) stop it. The root `CLAUDE.md` is read by every chat, so the line reaches each one
   before it starts work.
4. **Check:** Review. Reece decided against `.claude/settings.json` files in the part
   folders (2 November 2026), so no hook can enforce where a chat starts.

## Outcome

Open: waiting for the root `CLAUDE.md` owner.
