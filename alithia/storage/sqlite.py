"""
SQLite storage backend implementation (fallback).
"""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from cogents_core.utils import get_logger

from alithia.constants import DEFAULT_QUERY_HISTORY_LIMIT, DEFAULT_SQLITE_PATH

from .base import StorageBackend

logger = get_logger(__name__)


class SQLiteStorage(StorageBackend):
    """SQLite implementation of storage backend (fallback)."""

    def __init__(self, db_path: str = DEFAULT_SQLITE_PATH):
        """
        Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Establish connection to SQLite."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            self._create_tables()
            logger.info(f"Connected to SQLite database at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise

    def disconnect(self) -> None:
        """Close connection to SQLite."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Disconnected from SQLite")

    def test_connection(self) -> bool:
        """Test if connection is working."""
        try:
            if self.conn is None:
                return False
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"SQLite connection test failed: {e}")
            return False

    def _create_tables(self) -> None:
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()

        # Zotero papers cache
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS zotero_papers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                paper_title TEXT,
                paper_authors TEXT,
                paper_abstract TEXT,
                paper_url TEXT,
                zotero_item_key TEXT UNIQUE,
                tags TEXT,
                date_added TEXT,
                last_synced TEXT
            )
        """
        )

        # ArXiv processed ranges
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS arxiv_processed_ranges (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                from_date TEXT NOT NULL,
                to_date TEXT NOT NULL,
                query_categories TEXT NOT NULL,
                papers_found INTEGER,
                processed_at TEXT,
                UNIQUE(user_id, from_date, to_date, query_categories)
            )
        """
        )

        # ArXiv papers emailed
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS arxiv_papers_emailed (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                arxiv_id TEXT NOT NULL,
                paper_title TEXT,
                paper_authors TEXT,
                paper_summary TEXT,
                pdf_url TEXT,
                code_url TEXT,
                tldr TEXT,
                relevance_score REAL,
                published_date TEXT,
                emailed_at TEXT,
                UNIQUE(user_id, arxiv_id)
            )
        """
        )

        # Parsed papers cache
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS parsed_papers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                file_path TEXT,
                file_name TEXT,
                file_hash TEXT UNIQUE,
                paper_title TEXT,
                paper_authors TEXT,
                paper_abstract TEXT,
                full_text TEXT,
                sections TEXT,
                figures TEXT,
                tables TEXT,
                parsed_at TEXT,
                last_accessed TEXT
            )
        """
        )

        # Query history
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS query_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                paper_id TEXT,
                query_text TEXT,
                query_results TEXT,
                similarity_scores TEXT,
                queried_at TEXT,
                FOREIGN KEY (paper_id) REFERENCES parsed_papers(id)
            )
        """
        )

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_zotero_user ON zotero_papers(user_id, last_synced)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_arxiv_ranges_user ON arxiv_processed_ranges(user_id, query_categories)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_arxiv_emailed_user ON arxiv_papers_emailed(user_id, arxiv_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parsed_papers_hash ON parsed_papers(file_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_history_paper ON query_history(paper_id, queried_at)")

        self.conn.commit()

    def _dict_to_row(self, data: Dict[str, Any]) -> sqlite3.Row:
        """Convert dictionary to Row-like object for consistency."""
        return data

    # Zotero paper caching methods
    def cache_zotero_papers(self, user_id: str, papers: List[Dict[str, Any]]) -> None:
        """Cache Zotero papers for a user."""
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()

            for paper in papers:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO zotero_papers
                    (id, user_id, paper_title, paper_authors, paper_abstract,
                     paper_url, zotero_item_key, tags, date_added, last_synced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(uuid.uuid4()),
                        user_id,
                        paper.get("title", ""),
                        json.dumps(paper.get("authors", [])),
                        paper.get("abstract", ""),
                        paper.get("url", ""),
                        paper.get("zotero_item_key", ""),
                        json.dumps(paper.get("tags", [])),
                        paper.get("date_added", now),
                        now,
                    ),
                )

            self.conn.commit()
            logger.info(f"Cached {len(papers)} Zotero papers for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to cache Zotero papers: {e}")
            self.conn.rollback()
            raise

    def get_zotero_papers(self, user_id: str, max_age_hours: int = 24) -> Optional[List[Dict[str, Any]]]:
        """Get cached Zotero papers if they're fresh enough."""
        try:
            cursor = self.conn.cursor()
            cutoff_time = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()

            cursor.execute(
                """
                SELECT * FROM zotero_papers
                WHERE user_id = ? AND last_synced >= ?
                ORDER BY last_synced DESC
            """,
                (user_id, cutoff_time),
            )

            rows = cursor.fetchall()

            if not rows:
                logger.info(f"No fresh Zotero cache found for user {user_id}")
                return None

            logger.info(f"Retrieved {len(rows)} cached Zotero papers for user {user_id}")

            papers = []
            for row in rows:
                papers.append(
                    {
                        "title": row["paper_title"],
                        "authors": json.loads(row["paper_authors"]) if row["paper_authors"] else [],
                        "abstract": row["paper_abstract"],
                        "url": row["paper_url"],
                        "zotero_item_key": row["zotero_item_key"],
                        "tags": json.loads(row["tags"]) if row["tags"] else [],
                        "date_added": row["date_added"],
                    }
                )

            return papers

        except Exception as e:
            logger.error(f"Failed to get cached Zotero papers: {e}")
            return None

    # ArXiv processed ranges tracking
    def mark_date_range_processed(
        self,
        user_id: str,
        from_date: str,
        to_date: str,
        query_categories: str,
        papers_found: int,
    ) -> None:
        """Mark a date range as processed."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO arxiv_processed_ranges
                (id, user_id, from_date, to_date, query_categories, papers_found, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(uuid.uuid4()),
                    user_id,
                    from_date,
                    to_date,
                    query_categories,
                    papers_found,
                    datetime.utcnow().isoformat(),
                ),
            )

            self.conn.commit()
            logger.info(
                f"Marked date range {from_date}-{to_date} as processed " f"for user {user_id} ({papers_found} papers)"
            )

        except Exception as e:
            logger.error(f"Failed to mark date range as processed: {e}")
            self.conn.rollback()
            raise

    def get_processed_ranges(self, user_id: str, query_categories: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get processed date ranges for a user."""
        try:
            cursor = self.conn.cursor()
            cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y%m%d")

            cursor.execute(
                """
                SELECT from_date, to_date, papers_found, processed_at
                FROM arxiv_processed_ranges
                WHERE user_id = ? AND query_categories = ? AND from_date >= ?
                ORDER BY from_date DESC
            """,
                (user_id, query_categories, cutoff_date),
            )

            rows = cursor.fetchall()
            logger.info(f"Retrieved {len(rows)} processed ranges for user {user_id} (last {days_back} days)")

            return [
                {
                    "from_date": row["from_date"],
                    "to_date": row["to_date"],
                    "papers_found": row["papers_found"],
                    "processed_at": row["processed_at"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get processed ranges: {e}")
            return []

    # ArXiv papers emailed tracking
    def save_emailed_papers(self, user_id: str, papers: List[Dict[str, Any]]) -> None:
        """Save papers that were emailed to user."""
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()

            for paper in papers:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO arxiv_papers_emailed
                    (id, user_id, arxiv_id, paper_title, paper_authors, paper_summary,
                     pdf_url, code_url, tldr, relevance_score, published_date, emailed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(uuid.uuid4()),
                        user_id,
                        paper.get("arxiv_id", ""),
                        paper.get("title", ""),
                        json.dumps(paper.get("authors", [])),
                        paper.get("summary", ""),
                        paper.get("pdf_url", ""),
                        paper.get("code_url"),
                        paper.get("tldr"),
                        paper.get("relevance_score", 0.0),
                        paper.get("published_date"),
                        now,
                    ),
                )

            self.conn.commit()
            logger.info(f"Saved {len(papers)} emailed papers for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to save emailed papers: {e}")
            self.conn.rollback()
            raise

    def get_emailed_papers(
        self, user_id: str, arxiv_ids: Optional[List[str]] = None, days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """Get papers that were already emailed."""
        try:
            cursor = self.conn.cursor()
            cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

            if arxiv_ids:
                placeholders = ",".join("?" * len(arxiv_ids))
                cursor.execute(
                    f"""
                    SELECT * FROM arxiv_papers_emailed
                    WHERE user_id = ? AND arxiv_id IN ({placeholders}) AND emailed_at >= ?
                """,
                    [user_id] + arxiv_ids + [cutoff_date],
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM arxiv_papers_emailed
                    WHERE user_id = ? AND emailed_at >= ?
                    ORDER BY emailed_at DESC
                """,
                    (user_id, cutoff_date),
                )

            rows = cursor.fetchall()
            logger.info(f"Retrieved {len(rows)} emailed papers for user {user_id}")

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get emailed papers: {e}")
            return []

    def is_paper_emailed(self, user_id: str, arxiv_id: str) -> bool:
        """Check if a paper was already emailed."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM arxiv_papers_emailed
                WHERE user_id = ? AND arxiv_id = ?
                LIMIT 1
            """,
                (user_id, arxiv_id),
            )

            return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"Failed to check if paper was emailed: {e}")
            return False

    # PaperLens parsed papers caching
    def cache_parsed_paper(self, user_id: str, paper_data: Dict[str, Any]) -> str:
        """Cache a parsed paper."""
        try:
            cursor = self.conn.cursor()
            paper_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            cursor.execute(
                """
                INSERT OR REPLACE INTO parsed_papers
                (id, user_id, file_path, file_name, file_hash, paper_title,
                 paper_authors, paper_abstract, full_text, sections, figures,
                 tables, parsed_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    paper_id,
                    user_id,
                    paper_data.get("file_path", ""),
                    paper_data.get("file_name", ""),
                    paper_data.get("file_hash", ""),
                    paper_data.get("title"),
                    json.dumps(paper_data.get("authors", [])),
                    paper_data.get("abstract"),
                    paper_data.get("full_text", ""),
                    json.dumps(paper_data.get("sections", {})),
                    json.dumps(paper_data.get("figures", [])),
                    json.dumps(paper_data.get("tables", [])),
                    now,
                    now,
                ),
            )

            self.conn.commit()
            logger.info(f"Cached parsed paper {paper_id} for user {user_id}")
            return paper_id

        except Exception as e:
            logger.error(f"Failed to cache parsed paper: {e}")
            self.conn.rollback()
            raise

    def get_parsed_paper(self, user_id: str, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get a cached parsed paper by file hash."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT * FROM parsed_papers
                WHERE user_id = ? AND file_hash = ?
                LIMIT 1
            """,
                (user_id, file_hash),
            )

            row = cursor.fetchone()

            if not row:
                logger.info(f"No cached paper found for hash {file_hash}")
                return None

            # Update last_accessed time
            self.update_paper_access_time(row["id"])

            logger.info(f"Retrieved cached paper {row['id']} for user {user_id}")

            return {
                "id": row["id"],
                "file_path": row["file_path"],
                "file_name": row["file_name"],
                "file_hash": row["file_hash"],
                "title": row["paper_title"],
                "authors": json.loads(row["paper_authors"]) if row["paper_authors"] else [],
                "abstract": row["paper_abstract"],
                "full_text": row["full_text"],
                "sections": json.loads(row["sections"]) if row["sections"] else {},
                "figures": json.loads(row["figures"]) if row["figures"] else [],
                "tables": json.loads(row["tables"]) if row["tables"] else [],
                "parsed_at": row["parsed_at"],
            }

        except Exception as e:
            logger.error(f"Failed to get cached paper: {e}")
            return None

    def update_paper_access_time(self, paper_id: str) -> None:
        """Update the last_accessed timestamp for a paper."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE parsed_papers
                SET last_accessed = ?
                WHERE id = ?
            """,
                (datetime.utcnow().isoformat(), paper_id),
            )
            self.conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update paper access time: {e}")

    # PaperLens query history
    def save_query(
        self,
        user_id: str,
        paper_id: str,
        query_text: str,
        query_results: List[Dict[str, Any]],
        similarity_scores: Dict[str, float],
    ) -> None:
        """Save a query to history."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO query_history
                (id, user_id, paper_id, query_text, query_results, similarity_scores, queried_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(uuid.uuid4()),
                    user_id,
                    paper_id,
                    query_text,
                    json.dumps(query_results),
                    json.dumps(similarity_scores),
                    datetime.utcnow().isoformat(),
                ),
            )

            self.conn.commit()
            logger.info(f"Saved query for paper {paper_id}")

        except Exception as e:
            logger.error(f"Failed to save query: {e}")
            self.conn.rollback()
            raise

    def get_query_history(
        self, user_id: str, paper_id: Optional[str] = None, limit: int = DEFAULT_QUERY_HISTORY_LIMIT
    ) -> List[Dict[str, Any]]:
        """Get query history."""
        try:
            cursor = self.conn.cursor()

            if paper_id:
                cursor.execute(
                    """
                    SELECT * FROM query_history
                    WHERE user_id = ? AND paper_id = ?
                    ORDER BY queried_at DESC
                    LIMIT ?
                """,
                    (user_id, paper_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM query_history
                    WHERE user_id = ?
                    ORDER BY queried_at DESC
                    LIMIT ?
                """,
                    (user_id, limit),
                )

            rows = cursor.fetchall()
            logger.info(f"Retrieved {len(rows)} queries from history")

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get query history: {e}")
            return []
