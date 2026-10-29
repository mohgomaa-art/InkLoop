"""
InkLoop Asset Registry - SQLite Metadata and Lineage Persistence.
Manages transactional storage of asset metadata, content hashes, and lineage graph.
"""
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from app.contracts.artifacts import AssetType, LifecycleStatus
from app.storage.errors import (
    DuplicateAssetConflictError,
    AssetNotFoundError,
    LineageCycleError,
)
from app.storage.models import AssetMetadata, AssetFilter


class RegistryDB:
    """
    Transactional SQLite persistence layer for asset metadata and lineage relationships.
    """

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initializes tables, indexes, and pragmas."""
        with self._conn:
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA foreign_keys = ON;")

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    asset_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    run_id TEXT,
                    asset_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    managed_path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    byte_size INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    width INTEGER,
                    height INTEGER,
                    dpi REAL,
                    page_count INTEGER,
                    font_metadata TEXT,
                    created_at TEXT NOT NULL,
                    source_origin TEXT,
                    license_info TEXT,
                    engine_id TEXT,
                    engine_version TEXT,
                    config_hash TEXT,
                    lineage_operation TEXT,
                    lineage_params TEXT,
                    schema_version TEXT NOT NULL,
                    validation_state TEXT NOT NULL,
                    validation_errors TEXT,
                    lifecycle_status TEXT NOT NULL,
                    extra_metadata TEXT
                );
            """)

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS asset_lineage (
                    parent_id TEXT NOT NULL,
                    child_id TEXT NOT NULL,
                    PRIMARY KEY (parent_id, child_id),
                    FOREIGN KEY (parent_id) REFERENCES assets(asset_id),
                    FOREIGN KEY (child_id) REFERENCES assets(asset_id)
                );
            """)

            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_project ON assets (project_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_hash ON assets (content_sha256);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_type ON assets (asset_type);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_run ON assets (run_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_lineage_parent ON asset_lineage (parent_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_lineage_child ON asset_lineage (child_id);")

    def insert_asset(self, metadata: AssetMetadata) -> None:
        """
        Inserts an asset and records its parent lineage links.
        Guarantees idempotency for identical records and detects conflicting re-registrations.
        """
        existing = self.get_asset(metadata.asset_id)
        if existing:
            if existing.content_sha256 == metadata.content_sha256 and existing.managed_path == metadata.managed_path:
                # Idempotent re-registration of exact same content
                return
            raise DuplicateAssetConflictError(
                f"Asset ID '{metadata.asset_id}' already registered with differing content or path.",
                asset_id=metadata.asset_id
            )

        with self._conn:
            self._conn.execute("""
                INSERT INTO assets (
                    asset_id, project_id, run_id, asset_type, name, original_filename,
                    managed_path, mime_type, extension, byte_size, content_sha256,
                    width, height, dpi, page_count, font_metadata, created_at,
                    source_origin, license_info, engine_id, engine_version, config_hash,
                    lineage_operation, lineage_params, schema_version, validation_state,
                    validation_errors, lifecycle_status, extra_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.asset_id,
                metadata.project_id,
                metadata.run_id,
                str(metadata.asset_type.value if hasattr(metadata.asset_type, "value") else metadata.asset_type),
                metadata.name,
                metadata.original_filename,
                metadata.managed_path,
                metadata.mime_type,
                metadata.extension,
                metadata.byte_size,
                metadata.content_sha256,
                metadata.width,
                metadata.height,
                metadata.dpi,
                metadata.page_count,
                json.dumps(metadata.font_metadata) if metadata.font_metadata is not None else None,
                metadata.created_at,
                metadata.source_origin,
                metadata.license_info,
                metadata.engine_id,
                metadata.engine_version,
                metadata.config_hash,
                metadata.lineage_operation,
                json.dumps(metadata.lineage_params),
                metadata.schema_version,
                metadata.validation_state,
                json.dumps(metadata.validation_errors),
                str(metadata.lifecycle_status.value if hasattr(metadata.lifecycle_status, "value") else metadata.lifecycle_status),
                json.dumps(metadata.extra_metadata)
            ))

            for parent_id in metadata.parent_asset_ids:
                self._conn.execute(
                    "INSERT OR IGNORE INTO asset_lineage (parent_id, child_id) VALUES (?, ?)",
                    (parent_id, metadata.asset_id)
                )

    def _row_to_metadata(self, row: sqlite3.Row) -> AssetMetadata:
        """Converts an SQLite row back into a typed AssetMetadata model."""
        asset_id = row["asset_id"]

        # Fetch parents
        cur = self._conn.execute("SELECT parent_id FROM asset_lineage WHERE child_id = ? ORDER BY parent_id", (asset_id,))
        parents = [r[0] for r in cur.fetchall()]

        font_meta = json.loads(row["font_metadata"]) if row["font_metadata"] else None
        lineage_params = json.loads(row["lineage_params"]) if row["lineage_params"] else {}
        val_errors = json.loads(row["validation_errors"]) if row["validation_errors"] else []
        extra_meta = json.loads(row["extra_metadata"]) if row["extra_metadata"] else {}

        return AssetMetadata(
            asset_id=row["asset_id"],
            project_id=row["project_id"],
            run_id=row["run_id"],
            asset_type=AssetType(row["asset_type"]),
            name=row["name"],
            original_filename=row["original_filename"],
            managed_path=row["managed_path"],
            mime_type=row["mime_type"],
            extension=row["extension"],
            byte_size=row["byte_size"],
            content_sha256=row["content_sha256"],
            width=row["width"],
            height=row["height"],
            dpi=row["dpi"],
            page_count=row["page_count"],
            font_metadata=font_meta,
            created_at=row["created_at"],
            source_origin=row["source_origin"],
            license_info=row["license_info"],
            engine_id=row["engine_id"],
            engine_version=row["engine_version"],
            config_hash=row["config_hash"],
            parent_asset_ids=parents,
            lineage_operation=row["lineage_operation"],
            lineage_params=lineage_params,
            schema_version=row["schema_version"],
            validation_state=row["validation_state"],
            validation_errors=val_errors,
            lifecycle_status=LifecycleStatus(row["lifecycle_status"]),
            extra_metadata=extra_meta
        )

    def get_asset(self, asset_id: str) -> Optional[AssetMetadata]:
        """Retrieves asset metadata by stable identifier."""
        cur = self._conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_metadata(row)

    def get_by_hash(self, content_sha256: str) -> List[AssetMetadata]:
        """Retrieves all assets matching a content SHA-256 hash."""
        cur = self._conn.execute(
            "SELECT * FROM assets WHERE content_sha256 = ? ORDER BY created_at ASC",
            (content_sha256.lower().strip(),)
        )
        return [self._row_to_metadata(r) for r in cur.fetchall()]

    def list_assets(self, filter: Optional[AssetFilter] = None) -> List[AssetMetadata]:
        """Queries registered assets based on flexible filter criteria."""
        query = "SELECT * FROM assets WHERE 1=1"
        params: List[Any] = []

        if filter:
            if filter.project_id:
                query += " AND project_id = ?"
                params.append(filter.project_id)
            if filter.run_id:
                query += " AND run_id = ?"
                params.append(filter.run_id)
            if filter.asset_type:
                if isinstance(filter.asset_type, list):
                    placeholders = ",".join("?" for _ in filter.asset_type)
                    query += f" AND asset_type IN ({placeholders})"
                    params.extend(str(t.value if hasattr(t, "value") else t) for t in filter.asset_type)
                else:
                    query += " AND asset_type = ?"
                    params.append(str(filter.asset_type.value if hasattr(filter.asset_type, "value") else filter.asset_type))
            if filter.lifecycle_status:
                query += " AND lifecycle_status = ?"
                params.append(str(filter.lifecycle_status.value if hasattr(filter.lifecycle_status, "value") else filter.lifecycle_status))
            if filter.validation_state:
                query += " AND validation_state = ?"
                params.append(filter.validation_state)
            if filter.engine_id:
                query += " AND engine_id = ?"
                params.append(filter.engine_id)
            if filter.extension:
                query += " AND extension = ?"
                params.append(filter.extension)
            if filter.parent_id:
                query += " AND asset_id IN (SELECT child_id FROM asset_lineage WHERE parent_id = ?)"
                params.append(filter.parent_id)

        query += " ORDER BY created_at ASC, asset_id ASC"
        cur = self._conn.execute(query, params)
        return [self._row_to_metadata(r) for r in cur.fetchall()]

    def get_children(self, parent_id: str) -> List[AssetMetadata]:
        """Retrieves all downstream child assets derived from this parent."""
        cur = self._conn.execute("""
            SELECT a.* FROM assets a
            JOIN asset_lineage l ON a.asset_id = l.child_id
            WHERE l.parent_id = ?
            ORDER BY a.created_at ASC
        """, (parent_id,))
        return [self._row_to_metadata(r) for r in cur.fetchall()]

    def get_parents(self, child_id: str) -> List[AssetMetadata]:
        """Retrieves all predecessor parent assets for this child."""
        cur = self._conn.execute("""
            SELECT a.* FROM assets a
            JOIN asset_lineage l ON a.asset_id = l.parent_id
            WHERE l.child_id = ?
            ORDER BY a.created_at ASC
        """, (child_id,))
        return [self._row_to_metadata(r) for r in cur.fetchall()]

    def check_cycle(self, proposed_child_id: str, proposed_parent_ids: List[str]) -> bool:
        """
        Detects if adding proposed parents would introduce a cycle in the lineage DAG.
        Returns True if a cycle would be created.
        """
        visited = set()
        queue = list(proposed_parent_ids)

        while queue:
            curr = queue.pop(0)
            if curr == proposed_child_id:
                return True
            if curr not in visited:
                visited.add(curr)
                # Enqueue parents of curr
                cur = self._conn.execute("SELECT parent_id FROM asset_lineage WHERE child_id = ?", (curr,))
                for r in cur.fetchall():
                    queue.append(r[0])

        return False

    def close(self) -> None:
        """Closes the underlying SQLite database connection."""
        self._conn.close()
