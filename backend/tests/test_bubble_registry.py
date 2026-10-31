from app.canvas.bubble_registry import (
    BUBBLE_TYPE_BY_ID,
    BUBBLE_TYPES,
    attach_type_ids,
    describe_bubble_types,
    type_id_for_appearance,
    validate_bubble_registry,
)
from app.canvas.catalogue import BUBBLE_PRESETS


EXPECTED_TYPE_IDS = {
    "speech.normal",
    "speech.shout",
    "speech.whisper",
    "thought.cloud",
    "speech.offpanel",
    "narration.box",
    "caption.timeplace",
    "sfx.text",
}


def test_registry_has_exactly_eight_semantic_type_ids_and_contract_limits():
    assert len(BUBBLE_TYPES) == 8
    assert set(BUBBLE_TYPE_BY_ID) == EXPECTED_TYPE_IDS
    assert {item["type_id"] for item in describe_bubble_types()} == EXPECTED_TYPE_IDS
    assert BUBBLE_TYPE_BY_ID["speech.normal"].word_limit == 12
    assert BUBBLE_TYPE_BY_ID["speech.shout"].word_limit == 5
    assert BUBBLE_TYPE_BY_ID["speech.whisper"].word_limit == 8
    assert BUBBLE_TYPE_BY_ID["thought.cloud"].word_limit == 10
    assert BUBBLE_TYPE_BY_ID["narration.box"].word_limit == 16
    assert BUBBLE_TYPE_BY_ID["caption.timeplace"].word_limit == 5
    assert BUBBLE_TYPE_BY_ID["sfx.text"].word_limit == 3


def test_all_fifty_legacy_presets_remain_stable_appearance_variants():
    ids = [item["id"] for item in BUBBLE_PRESETS]
    assert len(ids) == 50
    assert len(set(ids)) == 50
    variants = attach_type_ids(BUBBLE_PRESETS)
    validate_bubble_registry(variants)
    assert len(variants) == 50
    assert {item["type_id"] for item in variants} <= EXPECTED_TYPE_IDS
    assert all(item["type_id"] == type_id_for_appearance(item["id"]) for item in variants)
    assert all(item["id"] in ids for item in variants)


def test_legacy_intents_map_to_semantics_without_minting_new_types():
    assert type_id_for_appearance("bubble_spoken_classic") == "speech.normal"
    assert type_id_for_appearance("bubble_thought_halftone") == "thought.cloud"
    assert type_id_for_appearance("bubble_whisper_soft_color") == "speech.whisper"
    assert type_id_for_appearance("bubble_broadcast_hand_inked") == "speech.offpanel"
    assert type_id_for_appearance("bubble_narration_classic") == "narration.box"
    assert len(BUBBLE_TYPE_BY_ID) == 8
