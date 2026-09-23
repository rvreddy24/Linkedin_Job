"""Storage engine for Ledger, Pipeline, Touches, and Config.

Provides dual support for local SQLite/CSV storage and Google Sheets.
"""

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from engine.models import NormalizedListing, ScoringResult, PipelineItem, TouchRecord
from engine.config import BASE_DIR, GOOGLE_SPREADSHEET_ID, GOOGLE_SHEETS_CREDENTIALS_FILE

DB_PATH = BASE_DIR / "ledger.db"
SHEETS_DIR = BASE_DIR / "sheets"


class StorageManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_sqlite()

    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Ledger table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ledger (
                    run_at TEXT,
                    listing_id TEXT PRIMARY KEY,
                    fingerprint TEXT,
                    source TEXT,
                    company TEXT,
                    title TEXT,
                    url TEXT,
                    type TEXT,
                    score INTEGER,
                    keep INTEGER,
                    one_line_fit TEXT,
                    concern TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_fp ON ledger(fingerprint)")

            # Pipeline table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline (
                    listing_id TEXT PRIMARY KEY,
                    fingerprint TEXT,
                    run_at TEXT,
                    type TEXT,
                    score INTEGER,
                    band TEXT,
                    company TEXT,
                    title TEXT,
                    location TEXT,
                    country TEXT,
                    source TEXT,
                    url TEXT,
                    one_line_fit TEXT,
                    angle TEXT,
                    approach_role TEXT,
                    asks_for TEXT,
                    concern TEXT,
                    agency_post INTEGER,
                    status TEXT DEFAULT 'new',
                    draft TEXT DEFAULT '',
                    last_touch_at TEXT
                )
            """)

            # Touches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS touches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    touched_at TEXT,
                    company_key TEXT,
                    listing_id TEXT,
                    action TEXT,
                    preview TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_touches_company ON touches(company_key, action)")
            conn.commit()

    def get_seen_identifiers(self) -> Tuple[Set[str], Set[str]]:
        """Returns (seen_listing_ids, seen_fingerprints) from Ledger."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT listing_id, fingerprint FROM ledger")
            rows = cursor.fetchall()
            listing_ids = {r[0] for r in rows if r[0]}
            fingerprints = {r[1] for r in rows if r[1]}
            return listing_ids, fingerprints

    def log_to_ledger(self, run_at: str, scored_pairs: List[Tuple[NormalizedListing, ScoringResult]]):
        """Append all scored rows to Ledger (including IGNORE)."""
        if not scored_pairs:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            rows_to_insert = []
            for item, score in scored_pairs:
                rows_to_insert.append((
                    run_at,
                    item.listing_id,
                    item.fingerprint,
                    item.source,
                    item.company,
                    item.title,
                    item.url,
                    score.type,
                    score.score,
                    1 if score.keep else 0,
                    score.one_line_fit,
                    score.concern,
                ))
            cursor.executemany("""
                INSERT OR IGNORE INTO ledger
                (run_at, listing_id, fingerprint, source, company, title, url, type, score, keep, one_line_fit, concern)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows_to_insert)
            conn.commit()

        # Also append to CSV if it exists
        csv_file = SHEETS_DIR / "Ledger.csv"
        try:
            with open(csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for item, score in scored_pairs:
                    writer.writerow([
                        run_at, item.listing_id, item.fingerprint, item.source, item.company,
                        item.title, item.url, score.type, score.score, score.keep,
                        score.one_line_fit, score.concern
                    ])
        except Exception as e:
            print(f"[Storage] Warning: Failed to append to Ledger.csv: {e}")

    def upsert_pipeline(self, pipeline_items: List[PipelineItem]):
        """Upsert kept items into Pipeline."""
        if not pipeline_items:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for p in pipeline_items:
                cursor.execute("""
                    INSERT INTO pipeline (
                        listing_id, fingerprint, run_at, type, score, band, company, title,
                        location, country, source, url, one_line_fit, angle, approach_role,
                        asks_for, concern, agency_post, status, draft, last_touch_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(listing_id) DO UPDATE SET
                        type=excluded.type,
                        score=excluded.score,
                        band=excluded.band,
                        one_line_fit=excluded.one_line_fit,
                        angle=excluded.angle,
                        approach_role=excluded.approach_role,
                        asks_for=excluded.asks_for,
                        concern=excluded.concern,
                        agency_post=excluded.agency_post
                """, (
                    p.listing_id, p.fingerprint, p.run_at, p.type, p.score, p.band,
                    p.company, p.title, p.location, p.country, p.source, p.url,
                    p.one_line_fit, p.angle, p.approach_role, p.asks_for, p.concern,
                    1 if p.agency_post else 0, p.status, p.draft, p.last_touch_at
                ))
            conn.commit()

        # Update Pipeline.csv
        self._sync_pipeline_csv()

    def _sync_pipeline_csv(self):
        csv_file = SHEETS_DIR / "Pipeline.csv"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT listing_id, fingerprint, run_at, type, score, band, company, title,
                           location, country, source, url, one_line_fit, angle, approach_role,
                           asks_for, concern, agency_post, status, draft, last_touch_at
                    FROM pipeline ORDER BY score DESC
                """)
                rows = cursor.fetchall()
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "listing_id", "fingerprint", "run_at", "type", "score", "band", "company", "title",
                    "location", "country", "source", "url", "one_line_fit", "angle", "approach_role",
                    "asks_for", "concern", "agency_post", "status", "draft", "last_touch_at"
                ])
                for r in rows:
                    writer.writerow(list(r))
        except Exception as e:
            print(f"[Storage] Warning: Failed to sync Pipeline.csv: {e}")

    def lookup_pipeline(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Lookup a Pipeline item by listing_id (accepts full ID like 'linkedin:4470667578' or just '4470667578')."""
        clean_id = str(listing_id or "").strip()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM pipeline WHERE listing_id = ? OR listing_id LIKE ?",
                (clean_id, f"%:{clean_id}")
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def update_pipeline_touch(self, listing_id: str, status: str, draft: Optional[str] = None):
        """Update status, draft text, and last_touch_at for a listing."""
        now_str = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if draft is not None:
                cursor.execute("""
                    UPDATE pipeline SET status = ?, draft = ?, last_touch_at = ? WHERE listing_id = ?
                """, (status, draft, now_str, listing_id))
            else:
                cursor.execute("""
                    UPDATE pipeline SET status = ?, last_touch_at = ? WHERE listing_id = ?
                """, (status, now_str, listing_id))
            conn.commit()
        self._sync_pipeline_csv()

    def record_touch(self, company_key_val: str, listing_id: str, action: str, preview: str = ""):
        """Record touch event in Touches."""
        now_str = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO touches (touched_at, company_key, listing_id, action, preview)
                VALUES (?, ?, ?, ?, ?)
            """, (now_str, company_key_val, listing_id, action, preview[:200]))
            conn.commit()

        # Append to Touches.csv
        csv_file = SHEETS_DIR / "Touches.csv"
        try:
            with open(csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([now_str, company_key_val, listing_id, action, preview[:200]])
        except Exception as e:
            print(f"[Storage] Warning: Failed to append Touches.csv: {e}")

    def get_last_touch_date(self, company_key_val: str, action: str = "draft") -> Optional[datetime]:
        """Get timestamp of most recent touch for company and action."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT touched_at FROM touches
                WHERE company_key = ? AND action = ?
                ORDER BY id DESC LIMIT 1
            """, (company_key_val, action))
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    return datetime.fromisoformat(row[0])
                except Exception:
                    pass
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Retrieve total, kept, and hot counts from Ledger."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM ledger")
            total_scored = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM ledger WHERE keep = 1")
            total_kept = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM ledger WHERE score >= 80")
            total_hot = cursor.fetchone()[0]
            return {
                "total_scored": total_scored,
                "total_kept": total_kept,
                "total_hot": total_hot,
            }


storage = StorageManager()
