import pytest

from app.canvas.bubble_registry import BUBBLE_TYPE_BY_ID
from app.text.lettering_layout import (
    LetteringValidationError,
    count_words,
    layout_lettering_text,
    type_id_for_text,
)


@pytest.mark.parametrize(
    ("type_id", "limit"),
    [
        ("speech.normal", 12),
        ("speech.shout", 5),
        ("speech.whisper", 8),
        ("thought.cloud", 10),
        ("speech.offpanel", 12),
        ("narration.box", 16),
        ("caption.timeplace", 5),
        ("sfx.text", 3),
    ],
)
def test_each_semantic_type_accepts_limit_and_rejects_one_word_over(type_id, limit):
    accepted = "word " * (limit - 1) + "word"
    layout = layout_lettering_text(
        accepted, type_id, max_width_px=900, max_height_px=600,
        requested_font_size_px=BUBBLE_TYPE_BY_ID[type_id].min_font_px,
    )
    assert layout.word_count == limit
    assert not layout.overflow

    with pytest.raises(LetteringValidationError) as error:
        layout_lettering_text(
            accepted + " extra", type_id, max_width_px=900, max_height_px=600,
        )
    assert error.value.code == "ERR_LETTERING_WORD_LIMIT"
    assert error.value.details == {"type_id": type_id, "word_count": limit + 1, "word_limit": limit}


def test_one_word_is_measured_with_active_font_and_fits_without_overflow():
    layout = layout_lettering_text(
        "Lantern", "speech.normal", max_width_px=200, max_height_px=80,
        font_family="Comic Neue", requested_font_size_px=24,
    )
    assert layout.lines == ["Lantern"]
    assert layout.direction == "ltr"
    assert layout.measurement_source == "Pillow font metrics"
    assert layout.content_width_px > 0
    assert layout.line_count == 1
    assert layout.font_size_px in range(16, 29)
    assert not layout.overflow


def test_arabic_layout_shapes_before_measurement_and_sets_rtl():
    text = "الضوء لا ينطفئ"
    layout = layout_lettering_text(
        text, "narration.box", max_width_px=260, max_height_px=100,
        font_family="Comic Neue", requested_font_size_px=20,
    )
    assert layout.direction == "rtl"
    assert layout.measured_font_family.lower().startswith("notosansarabic")
    assert layout.content_width_px > 0
    assert layout.text == text
    assert count_words(text) == 3


def test_minimum_font_overflow_is_reported_without_rewriting_text():
    text = "unbroken" * 10
    layout = layout_lettering_text(
        text, "speech.normal", max_width_px=30, max_height_px=20,
        requested_font_size_px=28,
    )
    assert layout.text == text
    assert layout.font_size_px == 16
    assert layout.overflow
    assert layout.diagnostics[0]["code"] == "ERR_LETTERING_MIN_FONT_OVERFLOW"
    assert layout.diagnostics[0]["details"]["font_size_px"] == 16


def test_line_limit_is_visible_when_explicit_lines_cannot_be_reflowed():
    layout = layout_lettering_text(
        "one\ntwo\nthree\nfour", "speech.normal",
        max_width_px=240, max_height_px=100, requested_font_size_px=24,
    )
    assert layout.lines == ["one", "two", "three", "four"]
    assert layout.line_count == 4
    assert layout.max_lines == 3
    assert layout.overflow
    assert layout.diagnostics[0]["code"] == "ERR_LETTERING_LINE_LIMIT"


def test_explicit_carrier_and_delivery_map_to_semantic_type_ids():
    assert type_id_for_text(carrier="speech_bubble", delivery="shout") == "speech.shout"
    assert type_id_for_text(carrier="thought_bubble") == "thought.cloud"
    assert type_id_for_text(content_kind="narration", carrier="caption") == "narration.box"
    assert type_id_for_text(content_kind="date_or_place", carrier="caption") == "caption.timeplace"
    assert type_id_for_text(carrier="sound_effect") == "sfx.text"
