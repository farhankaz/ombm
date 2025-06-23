# OMBM Quick Start Guide

Get your Safari bookmarks organized in 5 minutes!

## 🎯 What You'll Achieve

By the end of this guide, you'll have:
- ✅ OMBM installed and ready to use
- ✅ Your OpenAI API key securely stored
- ✅ Your first bookmark organization preview
- ✅ Knowledge of how to apply changes safely

## 📋 Prerequisites

Before starting, ensure you have:
- **macOS 10.15+** (Catalina or later)
- **Python 3.11+** (check with `python3 --version`)
- **Safari bookmarks** to organize
- **OpenAI API key** ([get one here](https://platform.openai.com/api-keys))

> **Don't have an OpenAI account?** Sign up at [OpenAI](https://platform.openai.com/signup) and add billing information to access the API.

## 🚀 Step 1: Install OMBM

Choose your preferred installation method:

### Option A: Homebrew (Recommended)
```bash
brew install ombm
```

### Option B: pipx (Isolated Installation)
```bash
# Install pipx if you don't have it
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install OMBM
pipx install ombm
```

### Option C: pip (Global Installation)
```bash
pip3 install ombm
```

**Verify installation:**
```bash
ombm --version
```

You should see the version number (e.g., `0.1.0`).

## 🔑 Step 2: Set Up Your API Key

### Get Your OpenAI API Key

1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Give it a name (e.g., "OMBM")
4. Copy the key (starts with `sk-...`)

### Store It Securely

OMBM can store your API key securely in macOS Keychain:

```bash
ombm set-key
```

When prompted, paste your API key. It will be stored securely and never displayed again.

**Verify it's stored:**
```bash
ombm key-status
```

You should see: ✅ OpenAI API key is stored in keychain.

> **Alternative:** You can also set the environment variable:
> ```bash
> export OPENAI_API_KEY="your-api-key-here"
> ```

## 🧪 Step 3: Your First Dry Run

Now let's organize your bookmarks! We'll start with a safe preview:

```bash
ombm organize
```

**What happens:**
1. OMBM extracts your Safari bookmarks
2. Scrapes content from each URL (this may take a few minutes)
3. Uses AI to generate semantic titles and descriptions
4. Creates a suggested folder hierarchy
5. Displays the results in a beautiful tree

**Example output:**
```
🔖 OMBM - Organize My Bookmarks
Version: 0.1.0
🔍 Running in dry-run mode (no changes will be made)

Step 1: Processing bookmarks...
[████████████████████████████████████████] 100% 25/25 bookmarks processed

Step 2: Generating taxonomy...
✓ Taxonomy generated successfully

Step 3: Building folder tree...

📂 Bookmarks
├── 💻 Development
│   ├── 🐍 Python Resources
│   │   ├── Django Documentation
│   │   └── Python.org Official Guide
│   └── 🌐 Web Development
│       ├── MDN Web Docs
│       └── CSS-Tricks
└── 📰 News & Articles
    ├── 🏛️ Politics
    │   └── BBC Politics
    └── 💰 Finance
        └── Financial Times

Total: 25 bookmarks in 7 folders
```

## ⚙️ Step 4: Customize Your Organization

Want to fine-tune the results? Try these options:

### Limit the Number of Bookmarks
```bash
# Process only the first 50 bookmarks
ombm organize --max 50
```

### Increase Processing Speed
```bash
# Use more concurrent workers
ombm organize --concurrency 8
```

### Verbose Output
```bash
# See detailed progress and debugging info
ombm organize --verbose
```

### Export to JSON
```bash
# Save the hierarchy to a file for review
ombm organize --json-out my-bookmarks.json
```

## 💾 Step 5: Apply the Changes

Once you're happy with the organization, apply it to Safari:

```bash
ombm organize --save
```

> **⚠️ Important:** This will modify your Safari bookmarks. OMBM creates a backup first, but it's good practice to export your bookmarks manually as well.

**Before applying changes:**
1. Open Safari > File > Export Bookmarks (manual backup)
2. Check that you're happy with the dry-run results
3. Run with `--save` flag

## 🎊 You're Done!

Congratulations! You've successfully organized your Safari bookmarks with OMBM.

**What just happened:**
- Your bookmarks are now organized into semantic folders
- Similar content is grouped together
- Each bookmark has an improved, descriptive title
- A backup was created before any changes

## 🔧 Next Steps

### Explore Advanced Features

**Work with cached data only:**
```bash
ombm organize --no-scrape
```

**Quiet mode for scripts:**
```bash
ombm organize --quiet --save
```

**Performance profiling:**
```bash
ombm organize --profile
```

### API Key Management

**Check key status:**
```bash
ombm key-status
```

**Update stored key:**
```bash
ombm delete-key
ombm set-key
```

### Configuration

OMBM stores its configuration in `~/.ombm/`:
- `config.toml` - Your preferences
- `cache.db` - Scraped content cache
- `logs/` - Application logs

## 🆘 Troubleshooting

### Common Issues

**"Permission denied accessing Safari"**
1. Open System Preferences > Security & Privacy > Privacy
2. Select "Automation" from the left sidebar  
3. Grant Terminal access to Safari

**"Rate limit exceeded"**
```bash
# Slow down the requests
ombm organize --concurrency 2

# Or process fewer bookmarks
ombm organize --max 25
```

**"No bookmarks found"**
- Ensure you have bookmarks in Safari
- Check that Safari is not running during the process

**Connection issues**
```bash
# Work with cached data only
ombm organize --no-scrape
```

### Getting Help

**View all commands:**
```bash
ombm --help
```

**Command-specific help:**
```bash
ombm organize --help
```

**Check logs:**
```bash
cat ~/.ombm/logs/ombm-$(date +%Y%m%d).log
```

## 💡 Tips for Best Results

1. **Start small:** Use `--max 50` for your first run
2. **Check the preview:** Always do a dry run first
3. **Backup manually:** Export bookmarks before using `--save`
4. **Use verbose mode:** Add `--verbose` to see what's happening
5. **Cache is your friend:** Re-runs are faster thanks to caching

## 🎯 What's Next?

- **Automate:** Set up a weekly cron job to re-organize
- **Customize:** Edit `~/.ombm/config.toml` for your preferences  
- **Integrate:** Use `--json-out` to feed data to other tools
- **Contribute:** Share feedback and feature requests

---

**Need more help?** Check the [full documentation](../README.md) or open an issue on GitHub.

Happy organizing! 🚀 