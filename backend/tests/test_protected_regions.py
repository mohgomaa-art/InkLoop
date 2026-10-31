from io import BytesIO

import pytest
from PIL import Image

from app.canvas.protected_regions import (
    ProtectedRegionService,
    ProtectedRegionStore,
    RegionBox,
    SegmentationObservation,
    normalize_concept,
)
from app.parsers import parse_sam_response


def _image_bytes(color=(240, 240, 240)):
    image = Image.new("RGB", (320, 180), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class _FixtureSegmenter:
    def __init__(self, boxes=None):
        self.calls = []
        self.boxes = boxes if boxes is not None else [
            RegionBox(x=0.42, y=0.12, width=0.18, height=0.24, label="face", source="sam", confidence=0.98)
        ]

    def segment(self, image_bytes, concept, purpose):
        self.calls.append({"image_bytes": image_bytes, "concept": concept, "purpose": purpose})
        return SegmentationObservation(
            boxes=self.boxes,
            model="fixture-sam-3.1",
            mask_available=True,
            mask_sha256="f" * 64,
        )


def test_region_cache_is_keyed_by_image_hash_and_normalized_concept(tmp_path):
    image = _image_bytes()
    segmenter = _FixtureSegmenter()
    store = ProtectedRegionStore(tmp_path / "protected.sqlite")
    service = ProtectedRegionService(store=store, segmenter=segmenter)

    first = service.get_or_segment(image, "  FACE  ", purpose="speech bubble face clearance")
    second = service.get_or_segment(image, "face", purpose="a later purpose is logged only on a miss")

    assert first.concept == "face"
    assert first.cache_hit is False
    assert first.estimated_cost_usd == pytest.approx(0.0025)
    assert second.cache_hit is True
    assert second.estimated_cost_usd == 0.0
    assert second.regions[0].region_id == first.regions[0].region_id
    assert second.regions[0].source == "sam"
    assert second.mask_available and second.mask_sha256 == "f" * 64
    assert len(segmenter.calls) == 1
    assert segmenter.calls[0]["concept"] == "face"
    audit = store.audit(first.image_sha256)
    assert [row["cache_hit"] for row in audit] == [0, 1]
    assert [row["estimated_cost_usd"] for row in audit] == [0.0025, 0.0]
    assert audit[0]["purpose"] == "speech bubble face clearance"


def test_distinct_image_or_concept_never_reuses_an_unrelated_region(tmp_path):
    segmenter = _FixtureSegmenter()
    service = ProtectedRegionService(
        store=ProtectedRegionStore(tmp_path / "protected.sqlite"), segmenter=segmenter,
    )
    first = service.get_or_segment(_image_bytes(), "face")
    second = service.get_or_segment(_image_bytes((200, 200, 200)), "face")
    third = service.get_or_segment(_image_bytes(), "lantern")
    assert len(segmenter.calls) == 3
    assert first.image_sha256 != second.image_sha256
    assert first.concept != third.concept
    assert normalize_concept("  Face   ") == "face"


def test_no_detected_region_is_unknown_and_never_gets_a_center_guess(tmp_path):
    service = ProtectedRegionService(
        store=ProtectedRegionStore(tmp_path / "protected.sqlite"),
        segmenter=_FixtureSegmenter(boxes=[]),
    )
    result = service.get_or_segment(_image_bytes(), "speaker head")
    assert result.regions == ()
    assert result.regions_unknown is True
    assert result.requires_manual_annotation is True
    assert result.override is None


def test_manual_annotation_resolves_unknown_with_stable_provenance(tmp_path):
    image = _image_bytes()
    segmenter = _FixtureSegmenter(boxes=[])
    service = ProtectedRegionService(
        store=ProtectedRegionStore(tmp_path / "protected.sqlite"), segmenter=segmenter,
    )
    unknown = service.get_or_segment(image, "face")
    annotated = service.annotate_manual(
        image, "FACE", x=0.4, y=0.1, width=0.2, height=0.25,
        label="Gomaa head", actor="creator-1",
    )
    reloaded = service.store.get(unknown.image_sha256, "face")
    assert annotated.regions_unknown is False
    assert annotated.requires_manual_annotation is False
    assert annotated.recorded_by == "creator-1"
    assert annotated.regions[0].source == "manual"
    assert annotated.regions[0].region_id == reloaded.regions[0].region_id
    assert len(segmenter.calls) == 1


def test_unknown_override_is_explicit_and_cannot_bypass_a_known_region(tmp_path):
    image = _image_bytes()
    unknown_service = ProtectedRegionService(
        store=ProtectedRegionStore(tmp_path / "unknown.sqlite"),
        segmenter=_FixtureSegmenter(boxes=[]),
    )
    unknown = unknown_service.get_or_segment(image, "face")
    allowed = unknown_service.authorize_unknown_override(
        image, "face", actor="creator-1", reason="Confirmed this panel has no visible face.",
    )
    assert allowed.regions_unknown is True
    assert allowed.requires_manual_annotation is False
    assert allowed.override == {"actor": "creator-1", "reason": "Confirmed this panel has no visible face."}
    assert allowed.recorded_by == "creator-1"

    known_service = ProtectedRegionService(
        store=ProtectedRegionStore(tmp_path / "known.sqlite"), segmenter=_FixtureSegmenter(),
    )
    known_service.get_or_segment(image, "face")
    with pytest.raises(ValueError, match="only valid when the concept has no assigned region"):
        known_service.authorize_unknown_override(image, "face", actor="creator-1", reason="test")


def test_manual_regions_must_be_normalized_and_inside_the_source_image(tmp_path):
    service = ProtectedRegionService(store=ProtectedRegionStore(tmp_path / "protected.sqlite"), segmenter=_FixtureSegmenter())
    with pytest.raises(ValueError, match="normalized and remain inside"):
        service.annotate_manual(
            _image_bytes(), "face", x=0.9, y=0.2, width=0.2, height=0.2, actor="creator-1",
        )


def test_sam_mask_payload_is_reduced_to_a_stable_digest():
    raw = "<|mask;x=0;y=0;data=encoded-mask-payload|>"
    parsed = parse_sam_response(raw)
    assert parsed.mask_available is True
    assert len(parsed.mask_sha256) == 64
    assert parse_sam_response(raw).mask_sha256 == parsed.mask_sha256
