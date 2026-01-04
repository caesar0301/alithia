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

Alithia uses optional dependencies to keep the base installation lightweight. The default installation includes PaperScout agent dependencies.

### Recommended: Default Installation

For most users, install with default dependencies (includes PaperScout agent: ArXiv fetching, Zotero integration, email notifications, etc.):

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
- And other PaperScout dependencies

**Note:** `alithia[paperscout]` is an alias for `alithia[default]` and works the same way.

### Minimal Installation

Install only the core library (includes `cogents-core` only, no PaperScout features):

```bash
pip install alithia
```

⚠️ **Warning:** This minimal installation does not include PaperScout agent dependencies. Most users should use `alithia[default]` instead.

### Install with PaperLens Support

For PDF analysis and deep paper interaction:

```bash
pip install alithia[paperlens]
```

This installs:
- `docling` - PDF parsing and OCR
- `onnxruntime` - Model inference

### Install All Features

Install everything (Default/PaperScout + PaperLens):

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

**Note:** You can also use `alithia[paperscout,dev]` as `paperscout` is an alias for `default`.

## Quick Start

### 1. Setup PaperScout Agent

The PaperScout Agent delivers daily paper recommendations from arXiv to your inbox.

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

## Storage Backend

Alithia uses **Supabase** (PostgreSQL) as the default stateful storage backend, with automatic fallback to **SQLite** when Supabase is unavailable. This enables:

- **Persistent caching** of Zotero libraries and parsed papers
- **Continuous paper feeding** that handles ArXiv indexing delays
- **Deduplication** to prevent duplicate email notifications  
- **Query history** tracking for PaperLens interactions

### Quick Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com) (free tier available)
2. **Run the migration**: Copy contents of `alithia/storage/migrations/001_initial_schema.sql` to Supabase SQL Editor
3. **Configure Alithia**: Add Supabase credentials to your config:

```json
{
  "storage": {
    "backend": "supabase",
    "fallback_to_sqlite": true,
    "user_id": "your_email@example.com"
  },
  "supabase": {
    "url": "https://xxxxx.supabase.co",
    "anon_key": "your_anon_key",
    "service_role_key": "your_service_role_key"
  }
}
```

### Storage Options

- **Supabase (default)**: Cloud PostgreSQL with automatic backups, full-text search, and multi-user support
- **SQLite (fallback)**: Local single-file database, works offline, no setup required

For detailed setup instructions, see [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md).

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request
