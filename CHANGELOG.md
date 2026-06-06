# Changelog

All notable changes to PressCL are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.3] — 2026-06-05

### Changed
- `setup.bat` rebranded to PressCL; auto-creates desktop shortcut via PowerShell
- Streamlit results table now auto-sizes height to show all outlet rows without scrolling

### Fixed
- `setup.bat` shortcut creation failed at step 4: CMD `^` line-continuation inside the quoted PowerShell `-Command` string was passed literally, aborting the script. Collapsed to a single line and replaced `\"` escaping with `[char]34`.
- `PressCL.lnk` launched nothing: `launch.vbs` started Streamlit hidden (window style `0`), where its internal `webbrowser.open()` fails silently. Now uses `--server.headless true` and opens the browser from VBS, with a port guard to avoid spawning duplicate instances.

---

## [0.2] — 2026-06-05

Major reorganization: all application code moved into `app/` subdirectory.
Streamlit GUI introduced alongside the existing CLI.

### Added
- **Streamlit GUI** (`app/app.py`): web interface for interactive searching — multi-query support, parallel worker control, live progress table, CSV/Parquet download
- `launch.vbs` and `stop.bat` for one-click launch/close on Windows
- `app/scraper/streamlit_runner.py`: adapter running scraper pool inside Streamlit's execution model
- Google News full-article retrieval via `trafilatura`
- Auto-generated Markdown run reports in `reports/` after each CLI run
- `validate.py`: standalone outlet selector validator

### Changed
- All source files moved from repo root into `app/` subdirectory
- Streamlit theme: terracotta colour palette, custom CSS, SVG logo
- `.gitignore` moved to `app/`

### Removed
- `INSTRUCTIONS.md`, `References.md`, `progress.md`, `report.md`, `launch.bat` from root (superseded by new structure or deleted as transient artifacts)
- Old Windows shortcut files at repo root

---

## [0.1] — 2026-06-04

First working release. CLI-only.

### Added
- **CLI** (`run.py`) with five commands: `run`, `merge`, `clean`, `check`, `list`
- 15 outlet scrapers across three base types: `BaseScraper` (HTML), `BaseApiScraper` (JSON), `BasePlaywrightScraper` (Playwright/Chromium)
- Multi-query fan-out with AND-within / OR-across phrase semantics
- Accent-insensitive keyword matching via `unicodedata.normalize`
- Parallel execution via `multiprocessing.Pool`
- CSV and Parquet output via `pandas` + `pyarrow`
- Logging queue (`QueueHandler` / `QueueListener`) for safe multiprocess log aggregation
- `setup.bat` one-time Windows installer
- Streamlit config and theme (`.streamlit/config.toml`)

---

[0.3]: https://github.com/brrxs/PressCL/compare/v0.2...v0.3
[0.2]: https://github.com/brrxs/PressCL/compare/v0.1...v0.2
[0.1]: https://github.com/brrxs/PressCL/releases/tag/v0.1
