"""
Transactional SQLite persistence layer for Style and Character Identity Profiles.
Guarantees project isolation, version history, atomic updates, and WAL concurrency.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from app.config import PROJECT_ROOT
from app.creative.models import (
    StyleProfile,
    CharacterIdentityProfile,
    ProfileStatus,
)


class CreativeProfileStore:
    """
    SQLite-backed transactional persistence store for StyleProfile and CharacterIdentityProfile.
    Thread-safe and supports multi-version revision snapshots.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        if db_path is None:
            db_dir = PROJECT_ROOT / "runs"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "creative_profiles.db")
        else:
            self.db_path = str(db_path)
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute("PRAGMA journal_mode = WAL;")
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS style_profiles (
                        profile_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (project_id, profile_id)
                    );
                """)
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS style_profile_versions (
                        profile_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (project_id, profile_id, version)
                    );
                """)
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS character_profiles (
                        profile_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        character_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (project_id, profile_id)
                    );
                """)
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS character_profile_versions (
                        profile_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (project_id, profile_id, version)
                    );
                """)
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_style_proj ON style_profiles(project_id);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_char_proj ON character_profiles(project_id);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_char_cid ON character_profiles(project_id, character_id);")

    # =========================================================================
    # Style Profile Operations
    # =========================================================================

    def save_style_profile(self, profile: StyleProfile) -> StyleProfile:
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            profile.updated_at = now_iso

            # Check if this profile exists
            existing = self.get_style_profile(profile.project_id, profile.profile_id)
            if existing and existing.approved_by_user and not profile.approved_by_user:
                # If an approved profile is edited, bump version
                profile.version = existing.version + 1

            payload = profile.model_dump_json()
            with self._conn:
                self._conn.execute("""
                    INSERT INTO style_profiles (profile_id, project_id, name, version, status, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, profile_id) DO UPDATE SET
                        name = excluded.name,
                        version = excluded.version,
                        status = excluded.status,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at;
                """, (
                    profile.profile_id,
                    profile.project_id,
                    profile.name,
                    profile.version,
                    profile.status.value if hasattr(profile.status, "value") else str(profile.status),
                    payload,
                    profile.created_at,
                    profile.updated_at
                ))
                # Record snapshot in versions
                self._conn.execute("""
                    INSERT OR REPLACE INTO style_profile_versions (profile_id, project_id, version, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    profile.profile_id,
                    profile.project_id,
                    profile.version,
                    payload,
                    now_iso
                ))
            return profile

    def get_style_profile(self, project_id: str, profile_id: str) -> Optional[StyleProfile]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT payload_json FROM style_profiles WHERE project_id = ? AND profile_id = ?",
                (project_id, profile_id)
            )
            row = cur.fetchone()
            if not row:
                return None
            return StyleProfile.model_validate_json(row["payload_json"])

    def list_style_profiles(self, project_id: str, include_archived: bool = False) -> List[StyleProfile]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT payload_json FROM style_profiles WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,)
            )
            results = []
            for row in cur.fetchall():
                prof = StyleProfile.model_validate_json(row["payload_json"])
                if not include_archived and prof.status == ProfileStatus.ARCHIVED:
                    continue
                results.append(prof)
            return results

    def approve_style_profile(self, project_id: str, profile_id: str) -> StyleProfile:
        prof = self.get_style_profile(project_id, profile_id)
        if not prof:
            raise KeyError(f"Style profile '{profile_id}' not found in project '{project_id}'")
        now_iso = datetime.now(timezone.utc).isoformat()
        prof.approved_by_user = True
        prof.approved_at = now_iso
        prof.status = ProfileStatus.APPROVED
        return self.save_style_profile(prof)

    def archive_style_profile(self, project_id: str, profile_id: str) -> StyleProfile:
        prof = self.get_style_profile(project_id, profile_id)
        if not prof:
            raise KeyError(f"Style profile '{profile_id}' not found in project '{project_id}'")
        prof.status = ProfileStatus.ARCHIVED
        return self.save_style_profile(prof)

    # =========================================================================
    # Character Identity Profile Operations
    # =========================================================================

    def save_character_profile(self, profile: CharacterIdentityProfile) -> CharacterIdentityProfile:
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            profile.updated_at = now_iso

            existing = self.get_character_profile(profile.project_id, profile.profile_id)
            if existing and existing.approved_by_user and not profile.approved_by_user:
                profile.version = existing.version + 1

            payload = profile.model_dump_json()
            with self._conn:
                self._conn.execute("""
                    INSERT INTO character_profiles (profile_id, project_id, character_id, name, version, status, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, profile_id) DO UPDATE SET
                        character_id = excluded.character_id,
                        name = excluded.name,
                        version = excluded.version,
                        status = excluded.status,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at;
                """, (
                    profile.profile_id,
                    profile.project_id,
                    profile.character_id,
                    profile.name,
                    profile.version,
                    profile.status.value if hasattr(profile.status, "value") else str(profile.status),
                    payload,
                    profile.created_at,
                    profile.updated_at
                ))
                self._conn.execute("""
                    INSERT OR REPLACE INTO character_profile_versions (profile_id, project_id, version, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    profile.profile_id,
                    profile.project_id,
                    profile.version,
                    payload,
                    now_iso
                ))
            return profile

    def get_character_profile(self, project_id: str, profile_id: str) -> Optional[CharacterIdentityProfile]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT payload_json FROM character_profiles WHERE project_id = ? AND profile_id = ?",
                (project_id, profile_id)
            )
            row = cur.fetchone()
            if not row:
                return None
            return CharacterIdentityProfile.model_validate_json(row["payload_json"])

    def get_character_profile_by_character_id(self, project_id: str, character_id: str) -> Optional[CharacterIdentityProfile]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT payload_json FROM character_profiles WHERE project_id = ? AND character_id = ? ORDER BY version DESC LIMIT 1",
                (project_id, character_id.lower())
            )
            row = cur.fetchone()
            if not row:
                return None
            return CharacterIdentityProfile.model_validate_json(row["payload_json"])

    def list_character_profiles(self, project_id: str, include_archived: bool = False) -> List[CharacterIdentityProfile]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT payload_json FROM character_profiles WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,)
            )
            results = []
            for row in cur.fetchall():
                prof = CharacterIdentityProfile.model_validate_json(row["payload_json"])
                if not include_archived and prof.status == ProfileStatus.ARCHIVED:
                    continue
                results.append(prof)
            return results

    def approve_character_profile(self, project_id: str, profile_id: str, canon_version: Optional[int] = None) -> CharacterIdentityProfile:
        prof = self.get_character_profile(project_id, profile_id)
        if not prof:
            raise KeyError(f"Character profile '{profile_id}' not found in project '{project_id}'")
        now_iso = datetime.now(timezone.utc).isoformat()
        prof.approved_by_user = True
        prof.approved_at = now_iso
        prof.status = ProfileStatus.APPROVED
        if canon_version is not None:
            prof.canon_version = canon_version
        return self.save_character_profile(prof)

    def archive_character_profile(self, project_id: str, profile_id: str) -> CharacterIdentityProfile:
        prof = self.get_character_profile(project_id, profile_id)
        if not prof:
            raise KeyError(f"Character profile '{profile_id}' not found in project '{project_id}'")
        prof.status = ProfileStatus.ARCHIVED
        return self.save_character_profile(prof)


_default_store: Optional[CreativeProfileStore] = None

def get_creative_profile_store() -> CreativeProfileStore:
    global _default_store
    if _default_store is None:
        _default_store = CreativeProfileStore()
    return _default_store
