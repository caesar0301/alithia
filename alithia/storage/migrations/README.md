# Database Migrations

This directory contains SQL migration scripts for setting up the Alithia storage backend.

## Files

- `001_initial_schema.sql` - Initial database schema for all Alithia agents

## Running Migrations

### For Supabase

1. Log in to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy and paste the contents of `001_initial_schema.sql`
4. Click "Run" to execute the migration
5. Verify that all tables were created successfully in the Table Editor

### For Local PostgreSQL

```bash
psql -U your_username -d your_database -f alithia/storage/migrations/001_initial_schema.sql
```

### For SQLite

SQLite tables are created automatically by the `SQLiteStorage` class on first connection. No manual migration is needed.

## Schema Overview

### PaperScout Agent Tables

- **zotero_papers**: Cache of user's Zotero library (24-hour TTL)
- **arxiv_processed_ranges**: Tracks processed ArXiv date ranges for continuous coverage
- **arxiv_papers_emailed**: Deduplication table to prevent duplicate email notifications

### PaperLens Agent Tables

- **parsed_papers**: Cache of parsed PDF papers (indefinite, invalidated on file change)
- **query_history**: User query history for search and interaction tracking

## Maintenance

The migration includes cleanup functions that can be run periodically:

```sql
-- Clean up old Zotero cache (older than 7 days)
SELECT cleanup_old_zotero_cache();

-- Clean up old processed ranges (older than 90 days)
SELECT cleanup_old_processed_ranges();

-- Clean up rarely accessed parsed papers (not accessed in 180 days)
SELECT cleanup_old_parsed_papers();
```

You can set up a cron job in Supabase to run these automatically:

1. Go to Database → Cron Jobs
2. Add a new job with schedule `0 2 * * *` (runs at 2 AM daily)
3. Use the cleanup functions in the SQL command

## Security Notes

- User isolation is implemented via `user_id` column in all tables
- Row Level Security (RLS) policies are commented out in the migration
- If using Supabase with authentication, uncomment and customize RLS policies
- Never store sensitive credentials (API keys, passwords) in the database

