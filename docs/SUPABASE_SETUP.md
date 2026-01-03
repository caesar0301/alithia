# Supabase Setup Guide for Alithia

This guide walks you through setting up Supabase as the storage backend for Alithia agents.

## Overview

Alithia uses Supabase (PostgreSQL) as the default stateful storage backend, with SQLite as an automatic fallback. This enables:

- **Persistent caching** of Zotero libraries and parsed papers
- **Continuous paper feeding** that handles ArXiv indexing delays
- **Deduplication** to prevent duplicate email notifications
- **Query history** tracking for PaperLens interactions

## Prerequisites

- A Supabase account (free tier is sufficient for personal use)
- Python 3.11 or higher
- Alithia installed with dependencies

## Step 1: Create a Supabase Project

1. Go to [Supabase](https://supabase.com) and sign in
2. Click "New Project"
3. Choose your organization and provide:
   - Project name (e.g., "alithia-storage")
   - Database password (save this securely)
   - Region (choose closest to you)
4. Click "Create new project" and wait for setup to complete (1-2 minutes)

## Step 2: Run Database Migrations

1. In your Supabase project dashboard, navigate to **SQL Editor**
2. Click "New Query"
3. Copy the entire contents of `alithia/storage/migrations/001_initial_schema.sql`
4. Paste into the SQL editor
5. Click "Run" to execute the migration

This will create all necessary tables:
- `zotero_papers` - Cached Zotero library
- `arxiv_processed_ranges` - Tracks processed date ranges
- `arxiv_papers_emailed` - Deduplication for emails
- `parsed_papers` - Cached parsed PDFs
- `query_history` - PaperLens query tracking

## Step 3: Get Your Credentials

1. In your Supabase dashboard, go to **Settings** → **API**
2. Copy the following values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon public key** (for basic operations)
   - **service_role secret key** (for full access - keep this secure!)

## Step 4: Configure Alithia

### Option 1: Configuration File (Recommended)

Edit your `alithia_config.json`:

```json
{
  "storage": {
    "backend": "supabase",
    "fallback_to_sqlite": true,
    "sqlite_path": "data/alithia.db",
    "user_id": "your_email@example.com"
  },
  "supabase": {
    "url": "https://xxxxx.supabase.co",
    "anon_key": "your_anon_key_here",
    "service_role_key": "your_service_role_key_here"
  }
}
```

### Option 2: Environment Variables

```bash
export ALITHIA_SUPABASE_URL="https://xxxxx.supabase.co"
export ALITHIA_SUPABASE_ANON_KEY="your_anon_key"
export ALITHIA_SUPABASE_SERVICE_KEY="your_service_role_key"
export ALITHIA_STORAGE_BACKEND="supabase"
export ALITHIA_STORAGE_FALLBACK="true"
```

## Step 5: Verify Connection

Run a simple test to verify the connection:

```python
from alithia.storage.factory import get_storage_backend
from alithia.config_loader import load_config

# Load configuration
config = load_config("alithia_config.json")

# Create storage backend
storage = get_storage_backend(config)

# Test connection
if storage.test_connection():
    print("✓ Successfully connected to Supabase!")
else:
    print("✗ Connection failed")

storage.disconnect()
```

## Configuration Options

### Storage Backend Selection

- **`storage.backend`**: `"supabase"` or `"sqlite"`
  - Default: `"supabase"`
  - Use `"sqlite"` to bypass Supabase entirely

- **`storage.fallback_to_sqlite`**: `true` or `false`
  - Default: `true`
  - If true, automatically falls back to SQLite if Supabase fails

- **`storage.sqlite_path`**: Path to SQLite database file
  - Default: `"data/alithia.db"`
  - Used for fallback or when `backend="sqlite"`

- **`storage.user_id`**: Identifier for multi-user setups
  - Default: Uses email from config
  - All data is isolated by user_id

### Supabase Credentials

- **`supabase.url`**: Your Supabase project URL
- **`supabase.anon_key`**: Public API key (safe for client-side)
- **`supabase.service_role_key`**: Private API key (full access)

**Security Note**: Never commit your `service_role_key` to version control. Use environment variables or a `.gitignore`'d config file.

## Usage Examples

### PaperScout Agent with Storage

The PaperScout agent automatically uses storage when configured:

```bash
# Storage is automatically initialized
python -m alithia.run paperscout_agent -c alithia_config.json
```

Behind the scenes:
- ✓ Caches Zotero library (24-hour TTL)
- ✓ Tracks processed ArXiv date ranges
- ✓ Prevents duplicate emails
- ✓ Handles ArXiv indexing delays

### PaperLens Agent with Storage

Enable storage when creating the engine:

```python
from alithia.paperlens.engine import PaperLensEngine
from alithia.storage.factory import get_storage_backend
from alithia.config_loader import load_config

# Load config and create storage
config = load_config()
storage = get_storage_backend(config)

# Create engine with storage
engine = PaperLensEngine(
    storage=storage,
    user_id=config.get("storage", {}).get("user_id", "default_user")
)

# Parse PDFs (automatically cached)
papers = engine.scan_pdf_directory(pdf_dir)
```

Benefits:
- ✓ Caches parsed PDFs (expensive operation)
- ✓ Skips re-parsing if file hasn't changed
- ✓ Tracks query history for analysis

## Maintenance

### Cleanup Old Data

The migration includes cleanup functions. Run periodically:

```sql
-- Clean up old Zotero cache (older than 7 days)
SELECT cleanup_old_zotero_cache();

-- Clean up old processed ranges (older than 90 days)
SELECT cleanup_old_processed_ranges();

-- Clean up rarely accessed parsed papers (not accessed in 180 days)
SELECT cleanup_old_parsed_papers();
```

### Automated Cleanup with Cron Jobs

In Supabase dashboard:
1. Go to **Database** → **Cron Jobs**
2. Click "Create a new cron job"
3. Schedule: `0 2 * * *` (runs at 2 AM daily)
4. SQL:
```sql
SELECT cleanup_old_zotero_cache();
SELECT cleanup_old_processed_ranges();
SELECT cleanup_old_parsed_papers();
```

### Monitor Storage Usage

Check your Supabase dashboard → **Database** → **Database** for:
- Table sizes
- Row counts
- Index efficiency

## Troubleshooting

### Connection Fails

**Problem**: "Failed to connect to Supabase"

**Solutions**:
1. Verify your credentials are correct
2. Check that your IP is allowed (Supabase → Settings → Database → Connection Pooling)
3. Ensure tables were created (run migration again if needed)
4. Check Supabase project status (it may be paused on free tier)

### Automatic Fallback to SQLite

If you see "Using SQLite storage" in logs:
- Supabase credentials may be missing or incorrect
- Network connection issues
- Supabase project may be paused

This is expected behavior when `fallback_to_sqlite: true`.

### Row Level Security (RLS) Issues

If using Supabase authentication:
1. Uncomment RLS policies in migration file
2. Customize policies for your auth setup
3. Re-run migration

### Performance Issues

For large datasets:
- Consider adding indexes (see migration file for examples)
- Use connection pooling in Supabase settings
- Increase batch sizes in storage operations

## Security Best Practices

1. **Never commit credentials**: Use environment variables or `.gitignore`'d config files
2. **Use service_role_key carefully**: Only in server-side code, never in client apps
3. **Enable RLS**: If sharing Supabase project with others
4. **Rotate keys**: Periodically regenerate API keys in Supabase dashboard
5. **Backup data**: Use Supabase's daily backups feature (Settings → Database)

## SQLite Fallback

If you prefer not to use Supabase:

```json
{
  "storage": {
    "backend": "sqlite",
    "sqlite_path": "data/alithia.db"
  }
}
```

SQLite provides:
- ✓ No external dependencies
- ✓ Single-file database
- ✓ Automatic table creation
- ✓ Same API as Supabase storage

Limitations:
- ✗ No cloud sync
- ✗ Single-machine only
- ✗ No automatic backups

## Advanced Configuration

### Custom Table Names

Modify `alithia/storage/supabase.py` to use custom table names:

```python
# Change table names in SupabaseStorage methods
self.manager.query_records("my_custom_zotero_table", ...)
```

### Multi-User Setup

Use different `user_id` values for each user:

```json
{
  "storage": {
    "user_id": "user1@example.com"
  }
}
```

All data is automatically isolated by `user_id`.

### Connection Pooling

For high-traffic scenarios, configure connection pooling in Supabase:
1. Go to Settings → Database → Connection Pooling
2. Enable pooler
3. Use pooler connection string in config

## Support

For issues or questions:
- GitHub Issues: https://github.com/caesar0301/alithia/issues
- Documentation: See project README
- Supabase Docs: https://supabase.com/docs

