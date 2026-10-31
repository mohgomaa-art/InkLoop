"""Stable per-image protected regions for lettering placement.

Region queries are keyed by source-image SHA-256 and a normalized concept.
Unknown remains an explicit state; the service never synthesizes a center box.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import unicodedata
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence

from app.config import PROJECT_ROOT, InkLoopConfig


SAM_QUERY_COST_USD = 0.0025
DEFAULT_PURPOSE = "bubble_protected_region"


def normalize_concept(concept: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(concept or "")).casefold()
    normalized = re.sub(r"[^\w\s-]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        raise ValueError("A protected-region query needs one explicit concept.")
    return normalized


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RegionBox:
    x: float
    y: float
    width: float
    height: float
    label: str
    source: str
    confidence: Optional[float] = None
    region_id: str = ""
    mask_sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SegmentationObservation:
    boxes: Sequence[RegionBox]
    model: str
    mask_available: bool = False
    mask_sha256: Optional[str] = None


@dataclass(frozen=True)
class RegionQueryResult:
    image_sha256: str
    concept: str
    model: str
    purpose: str
    image_width: int
    image_height: int
    regions: Sequence[RegionBox]
    mask_available: bool
    mask_sha256: Optional[str]
    regions_unknown: bool
    requires_manual_annotation: bool
    estimated_cost_usd: float
    cache_hit: bool = False
    source: str = "sam"
    override: Optional[Dict[str, str]] = None
    recorded_by: Optional[str] = None
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["regions"] = [region.to_dict() for region in self.regions]
        return data


class RegionSegmenter(Protocol):
    def segment(self, image_bytes: bytes, concept: str, purpose: str) -> SegmentationObservation:
        ...


class RegionProviderError(RuntimeError):
    pass


class MetaSamRegionSegmenter:
    """Adapter around the configured SAM 3.1 verifier; never simulates success."""

    def __init__(self, config: Optional[InkLoopConfig] = None):
        self.config = config or InkLoopConfig.load()

    def segment(self, image_bytes: bytes, concept: str, purpose: str) -> SegmentationObservation:
        if not self.config.has_credentials:
            raise RegionProviderError("SAM credentials are unavailable; region status remains unknown.")

        # The existing verifier issues exactly one image/concept request. Its
        # no-credential behavior can be simulated, so fail closed if it does.
        from PIL import Image
        from io import BytesIO
        from app.verification.l1_subject import L1SubjectChecker

        result = L1SubjectChecker(config=self.config).check(
            image_bytes,
            concept=concept,
            expected_subject_count=0,
            is_simulated=False,
        )
        if result.is_simulated:
            raise RegionProviderError("SAM returned a simulated result; protected regions were not accepted.")
        with Image.open(BytesIO(image_bytes)) as image:
            image_width, image_height = image.size
        if image_width <= 0 or image_height <= 0:
            raise RegionProviderError("SAM source image dimensions are invalid.")
        boxes = [
            RegionBox(
                x=float(box.x) / image_width,
                y=float(box.y) / image_height,
                width=float(box.width) / image_width,
                height=float(box.height) / image_height,
                label=concept,
                source="sam",
                confidence=float(box.confidence),
            )
            for box in result.boxes
        ]
        return SegmentationObservation(
            boxes=boxes,
            model=self.config.sam_model,
            mask_available=bool(result.mask_available),
            mask_sha256=result.mask_sha256,
        )


class ProtectedRegionStore:
    """SQLite cache and audit log, separate from active page/project databases."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @classmethod
    def default(cls) -> "ProtectedRegionStore":
        return cls(PROJECT_ROOT / "runs" / "bubble_protected_regions.sqlite")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS protected_region_queries (
                image_sha256 TEXT NOT NULL,
                concept TEXT NOT NULL,
                model TEXT NOT NULL,
                purpose TEXT NOT NULL,
                image_width INTEGER NOT NULL,
                image_height INTEGER NOT NULL,
                regions_json TEXT NOT NULL,
                mask_available INTEGER NOT NULL,
                mask_sha256 TEXT,
                regions_unknown INTEGER NOT NULL,
                source TEXT NOT NULL,
                override_json TEXT,
                recorded_by TEXT,
                estimated_cost_usd REAL NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(image_sha256, concept)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS protected_region_audit (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_sha256 TEXT NOT NULL,
                concept TEXT NOT NULL,
                model TEXT NOT NULL,
                purpose TEXT NOT NULL,
                cache_hit INTEGER NOT NULL,
                estimated_cost_usd REAL NOT NULL,
                created_at TEXT NOT NULL
            )""")

    @staticmethod
    def _record_from_row(row: sqlite3.Row, *, cache_hit: bool) -> RegionQueryResult:
        regions = tuple(RegionBox(**item) for item in json.loads(row["regions_json"]))
        override = json.loads(row["override_json"]) if row["override_json"] else None
        unknown = bool(row["regions_unknown"])
        return RegionQueryResult(
            image_sha256=row["image_sha256"], concept=row["concept"], model=row["model"],
            purpose=row["purpose"], image_width=int(row["image_width"]), image_height=int(row["image_height"]),
            regions=regions, mask_available=bool(row["mask_available"]), mask_sha256=row["mask_sha256"],
            regions_unknown=unknown, requires_manual_annotation=unknown and override is None,
            estimated_cost_usd=float(row["estimated_cost_usd"]), cache_hit=cache_hit,
            source=row["source"], override=override, recorded_by=row["recorded_by"], created_at=row["created_at"],
        )

    def get(self, image_sha256: str, concept: str) -> Optional[RegionQueryResult]:
        normalized = normalize_concept(concept)
        with self._lock, self._connect() as db:
            row = db.execute(
                "SELECT * FROM protected_region_queries WHERE image_sha256=? AND concept=?",
                (image_sha256, normalized),
            ).fetchone()
        return self._record_from_row(row, cache_hit=True) if row else None

    def save(self, result: RegionQueryResult) -> RegionQueryResult:
        regions_json = json.dumps([item.to_dict() for item in result.regions], ensure_ascii=False, sort_keys=True)
        override_json = json.dumps(result.override, ensure_ascii=False, sort_keys=True) if result.override else None
        with self._lock, self._connect() as db:
            db.execute("""INSERT INTO protected_region_queries
                (image_sha256, concept, model, purpose, image_width, image_height, regions_json,
                 mask_available, mask_sha256, regions_unknown, source, override_json, recorded_by, estimated_cost_usd, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(image_sha256, concept) DO UPDATE SET
                 model=excluded.model, purpose=excluded.purpose, image_width=excluded.image_width,
                 image_height=excluded.image_height, regions_json=excluded.regions_json,
                 mask_available=excluded.mask_available, mask_sha256=excluded.mask_sha256,
                 regions_unknown=excluded.regions_unknown, source=excluded.source,
                 override_json=excluded.override_json, recorded_by=excluded.recorded_by,
                 estimated_cost_usd=excluded.estimated_cost_usd,
                 created_at=excluded.created_at""",
                (result.image_sha256, result.concept, result.model, result.purpose, result.image_width,
                 result.image_height, regions_json, int(result.mask_available), result.mask_sha256,
                 int(result.regions_unknown), result.source, override_json, result.recorded_by, result.estimated_cost_usd,
                 result.created_at or _utc_now()),
            )
        saved = self.get(result.image_sha256, result.concept)
        assert saved is not None
        return replace(saved, cache_hit=result.cache_hit)

    def record_audit(self, result: RegionQueryResult, *, cache_hit: bool, cost: float) -> None:
        with self._lock, self._connect() as db:
            db.execute("""INSERT INTO protected_region_audit
                (image_sha256, concept, model, purpose, cache_hit, estimated_cost_usd, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (result.image_sha256, result.concept, result.model, result.purpose,
                 int(cache_hit), float(cost), _utc_now()),
            )

    def audit(self, image_sha256: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as db:
            if image_sha256:
                rows = db.execute(
                    "SELECT * FROM protected_region_audit WHERE image_sha256=? ORDER BY audit_id",
                    (image_sha256,),
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM protected_region_audit ORDER BY audit_id").fetchall()
        return [dict(row) for row in rows]


class ProtectedRegionService:
    def __init__(
        self,
        store: Optional[ProtectedRegionStore] = None,
        segmenter: Optional[RegionSegmenter] = None,
        config: Optional[InkLoopConfig] = None,
    ):
        self.store = store or ProtectedRegionStore.default()
        self.segmenter = segmenter or MetaSamRegionSegmenter(config)
        self.config = config or InkLoopConfig.load()
        self._query_locks = [threading.Lock() for _ in range(64)]

    @staticmethod
    def _image_dimensions(image_bytes: bytes) -> tuple[int, int]:
        from io import BytesIO
        from PIL import Image
        with Image.open(BytesIO(image_bytes)) as image:
            return image.size

    @staticmethod
    def _region_id(image_sha256: str, concept: str, region: RegionBox) -> str:
        stable = f"{image_sha256}:{concept}:{region.label}:{region.x:.6f}:{region.y:.6f}:{region.width:.6f}:{region.height:.6f}:{region.source}"
        return "pr_" + hashlib.sha256(stable.encode("utf-8")).hexdigest()[:18]

    def get_or_segment(
        self,
        image_bytes: bytes,
        concept: str,
        *,
        purpose: str = DEFAULT_PURPOSE,
    ) -> RegionQueryResult:
        if not image_bytes:
            raise ValueError("Protected-region segmentation needs image bytes.")
        normalized = normalize_concept(concept)
        image_sha256 = hashlib.sha256(image_bytes).hexdigest()
        key_digest = hashlib.sha256(f"{image_sha256}:{normalized}".encode("utf-8")).digest()
        query_lock = self._query_locks[int.from_bytes(key_digest[:2], "big") % len(self._query_locks)]
        with query_lock:
            return self._get_or_segment_locked(image_bytes, normalized, image_sha256, purpose)

    def _get_or_segment_locked(
        self,
        image_bytes: bytes,
        normalized: str,
        image_sha256: str,
        purpose: str,
    ) -> RegionQueryResult:
        cached = self.store.get(image_sha256, normalized)
        if cached is not None:
            self.store.record_audit(cached, cache_hit=True, cost=0.0)
            return replace(cached, cache_hit=True, estimated_cost_usd=0.0)

        image_width, image_height = self._image_dimensions(image_bytes)
        observation = self.segmenter.segment(image_bytes, normalized, purpose)
        regions: List[RegionBox] = []
        for box in observation.boxes:
            if box.source not in {"sam", "vlm", "manual"}:
                raise ValueError(f"Unsupported protected-region source '{box.source}'.")
            if box.width <= 0 or box.height <= 0 or box.x < 0 or box.y < 0 or box.x + box.width > 1 or box.y + box.height > 1:
                continue
            identified = RegionBox(
                x=round(float(box.x), 6), y=round(float(box.y), 6),
                width=round(float(box.width), 6), height=round(float(box.height), 6),
                label=box.label or normalized, source=box.source, confidence=box.confidence,
                mask_sha256=box.mask_sha256 or observation.mask_sha256,
            )
            regions.append(RegionBox(**{**identified.to_dict(), "region_id": self._region_id(image_sha256, normalized, identified)}))
        unknown = not regions
        result = RegionQueryResult(
            image_sha256=image_sha256, concept=normalized, model=observation.model or self.config.sam_model,
            purpose=purpose, image_width=image_width, image_height=image_height, regions=tuple(regions),
            mask_available=observation.mask_available, mask_sha256=observation.mask_sha256,
            regions_unknown=unknown, requires_manual_annotation=unknown, estimated_cost_usd=SAM_QUERY_COST_USD,
            cache_hit=False, source="sam", created_at=_utc_now(),
        )
        saved = self.store.save(result)
        self.store.record_audit(saved, cache_hit=False, cost=SAM_QUERY_COST_USD)
        return saved

    def annotate_manual(
        self,
        image_bytes: bytes,
        concept: str,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        label: Optional[str] = None,
        actor: str,
        replace_existing: bool = False,
        purpose: str = "manual_region_annotation",
    ) -> RegionQueryResult:
        if not actor.strip():
            raise ValueError("Manual region annotations require an actor identifier.")
        normalized = normalize_concept(concept)
        values = (float(x), float(y), float(width), float(height))
        x_value, y_value, width_value, height_value = values
        if width_value <= 0 or height_value <= 0 or x_value < 0 or y_value < 0 or x_value + width_value > 1 or y_value + height_value > 1:
            raise ValueError("Manual protected regions must be normalized and remain inside the source image.")
        image_sha256 = hashlib.sha256(image_bytes).hexdigest()
        image_width, image_height = self._image_dimensions(image_bytes)
        existing = self.store.get(image_sha256, normalized)
        regions = [] if replace_existing or existing is None else list(existing.regions)
        region = RegionBox(
            x=round(values[0], 6), y=round(values[1], 6), width=round(values[2], 6), height=round(values[3], 6),
            label=str(label or normalized), source="manual", confidence=1.0,
        )
        region = RegionBox(**{**region.to_dict(), "region_id": self._region_id(image_sha256, normalized, region)})
        regions = [item for item in regions if item.region_id != region.region_id]
        regions.append(region)
        result = RegionQueryResult(
            image_sha256=image_sha256, concept=normalized, model="manual", purpose=purpose,
            image_width=image_width, image_height=image_height, regions=tuple(regions),
            mask_available=bool(existing and existing.mask_available),
            mask_sha256=existing.mask_sha256 if existing else None,
            regions_unknown=False, requires_manual_annotation=False, estimated_cost_usd=0.0,
            cache_hit=False, source="manual", override=None, recorded_by=actor.strip(), created_at=_utc_now(),
        )
        saved = self.store.save(result)
        self.store.record_audit(saved, cache_hit=False, cost=0.0)
        return saved

    def authorize_unknown_override(
        self,
        image_bytes: bytes,
        concept: str,
        *,
        actor: str,
        reason: str,
        purpose: str = "explicit_unknown_region_override",
    ) -> RegionQueryResult:
        if not actor.strip() or not reason.strip():
            raise ValueError("An unknown-region override requires an actor and a reason.")
        normalized = normalize_concept(concept)
        image_sha256 = hashlib.sha256(image_bytes).hexdigest()
        image_width, image_height = self._image_dimensions(image_bytes)
        existing = self.store.get(image_sha256, normalized)
        if existing and not existing.regions_unknown:
            raise ValueError("Unknown-region overrides are only valid when the concept has no assigned region.")
        result = RegionQueryResult(
            image_sha256=image_sha256, concept=normalized,
            model=existing.model if existing else self.config.sam_model,
            purpose=purpose, image_width=image_width, image_height=image_height,
            regions=tuple(existing.regions) if existing else (),
            mask_available=bool(existing and existing.mask_available),
            mask_sha256=existing.mask_sha256 if existing else None,
            regions_unknown=True, requires_manual_annotation=False, estimated_cost_usd=0.0,
            cache_hit=False, source=existing.source if existing else "sam",
            override={"actor": actor.strip(), "reason": reason.strip()}, recorded_by=actor.strip(), created_at=_utc_now(),
        )
        saved = self.store.save(result)
        self.store.record_audit(saved, cache_hit=False, cost=0.0)
        return saved
