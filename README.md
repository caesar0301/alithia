# Alithia

[![PyPI version](https://img.shields.io/pypi/v/alithia.svg)](https://pypi.org/project/alithia/)


Time is one of the most valuable resources for a human researcher, best spent
on thinking, exploring, and creating in the world of ideas. With Alithia, we
aim to open a new frontier in research assistance. Alithia aspires to be your
powerful research companion: from reading papers to pursuing interest-driven
deep investigations, from reproducing experiments to detecting fabricated
results, from tracking down relevant papers to monitoring industrial
breakthroughs. At its core, Alithia forges a strong and instant link between your personal
research profile, the latest state-of-the-art developments, and pervasive cloud
resources, ensuring you stay informed, empowered, and ahead.

## Features

In Alithia, we connect each researcher’s profile with publicly available academic resources, leveraging widely accessible cloud infrastructure to automate the entire process. In its current version, Alithia is designed to support the following features:

* Reseacher Profile
  * Basic profile: research interests, expertise, language
  * Connected (personal) services:
    * LLM (OpenAI compatible)
    * Zotero library
    * Email notification
    * Github profile
    * Google scholar profile
    * X account message stream
  * Gems (general research digest or ideas)
* Academic Resources
  * arXiv papers
  * Google scholar search
  * Web search engines (e.g., tavily)
  * Individual researcher homepage

## Installation

Alithia uses optional dependencies to keep the base installation lightweight. The default installation includes Arxrec agent dependencies.

### Recommended: Default Installation

For most users, install with default dependencies (includes Arxrec agent: ArXiv fetching, Zotero integration, email notifications, etc.):

```bash
pip install alithia[default]
```

This installs:
- `arxiv` - ArXiv paper fetching
- `pyzotero` - Zotero library integration
- `scikit-learn` - Machine learning utilities
- `sentence-transformers` - Embedding models
- `feedparser` - RSS feed parsing
- `beautifulsoup4` & `lxml` - Web scraping
- `tiktoken` - Token counting
- And other Arxrec dependencies

**Note:** `alithia[arxrec]` is an alias for `alithia[default]` and works the same way.

### Minimal Installation

Install only the core library (includes `cogents-core` only, no Arxrec features):

```bash
pip install alithia
```

⚠️ **Warning:** This minimal installation does not include Arxrec agent dependencies. Most users should use `alithia[default]` instead.

### Install with PaperLens Support

For PDF analysis and deep paper interaction:

```bash
pip install alithia[paperlens]
```

This installs:
- `docling` - PDF parsing and OCR
- `onnxruntime` - Model inference

### Install All Features

Install everything (Default/Arxrec + PaperLens):

```bash
pip install alithia[all]
```

### Development Installation

For development, clone the repository and install with development dependencies:

```bash
git clone https://github.com/caesar0301/alithia.git
cd alithia
uv sync --extra default --extra dev
```

Or using pip:

```bash
pip install -e ".[default,dev]"
```

**Note:** You can also use `alithia[arxrec,dev]` as `arxrec` is an alias for `default`.

## Quick Start

### 1. Setup Arxrec Agent

The Arxrec Agent delivers daily paper recommendations from arXiv to your inbox.

**Prerequisites:**
1. **Zotero Account**: [Sign up](https://www.zotero.org) and get your user ID and API key from Settings → Feeds/API
2. **OpenAI API Key**: From any OpenAI-compatible LLM provider
3. **Email (Gmail)**: Enable 2FA and generate an App Password

**GitHub Actions Setup:**
1. Fork this repository
2. Go to Settings → Secrets and variables → Actions
3. Add secret `ALITHIA_CONFIG_JSON` with your configuration (see below)
4. Agent runs automatically daily at 01:00 UTC

### 2. Configuration

Create a JSON configuration with your credentials. See [alithia_config_example.json](alithia_config_example.json) for a complete example.

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request
