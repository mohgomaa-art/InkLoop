"""SQLite revision pointer and immutable page-document artifacts."""
import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Tuple
from app.contracts.artifacts import AssetType
from app.contracts.identity import IdPrefix, generate_id
from app.editor.models import EditablePageDocument, LayerKind
from app.storage.registry import AssetRegistry


class PageRevisionConflict(Exception):
    def __init__(self, current_revision: int):
        self.current_revision = current_revision
        super().__init__(f"Page changed since revision {current_revision} was loaded.")


class PageNotFound(Exception):
    pass


class PageDocumentStore:
    def __init__(self, db_path: Path, registry: AssetRegistry):
        self.registry = registry
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS pages (
            page_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, revision INTEGER NOT NULL,
            artifact_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '', deleted_at TEXT)""")
        page_columns = {row[1] for row in self._conn.execute("PRAGMA table_info(pages)")}
        for column, declaration in (("created_at", "TEXT NOT NULL DEFAULT ''"), ("updated_at", "TEXT NOT NULL DEFAULT ''"), ("deleted_at", "TEXT")):
            if column not in page_columns:
                self._conn.execute(f"ALTER TABLE pages ADD COLUMN {column} {declaration}")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS page_revisions (
            page_id TEXT NOT NULL, revision INTEGER NOT NULL, artifact_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(page_id, revision))""")
        self._conn.execute("""UPDATE pages SET
            created_at=COALESCE(NULLIF(created_at,''),(SELECT MIN(created_at) FROM page_revisions WHERE page_revisions.page_id=pages.page_id),CURRENT_TIMESTAMP),
            updated_at=COALESCE(NULLIF(updated_at,''),(SELECT MAX(created_at) FROM page_revisions WHERE page_revisions.page_id=pages.page_id),CURRENT_TIMESTAMP)
            WHERE created_at='' OR updated_at=''""")

    def _read_artifact(self, artifact_id: str) -> EditablePageDocument:
        resolved = self.registry.resolve_asset(artifact_id, verify_integrity=True)
        return EditablePageDocument.model_validate_json(resolved.absolute_path.read_bytes())

    def create(self, doc: EditablePageDocument) -> EditablePageDocument:
        with self._lock:
            doc.revision = 1
            payload = doc.model_dump_json(exclude_none=True).encode()
            parents = [a for a in doc.source_artifact_ids if self.registry.get_asset(a)]
            asset = self.registry.ingest_bytes(
                payload, f"{doc.page_id}-r1.json", doc.project_id, AssetType.GENERIC_ARTIFACT,
                name=f"{doc.page_id} revision 1", parent_asset_ids=parents or None,
                lineage_operation="editable_page_revision", lineage_params={"page_id": doc.page_id, "revision": 1},
                extra_metadata={"document_kind": "editable_page", "page_id": doc.page_id, "revision": 1},
            )
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute("INSERT INTO pages(page_id, project_id, revision, artifact_id, created_at, updated_at) VALUES (?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'))", (doc.page_id, doc.project_id, 1, asset.asset_id))
                self._conn.execute("INSERT INTO page_revisions(page_id, revision, artifact_id) VALUES (?, ?, ?)", (doc.page_id, 1, asset.asset_id))
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
            return doc

    def get(self, page_id: str) -> EditablePageDocument:
        row = self._conn.execute("SELECT artifact_id FROM pages WHERE page_id=?", (page_id,)).fetchone()
        if not row:
            raise PageNotFound(page_id)
        return self._read_artifact(row["artifact_id"])

    def delete(self, page_id: str) -> None:
        """Soft-delete the page pointer while retaining immutable revisions and source assets."""
        with self._lock:
            changed = self._conn.execute("UPDATE pages SET deleted_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE page_id=? AND deleted_at IS NULL", (page_id,)).rowcount
            if not changed:
                if not self._conn.execute("SELECT 1 FROM pages WHERE page_id=?", (page_id,)).fetchone():
                    raise PageNotFound(page_id)
                raise ValueError(f"Page {page_id} is already deleted.")

    def restore_deleted(self, page_id: str) -> None:
        with self._lock:
            changed = self._conn.execute("UPDATE pages SET deleted_at=NULL WHERE page_id=? AND deleted_at IS NOT NULL", (page_id,)).rowcount
            if not changed and not self._conn.execute("SELECT 1 FROM pages WHERE page_id=?", (page_id,)).fetchone():
                raise PageNotFound(page_id)

    def revisions(self, page_id: str) -> List[dict]:
        if not self._conn.execute("SELECT 1 FROM pages WHERE page_id=?", (page_id,)).fetchone():
            raise PageNotFound(page_id)
        rows = self._conn.execute("SELECT revision, artifact_id, created_at FROM page_revisions WHERE page_id=? ORDER BY revision DESC", (page_id,)).fetchall()
        return [dict(row) for row in rows]

    def list_pages(self, project_id: str | None = None) -> List[dict]:
        if project_id:
            rows = self._conn.execute("SELECT page_id, project_id, revision, artifact_id, created_at, updated_at FROM pages WHERE project_id=? AND deleted_at IS NULL ORDER BY updated_at DESC, rowid DESC", (project_id,)).fetchall()
        else:
            rows = self._conn.execute("SELECT page_id, project_id, revision, artifact_id, created_at, updated_at FROM pages WHERE deleted_at IS NULL ORDER BY updated_at DESC, rowid DESC").fetchall()
        results = []
        for row in rows:
            item = dict(row)
            try:
                doc = self._read_artifact(item["artifact_id"])
                item["template_id"] = str(getattr(doc.layout, "template_id", "custom")) if doc.layout else "custom"
                item["panel_count"] = len(doc.layout.panel_slots) if doc.layout else 0
                item["layer_count"] = len(doc.layers) if doc.layers else 0
                image_layers = [l for l in doc.layers if l.kind == LayerKind.IMAGE and l.source_asset_id]
                item["image_count"] = len(image_layers)
                item["preview_asset_id"] = image_layers[0].source_asset_id if image_layers else None
                panel_img_map = {l.panel_id: l.source_asset_id for l in image_layers if l.panel_id}
                if doc.layout and doc.layout.canvas_spec:
                    item["canvas_width"] = doc.layout.canvas_spec.width_px
                    item["canvas_height"] = doc.layout.canvas_spec.height_px
                if doc.layout and doc.layout.panel_slots:
                    item["panel_slots"] = [
                        {
                            "panel_id": s.panel_id,
                            "rect": s.rect.model_dump() if s.rect else None,
                            "asset_id": panel_img_map.get(s.panel_id),
                        }
                        for s in doc.layout.panel_slots
                    ]
            except Exception:
                pass
            results.append(item)
        return results

    def list_deleted_pages(self, project_id: str | None = None) -> List[dict]:
        if project_id:
            rows = self._conn.execute("SELECT page_id, project_id, revision, artifact_id, created_at, updated_at, deleted_at FROM pages WHERE project_id=? AND deleted_at IS NOT NULL ORDER BY deleted_at DESC, rowid DESC", (project_id,)).fetchall()
        else:
            rows = self._conn.execute("SELECT page_id, project_id, revision, artifact_id, created_at, updated_at, deleted_at FROM pages WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC, rowid DESC").fetchall()
        return [dict(row) for row in rows]

    def save(self, page_id: str, expected_revision: int, doc: EditablePageDocument) -> EditablePageDocument:
        with self._lock:
            row = self._conn.execute("SELECT project_id, revision, artifact_id FROM pages WHERE page_id=?", (page_id,)).fetchone()
            if not row:
                raise PageNotFound(page_id)
            if row["revision"] != expected_revision:
                raise PageRevisionConflict(row["revision"])
            if doc.page_id != page_id or doc.project_id != row["project_id"]:
                raise ValueError("Page identity and project are immutable.")
            doc.revision = expected_revision + 1
            payload = doc.model_dump_json(exclude_none=True).encode()
            prior = row["artifact_id"]
            parents = [prior] + [a for a in doc.source_artifact_ids if a != prior and self.registry.get_asset(a)]
            asset = self.registry.ingest_bytes(
                payload, f"{page_id}-r{doc.revision}.json", doc.project_id, AssetType.GENERIC_ARTIFACT,
                name=f"{page_id} revision {doc.revision}", parent_asset_ids=parents,
                lineage_operation="editable_page_revision", lineage_params={"page_id": page_id, "revision": doc.revision},
                extra_metadata={"document_kind": "editable_page", "page_id": page_id, "revision": doc.revision},
            )
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                changed = self._conn.execute("UPDATE pages SET revision=?, artifact_id=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE page_id=? AND revision=? AND deleted_at IS NULL", (doc.revision, asset.asset_id, page_id, expected_revision)).rowcount
                if changed != 1:
                    current = self._conn.execute("SELECT revision FROM pages WHERE page_id=?", (page_id,)).fetchone()[0]
                    raise PageRevisionConflict(current)
                self._conn.execute("INSERT INTO page_revisions(page_id, revision, artifact_id) VALUES (?, ?, ?)", (page_id, doc.revision, asset.asset_id))
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
            return doc

    def restore(self, page_id: str, expected_revision: int, revision_to_restore: int) -> EditablePageDocument:
        row = self._conn.execute("SELECT artifact_id FROM page_revisions WHERE page_id=? AND revision=?", (page_id, revision_to_restore)).fetchone()
        if not row:
            raise PageNotFound(f"Revision {revision_to_restore} of {page_id}")
        doc = self._read_artifact(row["artifact_id"])
        doc.revision = expected_revision
        return self.save(page_id, expected_revision, doc)
