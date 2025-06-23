# OMBM – Detailed Implementation Plan

**Version:** 1.0  **Date:** 22 Jun 2025

---

## 1  Planning Principles

* **Granularity** – Each task ≈ 2–4 engineering hrs.
* **Definition of Done** – Measurable artifact + green tests.
* **Critical‑path first** – Core pipeline before UX polish.

---

## 2  Legend

| Col   | Meaning                          |
| ----- | -------------------------------- |
| ID    | `T‑xx`; grouped by milestone     |
| Pri   | P1 (high), P2 (medium), P3 (low) |
| Dep   | Blocking task IDs (comma‑sep)    |
| Skill | Key expertise required           |

---

## 3  Task Breakdown

### Milestone M1 – Core Skeleton & Infrastructure

| ID   | Task                                  | Output                                                    | Acceptance Criteria                      | Pri | Dep  | Skill               |
| ---- | ------------------------------------- | --------------------------------------------------------- | ---------------------------------------- | --- | ---- | ------------------- |
| T‑01 | Bootstrap repo & CI pipeline          | GitHub repo w/ main branch, `pyproject.toml`, CI workflow | `ruff` + `pytest` run & pass on PR in CI | P1  | –    | git, Python tooling |
| T‑02 | Set up Typer CLI entrypoint           | `ombm/__main__.py` with `ombm --version`                  | Running `ombm --help` shows commands     | P1  | T‑01 | Python, Typer       |
| T‑03 | Implement structured logging baseline | `logging.py` with `structlog` config                      | Logs emit JSON lines in debug run        | P2  | T‑02 | Python logging      |
| T‑04 | Create Bookmark adapter stub          | `bookmark_adapter.py` returning mocked list               | Unit test asserts ≥1 BookmarkRecord      | P1  | T‑02 | AppleScript, Python |
| T‑05 | Implement SQLite cache schema         | `cache.py` creates tables on first run                    | `pytest` verifies table existence        | P1  | T‑01 | SQLite, aiosqlite   |
| T‑06 | Global settings loader                | `config.py` reads TOML; env overrides                     | Unit test loads defaults + override      | P2  | T‑02 | Python, tomli       |

### Milestone M2 – Scraping & Metadata Generation

| ID   | Task                               | Output                                       | Acceptance Criteria                         | Pri | Dep            | Skill                      |
| ---- | ---------------------------------- | -------------------------------------------- | ------------------------------------------- | --- | -------------- | -------------------------- |
| T‑11 | Playwright fetch helper            | `scraper.py` async `fetch(url)` returns text | Test hits example.com returns ≥200 chars    | P1  | T‑04           | Playwright                 |
| T‑12 | Fallback HTTPX fetch               | `scraper.py` uses HTTPX if Playwright fails  | Simulated 403 triggers fallback path        | P1  | T‑11           | HTTPX                      |
| T‑13 | Readability content cleaner        | `clean_text()` truncates to 10k chars        | Unit test length ≤10 000 & no HTML tags     | P2  | T‑11           | BeautifulSoup, readability |
| T‑14 | Scraper error‑retry logic          | Retry wrapper with 2 exponential retries     | Unit test uses `respx` to simulate failures | P1  | T‑12           | asyncio, testing           |
| T‑15 | OpenAI title+desc prompt template  | `prompts/title_desc.jinja`                   | Snapshot test returns JSON fields           | P1  | T‑05           | Prompt design              |
| T‑16 | LLM metadata function              | `llm.py` async `title_desc(url, text)`       | Mock OpenAI returns name & description      | P1  | T‑15           | OpenAI SDK                 |
| T‑17 | Cache integration for scrape & LLM | Write/read using url hash keys               | E2E test re‑run hits cache (no API call)    | P1  | T‑05,T‑14,T‑16 | SQLite                     |

### Milestone M3 – Taxonomy & Tree Rendering

| ID   | Task                          | Output                                   | Acceptance Criteria                        | Pri | Dep  | Skill              |
| ---- | ----------------------------- | ---------------------------------------- | ------------------------------------------ | --- | ---- | ------------------ |
| T‑21 | Aggregate metadata collection | Controller builds list of LLMMetadata    | Unit test list length == mocked bookmarks  | P1  | T‑17 | Python             |
| T‑22 | Taxonomy prompt template      | `prompts/taxonomy.jinja` JSON spec       | Snapshot includes folder hierarchy         | P1  | T‑21 | Prompt design      |
| T‑23 | LLM taxonomy generator        | `llm.py` async `propose_taxonomy(list)`  | Mock returns valid JSON; schema validated  | P1  | T‑22 | OpenAI SDK         |
| T‑24 | Tree model parser             | `tree_builder.py` → FolderNode structure | Unit test depth & leaf counts correct      | P1  | T‑23 | Python dataclasses |
| T‑25 | Rich Tree renderer            | `renderer.py` pretty‑prints tree         | Visual test: output matches sample fixture | P2  | T‑24 | Rich               |
| T‑26 | `--json-out` option           | Writes hierarchy JSON file               | File exists & passes schema check          | P2  | T‑24 | I/O                |

### Milestone M4 – Persistence & Side‑Effects

| ID   | Task                            | Output                                         | Acceptance Criteria                                                       | Pri | Dep  | Skill              |
| ---- | ------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------- | --- | ---- | ------------------ |
| T‑31 | AppleScript generator templates | `.applescript` files for folder ops            | Lint passes, unit test compares strings                                   | P2  | T‑04 | AppleScript        |
| T‑32 | Persistence manager module      | `persistence.py` executes AppleScript          | Dry‑run flag logs actions; `--save` moves sample bookmarks in dev profile | P1  | T‑31 | Python, subprocess |
| T‑33 | Undo snapshot backup            | Before save, export current bookmarks to plist | Backup file present after run                                             | P2  | T‑32 | macOS scripting    |

### Milestone M5 – UX, Config & Packaging

| ID   | Task                      | Output                                   | Acceptance Criteria                    | Pri | Dep       | Skill          |
| ---- | ------------------------- | ---------------------------------------- | -------------------------------------- | --- | --------- | -------------- |
| T‑41 | Verbose & quiet modes     | `--verbose`, `--silent` flags affect log | Integration test compares log lines    | P2  | T‑03      | Python         |
| T‑42 | Progress bars             | Add Rich progress to controller          | Displays live % for ≥10 bookmarks      | P3  | T‑25      | Rich           |
| T‑43 | Keychain integration      | Store/retrieve OpenAI key via `keyring`  | Manual test round‑trip, key not logged | P2  | T‑05      | macOS keychain |
| T‑44 | Homebrew bottle build     | CI job produces `ombm` zipapp + formula  | `brew install ./ombm.rb` runs tool     | P1  | T‑01,T‑25 | CI, packaging  |
| T‑45 | Readme + Quick‑start docs | `README.md` with usage examples          | Spell‑check pass, commands succeed     | P1  | T‑44      | Markdown       |

### Milestone M6 – QA & Release

| ID   | Task                            | Output                                      | Acceptance Criteria                            | Pri | Dep       | Skill               |
| ---- | ------------------------------- | ------------------------------------------- | ---------------------------------------------- | --- | --------- | ------------------- |
| T‑51 | E2E pipeline test on macOS‑CI   | GH Actions runs dry‑run on sample bookmarks | Job passes; artifact tree diff matches fixture | P1  | T‑44,T‑25 | GH Actions, macOS   |
| T‑52 | Performance benchmark script    | `bench.py` prints time per phase            | 500 bookmark run ≤ targets in spec             | P2  | T‑11,T‑16 | Python benchmarking |
| T‑53 | Security review checklist       | Doc covering key storage, PII, CVEs         | Checklist signed off by reviewer               | P2  | T‑43      | Security            |
| T‑54 | v1.0 Release tag & PyPI publish | Git tag `v1.0.0`, PyPI package              | `pipx install ombm` runs with `--help`         | P1  | T‑51,T‑45 | Packaging           |

---

## 4  Timeline & Sequencing

1. **Week 1** – M1 (T‑01 → T‑06)
2. **Week 2** – M2 (T‑11 … T‑17)
3. **Week 3** – M3 (T‑21 … T‑26)
4. **Week 4** – M4 (T‑31 … T‑33) + docs kickoff.
5. **Week 5** – M5 UX & packaging (T‑41 … T‑45).
6. **Week 6** – M6 QA & GA release (T‑51 … T‑54).

Parallelism allowed within a milestone where dependencies permit.

---

## 5  Skill Matrix Summary

| Skill                           | Tasks                          |
| ------------------------------- | ------------------------------ |
| Python async & Typer            | T‑02,11‑17,21‑26,32,41‑42      |
| AppleScript / macOS automation  | T‑04,31‑33                     |
| Web‑scraping (Playwright/HTTPX) | T‑11‑14,52                     |
| Prompt engineering / OpenAI SDK | T‑15‑16,22‑23                  |
| SQLite / aiosqlite              | T‑05,17,43                     |
| CI/CD & packaging               | T‑01,44,51,54                  |
| Testing (pytest, respx)         | All with unit/integration tags |
| Security & Keychain             | T‑43,53                        |
| Documentation                   | T‑45                           |

---

## 6  Status Tracker

Use this markdown table as a living checklist. Update **Owner**, **Status**, and **Notes** columns as work progresses. Recommended status emojis:<br>🟢 *Done*   🟡 *In Progress*   ⚪️ *Not Started*   🔴 *Blocked*

| ID   | Task                                  | Pri | Owner | Status | Notes |
| ---- | ------------------------------------- | --- | ----- | ------ | ----- |
| T‑01 | Bootstrap repo & CI pipeline          | P1  | Cline | 🟢     | Completed: repo init, pyproject.toml, CI workflow, tests passing |
| T‑02 | Set up Typer CLI entrypoint           | P1  | Cline | 🟢     | Completed: CLI working, script entry point fixed, all tests pass |
| T‑03 | Implement structured logging baseline | P2  | Cline | 🟢     | Completed: structlog config, JSON logs in debug, CLI integration |
| T‑04 | Create Bookmark adapter stub          | P1  | Cline | 🟢     | Completed: BookmarkAdapter with mocked data, models.py, comprehensive tests |
| T‑05 | Implement SQLite cache schema         | P1  | Cline | 🟢     | Completed: SQLite cache with aiosqlite, table creation, CRUD operations, comprehensive tests |
| T‑06 | Global settings loader                | P2  | Cline | 🟢     | Completed: TOML config system, env overrides, comprehensive tests, 92% coverage |
| T‑11 | Playwright fetch helper               | P1  | Cline | 🟢     | Completed: PlaywrightScraper with async fetch, 89% coverage, content extraction ≥200 chars |
| T‑12 | Fallback HTTPX fetch                  | P1  | Cline | 🟢     | Completed: HTTPXScraper fallback logic, WebScraper auto-failover, 403 error handling tested |
| T‑13 | Readability content cleaner           | P2  | Cline | 🟢     | Completed: Readability + BeautifulSoup integration, 10k char truncation, HTML tag removal |
| T‑14 | Scraper error‑retry logic             | P1  | Cline | 🟢     | Completed: Exponential backoff retry in LLM service, comprehensive error simulation tests |
| T‑15 | OpenAI title+desc prompt template     | P1  | Cline | 🟢     | Completed: Jinja2 template with examples/schema, JSON field generation verified |
| T‑16 | LLM metadata function                 | P1  | Cline | 🟢     | Completed: LLMService with OpenAI integration, 97% coverage, name/description generation |
| T‑17 | Cache integration for scrape & LLM    | P1  | Cline | 🟢     | Completed: BookmarkProcessor pipeline, 95% coverage, E2E cache testing with no API calls |
| T‑21 | Aggregate metadata collection         | P1  | Cline | 🟢     | Completed: BookmarkController with metadata aggregation pipeline, 87% coverage |
| T‑22 | Taxonomy prompt template              | P1  | Cline | 🟢     | Completed: Jinja2 template with comprehensive taxonomy generation instructions |
| T‑23 | LLM taxonomy generator                | P1  | Cline | 🟢     | Completed: LLMService.propose_taxonomy() with JSON validation and error handling |
| T‑24 | Tree model parser                     | P1  | Cline | 🟢     | Completed: TaxonomyParser converts JSON to FolderNode structures, 91% coverage |
| T‑25 | Rich Tree renderer                    | P2  | Cline | 🟢     | Completed: TreeRenderer with beautiful tree visualization, 100% coverage |
| T‑26 | `--json-out` option                   | P2  | Cline | 🟢     | Completed: JSON export for metadata, taxonomy, and folder trees |
| T‑31 | AppleScript generator templates       | P2  |       | ⚪️     |       |
| T‑32 | Persistence manager module            | P1  |       | ⚪️     |       |
| T‑33 | Undo snapshot backup                  | P2  |       | ⚪️     |       |
| T‑41 | Verbose & quiet modes                 | P2  |       | ⚪️     |       |
| T‑42 | Progress bars                         | P3  |       | ⚪️     |       |
| T‑43 | Keychain integration                  | P2  |       | ⚪️     |       |
| T‑44 | Homebrew bottle build                 | P1  |       | ⚪️     |       |
| T‑45 | Readme + Quick‑start docs             | P1  |       | ⚪️     |       |
| T‑51 | E2E pipeline test on macOS‑CI         | P1  |       | ⚪️     |       |
| T‑52 | Performance benchmark script          | P2  |       | ⚪️     |       |
| T‑53 | Security review checklist             | P2  |       | ⚪️     |       |
| T‑54 | v1.0 Release tag & PyPI publish       | P1  |       | ⚪️     |       |

---


**End of Implementation Plan**
