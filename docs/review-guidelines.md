# Review guidelines

What a review of a pull request checks before it is approved. The guidelines are for everyone who reviews: a person, the reviewer agent ([`.claude/agents/pr-reviewer.md`](../.claude/agents/pr-reviewer.md)) or another agent. Authors can use them to check their own work first. Most rules are in [CLAUDE.md](../CLAUDE.md); a few checks (addresses, writing, branches) are stated only here.

## Procedure

- **The reviewer agent:** whoever uses Claude Code runs the reviewer agent on the pull request, for example by asking Claude Code to "run the pr-reviewer agent on pull request <number>". It reads the change and reports findings without changing anything; that is an instruction, not a technical restriction. It runs on Claude Fable (`model: fable`, an alias that follows the current version), usually a different model from the one that wrote the change; if the author used the same model, say so in the pull request.
- **The author fixes what holds up** and answers the rest in the pull request. Posting the findings as a comment is optional.
- **Without Claude Code,** check your own pull request against these guidelines and ask a maintainer to run the reviewer agent before approving it.
- The review is advisory: CI (`lint-and-test`, required on `develop`) is the required check, and the maintainer approves. Claude Code sessions always run the agent (`CLAUDE.md`).

## How to review

- **Read the diff and the files around it,** not only the description. Check every claim against the change: a finding you haven't verified is a question, not a finding.
- **Report what is wrong or missing,** each finding with its file and line, what is wrong, why it matters (a concrete case where it goes wrong), and a fix where one is clear.
- **Rank the findings:**
  - **must fix:** a bug, a broken rule below, a missing piece the pull request needs;
  - **should fix:** a real problem, but not blocking;
  - **question:** something to clarify.
- **Leave out taste.** Wording and style only count where a rule below says so.
- **"No findings" is a valid result.** Don't pad the review.

## Already checked by CI

The `lint-and-test` workflow runs `ruff check`, `ruff format --check` and `pytest` (tests that need input outside `data/` are skipped). REUSE lint is not in CI: a new file type or folder needs a check that `REUSE.toml` covers it.

## What to check

### 1. Correctness

- The change does what the description says, and nothing it doesn't mention.
- The RDF follows the [TwinShip ontology](https://github.com/twinship-eu/twinship-ontology): the right classes and properties, `tw…` data properties with the datatype of their `rdfs:range`, IRIs under `https://twin-ship.eu/individuals/<vessel>/`.
- Unknown values are omitted, never written as `-1` or another sentinel; spreadsheet `-1` goes through `clean_value`.
- Tests cover the change, including edge cases (empty cells, a vessel without a component, several engines of one kind). Expected results change only on purpose, and the description says why.

### 2. What the pull request includes

- The checks for what changed were run, and are listed in the description.
- `README.md`, `CLAUDE.md` and `docs/` match the change: commands, assets, environment variables, the GraphDB layout.
- The pull request targets `develop` (or `main` for a release), from a short-lived branch. A release bumps the version in `pyproject.toml`, `pipeline_version` (`dagster_pipeline/assets/harmonisation.py`) and `uv.lock` (`uv lock`; CI's `uv sync --frozen` doesn't notice a stale lock).

### 3. The ontology copy

- `ontology/` and `shacl/twinship/` change only through `scripts/sync_ontology.sh`, together with `ontology/VERSION`, and the description names the twinship-ontology tag or commit. Any other change there is a finding: it belongs in twinship-ontology.
- After a sync, the futuristic vessel still validates, and changed results are explained.

### 4. The pipeline

- Dagster assets stay in the chain `spreadsheet_data` → … → `graphdb_upload` → `sparql_summary`; a new asset joins `full_pipeline` and is partitioned by vessel where it handles one vessel's data.
- Named graphs (`https://twin-ship.eu/graphs/<vessel>/{ontology,components,voyages}`): `graphdb_upload` replaces `ontology` and `components` (and clears the default graph), `futuristic_voyage_upload` replaces `voyages`; no asset clears another asset's graph.
- A new `tws:` type the pipeline writes is in `KnownTypeShape` (`shacl/pipeline/connections.ttl`). Pipeline-only shapes stay in `shacl/pipeline/`.
- Futuristic-vessel-only code stays behind a futuristic-vessel check (`is_futuristic`, the `FV` prefix, the `futuristic-vessel` partition) and doesn't affect other vessels.
- Docker tests that need a clean state use their own volumes, not the developer's `twinship-data-pipeline_*` volumes.

### 5. Confidentiality

- **Confidential vessel data never enters the repository.** `data/` holds only the public futuristic vessel data; other input is read from `TWINSHIP_VESSEL_DATA_DIR`. No other vessel's values, file names or identifiers in code, tests, fixtures, docs, commit messages or the description.
- No secrets: no passwords, tokens or Keycloak client secrets; secrets come from `.env` (template `.env.example`), and the realm template holds no real credentials.
- No internal addresses (servers, deployment-specific GraphDB repositories).
- Nothing refers to notes or documents outside the repository that readers can't open.

### 6. Licences

- Contributions come in under the repository's terms (`REUSE.toml`): code, deployment, `README.md`, `CLAUDE.md`, `.github/` and `.claude/` MIT; data, shapes, `docs/` and the TwinShip ontology copy CC BY 4.0. Third-party files under `ontology/external/` and `ontology/vocabularies/` keep their own licences. A new file type or folder is covered by `REUSE.toml`.
- Third-party material only where its licence allows, with its attribution (for example the Copernicus weather columns of the voyage data).

### 7. Writing

- Documentation is in English, plain and short, and describes the current state.
