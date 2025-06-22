# OMBM - Organize My Bookmarks

A macOS CLI tool for semantically organizing Safari bookmarks using AI.

## Overview

OMBM analyzes your Safari bookmarks by scraping their content and using Large Language Models to:
- Generate meaningful titles and descriptions
- Propose a semantic taxonomy for organization
- Display the suggested folder structure

## Features

- 🔍 **Smart Analysis**: Uses web scraping and AI to understand bookmark content
- 📁 **Semantic Organization**: Groups bookmarks into meaningful categories
- 🌳 **Tree Visualization**: Clear terminal display of proposed structure
- 🔒 **Privacy-First**: Local processing with optional cloud AI calls
- ⚡ **Fast & Concurrent**: Parallel processing for speed
- 🛡️ **Safe by Default**: Dry-run mode prevents accidental changes

## Installation

### Via Homebrew (Recommended)

```bash
brew install ombm
```

### Via pipx

```bash
pipx install ombm
```

### Via pip

```bash
pip install ombm
```

## Quick Start

1. **Dry run** (preview only, no changes):
   ```bash
   ombm organize
   ```

2. **With options**:
   ```bash
   ombm organize --max 100 --concurrency 8 --verbose
   ```

3. **Save changes** (applies organization to Safari):
   ```bash
   ombm organize --save
   ```

## Usage

```bash
ombm organize [OPTIONS]

Options:
  --max INTEGER              Maximum number of bookmarks to process
  --concurrency INTEGER      Maximum concurrent tasks [default: 4]
  --save                    Save changes to Safari (default is dry-run)
  --json-out PATH           Write hierarchy to JSON file
  --verbose                 Enable verbose logging
  --no-scrape              Use existing cache only
  --model TEXT             Override OpenAI model [default: gpt-4o]
  --profile                Display timing and memory stats
  --help                   Show this message and exit
```

## Requirements

- macOS 10.15+ (Catalina or later)
- Python 3.11+
- Safari with bookmarks
- OpenAI API key (set via `OPENAI_API_KEY` environment variable)

## Configuration

OMBM creates a configuration directory at `~/.ombm/` containing:
- `config.toml` - User preferences
- `cache.db` - SQLite cache for scraped content
- `logs/` - Application logs

## Development

```bash
# Clone the repository
git clone https://github.com/farhankazmi/ombm.git
cd ombm

# Install in development mode
pip install -e ".[dev]"

# Install Playwright browsers
playwright install webkit

# Run tests
pytest

# Run linting
ruff check .
ruff format .

# Type checking
mypy ombm/
```

## Privacy & Security

- Bookmark URLs may be sent to OpenAI for analysis
- Use `--no-scrape` to work with cached data only
- API keys are stored securely in macOS Keychain
- No telemetry or analytics by default

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for CLI
- Uses [Playwright](https://playwright.dev/) for web scraping
- Powered by [OpenAI](https://openai.com/) for semantic analysis
- Styled with [Rich](https://rich.readthedocs.io/) for beautiful terminal output

## Status

🚧 **In Development** - This project is currently in active development. Core functionality is being implemented.

Current milestone: **M1 - Core Skeleton & Infrastructure**

See [docs/plan.md](docs/plan.md) for detailed development roadmap.
