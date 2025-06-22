# Product Requirements Document (PRD)

## OMBM — Organize My Bookmarks (CLI) v1.0

**Last updated:** 22 Jun 2025

---

### 1. Purpose & Overview

OMBM is a macOS terminal command‑line tool that automatically organizes a user’s existing Safari bookmarks into semantically meaningful folders. It scrapes each bookmarked URL, uses LLM analysis to generate human‑readable titles/descriptions, proposes a taxonomy, and prints the recommended folder structure in a clear tree view.

### 2. Goals & Success Metrics

| Goal                                         | KPI / Target                                                       |
| -------------------------------------------- | ------------------------------------------------------------------ |
| Reduce cognitive load of unmanaged bookmarks | ≥ 80 % of users report improved findability (survey)               |
| Deliver accurate semantic grouping           | ≥ 90 % of LLM‑generated folder names accepted without manual edits |
| CLI responsiveness                           | Process 500 bookmarks in ≤ 5 min on M1 MacBook Air                 |

### 3. Scope

**In‑scope**

* Retrieval of Safari bookmarks via AppleScript / WebKit APIs
* Headless scraping of bookmark content (title, meta & visible text)
* LLM requests (titles, descriptions, taxonomy)
* Terminal tree output & dry‑run (no write) mode

**Out‑of‑scope (v1)**

* Writing changes back into Safari
* Support for non‑Safari browsers
* GUI wrapper

### 4. Personas & Use Cases

1. **Busy Knowledge Worker (Alice, 34)** — Has thousands of research links; wants quick semantic organization.
2. **Developer (Ben, 29)** — Needs command‑line integration in dotfiles.
3. **Digital Minimalist (Cara, 41)** — Runs weekly cleanup via cron.

### 5. User Stories & Acceptance Criteria

| ID    | User Story                                                           | Acceptance Criteria                                                   |
| ----- | -------------------------------------------------------------------- | --------------------------------------------------------------------- |
| US‑01 | As a user I run `ombm` with no flags and see a proposed folder tree. | CLI outputs tree with ≥1 level of folders and ≥1 bookmark per folder. |
| US‑02 | As a power user I run `ombm --save` to persist changes.              | Tool writes new folders & moves bookmarks; exits with success code 0. |
| US‑03 | As a user I cancel mid‑run with `Ctrl‑C`.                            | Tool stops gracefully and leaves bookmarks untouched.                 |

### 6. Functional Requirements

1. **Bookmark retrieval** — `FR‑01` Use macOS AppleScript to export Safari bookmarks to JSON list.
2. **Content scraping** — `FR‑02` Fetch URL HTML; fallback to `<title>` when blocked.
3. **LLM integration**

   * `FR‑03` For each URL call `generateTitleAndDescription()`
   * `FR‑04` After batch complete call `proposeTaxonomy()` returning folder hierarchy in JSON.
4. **Output rendering** — `FR‑05` Pretty‑print tree with folder/bookmark counts.
5. **Persistence (optional flag)** — `FR‑06` Move bookmarks using Safari Bookmark APIs.
6. **CLI options** — `--dry‑run` (default), `--save`, `--max <n>`, `--concurrency <n>`, `--verbose`, `--json-out <file>`.

### 7. Non‑Functional Requirements

* **Performance:** ≤ 600 ms average per bookmark scrape + LLM call using 4‑thread concurrency.
* **Reliability:** Retry failed scrapes up to 2×; skip after.
* **Security & Privacy:** Never transmit private reading list; allow `--no-upload` mode to disable live scraping.
* **Usability:** Zero‑config install via Homebrew.

### 8. Technical Considerations

* **Language:** Python 3.11 with Typer for CLI.
* **Bookmark access:** AppleScript `tell application "Safari" to ...`
* **Scraper:** Playwright headless WebKit; fallback to requests‑HTML.
* **LLM Provider:** OpenAI GPT‑4o; batching of prompts to reduce cost.
* **Rate limiting:** Token bucket; respect provider QPS.
* **Caching:** SQLite cache keyed by URL hash for repeat runs.

### 9. Security & Compliance

* Store API keys in Keychain; never log.
* Sanitize scraped HTML before prompt.
* Conform to Apple App Sandbox guidelines.

### 10. Deployment & Distribution

* Brew formula `brew install ombm`.
* GitHub Actions CI (flake8, pytest, build artefact, Homebrew release).

### 11. Assumptions & Dependencies

* User grants automation permissions to Safari.
* OpenAI API key present in environment.
* Internet connectivity for scraping & LLM calls.

### 12. Risks & Mitigations

| Risk                        | Likelihood | Impact | Mitigation                                        |
| --------------------------- | ---------- | ------ | ------------------------------------------------- |
| LLM misclassification       | Medium     | Medium | Manual review flag; allow `--interactive` editing |
| Scraper blocked by paywalls | High       | Low    | Detect 403 & use `<title>` fallback               |
| Safari API changes          | Low        | High   | Abstract via adapter; monitor macOS updates       |

### 13. Open Questions

1. Should descriptions be stored in bookmark comments field?
2. How to localize taxonomy names?
3. Provide backup/undo mechanism for `--save`?

### 14. Future Enhancements (v1.x+)

* Chrome/Firefox support
* iCloud bookmark syncing awareness
* GUI (SwiftUI) companion
* Periodic cron mode (`ombm --schedule weekly`)

---

*Author*: **Farhan Kazmi / ChatGPT**
