"""
InkLoop Autonomous Story-to-Bubble Stylist Engine.
Maps beat emotional intent, narrative function, dialogue delivery, and carrier types
directly to expressive comic and manga speech bubble geometry, tail style, and accents.
"""
import re
from typing import Optional, Dict, Any

from app.canvas.bubble_models import (
    BubbleShape,
    TailType,
    BubbleAccent,
    BubbleStyleRecommendation,
)


def recommend_bubble_style(
    emotional_intent: str = "",
    narrative_function: Optional[str] = None,
    delivery: Optional[str] = None,
    carrier: Optional[str] = None,
    sfx_category: Optional[str] = None,
    action_context: Optional[str] = None,
    story_event: Optional[str] = None,
    dialogue_text: Optional[str] = None,
) -> BubbleStyleRecommendation:
    """
    Deterministically deduces the most expressive speech/emotion/power bubble
    based on the story direction and character intent.
    """
    intent = (emotional_intent or "").lower()
    deliv = (delivery or "").lower()
    carr = (carrier or "").lower()
    func = (narrative_function or "").lower()
    sfx = (sfx_category or "").lower()
    action = f"{story_event or ''} {action_context or ''}".lower()
    dialogue = (dialogue_text or "").strip()
    dialogue_lower = dialogue.lower()
    letters = [char for char in dialogue if char.isalpha()]
    emphatic_caps = len(letters) >= 3 and sum(char.isupper() for char in letters) / len(letters) >= 0.9
    emphatic_punctuation = "!!" in dialogue or "!?" in dialogue or "?!" in dialogue
    stammered = bool(re.match(r"^(?:wh-|p-|n-|i-|m-|h-|y-)", dialogue_lower))
    # Context enriches a short line, while the speaker's delivery/emotion stays
    # the primary signal so a background event cannot turn calm dialogue into SFX.
    if not intent.strip():
        intent = f"{deliv} {action}".strip()
    if not deliv:
        for action_pattern, inferred_delivery in (
            (r"\b(whisper|whispers|whispered|murmur|murmurs)\b", "whisper"),
            (r"\b(shout|shouts|shouted|yell|yells|yelled|scream|screams)\b", "shout"),
            (r"\b(cry|cries|cried|sob|sobs|sobbed)\b", "crying"),
            (r"\b(laugh|laughs|laughed|giggle|giggles)\b", "joyful"),
        ):
            if re.search(action_pattern, action):
                deliv = inferred_delivery
                if inferred_delivery in {"crying", "joyful"}:
                    intent = f"{intent} {inferred_delivery}".strip()
                break

    # 1. Thought / Internal Monologue
    if "thought" in carr or "internal_thought" in carr or any(w in intent for w in ("thought", "dream", "ponder", "internal monologue", "remember")) or ("wonder" in intent and carr != "speech_bubble"):
        return BubbleStyleRecommendation(
            shape=BubbleShape.THOUGHT_CLOUD,
            tail_type=TailType.BUBBLE_CHAIN,
            halftone_shadow=False,
            accent=BubbleAccent.NONE,
            stroke_width=2.5,
            padding_x=28.0,
            padding_y=22.0,
            reasoning="Thought bubble selected for internal monologue and contemplative reflection.",
        )

    # 2. Narration / Time / Location Stamp / Exposition
    if any(c in carr for c in ("narration", "caption")) or any(w in intent for w in ("meanwhile", "later", "exposition", "setting the scene", "time transition")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.TILTED_BANNER if "dramatic" in intent or "action" in func else BubbleShape.ROUNDED_RECTANGLE,
            tail_type=TailType.NONE,
            halftone_shadow=True,
            accent=BubbleAccent.NONE,
            stroke_width=2.0,
            fill_color="#FCFCF8",
            padding_x=20.0,
            padding_y=14.0,
            reasoning="Narration banner selected for narrative caption or setting the scene.",
        )

    # 3. Whisper / Secret / Faint voice
    if "whisper" in deliv or any(w in intent for w in ("whisper", "secret", "muffled", "faint", "dying breath", "hushed")) or (
        "..." in dialogue and any(w in action for w in ("whisper", "stealth", "secret", "hushed", "quietly"))
    ):
        return BubbleStyleRecommendation(
            shape=BubbleShape.WHISPER_CLOUD_SOFT,
            tail_type=TailType.WHISPER_DASHED,
            halftone_shadow=False,
            accent=BubbleAccent.NONE,
            stroke_width=2.0,
            stroke_dash="5 4",
            stroke_color="#555555",
            padding_x=22.0,
            padding_y=16.0,
            reasoning="Dashed whisper bubble selected for secretive or hushed dialogue.",
        )

    # 4. Supreme Power, Attack, Energy Blast or Manga Impact SFX
    impact_words = ("blast", "explosion", "special move", "superpower", "technique", "shockwave", "aura", "divine power")
    explicit_power_intent = any(word in intent for word in impact_words)
    impact_delivery = any(word in action for word in impact_words) and (
        any(word in deliv for word in ("shout", "scream", "yell", "battle"))
        or emphatic_caps or emphatic_punctuation
    )
    if sfx in ("impact", "energy") or explicit_power_intent or impact_delivery:
        return BubbleStyleRecommendation(
            shape=BubbleShape.EXPLOSIVE_BLAST,
            tail_type=TailType.LIGHTNING_BOLT,
            halftone_shadow=True,
            accent=BubbleAccent.SPEEDLINE_NEEDLES,
            stroke_width=4.0,
            padding_x=32.0,
            padding_y=24.0,
            reasoning="Explosive blast with radial needles selected for supreme power and impact.",
        )

    # 5. Shout / Scream / Battle Roar / Anger
    if (
        any(w in deliv for w in ("shout", "scream", "yell", "furious", "angry", "battle"))
        or any(w in f"{intent} {action}" for w in ("shout", "scream", "yell", "roar", "furious", "anger", "angry", "rage", "battle cry", "alarm", "urgent call"))
        or emphatic_caps or emphatic_punctuation
        or (
            any(w in action for w in ("battle", "combat", "fight", "punch", "strike", "slash", "attack", "explosion", "roar"))
            and any(w in deliv for w in ("shout", "scream", "yell", "furious", "angry"))
        )
    ):
        return BubbleStyleRecommendation(
            shape=BubbleShape.SHOUT_BURST,
            tail_type=TailType.LIGHTNING_BOLT,
            halftone_shadow=True,
            accent=BubbleAccent.SPEEDLINE_NEEDLES if "battle" in intent else BubbleAccent.NONE,
            stroke_width=3.5,
            padding_x=28.0,
            padding_y=20.0,
            reasoning="Jagged starburst with lightning tail selected for shout or intense scream.",
        )

    # 6. Fear / Shivering / Extreme Hesitation
    if any(w in f"{intent} {action}" for w in ("fear", "terrified", "panic", "shiver", "tremble", "nervous", "stutter", "hesitat", "dread", "anxious", "scared")) or (
        stammered and any(w in f"{intent} {action}" for w in ("fear", "panic", "nervous", "hesitat", "anxious", "scared"))
    ):
        return BubbleStyleRecommendation(
            shape=BubbleShape.FEAR_TREMBLE,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=False,
            accent=BubbleAccent.SWEAT_DROP,
            stroke_width=2.2,
            padding_x=24.0,
            padding_y=18.0,
            reasoning="Trembling wavy bubble with sweat drop selected for fear or nervous shivering.",
        )

    # 7. Affection / Love / Delight / Sweet Adoration
    if any(w in intent for w in ("love", "affection", "heart", "blush", "delight", "sweet", "crush", "adoring", "infatuat", "warmth", "joyful", "joy", "happy", "happiness", "excited", "excitement", "euphoric", "celebrat")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.AFFECTION_HEART,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=True,
            accent=BubbleAccent.SPARKLES,
            stroke_width=2.5,
            padding_x=26.0,
            padding_y=22.0,
            reasoning="Heart-shaped expressive bubble with sparkles selected for affection or delight.",
        )

    # 8. Slime / Disgust / Comedic Mess / Goo / Surprise
    if any(w in intent for w in ("slime", "disgust", "goo", "splat", "mess", "melt", "gross", "sticky", "drool")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.SPLAT_SURPRISE,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=True,
            accent=BubbleAccent.NONE,
            stroke_width=2.8,
            padding_x=30.0,
            padding_y=24.0,
            reasoning="Viscous slime splat bubble selected for gooey surprise or disgust.",
        )

    # 9. Robotic / AI / Comms / Intercom / Television (Delivery or Intent)
    if deliv in ("robotic", "android", "cyborg") or any(w in f"{intent} {action}" for w in ("robot", "synthetic", "ai system", "cybernetic")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.GLITCH_DIGITAL_CRT if "glitch" in intent or "cyber" in intent else BubbleShape.ELECTRIC_ROBOTIC,
            tail_type=TailType.LIGHTNING_BOLT,
            halftone_shadow=True,
            accent=BubbleAccent.NONE,
            stroke_width=2.5,
            padding_x=24.0,
            padding_y=16.0,
            reasoning="Chamfered electric polygon with lightning tail selected for robotic or synth delivery.",
        )

    # 10. Remote Device / Radio Broadcast / Phone / Intercom
    if deliv == "remote_device" or any(w in f"{intent} {action}" for w in ("walkie", "radio", "broadcast", "phone speaker", "transceiver", "intercom", "comms")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.RADIO_BROADCAST_ZIGZAG,
            tail_type=TailType.ZIGZAG_ANTENNA,
            halftone_shadow=True,
            accent=BubbleAccent.ELECTRIC_SPARKS,
            stroke_width=2.5,
            padding_x=26.0,
            padding_y=18.0,
            reasoning="Zigzag broadcast perimeter with antenna pulse selected for radio/phone comms.",
        )

    # 10. Dark Aura / Demon / Villain / Cursed Entity (Inverted Mode)
    if any(w in intent for w in ("curse", "demon", "shadow", "villain", "monster", "evil", "ghostly", "dark aura", "sinister")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.DARK_AURA_GHOST,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=True,
            inverted_dark_mode=True,
            fill_color="#111111",
            stroke_color="#FFFFFF",
            accent=BubbleAccent.NONE,
            stroke_width=2.8,
            padding_x=28.0,
            padding_y=22.0,
            reasoning="Dark rising aura with inverted black fill selected for sinister or demonic dialogue.",
        )

    # 11. Freezing / Chilling / Murderous Frost
    if any(w in intent for w in ("freeze", "freezing", "ice", "frost", "chilling", "cold", "murderous")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.ICICLE_FROST,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=False,
            accent=BubbleAccent.NONE,
            stroke_width=2.5,
            padding_x=26.0,
            padding_y=20.0,
            reasoning="Hanging icicle spikes selected for freezing cold or chilling dialogue.",
        )

    # 12. Sadness / Crying / Remorse / Grief
    if any(w in intent for w in ("crying", "tears", "sad", "weep", "sobbing", "remorse", "grief", "heartbroken")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.DROPLET_TEAR_SAD,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=False,
            accent=BubbleAccent.SWEAT_DROP,
            stroke_width=2.2,
            padding_x=26.0,
            padding_y=22.0,
            reasoning="Downward teardrop bubble selected for sad or weeping dialogue.",
        )

    # 13. Digital / Glitch / Cybernetic Artifacts
    if any(w in intent for w in ("glitch", "cyber", "hologram", "digital artifact", "corrupt")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.GLITCH_DIGITAL_CRT,
            tail_type=TailType.LIGHTNING_BOLT,
            halftone_shadow=True,
            accent=BubbleAccent.NONE,
            stroke_width=2.5,
            padding_x=24.0,
            padding_y=16.0,
            reasoning="Stepped digital CRT glitch block selected for cybernetic communication.",
        )

    # 10. Default Calm / Conversational Dialogue
    if any(w in intent for w in ("curious", "curiosity", "wonder", "questioning", "inquisitive")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.SCALLOPED_FLOWER,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=False,
            accent=BubbleAccent.DIZZINESS_SWIRL,
            stroke_width=2.4,
            padding_x=24.0,
            padding_y=18.0,
            reasoning="Soft scalloped bubble selected for curious or wondering delivery.",
        )

    if any(w in intent for w in ("surprised", "astonished", "shocked", "startled", "confused", "bewildered")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.SPLAT_SURPRISE,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=False,
            accent=BubbleAccent.SHOCK_MARKS,
            stroke_width=2.8,
            padding_x=26.0,
            padding_y=20.0,
            reasoning="Splat surprise bubble selected for a sudden shock or confused reaction.",
        )

    if any(w in intent for w in ("calm", "gentle", "reassuring", "soothing", "hopeful", "comforting")) or any(w in deliv for w in ("calm", "gentle", "soft")):
        return BubbleStyleRecommendation(
            shape=BubbleShape.OVAL,
            tail_type=TailType.SMOOTH_POINTER,
            halftone_shadow=False,
            accent=BubbleAccent.NONE,
            stroke_width=2.1,
            padding_x=24.0,
            padding_y=17.0,
            reasoning="Light oval bubble selected for calm, gentle, or reassuring dialogue.",
        )

    return BubbleStyleRecommendation(
        shape=BubbleShape.OVAL if any(w in intent for w in ("casual", "friendly", "conversational")) else BubbleShape.ROUNDED_RECTANGLE,
        tail_type=TailType.SMOOTH_POINTER,
        halftone_shadow=False,
        accent=BubbleAccent.NONE,
        stroke_width=2.5,
        padding_x=24.0,
        padding_y=18.0,
        reasoning="Classic smooth bubble selected for natural dialogue delivery.",
    )
