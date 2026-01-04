-- Initial schema for Alithia storage backend
-- This schema is designed for PostgreSQL (Supabase), but can be adapted for other databases

-- Enable UUID extension (PostgreSQL/Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PAPERSCOUT AGENT TABLES
-- ============================================================================

-- Table: zotero_papers
-- Purpose: Cache Zotero library papers to avoid frequent API calls
-- Expiration: 24 hours (application-level)
CREATE TABLE IF NOT EXISTS zotero_papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    paper_title TEXT,
    paper_authors JSONB DEFAULT '[]'::jsonb,
    paper_abstract TEXT,
    paper_url TEXT,
    zotero_item_key TEXT NOT NULL UNIQUE,  -- Unique Zotero item identifier
    tags JSONB DEFAULT '[]'::jsonb,
    date_added TIMESTAMPTZ,
    last_synced TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT zotero_papers_item_key_unique UNIQUE (zotero_item_key)
);

CREATE INDEX IF NOT EXISTS idx_zotero_papers_user_synced 
    ON zotero_papers(user_id, last_synced DESC);

COMMENT ON TABLE zotero_papers IS 'Cached Zotero library papers for each user';
COMMENT ON COLUMN zotero_papers.user_id IS 'User identifier from config';
COMMENT ON COLUMN zotero_papers.zotero_item_key IS 'Unique Zotero item key for deduplication';
COMMENT ON COLUMN zotero_papers.last_synced IS 'When this paper was last synced from Zotero';

-- Table: arxiv_processed_ranges
-- Purpose: Track date ranges that have been processed to handle ArXiv indexing delays
-- This ensures continuous paper coverage even when ArXiv has indexing delays
CREATE TABLE IF NOT EXISTS arxiv_processed_ranges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    from_date DATE NOT NULL,                    -- Start date of processed range (YYYYMMDD)
    to_date DATE NOT NULL,                      -- End date of processed range (YYYYMMDD)
    query_categories TEXT NOT NULL,             -- ArXiv categories (e.g., "cs.AI+cs.CV")
    papers_found INTEGER DEFAULT 0,             -- Number of papers found in this range
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Prevent duplicate processing of same date range
    CONSTRAINT arxiv_processed_ranges_unique 
        UNIQUE (user_id, from_date, to_date, query_categories)
);

CREATE INDEX IF NOT EXISTS idx_arxiv_ranges_user_cat 
    ON arxiv_processed_ranges(user_id, query_categories, from_date DESC);

COMMENT ON TABLE arxiv_processed_ranges IS 'Track processed ArXiv date ranges for continuous coverage';
COMMENT ON COLUMN arxiv_processed_ranges.from_date IS 'Start date in YYYYMMDD format';
COMMENT ON COLUMN arxiv_processed_ranges.to_date IS 'End date in YYYYMMDD format';
COMMENT ON COLUMN arxiv_processed_ranges.query_categories IS 'ArXiv query categories used';

-- Table: arxiv_papers_emailed
-- Purpose: Track papers that have been emailed to users to prevent duplicates
CREATE TABLE IF NOT EXISTS arxiv_papers_emailed (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    arxiv_id TEXT NOT NULL,                     -- ArXiv paper ID (e.g., "2301.12345")
    paper_title TEXT,
    paper_authors JSONB DEFAULT '[]'::jsonb,
    paper_summary TEXT,
    pdf_url TEXT,
    code_url TEXT,                              -- GitHub/code repository URL (optional)
    tldr TEXT,                                   -- Generated TLDR summary (optional)
    relevance_score REAL,                       -- Computed relevance score
    published_date TIMESTAMPTZ,                 -- ArXiv publication date
    emailed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Prevent duplicate emails for same paper to same user
    CONSTRAINT arxiv_papers_emailed_unique 
        UNIQUE (user_id, arxiv_id)
);

CREATE INDEX IF NOT EXISTS idx_arxiv_emailed_user_id 
    ON arxiv_papers_emailed(user_id, arxiv_id);
CREATE INDEX IF NOT EXISTS idx_arxiv_emailed_date 
    ON arxiv_papers_emailed(user_id, emailed_at DESC);

COMMENT ON TABLE arxiv_papers_emailed IS 'Papers that have been emailed to users (deduplication)';
COMMENT ON COLUMN arxiv_papers_emailed.arxiv_id IS 'ArXiv paper ID without version (e.g., 2301.12345)';
COMMENT ON COLUMN arxiv_papers_emailed.relevance_score IS 'Computed relevance score from reranker';

-- ============================================================================
-- PAPERLENS AGENT TABLES
-- ============================================================================

-- Table: parsed_papers
-- Purpose: Cache parsed PDF papers to avoid expensive re-parsing
-- Expiration: None (cached indefinitely until file changes)
CREATE TABLE IF NOT EXISTS parsed_papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,             -- MD5 hash for change detection
    paper_title TEXT,
    paper_authors JSONB DEFAULT '[]'::jsonb,
    paper_abstract TEXT,
    full_text TEXT,                             -- Complete extracted text
    sections JSONB DEFAULT '{}'::jsonb,         -- Section name -> content mapping
    figures JSONB DEFAULT '[]'::jsonb,          -- List of figure descriptions/captions
    tables JSONB DEFAULT '[]'::jsonb,           -- List of table descriptions/captions
    parsed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT parsed_papers_hash_unique UNIQUE (file_hash)
);

CREATE INDEX IF NOT EXISTS idx_parsed_papers_user_hash 
    ON parsed_papers(user_id, file_hash);
CREATE INDEX IF NOT EXISTS idx_parsed_papers_accessed 
    ON parsed_papers(last_accessed DESC);

COMMENT ON TABLE parsed_papers IS 'Cached parsed PDF papers to avoid re-parsing';
COMMENT ON COLUMN parsed_papers.file_hash IS 'MD5 hash of PDF file for change detection';
COMMENT ON COLUMN parsed_papers.full_text IS 'Complete extracted text from PDF';
COMMENT ON COLUMN parsed_papers.sections IS 'JSON object mapping section names to content';
COMMENT ON COLUMN parsed_papers.last_accessed IS 'Last time this cached paper was accessed';

-- Table: query_history
-- Purpose: Store user queries and results for PaperLens interactions
CREATE TABLE IF NOT EXISTS query_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    paper_id UUID REFERENCES parsed_papers(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    query_results JSONB DEFAULT '[]'::jsonb,    -- List of search results
    similarity_scores JSONB DEFAULT '{}'::jsonb, -- Section/chunk ID -> similarity score
    queried_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_history_paper 
    ON query_history(paper_id, queried_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_user 
    ON query_history(user_id, queried_at DESC);

COMMENT ON TABLE query_history IS 'User query history for PaperLens interactions';
COMMENT ON COLUMN query_history.paper_id IS 'Reference to the parsed paper';
COMMENT ON COLUMN query_history.query_results IS 'JSON array of search result objects';
COMMENT ON COLUMN query_history.similarity_scores IS 'JSON object mapping chunk IDs to scores';

-- ============================================================================
-- SECURITY & PERFORMANCE
-- ============================================================================

-- Enable Row Level Security (RLS) for multi-user isolation
-- Note: This requires proper user authentication setup in Supabase
-- Uncomment these if you're using Supabase with authentication

-- ALTER TABLE zotero_papers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE arxiv_processed_ranges ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE arxiv_papers_emailed ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE parsed_papers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (adjust based on your auth setup):
-- CREATE POLICY "Users can only access their own data" ON zotero_papers
--     FOR ALL USING (user_id = current_setting('app.user_id')::TEXT);

-- ============================================================================
-- CLEANUP FUNCTIONS
-- ============================================================================

-- Function to clean up old Zotero cache (older than 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_zotero_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM zotero_papers
    WHERE last_synced < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_zotero_cache IS 'Delete Zotero cache older than 7 days';

-- Function to clean up old processed ranges (older than 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_processed_ranges()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM arxiv_processed_ranges
    WHERE processed_at < NOW() - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_processed_ranges IS 'Delete processed ranges older than 90 days';

-- Function to clean up rarely accessed parsed papers (not accessed in 180 days)
CREATE OR REPLACE FUNCTION cleanup_old_parsed_papers()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM parsed_papers
    WHERE last_accessed < NOW() - INTERVAL '180 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_parsed_papers IS 'Delete parsed papers not accessed in 180 days';

-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================

-- Grant necessary permissions (adjust based on your setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;

