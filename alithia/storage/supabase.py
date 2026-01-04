"""
Supabase storage backend implementation.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from cogents_core.utils import get_logger

from alithia.constants import DEFAULT_QUERY_HISTORY_LIMIT
from alithia.utils.supabase_client import SupabaseClientManager

from .base import StorageBackend

logger = get_logger(__name__)


class SupabaseStorage(StorageBackend):
    """Supabase implementation of storage backend."""

    def __init__(self, url: str, key: str):
        """
        Initialize Supabase storage.

        Args:
            url: Supabase project URL
            key: Supabase API key
        """
        self.manager = SupabaseClientManager(url, key)
        self._connected = False

    def connect(self) -> None:
        """Establish connection to Supabase."""
        try:
            if self.manager.test_connection():
                self._connected = True
                logger.info("Connected to Supabase successfully")
            else:
                raise ConnectionError("Failed to connect to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

    def disconnect(self) -> None:
        """Close connection to Supabase."""
        self._connected = False
        logger.info("Disconnected from Supabase")

    def test_connection(self) -> bool:
        """Test if connection is working."""
        return self.manager.test_connection()

    # Zotero paper caching methods
    def cache_zotero_papers(self, user_id: str, papers: List[Dict[str, Any]]) -> None:
        """Cache Zotero papers for a user."""
        try:
            records = []
            now = datetime.utcnow().isoformat()

            for paper in papers:
                record = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "paper_title": paper.get("title", ""),
                    "paper_authors": paper.get("authors", []),
                    "paper_abstract": paper.get("abstract", ""),
                    "paper_url": paper.get("url", ""),
                    "zotero_item_key": paper.get("zotero_item_key", ""),
                    "tags": paper.get("tags", []),
                    "date_added": paper.get("date_added", now),
                    "last_synced": now,
                }
                records.append(record)

            # Upsert using zotero_item_key as conflict column
            self.manager.upsert_records("zotero_papers", records, conflict_columns=["zotero_item_key"])
            logger.info(f"Cached {len(records)} Zotero papers for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to cache Zotero papers: {e}")
            raise

    def get_zotero_papers(self, user_id: str, max_age_hours: int = 24) -> Optional[List[Dict[str, Any]]]:
        """Get cached Zotero papers if they're fresh enough."""
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()

            # Query papers that were synced recently
            records = self.manager.query_records(
                "zotero_papers",
                filters={"user_id": user_id},
                order_by="-last_synced",
            )

            # Filter by last_synced time
            fresh_records = [r for r in records if r.get("last_synced", "") >= cutoff_time]

            if not fresh_records:
                logger.info(f"No fresh Zotero cache found for user {user_id}")
                return None

            logger.info(f"Retrieved {len(fresh_records)} cached Zotero papers for user {user_id}")

            # Convert back to expected format
            papers = []
            for record in fresh_records:
                papers.append(
                    {
                        "title": record.get("paper_title", ""),
                        "authors": record.get("paper_authors", []),
                        "abstract": record.get("paper_abstract", ""),
                        "url": record.get("paper_url", ""),
                        "zotero_item_key": record.get("zotero_item_key", ""),
                        "tags": record.get("tags", []),
                        "date_added": record.get("date_added"),
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
            record = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "from_date": from_date,
                "to_date": to_date,
                "query_categories": query_categories,
                "papers_found": papers_found,
                "processed_at": datetime.utcnow().isoformat(),
            }

            # Upsert to avoid duplicates
            self.manager.upsert_record(
                "arxiv_processed_ranges",
                record,
                conflict_columns=["user_id", "from_date", "to_date", "query_categories"],
            )

            logger.info(
                f"Marked date range {from_date}-{to_date} as processed " f"for user {user_id} ({papers_found} papers)"
            )

        except Exception as e:
            logger.error(f"Failed to mark date range as processed: {e}")
            raise

    def get_processed_ranges(self, user_id: str, query_categories: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get processed date ranges for a user."""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y%m%d")

            records = self.manager.query_records(
                "arxiv_processed_ranges",
                filters={"user_id": user_id, "query_categories": query_categories},
                order_by="-from_date",
            )

            # Filter by date
            recent_records = [r for r in records if r.get("from_date", "") >= cutoff_date]

            logger.info(
                f"Retrieved {len(recent_records)} processed ranges for user {user_id} " f"(last {days_back} days)"
            )

            return [
                {
                    "from_date": r.get("from_date"),
                    "to_date": r.get("to_date"),
                    "papers_found": r.get("papers_found", 0),
                    "processed_at": r.get("processed_at"),
                }
                for r in recent_records
            ]

        except Exception as e:
            logger.error(f"Failed to get processed ranges: {e}")
            return []

    # ArXiv papers emailed tracking
    def save_emailed_papers(self, user_id: str, papers: List[Dict[str, Any]]) -> None:
        """Save papers that were emailed to user."""
        try:
            records = []
            now = datetime.utcnow().isoformat()

            for paper in papers:
                record = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "arxiv_id": paper.get("arxiv_id", ""),
                    "paper_title": paper.get("title", ""),
                    "paper_authors": paper.get("authors", []),
                    "paper_summary": paper.get("summary", ""),
                    "pdf_url": paper.get("pdf_url", ""),
                    "code_url": paper.get("code_url"),
                    "tldr": paper.get("tldr"),
                    "relevance_score": paper.get("relevance_score", 0.0),
                    "published_date": paper.get("published_date"),
                    "emailed_at": now,
                }
                records.append(record)

            # Upsert to avoid duplicates
            self.manager.upsert_records("arxiv_papers_emailed", records, conflict_columns=["user_id", "arxiv_id"])

            logger.info(f"Saved {len(records)} emailed papers for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to save emailed papers: {e}")
            raise

    def get_emailed_papers(
        self, user_id: str, arxiv_ids: Optional[List[str]] = None, days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """Get papers that were already emailed."""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

            if arxiv_ids:
                # Query specific papers
                all_records = []
                for arxiv_id in arxiv_ids:
                    records = self.manager.query_records(
                        "arxiv_papers_emailed",
                        filters={"user_id": user_id, "arxiv_id": arxiv_id},
                    )
                    all_records.extend(records)
            else:
                # Query all papers for user
                all_records = self.manager.query_records(
                    "arxiv_papers_emailed",
                    filters={"user_id": user_id},
                    order_by="-emailed_at",
                )

            # Filter by date
            recent_records = [r for r in all_records if r.get("emailed_at", "") >= cutoff_date]

            logger.info(f"Retrieved {len(recent_records)} emailed papers for user {user_id}")

            return recent_records

        except Exception as e:
            logger.error(f"Failed to get emailed papers: {e}")
            return []

    def is_paper_emailed(self, user_id: str, arxiv_id: str) -> bool:
        """Check if a paper was already emailed."""
        try:
            records = self.manager.query_records(
                "arxiv_papers_emailed",
                filters={"user_id": user_id, "arxiv_id": arxiv_id},
                limit=1,
            )
            return len(records) > 0

        except Exception as e:
            logger.error(f"Failed to check if paper was emailed: {e}")
            return False

    # PaperLens parsed papers caching
    def cache_parsed_paper(self, user_id: str, paper_data: Dict[str, Any]) -> str:
        """Cache a parsed paper."""
        try:
            paper_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            record = {
                "id": paper_id,
                "user_id": user_id,
                "file_path": paper_data.get("file_path", ""),
                "file_name": paper_data.get("file_name", ""),
                "file_hash": paper_data.get("file_hash", ""),
                "paper_title": paper_data.get("title"),
                "paper_authors": paper_data.get("authors", []),
                "paper_abstract": paper_data.get("abstract"),
                "full_text": paper_data.get("full_text", ""),
                "sections": paper_data.get("sections", {}),
                "figures": paper_data.get("figures", []),
                "tables": paper_data.get("tables", []),
                "parsed_at": now,
                "last_accessed": now,
            }

            # Upsert using file_hash as conflict column
            self.manager.upsert_record("parsed_papers", record, conflict_columns=["file_hash"])

            logger.info(f"Cached parsed paper {paper_id} for user {user_id}")
            return paper_id

        except Exception as e:
            logger.error(f"Failed to cache parsed paper: {e}")
            raise

    def get_parsed_paper(self, user_id: str, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get a cached parsed paper by file hash."""
        try:
            records = self.manager.query_records(
                "parsed_papers",
                filters={"user_id": user_id, "file_hash": file_hash},
                limit=1,
            )

            if not records:
                logger.info(f"No cached paper found for hash {file_hash}")
                return None

            record = records[0]

            # Update last_accessed time
            self.update_paper_access_time(record["id"])

            logger.info(f"Retrieved cached paper {record['id']} for user {user_id}")

            return {
                "id": record.get("id"),
                "file_path": record.get("file_path"),
                "file_name": record.get("file_name"),
                "file_hash": record.get("file_hash"),
                "title": record.get("paper_title"),
                "authors": record.get("paper_authors", []),
                "abstract": record.get("paper_abstract"),
                "full_text": record.get("full_text", ""),
                "sections": record.get("sections", {}),
                "figures": record.get("figures", []),
                "tables": record.get("tables", []),
                "parsed_at": record.get("parsed_at"),
            }

        except Exception as e:
            logger.error(f"Failed to get cached paper: {e}")
            return None

    def update_paper_access_time(self, paper_id: str) -> None:
        """Update the last_accessed timestamp for a paper."""
        try:
            self.manager.update_record(
                "parsed_papers",
                paper_id,
                {"last_accessed": datetime.utcnow().isoformat()},
            )
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
            record = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "paper_id": paper_id,
                "query_text": query_text,
                "query_results": query_results,
                "similarity_scores": similarity_scores,
                "queried_at": datetime.utcnow().isoformat(),
            }

            self.manager.insert_record("query_history", record)

            logger.info(f"Saved query for paper {paper_id}")

        except Exception as e:
            logger.error(f"Failed to save query: {e}")
            raise

    def get_query_history(
        self, user_id: str, paper_id: Optional[str] = None, limit: int = DEFAULT_QUERY_HISTORY_LIMIT
    ) -> List[Dict[str, Any]]:
        """Get query history."""
        try:
            filters = {"user_id": user_id}
            if paper_id:
                filters["paper_id"] = paper_id

            records = self.manager.query_records(
                "query_history",
                filters=filters,
                order_by="-queried_at",
                limit=limit,
            )

            logger.info(f"Retrieved {len(records)} queries from history")

            return records

        except Exception as e:
            logger.error(f"Failed to get query history: {e}")
            return []
