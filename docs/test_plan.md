# OMBM – Quality‑Assurance Test Plan

**Version:** 1.0  **Date:** 22 Jun 2025

---

## 1  Test Objectives

* Verify OMBM meets all functional requirements in the PRD.
* Validate non‑functional goals (performance, error recovery, security, usability).
* Provide repeatable scripts enabling automated CI and manual acceptance testing.

---

## 2  Test Scope

| In Scope                                         | Out of Scope                           |
| ------------------------------------------------ | -------------------------------------- |
| CLI functionality (`ombm` flags, dry‑run & save) | GUI wrappers (future)                  |
| Safari bookmark retrieval & re‑write             | Non‑Safari browsers                    |
| Scraping & LLM metadata generation               | LLM provider benchmarking              |
| Cache behaviour & undo backup                    | Cross‑platform support (Linux/Windows) |
| Performance under 500 bookmarks                  | >5 000 bookmarks stress (future)       |

---

## 3  Test Levels

1. **Unit** – Individual modules (pytest‑asyncio, coverage ≥ 85 %).
2. **Integration** – Subsystem flows (scraper ⇄ LLM ⇄ cache) using mocks.
3. **System / E2E** – Full CLI on sample Safari profile in macOS GitHub Actions runner.
4. **User Acceptance** – Manual run on real bookmark library, observing output accuracy.

---

## 4  Test Environments

| Env             | Purpose                       | Config                            |
| --------------- | ----------------------------- | --------------------------------- |
| **Local Dev**   | Rapid unit & integration runs | macOS 14, Python 3.11, Safari 17  |
| **CI (GitHub)** | Automated pipeline on each PR | macos‑12 (Intel) & macos‑14 (ARM) |
| **Staging**     | Pre‑release build validation  | Ad‑hoc M1 Mac mini Jenkins agent  |

---

## 5  Tooling & Frameworks

* **pytest**, **pytest‑asyncio** – Unit/integration framework.
* **respx** – Mock HTTP/LLM endpoints.
* **Playwright Test** (headless sanity smoke).
* **coverage.py** – Code‑coverage gates.
* **GH Actions** – CI orchestration & artifact diff.
* **speedtest.py** script – Performance timing.

---

## 6  Entry & Exit Criteria

| Phase       | Entry                                          | Exit                                                  |
| ----------- | ---------------------------------------------- | ----------------------------------------------------- |
| Unit        | Code module merged into feature branch         | ≥ 90 % tests pass, coverage ≥ 85 %                    |
| Integration | All linked unit tests green                    | All flows pass & contract schemas validate            |
| System      | Docker image built, test Safari profile loaded | CLI exits 0, outputs match fixtures, perf within spec |
| UAT         | Code freeze, Release Candidate built           | Stakeholder sign‑off, no Sev 1/2 bugs                 |

---

## 7  Traceability Matrix (Tasks → Test Cases)

| Task ID | Primary Test Case IDs                            |
| ------- | ------------------------------------------------ |
| T‑11    | IT‑SCR‑01, IT‑SCR‑02                             |
| T‑16    | UT‑LLM‑01, IT‑LLM‑02                             |
| T‑24    | UT‑TREE‑01                                       |
| T‑25    | ST‑CLI‑03                                        |
| …       | … (full mapping maintained in `/tests/TRACE.md`) |

---

## 8  Detailed QA Test Scripts

> **Notation:**
> TC‑IDs encode level (UT = Unit, IT = Integration, ST = System, UAT = User Acceptance).

### 8.1 System Test Scripts (CLI focus)

| TC‑ID         | Title                              | Pre‑conditions                                                       | Steps                                                     | Expected Results                                                                     |
| ------------- | ---------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **ST‑CLI‑01** | Dry‑run categorizes sample profile | `SafariTestProfile` with 10 bookmarks; OpenAI key set; cache cleared | 1. `ombm --dry-run --max 10`<br>2. Observe console output | *Exit code 0*<br>*Rich tree shows ≥ 1 folder*<br>*No bookmarks remain uncategorized* |
| **ST‑CLI‑02** | Cache hit skips LLM call           | Cache DB populated by ST‑CLI‑01                                      | `ombm --dry-run --max 10 --no-scrape`                     | Runtime < 50 % of ST‑CLI‑01; log shows “cache hit” & zero OpenAI calls               |
| **ST‑CLI‑03** | JSON export flag                   | Same profile                                                         | `ombm --dry-run --json-out result.json`                   | `result.json` exists, validates against schema                                       |
| **ST‑CLI‑04** | Persistence save path              | Dev Safari profile clone                                             | `ombm --save --max 5`                                     | Folders created & bookmarks moved; backup plist timestamped; undo plist size > 0     |
| **ST‑CLI‑05** | Ctrl‑C graceful cancel             | Run with 100 bookmarks                                               | Send SIGINT after 3 s                                     | Process exits ‑–1; bookmarks untouched; log “Interrupted”                            |

### 8.2 Integration Scripts

| TC‑ID         | Subsystem         | Steps                              | Expected Results                                           |
| ------------- | ----------------- | ---------------------------------- | ---------------------------------------------------------- |
| **IT‑SCR‑01** | Scraper fallback  | Mock website returns 403           | `fetch()` returns HTML title only; warning logged          |
| **IT‑LLM‑02** | Title+Desc prompt | Mock OpenAI returns JSON w/ fields | `title_desc()` returns dataclass populated; tokens counted |

### 8.3 Unit Test Examples

| TC‑ID            | Module          | Assertion                                     |
| ---------------- | --------------- | --------------------------------------------- |
| **UT‑CONFIG‑01** | `config.load()` | Env var overrides TOML value                  |
| **UT‑CACHE‑02**  | `Cache.put/get` | Round‑trip stores & fetches within 10 ms      |
| **UT‑TREE‑01**   | `build_tree()`  | Depth and leaf counts match fixture hierarchy |

### 8.4 Performance & Stress

| TC‑ID         | Scenario                      | Metric        | Pass Threshold    |
| ------------- | ----------------------------- | ------------- | ----------------- |
| **PT‑500‑01** | Process 500 bookmarks dry‑run | Total runtime | ≤ 5 min (M2 spec) |
| **PT‑MEM‑02** | Peak RSS during 500 run       | Memory usage  | ≤ 500 MB          |

### 8.5 Security Tests

| TC‑ID          | Check            | Method               | Expected                               |
| -------------- | ---------------- | -------------------- | -------------------------------------- |
| **SEC‑KEY‑01** | API key leakage  | Run with `--verbose` | Key string NOT present in logs         |
| **SEC‑PII‑02** | URL privacy flag | Run `--local-only`   | No outbound network except local cache |

### 8.6 Accessibility / Usability

| TC‑ID          | Focus          | Step                              | Expected                                     |
| -------------- | -------------- | --------------------------------- | -------------------------------------------- |
| **UX‑TERM‑01** | Color contrast | Run tool in low‑contrast terminal | Tree coloring still legible (Rich auto ANSI) |

---

## 9  Defect Severity Levels

| Sev          | Definition                             | SLA to Fix (pre‑GA) |
| ------------ | -------------------------------------- | ------------------- |
| 1 – Critical | Crash, data loss, wrong bookmark moves | 24 h                |
| 2 – Major    | Incorrect folder suggestion > 10 %     | 48 h                |
| 3 – Minor    | Cosmetic UI issues, log typos          | Next sprint         |

---

## 10  Schedule Alignment

* **Week 1–3:** Unit + integration automated in tandem with dev.
* **Week 4:** First full System test pass (ST‑CLI‑01 .. 04).
* **Week 5:** Performance + security focused runs.
* **Week 6:** UAT sign‑off & release regression.

---

## 11  Reporting

* CI publishes JUnit XML + HTML coverage.
* Weekly QA status email includes pass‑rate % and open defects.

---

**End of QA Test Plan**
