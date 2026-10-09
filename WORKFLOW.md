# Dev workflow

Lightweight discipline for changes to `bolsa_core`, borrowed from the
ECC agent-orchestration pattern (plan -> TDD -> security -> review) but
without installing that framework -- this project is small enough to run
the same gates by hand.

This is the shared package consumed by `bolsa-skill` (Claude Code skill)
and `bolsa-web` (public web platform) via a pinned git dependency. A
change here does not take effect in either consumer until it's pushed
and that consumer's `uv.lock` is re-pinned (`uv lock --upgrade-package
bolsa-core`) -- don't forget that second step, or the consumer keeps
running the old behavior silently.

1. **Plan before coding.** For anything beyond a one-line fix, write
   down (in the PR description or a scratch note, not necessarily a
   file) what changes and why before touching `src/`. If the change
   touches `FundingOpportunity`/`Profile`/`Researcher`/`LattesExtract`
   schemas, check `references/schemas.md` (in `bolsa-skill`, since that's
   where the schema reference doc lives) first and update it alongside
   the code, in both repos if the change is consumer-visible.

2. **Test first.** Add/extend the matching `tests/test_*.py` before or
   together with the implementation. Run:

   ```
   uv run pytest
   ```

   New fetching/parsing logic needs a fixture under `tests/fixtures/`
   (or `fixtures/private/` if it's real personal data that shouldn't be
   committed) -- don't hit live network in tests.

3. **Security/trust check.** This package's main risk surface is
   external HTML/PDF/API parsing (`funding.py`, `lattes.py`,
   `openalex.py`). Before merging changes there:
   - no `eval`/`exec`/shell calls on fetched content
   - HTML parsing stays through `selectolax`, not string concatenation
     into anything executed
   - don't add confidence/validation layers on user-supplied IDs
     (ORCID etc.) -- see memory `feedback_trust_input_dont_overvalidate`

4. **Review the diff yourself** (or via `/code-review`) focusing on:
   correctness, and that every funding/eligibility claim still carries
   `url` + `consulted_at` per the inviolable rule in `bolsa-skill`'s
   `SKILL.md`.

5. **Keep docs in sync.** If behavior visible to a consumer changes,
   update `bolsa-skill`'s `SKILL.md`/`references/schemas.md` (and
   `bolsa-web` if the web API surface is affected) in the same change,
   not later -- and bump that consumer's lock as described above.

No new tooling/dependencies needed for this -- `pytest` already covers
step 2, and steps 1/3/4/5 are just habits.
