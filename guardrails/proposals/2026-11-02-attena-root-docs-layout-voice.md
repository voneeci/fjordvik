# Point the root README and CLAUDE.md to the layout map and the voice guide

From Attena, 2 November 2026. For the chat that maintains the repository's root
`README.md` and `CLAUDE.md`. Attena does not edit those files.

1. **Rules:** L1 to L6 and W9 (new in `GUARDRAILS.md`, 2 November 2026).
2. **Wording:**
   - Root `README.md`, where it describes the repository's folders, add:

     > `guardrails/layout.md` lists where each kind of file lives and why.

   - Root `CLAUDE.md`, under "Rules for this repo", add:

     > - Put each new file where `guardrails/layout.md` allows (GUARDRAILS.md section 6).
     >   A new folder needs a map entry first: suggest it in `guardrails/proposals/`.
     >   Write documents in Reece's voice (rule W9), following W1 to W8 where they differ.

3. **Why:** a file off the layout map now fails every part's tests. Chats read the root
   `CLAUDE.md` first, so the line reaches them before they create a folder, rather than
   after a test fails. The README line helps a reader find their way round the repository.
4. **Check:** Review. `check.py` already enforces the map itself.

## Outcome

Open: waiting for the root `README.md` and `CLAUDE.md` owner.
