# Contributing to OMBM

Thank you for your interest in contributing to OMBM! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

We welcome contributions of all kinds:
- 🐛 **Bug reports** and feature requests
- 📖 **Documentation** improvements  
- 🧪 **Tests** for better coverage
- ✨ **New features** and enhancements
- 🔧 **Bug fixes** and optimizations

## 📋 Getting Started

### Prerequisites

- **macOS 10.15+** (for Safari integration testing)
- **Python 3.11+**
- **Git** for version control
- **OpenAI API key** for testing AI features

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/ombm.git
   cd ombm
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install webkit
   ```

5. **Set up pre-commit hooks (optional but recommended):**
   ```bash
   pre-commit install
   ```

6. **Verify setup:**
   ```bash
   pytest --version
   ombm --version
   ```

### Project Structure

```
ombm/
├── ombm/                   # Main package
│   ├── __init__.py
│   ├── __main__.py        # CLI entrypoint
│   ├── controller.py      # Main orchestration
│   ├── pipeline.py        # Processing pipeline
│   ├── llm.py            # OpenAI integration
│   ├── scraper.py        # Web scraping
│   ├── cache.py          # SQLite caching
│   ├── keychain.py       # Secure key storage
│   ├── models.py         # Data models
│   ├── logging.py        # Structured logging
│   └── prompts/          # LLM prompt templates
├── tests/                 # Test suite
├── docs/                  # Documentation
└── pyproject.toml        # Project configuration
```

## 🔄 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-chrome-support`
- `fix/rate-limit-handling`
- `docs/update-readme`

### 2. Make Your Changes

Follow our coding standards (see below) and write tests for new functionality.

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ombm

# Run specific test file
pytest tests/test_main.py -v

# Run linting
ruff check .
ruff format .

# Type checking
mypy ombm/
```

### 4. Commit Your Changes

Use clear, descriptive commit messages following [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git add .
git commit -m "feat: add support for Chrome bookmarks"
```

**Commit Types:**
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `style:` Code style changes
- `chore:` Build process or auxiliary tool changes

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable

## 📏 Coding Standards

### Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Format code
ruff format .

# Check for issues
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Type Hints

All new code should include type hints:

```python
def process_bookmarks(
    bookmarks: list[BookmarkRecord],
    concurrency: int = 4
) -> list[LLMMetadata]:
    """Process bookmarks with type hints."""
    pass
```

### Documentation

- Use clear docstrings for all public functions and classes
- Follow Google-style docstring format
- Include type information and examples when helpful

```python
def generate_title(url: str, content: str) -> str:
    """Generate semantic title for bookmark.
    
    Args:
        url: The bookmark URL
        content: Extracted text content
        
    Returns:
        Generated semantic title
        
    Raises:
        LLMError: If title generation fails
    """
    pass
```

### Error Handling

- Use specific exception types
- Provide helpful error messages
- Log errors appropriately

```python
try:
    result = await scrape_url(url)
except TimeoutError as e:
    logger.warning(f"Timeout scraping {url}: {e}")
    raise ScrapingError(f"Failed to scrape {url}") from e
```

## 🧪 Testing Guidelines

### Test Structure

- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test component interactions
- **E2E tests**: Test full workflows (use sparingly)

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch

class TestBookmarkProcessor:
    def test_process_bookmark_success(self):
        """Test successful bookmark processing."""
        # Arrange
        processor = BookmarkProcessor()
        bookmark = BookmarkRecord(...)
        
        # Act
        result = processor.process(bookmark)
        
        # Assert
        assert isinstance(result, LLMMetadata)
        assert result.name == "Expected Title"
```

### Test Categories

Mark tests with appropriate categories:

```python
@pytest.mark.integration
def test_full_pipeline():
    """Integration test for complete pipeline."""
    pass

@pytest.mark.slow
def test_large_dataset():
    """Test with large dataset (slow)."""
    pass
```

Run specific test categories:

```bash
# Run only unit tests (default)
pytest

# Run integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Mocking External Services

Always mock external services in tests:

```python
@patch('ombm.llm.openai.AsyncOpenAI')
def test_llm_service(mock_openai):
    """Test LLM service with mocked OpenAI."""
    mock_client = Mock()
    mock_openai.return_value = mock_client
    
    service = LLMService()
    # Test implementation...
```

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected vs actual behavior**
4. **Environment details:**
   - OMBM version (`ombm --version`)
   - Python version (`python --version`)
   - macOS version
5. **Relevant logs** from `~/.ombm/logs/`
6. **Example bookmark URLs** (if safe to share)

## ✨ Feature Requests

For feature requests:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** and motivation
3. **Provide examples** of how it would work
4. **Consider implementation complexity**
5. **Discuss breaking changes** if applicable

## 📚 Documentation Contributions

Documentation improvements are always welcome:

- Fix typos and grammar
- Add examples and use cases
- Improve clarity and organization
- Add troubleshooting sections

### Building Documentation Locally

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build documentation
mkdocs serve
```

## 🔍 Code Review Process

All contributions go through code review:

1. **Automated checks** must pass (tests, linting, type checking)
2. **Manual review** by maintainers
3. **Discussion** and iteration if needed
4. **Approval** and merge

### Review Criteria

- Code quality and style
- Test coverage
- Documentation updates
- Backward compatibility
- Performance impact

## 🎯 Development Priorities

See [docs/plan.md](docs/plan.md) for current development priorities and roadmap.

**Current focus areas:**
- Performance optimizations
- Browser compatibility (Chrome, Firefox)
- Advanced organization algorithms
- User experience improvements

## 🏷️ Release Process

Releases follow semantic versioning (SemVer):

- **Patch** (0.1.1): Bug fixes
- **Minor** (0.2.0): New features, backward compatible
- **Major** (1.0.0): Breaking changes

## 📞 Getting Help

Need help with development?

- **GitHub Discussions**: For questions and ideas
- **GitHub Issues**: For bug reports and feature requests
- **Code comments**: For specific implementation questions

## 🙏 Recognition

Contributors are recognized in:
- Release notes
- GitHub contributors page
- Project acknowledgments

Thank you for contributing to OMBM! 🚀

---

## Quick Reference

### Common Commands

```bash
# Setup
pip install -e ".[dev]"
playwright install webkit

# Development
pytest                    # Run tests
ruff format .            # Format code
ruff check .             # Lint code
mypy ombm/              # Type check

# Git workflow
git checkout -b feature/name
git commit -m "feat: description"
git push origin feature/name
```

### File Locations

- **Source code**: `ombm/`
- **Tests**: `tests/`
- **Configuration**: `pyproject.toml`
- **Documentation**: `docs/`
- **User config**: `~/.ombm/config.toml` 