# OMBM - Organize My Bookmarks

A macOS CLI tool that automatically organizes your Safari bookmarks into semantically meaningful folders using AI.

[![PyPI version](https://badge.fury.io/py/ombm.svg)](https://badge.fury.io/py/ombm)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-311/)

## Overview

OMBM transforms your cluttered Safari bookmarks into an organized, hierarchical structure by:
- 🔍 **Smart Content Analysis**: Scrapes bookmark content and extracts meaningful information
- 🤖 **AI-Powered Organization**: Uses OpenAI GPT models to generate semantic titles and folder structures
- 📁 **Intelligent Categorization**: Groups related bookmarks into logical folders automatically
- 🌳 **Beautiful Visualization**: Displays proposed organization in an elegant tree format
- 🔒 **Privacy & Security**: Secure API key storage and optional local-only processing

## ✨ Features

### Core Functionality
- **Semantic Analysis**: Generates human-readable titles and descriptions for bookmarks
- **Auto-Categorization**: Creates meaningful folder hierarchies based on content similarity
- **Batch Processing**: Handles hundreds of bookmarks efficiently with concurrent processing
- **Cache System**: Remembers analyzed content to avoid re-processing

### User Experience
- **Progress Tracking**: Real-time progress bars for large bookmark collections
- **Flexible Output**: Terminal tree view, JSON export, or direct Safari integration
- **Multiple Modes**: Verbose, normal, and quiet operation modes
- **Safe by Default**: Dry-run mode prevents accidental changes

### Security & Privacy
- **Keychain Integration**: Secure API key storage in macOS Keychain
- **Privacy Options**: Local cache-only mode for sensitive bookmarks
- **No Telemetry**: No usage tracking or analytics

## 🚀 Quick Start

### 1. Installation

#### Via Homebrew (Recommended)
```bash
brew install ombm
```

#### Via pipx (Isolated Environment)
```bash
pipx install ombm
```

#### Via pip
```bash
pip install ombm
```

### 2. Setup Your OpenAI API Key

OMBM uses OpenAI's GPT models for semantic analysis. You'll need an API key:

1. Get your API key from [OpenAI](https://platform.openai.com/api-keys)
2. Store it securely in keychain:
   ```bash
   ombm set-key
   ```
   
Alternatively, set as environment variable:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Your First Run

**Preview organization** (safe, no changes):
```bash
ombm organize
```

This will:
- ✅ Analyze your Safari bookmarks
- ✅ Generate semantic titles and descriptions  
- ✅ Propose a folder hierarchy
- ✅ Display the results in a beautiful tree

**Apply the organization** (writes to Safari):
```bash
ombm organize --save
```

## 📖 Usage Guide

### Basic Commands

#### Organize Bookmarks
```bash
# Dry run (preview only)
ombm organize

# Organize with custom limits
ombm organize --max 100 --concurrency 8

# Save changes to Safari
ombm organize --save

# Export to JSON
ombm organize --json-out bookmarks.json
```

#### API Key Management
```bash
# Store API key in keychain
ombm set-key

# Check key status
ombm key-status

# Remove stored key
ombm delete-key
```

### Command Options

```bash
ombm organize [OPTIONS]

Core Options:
  --save                 Persist organization to Safari (default: dry-run)
  --max INTEGER          Limit number of bookmarks to process
  --concurrency INTEGER  Max concurrent tasks [default: 4]
  --json-out PATH        Export hierarchy to JSON file

AI Configuration:
  --model TEXT           OpenAI model to use [default: gpt-4o]
  --no-scrape           Use cache only, no new web requests

Output Control:
  --verbose             Enable detailed logging and progress info
  --quiet               Suppress non-essential output
  --json-logs           Output logs in JSON format

Performance:
  --profile             Show timing and memory statistics
```

### Advanced Examples

**Large bookmark collection with progress tracking:**
```bash
ombm organize --max 500 --concurrency 10 --verbose
```

**Quick organization using cache only:**
```bash
ombm organize --no-scrape --quiet --save
```

**Export for external processing:**
```bash
ombm organize --json-out my-bookmarks.json --profile
```

## 🔧 Configuration

OMBM creates a configuration directory at `~/.ombm/`:

```
~/.ombm/
├── config.toml     # User preferences and settings
├── cache.db        # SQLite database for scraped content
└── logs/           # Application logs
    └── ombm-YYYYMMDD.log
```

### Configuration File

The `config.toml` file allows you to set default preferences:

```toml
[general]
max_bookmarks = 0  # 0 = unlimited
concurrency = 4
model = "gpt-4o"
verbose = false

[cache]
enabled = true
ttl_days = 30

[logging]
level = "INFO"
json_format = false
```

## 🛡️ Privacy & Security

### Data Handling
- **Local Processing**: Content analysis happens locally when possible
- **Secure Storage**: API keys stored in macOS Keychain, never in plain text
- **Optional Cloud**: Use `--no-scrape` to work entirely with cached data
- **No Telemetry**: OMBM collects no usage analytics or telemetry data

### API Key Security
- Keys are stored using macOS Keychain Services
- Automatic fallback to environment variables
- Keys are never logged or exposed in error messages
- Secure prompt with hidden input for key entry

### Privacy Options
```bash
# Work offline with cached data only
ombm organize --no-scrape

# Check what data would be sent
ombm organize --verbose  # Shows URLs being processed

# Use local environment instead of keychain
export OPENAI_API_KEY="your-key"
ombm organize
```

## 🧪 How It Works

1. **Bookmark Extraction**: Retrieves bookmarks from Safari using AppleScript
2. **Content Scraping**: Fetches webpage content using Playwright WebKit engine
3. **Text Extraction**: Extracts clean, readable text from HTML content
4. **AI Analysis**: Sends content to OpenAI for semantic title and description generation
5. **Taxonomy Generation**: Groups related bookmarks and creates folder hierarchy
6. **Presentation**: Displays proposed organization in terminal or exports to JSON
7. **Optional Persistence**: Applies changes to Safari bookmarks when `--save` is used

## 🔍 Troubleshooting

### Common Issues

**"No OpenAI API key found"**
```bash
# Store your key securely
ombm set-key

# Or check if already stored
ombm key-status
```

**"Permission denied accessing Safari"**
- Grant Terminal automation permissions in System Preferences > Privacy & Security

**"Rate limit exceeded"**
```bash
# Reduce concurrency
ombm organize --concurrency 2

# Or process in smaller batches
ombm organize --max 50
```

**Scraping failures**
```bash
# Use cache-only mode
ombm organize --no-scrape

# Or enable verbose logging to debug
ombm organize --verbose
```

### Getting Help

```bash
# Show all available commands
ombm --help

# Get help for specific command
ombm organize --help

# Check API key status
ombm key-status

# View recent logs
tail -f ~/.ombm/logs/ombm-$(date +%Y%m%d).log
```

## 💻 Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/farhankazmi/ombm.git
cd ombm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install in development mode
pip install -e ".[dev]"

# Install Playwright browsers
playwright install webkit
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ombm

# Run specific test file
pytest tests/test_main.py -v

# Run integration tests
pytest tests/ -m integration
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy ombm/

# All quality checks
ruff format . && ruff check . && mypy ombm/ && pytest
```

### Building Distribution

```bash
# Build package
python -m build

# Install locally
pip install dist/ombm-*.whl
```

## 🤝 Contributing

We welcome contributions! Please see our [contributing guidelines](CONTRIBUTING.md) for details.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Ensure all tests pass: `pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to your branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Development Priorities

See [docs/plan.md](docs/plan.md) for the current development roadmap and task priorities.

## 📋 Requirements

- **Operating System**: macOS 10.15+ (Catalina or later)
- **Python**: 3.11 or higher
- **Browser**: Safari with bookmarks to organize
- **API Access**: OpenAI API key for semantic analysis
- **Permissions**: Terminal automation access to Safari

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

OMBM is built with excellent open-source tools:

- **[Typer](https://typer.tiangolo.com/)** - Elegant CLI framework
- **[Rich](https://rich.readthedocs.io/)** - Beautiful terminal formatting
- **[Playwright](https://playwright.dev/)** - Reliable web automation
- **[OpenAI](https://openai.com/)** - Advanced language models
- **[aiosqlite](https://aiosqlite.omnilib.dev/)** - Async SQLite operations
- **[keyring](https://github.com/jaraco/keyring)** - Secure credential storage

## 📊 Project Status

🎉 **Beta Release** - Core functionality implemented and tested

**Current Milestone**: M5 - User Experience & Packaging
- ✅ Verbose & quiet modes
- ✅ Progress bars  
- ✅ Keychain integration
- 🔄 Homebrew bottle build
- ✅ README + Quick-start docs

**Latest Version**: 0.1.0

For detailed development progress, see [docs/plan.md](docs/plan.md).

---

<p align="center">
  <b>Transform your bookmark chaos into organized clarity with OMBM!</b>
</p>
