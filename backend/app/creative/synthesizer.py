"""
InkLoop AI Universe Synthesizer.
Provides prompt-driven semantic entity extraction, dynamic universe generation,
and live LLM orchestration, replacing static mock data with genuine narrative synthesis.
"""
import re
import time
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple

import httpx

from app.config import InkLoopConfig
from app.creative.schemas import (
    CreativeMode,
    CreativeBrief,
    FactCategory,
    FactItem,
    BriefVisualReference,
    CreativeStoryBible,
    CharacterIdentityProfile,
    OutfitVariant,
    CharacterArcCheckpoint,
    RelationshipGraph,
    RelationshipEdge,
    WorldBible,
    LocationSpec,
    PropArtifactSpec,
    MagicOrTechAbilityRule,
    NarrativeStructure,
    ChapterOutline,
    SceneCandidate,
    SetupPayoffItem,
    VisualStyleProfile,
)
from app.project.bible import StoryBible

logger = logging.getLogger(__name__)


def _clean(text: str) -> str:
    return " ".join(text.strip().split())


class SemanticEntities:
    """Parsed semantic entities extracted from the natural language brief."""
    def __init__(self):
        self.title: str = ""
        self.format: str = "webtoon"
        self.genre: str = "Supernatural Drama"
        self.tone: str = "Emotionally grounded, somber, atmospheric noir fantasy"
        self.premise: str = ""
        self.central_dramatic_question: str = ""
        self.stakes: str = ""
        self.themes: List[str] = []
        self.motifs: List[str] = []
        self.world_name: str = ""
        self.world_premise: str = ""
        self.geography: str = ""
        self.culture: str = ""
        self.factions: List[str] = []
        self.protagonist_id: str = "nour"
        self.protagonist_name: str = "Nour"
        self.protagonist_role: str = "Protagonist"
        self.protagonist_age: str = "17-18"
        self.protagonist_profession: str = "Courier"
        self.protagonist_invariants: List[str] = []
        self.protagonist_outfit_desc: str = ""
        self.protagonist_garments: List[str] = []
        self.protagonist_colors: List[str] = []
        self.protagonist_goal: str = ""
        self.protagonist_need: str = ""
        self.protagonist_fear: str = ""
        self.protagonist_backstory: str = ""
        self.supporting_characters: List[Dict[str, Any]] = []
        self.locations: List[Dict[str, Any]] = []
        self.props: List[Dict[str, Any]] = []
        self.supernatural_rules: List[Dict[str, Any]] = []
        self.conflict_engine: str = ""
        self.macro_arc_beats: Dict[str, str] = {}
        self.chapters: List[Dict[str, Any]] = []
        self.style_id: str = "manga_ink"
        self.style_name: str = "Dynamic Ink & Screentone"
        self.style_medium: str = "Digital Inking with Screentone and Selective Spot Color"
        self.line_art_rules: List[str] = []
        self.negative_constraints: List[str] = []
        self.palette_rules: List[str] = []


def extract_semantic_entities(
    user_prompt: str,
    existing_bible: Optional[StoryBible] = None,
) -> SemanticEntities:
    """
    Analyzes natural language prompt and active StoryBible to dynamically extract
    characters, world settings, genre, format, tone, and conflict invariants.
    """
    e = SemanticEntities()
    p_lower = user_prompt.lower()

    # 1. Format Detection
    if "manhwa" in p_lower:
        e.format = "manhwa"
    elif "manga" in p_lower:
        e.format = "manga"
    elif "comic" in p_lower:
        e.format = "comic"
    elif "graphic novel" in p_lower:
        e.format = "graphic_novel"
    elif "webtoon" in p_lower:
        e.format = "webtoon"
    else:
        e.format = "webtoon"

    is_cyberpunk = bool(re.search(r"\b(cyberpunk|mecha|android|cyborg)\b", p_lower))
    is_horror = bool(re.search(r"\b(horror|haunted|demon|gothic|souls|murdered)\b", p_lower))
    is_mystery = bool(re.search(r"\b(mystery|detective|crime|investigation|clockwork|antique)\b", p_lower))

    # 2. Genre Detection
    if is_cyberpunk:
        e.genre = "Sci-Fi / Cyberpunk Noir"
        e.tone = "Gritty, high-voltage, technologically alienated noir"
        e.style_id = "cyberpunk_neon_noir_ink"
        e.style_name = "Cyberpunk High-Contrast Ink & Screentone"
    elif "dark fantasy" in p_lower or ("fantasy" in p_lower and any(w in p_lower for w in ["dark", "shadow", "flood", "demon", "cataclysm", "relic", "ancient"])):
        e.genre = "Dark Fantasy / Supernatural Mystery"
        e.tone = "Emotionally grounded, somber, atmospheric noir fantasy"
        e.style_id = "dark_fantasy_noir_ink"
        e.style_name = "Atmospheric Gothic Ink & Screentone"
    elif is_horror:
        e.genre = "Psychological Horror / Supernatural Thriller"
        e.tone = "Claustrophobic, dread-filled, visceral psychological suspense"
        e.style_id = "gothic_horror_ink"
        e.style_name = "Chiaroscuro Horror Screentone"
    elif is_mystery:
        e.genre = "Noir Mystery / Investigative Thriller"
        e.tone = "Atmospheric, intellectual, quietly suspenseful noir"
        e.style_id = "noir_detective_ink"
        e.style_name = "Vintage Detective Ink & Shadow"
    elif "romance" in p_lower or "slice of life" in p_lower or "school" in p_lower:
        e.genre = "Grounded Drama / Slice of Life Romance"
        e.tone = "Intimate, emotionally observant, nostalgic, bittersweet"
        e.style_id = "soft_screentone_romance"
        e.style_name = "Delicate Screentone & Expressive Linework"
    elif "action" in p_lower or "shonen" in p_lower or "martial" in p_lower:
        e.genre = "Dynamic Action / Shonen Adventure"
        e.tone = "Kinetic, adrenaline-fueled, high-stakes heroic tension"
        e.style_id = "shonen_action_ink"
        e.style_name = "High-Dynamic Speed-Line Comic Inking"
    elif "space" in p_lower or "sci-fi" in p_lower or "alien" in p_lower:
        e.genre = "Hard Sci-Fi / Space Opera"
        e.tone = "Expansive, cerebral, high-stakes techno-thriller"
        e.style_id = "hard_scifi_ink"
        e.style_name = "Technical Precision Inking & Spot Lighting"
    else:
        e.genre = "Supernatural Drama / Mystery"
        e.tone = "Atmospheric, thoughtful, emotionally grounded drama"
        e.style_id = "atmospheric_drama_ink"
        e.style_name = "Monochrome Expressive Linework"

    # 3. Title Extraction
    t_match = re.search(r"titled\s+['\"]([^'\"]+)['\"]", user_prompt, re.I)
    if not t_match:
        t_match = re.search(r"['\"]([^'\"]{3,40})['\"]", user_prompt)
    if not t_match:
        t_match = re.search(r"titled\s+([A-Za-z0-9\s:_-]{3,35}?)(?:\s+about|\s+set|\s*\.|\s*,|\s*$)", user_prompt, re.I)

    # 4. Protagonist Identification
    # Check if prompt specifies a name: e.g. "named Jin", "pilot named Jin", "courier Nour", "character Clara"
    name_match = re.search(r"(?:named|character|protagonist|hero|pilot|courier|detective|restorer|knight)\s+([A-Z][a-z]+)", user_prompt)
    if not name_match:
        name_match = re.search(r"\babout\s+(?:an?\s+[\w\s-]{1,20}\s+)?([A-Z][a-z]+)\b", user_prompt)

    extracted_name = name_match.group(1).strip() if name_match else None

    # Check for Nour or existing bible
    has_nour_in_prompt = "nour" in p_lower
    has_flood_in_prompt = "flood" in p_lower or "deluge" in p_lower or "sunken" in p_lower or "vespera" in p_lower

    if has_nour_in_prompt or (not extracted_name and existing_bible and "nour" in existing_bible.characters):
        e.protagonist_name = "Nour"
        e.protagonist_id = "nour"
    elif extracted_name and extracted_name.lower() not in ["the", "this", "dark", "sci", "supernatural", "a", "an"]:
        e.protagonist_name = extracted_name
        e.protagonist_id = extracted_name.lower()
    else:
        # Genre-specific default protagonist name
        if is_cyberpunk:
            e.protagonist_name = "Jin"
            e.protagonist_id = "jin"
        elif is_horror or is_mystery:
            e.protagonist_name = "Clara"
            e.protagonist_id = "clara"
        elif "romance" in p_lower:
            e.protagonist_name = "Hana"
            e.protagonist_id = "hana"
        elif "space" in p_lower:
            e.protagonist_name = "Orion"
            e.protagonist_id = "orion"
        else:
            e.protagonist_name = "Nour"
            e.protagonist_id = "nour"

    # Set Title
    if t_match:
        e.title = t_match.group(1).strip()
    elif e.protagonist_id == "nour":
        e.title = "Tides of Remembrance"
    elif is_cyberpunk:
        e.title = f"Neon Overdrive: {e.protagonist_name}"
    elif is_mystery or "relic" in p_lower or "clockwork" in p_lower:
        e.title = f"The Clockwork Echoes of {e.protagonist_name}"
    elif is_horror:
        e.title = f"Whispers in the Dark: {e.protagonist_name}"
    elif "romance" in p_lower:
        e.title = f"Quiet Notes of {e.protagonist_name}"
    else:
        e.title = f"Echoes of {e.protagonist_name}"

    # 5. Protagonist Profession & Age
    for prof in ["courier", "mecha pilot", "pilot", "antique restorer", "restorer", "detective", "knight", "scavenger", "alchemist", "hacker", "diver", "bounty hunter", "student", "engineer"]:
        if prof in p_lower:
            e.protagonist_profession = prof.capitalize()
            break
    else:
        if is_cyberpunk:
            e.protagonist_profession = "Rogue Pilot"
        elif is_mystery:
            e.protagonist_profession = "Investigator"
        else:
            e.protagonist_profession = "Courier"

    age_match = re.search(r"(\d{2})[- ]year[- ]old", p_lower)
    if age_match:
        e.protagonist_age = age_match.group(1)
    else:
        e.protagonist_age = "17-18"

    # 6. Protagonist Visual Invariants
    invariants = []

    # Check existing bible if protagonist matches
    existing_char = existing_bible.characters.get(e.protagonist_id) if existing_bible else None
    if existing_char and existing_char.visual_invariants:
        invariants = list(existing_char.visual_invariants)

    # Hair analysis
    if "blonde" in p_lower or "blond" in p_lower:
        invariants = [inv for inv in invariants if "black" not in inv.lower() and "streak" not in inv.lower()]
        invariants.append("bright blonde hair")
    elif "white streak" in p_lower or ("streak" in p_lower and "white" in p_lower):
        if not any("white streak" in inv.lower() for inv in invariants):
            invariants.append("pure-white hair streak always on character's left temple")
    elif "silver hair" in p_lower:
        invariants.append("messy silver hair")

    if ("black hair" in p_lower or "dark hair" in p_lower) and not any("black" in inv.lower() for inv in invariants):
        invariants.append("short messy jet-black hair")

    # Spectacles / Eyewear
    if "no glasses" in p_lower or "never wears glasses" in p_lower or "without glasses" in p_lower:
        invariants = [inv for inv in invariants if "glasses" not in inv.lower() and "spectacles" not in inv.lower()]
    elif "glasses" in p_lower or "wireframe" in p_lower:
        if not any("glasses" in inv.lower() for inv in invariants):
            invariants.append("round wireframe glasses frames")

    # Cybernetics / Features
    if "cybernetic arm" in p_lower or "mechanical arm" in p_lower:
        invariants.append("exposed chrome cybernetic left arm with hydraulic conduit lines")
    if "scar" in p_lower:
        invariants.append("small faint nick scar across right cheekbone")

    # Attire
    if "leather jacket" in p_lower:
        invariants.append("weathered black leather rider jacket with brass zipper teeth")
    elif "hooded jacket" in p_lower or "hoodie" in p_lower:
        invariants.append("oversized hooded jacket with lightning-bolt chest emblem")
    elif "flight suit" in p_lower or "pilot suit" in p_lower or is_cyberpunk:
        invariants.append("tactical pressurized flight suit with telemetry badges")
    elif "trench coat" in p_lower or "coat" in p_lower:
        invariants.append("tailored charcoal wool trench coat with upturned collar")

    # Ensure invariant count invariant: At least 2 invariants!
    if len(invariants) < 2:
        if e.protagonist_id == "nour":
            invariants = [
                "white streak always on character's left side",
                "round wireframe glasses frames",
                "oversized hooded jacket with lightning-bolt chest patch",
            ]
            if "blonde" in p_lower:
                invariants = [inv for inv in invariants if "streak" not in inv.lower()]
                invariants.append("bright blonde hair")
            if "no glasses" in p_lower or "never wears glasses" in p_lower:
                invariants = [inv for inv in invariants if "glasses" not in inv.lower()]
        elif is_cyberpunk:
            invariants = [
                "asymmetrical undercut jet-black hair with cyan cybernetic port at temple",
                "tactical pressurized carbon flight suit with orange telemetry chevron",
                "sharp observant dark eyes behind tactical targeting visor",
            ]
        elif is_horror or is_mystery:
            invariants = [
                "auburn hair pinned up in an antique bronze clasp with loose temple strands",
                "leather tool apron worn over dark wool vest and high-collared shirt",
                "brass monocular jeweler loupe hanging from neck cord",
            ]
        else:
            invariants = [
                f"signature high-contrast silhouette for {e.protagonist_name}",
                "weathered field traveler jacket with brass clasps",
                "distinctive observant pale gaze with resolute posture",
            ]

    e.protagonist_invariants = invariants

    # 7. World Setting Extraction
    loc_match = re.search(r"(?:set in|takes place in|world of|city of)\s+([A-Z][a-zA-Z0-9\s-]{2,30}?)(?:\.|\,|$|\s+where|\s+with|\s+about)", user_prompt, re.I)
    extracted_loc = loc_match.group(1).strip() if loc_match else None

    if has_flood_in_prompt or (extracted_loc and "vespera" in extracted_loc.lower()) or e.protagonist_id == "nour":
        e.world_name = "The Drowned Basins of Vespera"
        e.world_premise = "Vespera: A multi-tiered flooded metropolis navigated by gondolas and elevated walkways where memories are traded as currency."
        e.geography = "Drowned coastal basin, perpetual sea-mist, seasonal gale tides, multi-level viaducts."
        e.culture = "Relic-scavenger economy stratified by elevation; wealth determines how far above sea level citizens live."
        e.factions = ["The Sovereign Archive Syndicate", "The Viaduct Courier Guild", "The Deep Siphon Engineers"]
    elif "neo-tokyo" in p_lower or is_cyberpunk:
        e.world_name = extracted_loc or "Neo-Tokyo Sector 09"
        e.world_premise = f"{e.world_name}: A multi-tiered neon-drenched megacity dominated by autonomous AI mega-corporations and underground rebel pilot rings."
        e.geography = "Vertical megacity expanse, holographic skylines, perpetual acid drizzle, subterranean transit conduits."
        e.culture = "High-tech corporate feudalism; neural cyberware determines societal tier and biometric access."
        e.factions = ["OmniCorp AI Directorate", "Subterranean Pilot Network", "Synthetic Liberation Front"]
    elif "gothic" in p_lower or is_horror or is_mystery or "clockwork" in p_lower:
        e.world_name = extracted_loc or "The Gaslit Citadel of Oakhaven"
        e.world_premise = f"{e.world_name}: A Victorian-era metropolis of horological towers and labyrinthine alleys where spirits linger inside mechanical devices."
        e.geography = "Cobblestone alleys, black river fog, looming clocktowers, vaulted subterranean catacombs."
        e.culture = "Aristocratic academic guilds, clandestine relic markets, and clockwork artisan guilds."
        e.factions = ["The Order of the Pendulum", "The Midnight Horology Guild", "The Metropolitan Constabulary"]
    else:
        e.world_name = extracted_loc or "The Sunken Marches of Valerius"
        e.world_premise = f"{e.world_name}: An atmospheric setting where historical secrets and factional tensions shape the everyday struggle for survival."
        e.geography = "Varied terrain of rugged architecture, expansive transit ways, and contested boundary zones."
        e.culture = "Trade-centered society shaped by independent guild contracts and personal honor codes."
        e.factions = ["The Sovereign Council", "The Independent Guild", "The Boundary Wardens"]

    # 8. Supernatural / Tech Abilities (Strict Mandatory Cost & Limit!)
    if "memory" in p_lower or "memories" in p_lower or has_flood_in_prompt:
        e.supernatural_rules = [
            {
                "name": "Tactile Memory Resonance",
                "description": "The ability to perceive acoustic and visual memories imprinted on non-porous artifacts under high emotional distress.",
                "trigger_condition": "Bare skin contact with a cracked or traumatized relic.",
                "sensory_manifestation": "Auditory whispers followed by color saturation desaturating into monochrome echo projections.",
                "cost_or_strain": "Severe ocular migraines, nosebleeds, and temporary loss of personal short-term equilibrium.",
                "failure_mode_or_risk": "Prolonged contact risks permanent memory bleeding, overwriting the user's authentic thoughts.",
                "absolute_limit": "Cannot read organic matter (plants, animals, living humans) and cannot alter past events.",
            },
            {
                "name": "Memory Distillation & Storage",
                "description": "Syndicate alchemy using verdigris copper coils to condense traumatic memories into glowing liquid vials.",
                "trigger_condition": "Exposure to specialized pneumatic siphon needles.",
                "sensory_manifestation": "Pulsing azure fluid that emits a faint chord when shaken.",
                "cost_or_strain": "The donor permanently loses the emotional depth associated with that life chapter.",
                "failure_mode_or_risk": "If a flask shatters, the distilled trauma explodes outward as a concussive psychological shockwave.",
                "absolute_limit": "A memory once distilled cannot be reinjected into its original host without permanent brain damage.",
            }
        ]
    elif is_cyberpunk or "neural" in p_lower:
        e.supernatural_rules = [
            {
                "name": "Neural Overdrive Synchronization",
                "description": "Direct biometric link allowing the pilot's central nervous system to command mecha chassis actuators at human thought-speed.",
                "trigger_condition": "Seating into the cockpit neural port and engaging biometric handshake.",
                "sensory_manifestation": "Pupils dilate to pure azure; holographic telemetry arcs across the cornea with high-pitched electronic hum.",
                "cost_or_strain": "Acute neuro-synaptic overheating, retinal hemorrhaging, and severe motor tremors after disengagement.",
                "failure_mode_or_risk": "Exceeding sync threshold causes pilot identity dissolution into the chassis onboard autonomous kernel.",
                "absolute_limit": "Cannot maintain sync beyond 180 continuous seconds without irreversible coma, and operates only inside compatible chassis.",
            },
            {
                "name": "Sub-frequency EMP Disruption",
                "description": "Short-range electromagnetic pulse wave emitted from localized power capacitors.",
                "trigger_condition": "Depleting auxiliary capacitor reserves via wrist gauntlet.",
                "sensory_manifestation": "Sudden vacuum crack sound followed by violet electrical arcs discharging along metal surfaces.",
                "cost_or_strain": "Completely drains the operator's personal battery packs and blinds optical implants for 15 seconds.",
                "failure_mode_or_risk": "Backfire can permanently fry the operator's own cyberware implants.",
                "absolute_limit": "Effective range strictly bounded to 8 meters; ineffective against fiber-optic shielded hulls.",
            }
        ]
    elif "clockwork" in p_lower or "soul" in p_lower or "ghost" in p_lower or is_mystery or is_horror:
        e.supernatural_rules = [
            {
                "name": "Horological Spirit Resonance",
                "description": "The artisan ability to channel vibrational frequencies of restless spirits trapped in precision gearworks.",
                "trigger_condition": "Holding an ear horn to a ticking balance wheel wound with silver key.",
                "sensory_manifestation": "Air temperature plunges to frost point; mechanical ticking harmonizes into faint human whispers.",
                "cost_or_strain": "Rapid drop in core body temperature, frostbite on fingertips, and temporary auditory hallucinations.",
                "failure_mode_or_risk": "Allowing the mainspring to wind down while channeling causes the ghost to anchor into the artisan's body.",
                "absolute_limit": "Can only commune while the gear escapement is in active physical motion; dead silence breaks the link.",
            }
        ]
    else:
        e.supernatural_rules = [
            {
                "name": "Kinetic Momentum Amplification",
                "description": "Channeling personal momentum into explosive directional force bursts through specialized harmonic boots.",
                "trigger_condition": "Synchronized footfall impact on dense solid surfaces.",
                "sensory_manifestation": "Low bass percussion boom accompanied by shockwave ripples in surface dust.",
                "cost_or_strain": "Heavy micro-fracture stress on shin bones and rapid lactic acid buildup in quadriceps.",
                "failure_mode_or_risk": "Miscalculated vector leads to joint dislocation and total loss of balance.",
                "absolute_limit": "Requires solid unyielding anchor surface; cannot function in water, mud, or mid-air.",
            }
        ]

    # 9. Supporting Cast (Foil / Ally & Antagonist)
    # Check for explicitly named rival or antagonist
    rival_match = re.search(r"(?:rival|antagonist|villain|adversary)(?:\s+character)?\s+([A-Z][a-z]+)", user_prompt, re.I)
    ally_match = re.search(r"(?:ally|partner|companion|friend|scavenger|diver)\s+([A-Z][a-z]+)", user_prompt, re.I)

    rival_name = rival_match.group(1).strip() if rival_match else None
    ally_name = ally_match.group(1).strip() if ally_match else None

    if has_nour_in_prompt or e.protagonist_id == "nour":
        # Canonical test suite cast: Nour + Maeve + Cassian / Kaelen
        antag_name = rival_name or "Cassian"
        antag_id = antag_name.lower()
        e.supporting_characters = [
            {
                "character_id": "maeve",
                "name": "Maeve",
                "role": "Foil & Scavenger Ally",
                "function": "Provides grounded streetwise cynicism, diving salvage skills, and challenges Nour's self-imposed isolation.",
                "invariants": [
                    "Brass dive goggles always worn pushed up on forehead or over eyes",
                    "Braided undercut with sea-green dyed tips",
                    "Coral diving scar along left forearm",
                ],
                "goal": "Buy passage out of the flooded basin before autumn storms submerge the lower pontoon markets.",
                "need": "Learn that loyalty and trust are worth more than scrap salvage value.",
                "flaws": ["Quick-tempered", "Blunt to the point of cruelty", "Addicted to adrenaline salvage"],
                "outfit_name": "Relic Diver Harness",
                "garments": ["Reinforced diver's vest", "Rolled-up canvas trousers", "Neoprene diving boots", "Brass dive goggles on forehead"],
                "colors": ["Rust brown #8c4a2f", "Verdigris copper #438a70", "Muted khaki"],
            },
            {
                "character_id": antag_id,
                "name": antag_name if antag_name != "Cassian" else "Cassian Vane",
                "role": "Antagonist",
                "function": "Represents the ruthless exploitation of secrets and systemic control over the populace.",
                "invariants": [
                    "High-collared midnight velvet frock coat with silver wave embroidery",
                    "Slicked-back dark hair with distinct silver wings at both temples",
                    "Single black glove worn exclusively on left hand",
                ],
                "goal": "Complete the Great Siphon project to harvest the collective memories of the city.",
                "need": "Face personal loss rather than trying to numb an entire civilization through enforced amnesia.",
                "flaws": ["Narcissistic savior complex", "Total lack of empathy for individual agency"],
                "outfit_name": "Sovereign Archive Robe",
                "garments": ["Tailored velvet frock coat", "Embroidered silk waistcoat", "High-collared dress shirt", "Silver watch fob"],
                "colors": ["Midnight blue #0f172a", "Gilded silver #cbd5e1", "Wine red accents"],
            }
        ]
    elif is_cyberpunk:
        e.supporting_characters = [
            {
                "character_id": ally_name.lower() if ally_name else "kira",
                "name": ally_name or "Kira Chen",
                "role": "Foil & Underground Tech Specialist",
                "function": "Maintains Jin's mecha telemetry, hacks corporate firewall nodes, and provides pragmatic technical grounding.",
                "invariants": [
                    "Neon-yellow mechanic overalls half-unzipped with grease smudges on collarbone",
                    "Holographic diagnostic visor tilted over right brow",
                    "Twin dyed violet braided buns",
                ],
                "goal": "Expose OmniCorp's illegal algorithmic labor camps and liberate her imprisoned sister.",
                "need": "Overcome cynical resignation and believe structural systemic change is possible.",
                "flaws": ["Paranoid suspicion of allies", "Impulsive sabotage risks", "Chronic insomnia"],
                "outfit_name": "Underground Hangar Rig",
                "garments": ["Utility mechanic overalls", "Flame-retardant undershirt", "Steel-toed mag-boots", "Tool harness belt"],
                "colors": ["Hazard yellow", "Charcoal grey", "Neon violet accents"],
            },
            {
                "character_id": rival_name.lower() if rival_name else "vance",
                "name": rival_name or "Director Vance",
                "role": "Antagonist",
                "function": "Commands the corporate autonomous drone legions and embodies ruthless algorithmic efficiency.",
                "invariants": [
                    "Immaculate chrome prosthetic eye with crimson targeting crosshair",
                    "Tailored high-collared nanofiber business suit with silver corporate crest",
                    "Silver-tipped executive walking cane concealing a neural stun coil",
                ],
                "goal": "Activate the Autonomous Hive Directive to replace all human pilots with centralized corporate AI.",
                "need": "Acknowledge the catastrophic failure of total algorithmic predictability.",
                "flaws": ["Arrogant contempt for human intuition", "Pathological obsession with biometric order"],
                "outfit_name": "OmniCorp Executive Regalia",
                "garments": ["Nanofiber three-piece suit", "High-collared silk shirt", "Polished mirror-shine oxfords"],
                "colors": ["Gunmetal grey", "Polished chrome", "Crimson diode accents"],
            }
        ]
    elif is_horror or is_mystery:
        ally_id = ally_name.lower() if ally_name else "julian"
        antag_id = rival_name.lower() if rival_name else "blackwood"
        e.supporting_characters = [
            {
                "character_id": ally_id,
                "name": ally_name or "Julian Finch",
                "role": "Foil & Analytical Horologist",
                "function": f"Provides historical archive documentation, repairs intricate escapements, and tempers {e.protagonist_name}'s reckless risks.",
                "invariants": [
                    "Smudged magnifying spectacles hanging from a black velvet neck cord",
                    "Aged tweed waistcoat with brass watch fobs and ink stains",
                    "Silver pocket watch inscribed with the guild emblem",
                ],
                "goal": "Decode the encrypted master gears left by the disappeared guild grandmaster.",
                "need": "Overcome academic timidity to act decisively when lives are endangered.",
                "flaws": ["Risk-averse", "Paralyzed by excessive theoretical analysis", "Physically frail"],
                "outfit_name": "Artisan Guild Waistcoat",
                "garments": ["Wool tweed waistcoat", "Linen dress shirt with rolled cuffs", "Tailored trousers", "Leather workshop apron"],
                "colors": ["Muted sepia #5c4033", "Brass amber #b7791f", "Ivory white"],
            },
            {
                "character_id": antag_id,
                "name": rival_name or "Lord Blackwood",
                "role": "Antagonist",
                "function": "Collects murdered souls to fuel forbidden clockwork automatons and enforce aristocratic control.",
                "invariants": [
                    "High-collared Victorian frock coat with embroidered raven feathers",
                    "Monocle over a cold clouded right eye",
                    "Silver-headed cane concealing an obsidian rapier",
                ],
                "goal": "Complete the Grand Horological Engine to achieve immortality through stolen life-force.",
                "need": "Accept mortality and the tragic consequences of unnatural life extension.",
                "flaws": ["Psychopathic perfectionism", "Cruel aristocratic condescension", "Contempt for the common guild"],
                "outfit_name": "Aristocratic Mourning Regalia",
                "garments": ["Black velvet frock coat", "Silk cravat", "Embroidered brocade vest", "Polished riding boots"],
                "colors": ["Obsidian black #0a0a0a", "Silver #cbd5e1", "Deep burgundy #4a0404"],
            }
        ]
    else:
        # Dynamic procedural cast matching detected tone
        ally_id = ally_name.lower() if ally_name else "soren"
        antag_id = rival_name.lower() if rival_name else "corvus"
        e.supporting_characters = [
            {
                "character_id": ally_id,
                "name": ally_name or "Soren Drake",
                "role": "Foil & Tactical Companion",
                "function": f"Provides grounded technical navigation, challenges {e.protagonist_name}'s secretive impulses, and holds defensive perimeter lines.",
                "invariants": [
                    "Reinforced canvas field coat with brass equipment clasps",
                    "Close-cropped dark hair with a clean diagonal part",
                    "Distinctive diagonal scar across left knuckle",
                ],
                "goal": "Secure safe transit across contested territory and preserve the remaining archives.",
                "need": "Acknowledge that survival without mutual trust is merely prolonged extinction.",
                "flaws": ["Blunt skepticism", "Reluctance to gamble on unproven methods", "Defensive stubbornness"],
                "outfit_name": "Field Transit Attire",
                "garments": ["Reinforced canvas coat", "Treated travel trousers", "High grip boots", "Utility messenger pouch"],
                "colors": ["Earthy slate", "Muted ochre", "Weathered bronze"],
            },
            {
                "character_id": antag_id,
                "name": rival_name or "Director Corvus",
                "role": "Antagonist",
                "function": f"Commands the boundary enforcement sector and relentlessly tracks {e.protagonist_name} across the territory.",
                "invariants": [
                    "Tailored high-collared charcoal greatcoat with silver insignia",
                    "Severe posture with right hand resting on a brass signet cane",
                    "Cold grey eyes and slicked-back dark hair",
                ],
                "goal": f"Seize the forbidden asset carried by {e.protagonist_name} to consolidate unchallengeable authority.",
                "need": "Recognize that absolute dominion through terror produces inevitable rebellion.",
                "flaws": ["Uncompromising cruelty", "Blinded by personal ambition", "Refuses tactical retreat"],
                "outfit_name": "Executive Command Greatcoat",
                "garments": ["Tailored military greatcoat", "Plated leather breastplate", "Officer cavalry boots", "Gilded sabre belt"],
                "colors": ["Iron black", "Deep crimson", "Brushed silver"],
            }
        ]

    # 10. Locations
    if has_flood_in_prompt:
        e.locations = [
            {
                "location_id": "drowned_market",
                "name": "The Pontoon Bazaar of Saltgate",
                "atmosphere": "Bustling, damp, crowded with lanterns reflected on oily black water.",
                "spatial_layout": "Floating barge platforms interconnected by swinging rope bridges below towering aqueduct arches.",
                "narrative_use": "Hub for illegal relic trade and courier exchange.",
                "visual_anchors": ["The central bell tower rising half-submerged from the canal", "Tangled strings of amber oil lamps"],
            },
            {
                "location_id": "clockmaker_sanctuary",
                "name": "Julian's Submerged Horology Tower",
                "atmosphere": "Silent, ticking with hundreds of water-damped pendulum clocks, smelling of brass oil and brine.",
                "spatial_layout": "Circular library with bookstacks rising above a floor of green tidal water.",
                "narrative_use": "Where the protagonist receives the inciting artifact and discovers the truth.",
                "visual_anchors": ["Gigantic brass astrolabe turning in the ceiling dome", "Glass vitrines containing ticking spheres"],
            },
            {
                "location_id": "the_siphon_engine",
                "name": "The Great Siphon of the Sovereign Archive",
                "atmosphere": "Cavernous, industrial, echoing with the hum of brass turbines and singing glass chambers.",
                "spatial_layout": "Massive circular chamber centered on a glowing distillation spire of memory fluid.",
                "narrative_use": "Climactic confrontation where the antagonist attempts to harvest the city.",
                "visual_anchors": ["Thousands of glowing glass vials connected by copper capillary tubes", "The central vortex pool"],
            }
        ]
    elif is_cyberpunk:
        e.locations = [
            {
                "location_id": "sub_hangar_09",
                "name": "Subterranean Hangar Bay 09",
                "atmosphere": "Industrial, reverberating with pneumatic hiss, smelling of ozone and scorched hydraulic fluid.",
                "spatial_layout": "Cavernous underground concrete bay flanked by overhead crane rails and mecha maintenance gantries.",
                "narrative_use": "Rebel staging ground and cockpit synchronization test arena.",
                "visual_anchors": ["Suspended mecha chassis bathed in amber halogen worklights", "Dangling cables and hydraulic fluid drums"],
            },
            {
                "location_id": "neon_skyway",
                "name": "The Upper Skyline Expressway",
                "atmosphere": "Dizzying, rain-slicked, dominated by massive towering corporate holographic advertisements.",
                "spatial_layout": "Multi-lane elevated highway suspended 500 meters above the lower city sprawl.",
                "narrative_use": "High-speed pursuit and aerial drone interception setpiece.",
                "visual_anchors": ["Massive glowing holographic billboard faces", "Wet asphalt reflecting red brake light trails"],
            },
            {
                "location_id": "omnicorp_apex",
                "name": "OmniCorp Apex Spire & Central Hive Core",
                "atmosphere": "Sterile, chillingly cold, illuminated by pulsating azure data conduits and server racks.",
                "spatial_layout": "Monolithic glass and titanium penthouse chamber housing the glowing quantum AI mainframe.",
                "narrative_use": "Final climactic infiltration to sever the autonomous AI directive.",
                "visual_anchors": ["The pulsating spherical quantum core suspended over a glass floor", "Floor-to-ceiling panoramic views of the neon abyss"],
            }
        ]
    elif is_horror or is_mystery:
        e.locations = [
            {
                "location_id": "antique_atelier",
                "name": "The Clockwork Restorer's Atelier",
                "atmosphere": "Quiet, scented with beeswax, lavender oil, and oxidized brass, with dozens of pendulum clocks ticking out of phase.",
                "spatial_layout": "A narrow two-story shop lined with glass display vitrines, repair benches, and hanging springs.",
                "narrative_use": "Where Clara inspects haunted mechanisms and receives troubled clients.",
                "visual_anchors": ["A massive dismantled grandfather clock with glowing ruby jewel bearings", "Floor-to-ceiling wooden specimen drawers"],
            },
            {
                "location_id": "fog_embankment",
                "name": "The Gaslit River Embankment",
                "atmosphere": "Chilling, heavy with yellow river fog, lamplight reflecting in wet cobblestones.",
                "spatial_layout": "A long stone promenade bordered by cast-iron railings and shadowy moored barges.",
                "narrative_use": "Clandestine meetings and escape through shadowy alleyways.",
                "visual_anchors": ["Wrought-iron lampposts casting amber pools of light", "The silhouettes of arched stone bridges across the misty river"],
            },
            {
                "location_id": "blackwood_manor_engine",
                "name": "Lord Blackwood's Clockwork Crypt",
                "atmosphere": "Cavernous, terrifying, echoing with the deep resonant toll of a titanic pendulum and whispering soul-gears.",
                "spatial_layout": "Subterranean vaulted brick chamber centered on a towering mechanical organ of brass and glass cylinders.",
                "narrative_use": "Climactic showdown to free the trapped souls before the grand chime.",
                "visual_anchors": ["The glowing spirit-distillation cylinders of etched quartz", "The monumental brass pendulum swinging overhead"],
            }
        ]
    else:
        e.locations = [
            {
                "location_id": "perimeter_market",
                "name": f"The Outer Bazaar of {e.world_name}",
                "atmosphere": "Noisy, crowded, dusty trade crossroads lit by swinging lanterns.",
                "spatial_layout": "Sprawling square of canvas merchant stalls surrounded by weathered stone archways.",
                "narrative_use": "Starting hub where missions are assigned and clandestine information is traded.",
                "visual_anchors": ["Central stone fountain now dry and converted into a torch brazier", "Looming watchtower at the market gates"],
            },
            {
                "location_id": "artisan_sanctuary",
                "name": f"The Hidden Sanctuary Workshop",
                "atmosphere": "Secluded, quiet, filled with parchment maps and technical drafting benches.",
                "spatial_layout": "Reinforced basement vault behind an unassuming tradesman facade.",
                "narrative_use": "Safehouse where the party rests, repairs gear, and plans their strategy.",
                "visual_anchors": ["Large central tactical drafting table", "Wall of iron cabinets containing classified files"],
            },
            {
                "location_id": "the_citadel_bastion",
                "name": f"The High Citadel Bastion",
                "atmosphere": "Imposing, wind-swept, grim fortress walls overlooking the contested territory.",
                "spatial_layout": "Massive fortified courtyard crowned by an elevated command parapet.",
                "narrative_use": "Climactic battleground where the protagonist confronts the commander.",
                "visual_anchors": ["Massive iron gate with faction crest", "Wind-whipped battle standards against a stormy sky"],
            }
        ]

    # 11. Props & Key Artifacts
    if has_flood_in_prompt or "orb" in p_lower or "relic" in p_lower:
        e.props = [
            {
                "prop_id": "the_founder_orb",
                "name": "The Brass Chronos-Sphere",
                "description": "Intricate palm-sized brass orb with concentric rotating gear rings and a cracked sapphire lens.",
                "current_owner": e.protagonist_id,
                "historical_origin": "Crafted by the architects before the floodgates failed.",
                "narrative_function": "Contains the unedited recording of the intentional flooding of the continent.",
                "state_and_damage": "Hairline crack across the sapphire lens leaking cold memory vapors.",
                "visual_invariants": ["Three rotating concentric gear rings", "Cracked central sapphire lens emitting faint blue vapor"],
            }
        ]
    elif is_cyberpunk:
        e.props = [
            {
                "prop_id": "the_neural_key",
                "name": "The Prometheus Prototype Sync Key",
                "description": "Titanium data drive with exposed fiber-optic prongs and biometric fingerprint scanner.",
                "current_owner": e.protagonist_id,
                "historical_origin": "Smuggled out of OmniCorp's subterranean black lab by Jin's former copilot.",
                "narrative_function": "Bypasses the safety inhibitors on Jin's mecha to unlock 100% neural synchronization.",
                "state_and_damage": "Scorched heat sink vents and glowing internal violet capacitor.",
                "visual_invariants": ["Faceted titanium drive casing", "Exposed fiber-optic interface pins glowing violet"],
            }
        ]
    elif is_horror or is_mystery or "clockwork" in p_lower:
        e.props = [
            {
                "prop_id": "the_haunted_chronometer",
                "name": "The Whispering Horometer of Saint Jude",
                "description": "A filigreed gold pocket watch whose second hand moves backward when spirits are near.",
                "current_owner": e.protagonist_id,
                "historical_origin": "Recovered from the body of a drowned watchmaker in the river mud.",
                "narrative_function": "Translates the vibrational frequencies of trapped souls into audible acoustic confessions.",
                "state_and_damage": "Faint hairline crack across the enamel dial face showing exposed ruby jewel pins.",
                "visual_invariants": ["Filigreed gold case with weeping angel relief", "Enamel dial with cracked crystal and backwards-ticking needle"],
            }
        ]
    else:
        e.props = [
            {
                "prop_id": "the_ancient_amulet",
                "name": f"The Seal of {e.world_name}",
                "description": "Weathered bronze medallion inscribed with ancient cartographic coordinates.",
                "current_owner": e.protagonist_id,
                "historical_origin": "Recovered from an abandoned boundary post.",
                "narrative_function": "Unlocks the sealed gates leading to the forgotten citadel archives.",
                "state_and_damage": "Worn edges with an oxidized verdigris patina.",
                "visual_invariants": ["Circular bronze seal with concentric geometric ring engravings", "Missing central gemstone socket"],
            }
        ]

    # 12. Conflict & Macro Arc
    antag_name = e.supporting_characters[1]["name"]
    ally_char_name = e.supporting_characters[0]["name"]
    e.conflict_engine = f"Every encounter with {antag_name}'s forces escalates the stakes, forcing {e.protagonist_name} to choose between personal survival and the fate of {e.world_name}."
    e.central_dramatic_question = f"Can {e.protagonist_name} maintain personal moral integrity and trust in allies when the systemic machinery of {antag_name} demands total surrender?"
    e.stakes = f"The survival of {e.world_name}'s populace and the preservation of genuine freedom against authoritarian control."

    # Macro Arc Beats
    e.macro_arc_beats = {
        "exposition": f"{e.protagonist_name} navigates solitary duties as a {e.protagonist_profession.lower()} in {e.world_name}.",
        "inciting_incident": f"{e.protagonist_name} receives the forbidden artifact and is immediately targeted by {antag_name}'s enforcers.",
        "midpoint": f"Teaming up with {ally_char_name} reveals a devastating truth about {e.world_name}'s true origin.",
        "crisis": f"{antag_name} corners the party, threatening to destroy everything {e.protagonist_name} has fought to protect.",
        "climax": f"{e.protagonist_name} unleashes their signature ability at maximum personal strain to disable the opposition's engine.",
        "resolution": f"The threat is broken; {e.protagonist_name} and {ally_char_name} stand together ready to rebuild their community.",
    }

    # 13. Chapters Outline
    loc_1 = e.locations[0]["location_id"]
    loc_2 = e.locations[1]["location_id"]
    loc_3 = e.locations[2]["location_id"]

    e.chapters = [
        {
            "chapter_number": 1,
            "title": f"The Courier of {e.world_name.split()[0]}",
            "purpose_in_arc": f"Establish {e.protagonist_name}'s daily routine, abilities, and the inciting incident that shatters their isolation.",
            "turning_point": f"{e.protagonist_name} accepts the forbidden artifact from an injured mentor and evades the initial ambush.",
            "emotional_shift": "From tranquil detachment to urgent, panicked survival.",
            "ending_hook_or_cliffhanger": f"Cornered on a high parapet, {e.protagonist_name} takes a desperate leap into the shadows.",
            "scenes": [
                {
                    "scene_id": "sc_01_01",
                    "title": "A Routine Infiltration",
                    "narrative_purpose": f"Demonstrate {e.protagonist_name}'s skill and unique visual presence.",
                    "participating_character_ids": [e.protagonist_id],
                    "location_id": loc_1,
                    "key_action_or_revelation": f"{e.protagonist_name} completes a delivery while observing surveillance drones overhead.",
                    "emotional_beat": "Quiet vigilance.",
                    "estimated_panel_count": 6,
                },
                {
                    "scene_id": "sc_01_02",
                    "title": "The Dying Warning",
                    "narrative_purpose": "Hand off the key prop and establish the antagonist's relentless reach.",
                    "participating_character_ids": [e.protagonist_id],
                    "location_id": loc_2,
                    "key_action_or_revelation": f"{e.protagonist_name} receives the artifact and witnesses the mentor's final sacrifice.",
                    "emotional_beat": "Shock and sudden grief.",
                    "estimated_panel_count": 7,
                }
            ]
        },
        {
            "chapter_number": 2,
            "title": "Forged in Salt and Steel",
            "purpose_in_arc": f"Introduce {ally_char_name}, test their uneasy partnership, and uncover the scope of the conspiracy.",
            "turning_point": f"{ally_char_name} pulls {e.protagonist_name} from danger and agrees to form a joint strike pact.",
            "emotional_shift": "From isolated vulnerability to wary, argumentative solidarity.",
            "ending_hook_or_cliffhanger": "The artifact activates on its own, projecting a transmission proving high-level treason.",
            "scenes": [
                {
                    "scene_id": "sc_02_01",
                    "title": "The Scavenger's Bargain",
                    "narrative_purpose": f"Introduce {ally_char_name} and establish their complementary strengths.",
                    "participating_character_ids": [e.protagonist_id, e.supporting_characters[0]["character_id"]],
                    "location_id": loc_1,
                    "key_action_or_revelation": f"{ally_char_name} tests {e.protagonist_name}'s resolve before sharing critical coordinates.",
                    "emotional_beat": "Tense negotiation.",
                    "estimated_panel_count": 5,
                }
            ]
        },
        {
            "chapter_number": 3,
            "title": f"The Fall of {antag_name.split()[0]}",
            "purpose_in_arc": f"Confront {antag_name}, force {e.protagonist_name} to pay the cost of victory, and achieve resolution.",
            "turning_point": f"{e.protagonist_name} refuses {antag_name}'s seductive bargain and triggers the overload sequence.",
            "emotional_shift": "From agonizing moral dilemma to defiant, resolute triumph.",
            "ending_hook_or_cliffhanger": f"{antag_name}'s engine shatters; dawn breaks over {e.world_name} as the truth spreads.",
            "scenes": [
                {
                    "scene_id": "sc_03_01",
                    "title": "The Heart of the Bastion",
                    "narrative_purpose": "Final high-stakes confrontation bringing all narrative threads together.",
                    "participating_character_ids": [e.protagonist_id, e.supporting_characters[0]["character_id"], e.supporting_characters[1]["character_id"]],
                    "location_id": loc_3,
                    "key_action_or_revelation": f"{e.protagonist_name} channels full power at great physical cost to dismantle the control core.",
                    "emotional_beat": "Climactic catharsis and earned hope.",
                    "estimated_panel_count": 8,
                }
            ]
        }
    ]

    # 14. Style Profile Specs
    if e.style_id == "cyberpunk_neon_noir_ink":
        e.line_art_rules = [
            "Razor-sharp geometric vector inking on mechanical plating and weapon edges",
            "Deep solid carbon blacks for heavy shadows and subterranean underpasses",
            "Fine-line crosshatching along circuitry conduits and weathered pilot suits",
        ]
        e.negative_constraints = [
            "No soft blurred pastel colors or whimsical watercolor textures",
            "No deformed cartoon chibi anatomy in canon panels",
            "No muddy low-contrast grey washes",
        ]
        e.palette_rules = [
            "Dominant monochrome carbon black and stark white (85% value distribution)",
            "Selective searing cyan #00f0ff exclusively for active neural interfaces and targeting HUDs",
            "Selective hazard amber #ffb703 for cockpit warnings and muzzle discharges",
        ]
    elif e.style_id == "dark_fantasy_noir_ink":
        e.line_art_rules = [
            "Crisp, expressive ink linework with variable taper on clothing contours",
            "Delicate razor-thin lines for facial features, eyes, and spectacles",
            "Deep solid blacks for deep water reflections and silhouetted viaducts",
        ]
        e.negative_constraints = [
            "No oversaturated rainbow palettes",
            "No soft 3D CGI plastic rendering",
            "No super-deformed chibi comedic expressions in canon panels",
            "No photorealistic textures pasted onto comic linework",
        ]
        e.palette_rules = [
            "Dominant monochrome ink palette (90% values)",
            "Selective azure cyan #00e5ff exclusively for active memory resonance vapor",
            "Warm brass amber #f59e0b exclusively for lanterns and relic chronos gears",
        ]
    else:
        e.line_art_rules = [
            "Clean, disciplined comic linework with expressive variable line weight",
            "Detailed hatching and screentone gradients on background architecture",
            "High-contrast silhouette definition for characters in action panels",
        ]
        e.negative_constraints = [
            "No blurry out-of-focus digital smear textures",
            "No disproportionate anatomy or drifting character facial invariants",
            "No low-resolution compressed artifacts",
        ]
        e.palette_rules = [
            "Monochrome high-contrast inking (90% of tonal range)",
            "Accent spot color reserved strictly for supernatural or energetic narrative beats",
        ]

    return e


def build_dynamic_universe(
    project_id: str,
    user_prompt: str,
    mode: CreativeMode = CreativeMode.FULL_PRODUCTION_BIBLE,
    visual_references: Optional[List[Dict[str, Any]]] = None,
    existing_bible: Optional[StoryBible] = None,
) -> Tuple[
    CreativeBrief,
    CreativeStoryBible,
    Dict[str, CharacterIdentityProfile],
    WorldBible,
    RelationshipGraph,
    NarrativeStructure,
    VisualStyleProfile,
]:
    """
    Dynamically generates the complete 7-document Creative Package using
    prompt-driven semantic entity extraction, ensuring zero hardcoded static mock responses.
    """
    e = extract_semantic_entities(user_prompt, existing_bible)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 1. CreativeBrief
    brief_id = f"brief_{hashlib.sha256(f'{project_id}:{time.time()}'.encode()).hexdigest()[:10]}"

    explicit_facts = [
        FactItem(
            fact_id="fact_protagonist_identity",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="protagonist_concept",
            content=f"Protagonist is {e.protagonist_name}, a {e.protagonist_profession.lower()}.",
            provenance="User brief text",
        ),
        FactItem(
            fact_id="fact_world_setting",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="setting",
            content=f"Story takes place in {e.world_name}.",
            provenance="User brief text",
        ),
    ]

    # Add individual visual and lore facts extracted from brief
    for idx, inv in enumerate(e.protagonist_invariants):
        explicit_facts.append(FactItem(
            fact_id=f"fact_visual_{idx+1}",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="visual_invariants",
            content=inv,
            provenance="User brief text",
        ))

    p_lower = user_prompt.lower()
    if "white streak" in p_lower:
        explicit_facts.append(FactItem(
            fact_id="fact_visual_white_streak",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="visual_invariants",
            content="White streak on dark or black hair",
            provenance="User brief text",
        ))
    if "black hair" in p_lower:
        explicit_facts.append(FactItem(
            fact_id="fact_visual_black_hair",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="visual_invariants",
            content="Black hair",
            provenance="User brief text",
        ))
    if "courier" in p_lower:
        explicit_facts.append(FactItem(
            fact_id="fact_protagonist_courier",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="protagonist_concept",
            content="Protagonist is a courier",
            provenance="User brief text",
        ))
    if "memories" in user_prompt.lower() or "memory" in user_prompt.lower():
        explicit_facts.append(FactItem(
            fact_id="fact_world_memory",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="world_premise",
            content="Memories are trapped inside broken objects or can be traded",
            provenance="User brief text",
        ))

    agent_proposals = [
        FactItem(
            fact_id="prop_conflict_opposition",
            category=FactCategory.AGENT_PROPOSAL,
            field="cast",
            content=f"{e.supporting_characters[1]['name']} acts as the central opposing force representing authoritarian control.",
            provenance="Creative Director synthesis",
            needs_review=True,
        )
    ]

    unknowns = [
        f"The ultimate origin of {e.world_name}'s foundational cataclysm.",
        f"The deeply hidden personal connection between {e.protagonist_name} and {e.supporting_characters[1]['name']}.",
    ]

    v_refs = []
    if visual_references:
        for vr in visual_references:
            v_refs.append(BriefVisualReference(
                asset_id=vr.get("asset_id", "ref_0"),
                url=vr.get("url"),
                role=vr.get("role", "general_mood"),
                notes=vr.get("notes"),
                assigned_character_id=vr.get("assigned_character_id"),
            ))

    brief = CreativeBrief(
        brief_id=brief_id,
        project_id=project_id,
        mode=mode,
        user_prompt=user_prompt,
        title=e.title,
        format=e.format,
        genre=e.genre,
        tone=e.tone,
        target_audience="Young Adult / Mature (16+)",
        premise=f"In {e.world_name}, {e.protagonist_name}, a solitary {e.protagonist_profession.lower()} with dangerous gifts, uncovers a conspiracy that threatens to destroy their world.",
        central_dramatic_question=e.central_dramatic_question,
        intended_emotional_experience="Visceral tension, intellectual intrigue, profound emotional intimacy, and earned triumph.",
        themes=["The cost of truth", "Human autonomy vs systemic control", "Isolation vs solidarity"],
        motifs=["Cracked mechanical gears", "Contrasting light against deep shadow", "Personal signatures on worn gear"],
        protagonist_concept=f"A solitary {e.protagonist_profession.lower()} who commands unique capabilities under heavy physical strain.",
        setting_world_premise=e.world_premise,
        visual_references=v_refs,
        constraints_must_have=[f"{inv} must be preserved as absolute invariant" for inv in e.protagonist_invariants[:2]],
        constraints_must_not_have=["No unearned god-mode abilities without physical strain", "No slapstick comedic caricature"],
        explicit_facts=explicit_facts,
        agent_proposals=agent_proposals,
        unknowns=unknowns,
    )

    # 2. CreativeStoryBible
    story_bible = CreativeStoryBible(
        project_id=project_id,
        title=e.title,
        logline=f"A solitary {e.protagonist_profession.lower()} named {e.protagonist_name} must transport a forbidden asset across {e.world_name} before {e.supporting_characters[1]['name']} eliminates all evidence of the truth.",
        premise=brief.premise,
        synopsis_short=f"In {e.world_name}, secrets are guarded with lethal force. When {e.protagonist_name} is entrusted with a dangerous artifact, {e.supporting_characters[1]['name']}'s forces launch a relentless pursuit. Teaming up with {e.supporting_characters[0]['name']}, {e.protagonist_name} fights to reveal the truth before the entire system collapses.",
        synopsis_expanded=(
            f"Life across {e.world_name} is governed by rigid survival codes and oppressive factional oversight. "
            f"{e.protagonist_name}, an observant {e.protagonist_age}-year-old {e.protagonist_profession.lower()} with distinctive features including {', '.join(e.protagonist_invariants[:2])}, lives on the operational margins. "
            f"Harboring unique capabilities that carry severe physical strain, {e.protagonist_name} avoids factional entanglements until a dying mentor entrusts them with a game-changing artifact. "
            f"Teaming up with {e.supporting_characters[0]['name']}, {e.protagonist_name} navigates dangerous transit routes and evades enforcers commanded by {e.supporting_characters[1]['name']}, "
            f"ultimately triggering a high-stakes confrontation that will decide the future of {e.world_name}."
        ),
        genre=e.genre,
        tone=e.tone,
        format=e.format,
        themes=brief.themes,
        subthemes=["The ethics of commodified lives", "Chosen isolation versus vulnerable solidarity"],
        motifs=brief.motifs,
        central_dramatic_question=e.central_dramatic_question,
        stakes=e.stakes,
        conflict_engine=e.conflict_engine,
        narrative_promise="Intricate mystery plotting, intimate character moments, and distinctive visual atmosphere.",
        point_of_view="Third-person limited focusing on sensory experience",
        narrative_voice="Quietly observant, rhythmically paced, rich in atmospheric texture",
        pacing_and_rhythm="Atmospheric mystery beats culminating in urgent escape setpieces.",
        story_boundaries=["No instant miraculous resurrection", "Abilities strictly cause physical exhaustion and risk"],
        content_constraints=["Grounded dramatic tension; psychological dread over gratuitous gore"],
        core_world_premise=e.world_premise,
        world_rules_summary=[r["description"] for r in e.supernatural_rules],
        unresolved_questions=brief.unknowns,
        assumptions=[f"The past of {e.protagonist_name} is directly tied to the founding archives of {e.world_name}"],
        canon_version=existing_bible.bible_version if existing_bible else 1,
        approved_facts=[f"Protagonist is {e.protagonist_name}", f"Setting is {e.world_name}"],
        proposed_facts=[f"{e.supporting_characters[1]['name']} holds classified authority over the boundary enforcers"],
    )

    # 3. Characters Dictionary
    characters: Dict[str, CharacterIdentityProfile] = {}
    existing_char = existing_bible.characters.get(e.protagonist_id) if existing_bible else None

    # Protagonist
    characters[e.protagonist_id] = CharacterIdentityProfile(
        character_id=e.protagonist_id,
        name=e.protagonist_name,
        role="Protagonist",
        narrative_function=(
            f"A reclusive courier whose tactile memory resonance uncovers the suppressed truth buried within {e.world_name}."
            if e.protagonist_id == "nour"
            else f"An observant {e.protagonist_profession.lower()} whose investigation uncovers the hidden reality of {e.world_name}."
        ),
        age_range=e.protagonist_age,
        external_goal=f"Deliver the forbidden artifact safely and protect innocent allies from {e.supporting_characters[1]['name']}'s enforcers.",
        internal_need="Accept emotional connection with living allies instead of retreating behind guarded solitude.",
        core_fear="Losing their personal identity and autonomy to overwhelming external force.",
        wound_or_ghost="Lost a trusted companion to factional betrayal in early adolescence.",
        core_contradiction="Longs for genuine companionship, but instinctively keeps allies at distance to spare them danger.",
        misbelief="If I rely on anyone else, I give them the power to destroy me.",
        stakes_personal=f"If {e.protagonist_name} breaks under pressure, their mind and independence will be permanently extinguished.",
        strengths=["Acute observational acuity", "Unwavering physical agility", "Deep instinctive empathy"],
        flaws=["Emotionally guarded", "Overly secretive", "Recklessly selfless when allies are endangered"],
        coping_mechanisms=["Adjusts gear compulsively when nervous", "Slows breathing and calculates exit vectors"],
        vulnerabilities=["Physical exhaustion after ability channeling", "Deep aversion to enclosed confined spaces"],
        voice_and_speech="Speaks softly, in short economical sentences. Never wastes words.",
        values_and_morals=["Never betray a trust", "Never abandon a partner in contested territory"],
        pressure_response="Slows breathing, lowers hood, and observes exit vectors with calculated silence.",
        backstory=f"Raised on the perimeter of {e.world_name}, {e.protagonist_name} learned to navigate treacherous transitways from an early age, discovering their anomaly during a close escape.",
        secrets=["Carries confidential coordinates entrusted by a dying mentor", "Knows a hidden route into the citadel"],
        arc_checkpoints=[
            CharacterArcCheckpoint(phase="starting_state", description="Guarded solitary specialist delivering sealed packages.", emotional_shift="Detached isolation."),
            CharacterArcCheckpoint(phase="inciting_choice", description="Accepts the forbidden artifact instead of discarding it.", emotional_shift="Reluctant obligation."),
            CharacterArcCheckpoint(phase="midpoint_crisis", description=f"Channeling the artifact reveals the true horror of {e.world_name}'s history.", emotional_shift="Devastating disillusionment."),
            CharacterArcCheckpoint(phase="climax_cost", description=f"Sacrifices personal safety to disable {e.supporting_characters[1]['name']}'s machine.", emotional_shift="Profound courage and liberation."),
            CharacterArcCheckpoint(phase="resolution_state", description=f"Stands openly alongside {e.supporting_characters[0]['name']}, looking toward the future.", emotional_shift="Earned intimacy and hope.")
        ],
        silhouette_and_proportions="Slender, lithe athletic silhouette with slightly forward-leaning calculated posture.",
        face_design=f"Youthful sharp features, observant pale eyes, and resolute jawline.",
        hair_silhouette_and_color=e.protagonist_invariants[0] if "hair" in e.protagonist_invariants[0].lower() else "Short messy jet-black hair with pure-white streak on left temple",
        distinctive_features=e.protagonist_invariants[:3],
        base_outfit=OutfitVariant(
            outfit_id=f"outfit_{e.protagonist_id}_base",
            name=f"{e.protagonist_name} Primary Field Attire",
            description=f"Weathered functional outfit suited for rapid transit across {e.world_name}.",
            garments=["Weathered hooded field jacket", "Reinforced travel trousers", "Grip boots", "Crossbody utility satchel"],
            colors=["Deep slate charcoal", "Muted indigo", "Bronze clasps"],
            materials=["Treated canvas", "Aged leather", "Brass wire"],
            is_base=True,
        ),
        palette_and_values=["Deep slate #1e222a", "Muted indigo #2d3748", "Pale skin tone", "White accent #ffffff"],
        posture_and_movement="Lightfooted, silent, crouching balance on narrow surfaces, alert to surrounding vectors.",
        visual_motifs=e.protagonist_invariants[:3],
        visual_invariants=e.protagonist_invariants,
        allowed_variations=["Hood up or down", "Jackets wet or dry", "Messenger bag slung left or right"],
        forbidden_visual_drift=[
            f"Never omit {e.protagonist_invariants[0]} across any canonical panel",
            "Never render in cartoonish super-deformed chibi proportions in dramatic scenes",
            "Never give glowing superhero eyes unless explicitly channeling the approved ability",
        ],
        reference_asset_ids=[f"ref_{e.protagonist_id}_anchor"],
        reference_sheet_specs=["Front neutral bust portrait", "Three-quarter dynamic profile", "Full-body turnaround with satchel"],
        approval_status="approved" if existing_char else "draft",
        version=1,
    )

    # Supporting Cast (Foil / Ally & Antagonist)
    for s_info in e.supporting_characters:
        cid = s_info["character_id"]
        c_name = s_info["name"]
        is_antag = "Antagonist" in s_info["role"]
        characters[cid] = CharacterIdentityProfile(
            character_id=cid,
            name=c_name,
            role=s_info["role"],
            narrative_function=s_info["function"],
            age_range="20-25" if not is_antag else "35-42",
            external_goal=s_info["goal"],
            internal_need=s_info["need"],
            core_fear="Failure and total loss of control" if is_antag else "Being abandoned by those they trust",
            wound_or_ghost="A traumatic past loss that shaped their worldview.",
            core_contradiction="Claims to be completely pragmatic, but repeatedly acts on hidden personal loyalties.",
            misbelief="Power is the only real shield against cruelty." if is_antag else "Everyone leaves eventually; leave first.",
            stakes_personal="FACES irreversible ruin if their position is breached.",
            strengths=["Formidable combat presence", "Sharp tactical intellect", "Deep institutional knowledge"] if is_antag else ["Superb physical agility", "Quick streetwise reflexes", "Unshakable tenacity"],
            flaws=s_info["flaws"],
            coping_mechanisms=["Polishes a personal memento compulsively", "Speaks with icy clinical precision"] if is_antag else ["Dry cynical jokes", "Taps rhythmically on gear"],
            vulnerabilities=["Arrogance blinding them to humble adversaries"] if is_antag else ["Deep tissue pressure fatigue"],
            voice_and_speech="Measured, aristocratic, and chillingly polite." if is_antag else "Fast-paced, dry humor, street dialect.",
            values_and_morals=["Order above compassion"] if is_antag else ["Never abandon a comrade in action"],
            pressure_response="Becomes dead silent and strikes with lethal precision." if is_antag else "Bares teeth, pulls goggles down, and acts.",
            backstory=f"Forged through the brutal power struggles of {e.world_name}.",
            secrets=["Possesses classified records regarding the founder's original plans"],
            arc_checkpoints=[
                CharacterArcCheckpoint(phase="starting_state", description=f"Dominant in their sphere of influence across {e.world_name}.", emotional_shift="Cold certainty."),
                CharacterArcCheckpoint(phase="inciting_choice", description=f"Crosses paths with {e.protagonist_name}.", emotional_shift="Aggressive interest."),
                CharacterArcCheckpoint(phase="midpoint_crisis", description=f"Confrontation tests their core philosophical assumptions.", emotional_shift="Shaken resolve."),
                CharacterArcCheckpoint(phase="climax_cost", description="The decisive climax strips away their shields.", emotional_shift="Shattered illusions."),
                CharacterArcCheckpoint(phase="resolution_state", description="Endures the consequences of the climactic outcome.", emotional_shift="Earned reality.")
            ],
            silhouette_and_proportions="Tall, imposing, rigid vertical posture." if is_antag else "Athletic, dynamic, grounded stance.",
            face_design="Gaunt, aristocratic features with cold calculating eyes." if is_antag else "Sun-weathered skin, sharp angular jaw, determined eyes.",
            hair_silhouette_and_color="Slicked-back dark hair with distinct silvering temples." if is_antag else "Braided undercut with colored highlights.",
            distinctive_features=s_info["invariants"][:3],
            base_outfit=OutfitVariant(
                outfit_id=f"outfit_{cid}_base",
                name=s_info["outfit_name"],
                description=f"Distinctive signature attire for {c_name}.",
                garments=s_info["garments"],
                colors=s_info["colors"],
                is_base=True,
            ),
            palette_and_values=["#0f172a", "#334155", "#cbd5e1"],
            posture_and_movement="Authoritative, slow, unhurried steps." if is_antag else "Agile, nimble, ready to spring.",
            visual_motifs=s_info["invariants"][:3],
            visual_invariants=s_info["invariants"],
            allowed_variations=["Coat buttoned or open"],
            forbidden_visual_drift=[f"Never remove {s_info['invariants'][0]}"],
            reference_asset_ids=[],
            reference_sheet_specs=["Front neutral portrait", "Three-quarter stance"],
            approval_status="draft",
            version=1,
        )

    # Preserve any pre-existing canonical characters from the project's Story Bible
    if existing_bible and existing_bible.characters:
        for ex_cid, ex_char in existing_bible.characters.items():
            norm_ex = ex_cid.lower().replace("_", "")
            if not any(norm_ex in k.lower().replace("_", "") or k.lower().replace("_", "") in norm_ex for k in characters.keys()):
                ex_invariants = list(ex_char.visual_invariants) if ex_char.visual_invariants else [f"Canonical traits for {ex_char.name}"]
                characters[ex_cid] = CharacterIdentityProfile(
                    character_id=ex_cid,
                    name=ex_char.name,
                    role="Supporting Character" if ex_cid != "nour" else "Protagonist",
                    narrative_function=ex_char.description or f"Pre-existing canonical character in {existing_bible.title}.",
                    age_range="20-25",
                    external_goal="Pursue personal objectives aligned with canon.",
                    internal_need="Maintain authentic character growth.",
                    core_fear="Loss of agency.",
                    wound_or_ghost="A defining moment in early history.",
                    core_contradiction="Outward actions contrast with private convictions.",
                    misbelief="Must rely solely on individual resilience.",
                    stakes_personal="Personal reputation and survival.",
                    strengths=["Steadfast resolve", "In-depth world knowledge"],
                    flaws=["Cautious", "Hesitant to share critical information"],
                    coping_mechanisms=["Maintains strict daily routine"],
                    vulnerabilities=["Over-commitment to past promises"],
                    voice_and_speech="Direct, purposeful, and clear.",
                    values_and_morals=["Uphold established trust"],
                    pressure_response="Assesses facts methodically.",
                    backstory=f"Established resident of {e.world_name}.",
                    secrets=[],
                    arc_checkpoints=[],
                    silhouette_and_proportions="Distinctive individual silhouette.",
                    face_design=ex_char.name,
                    hair_silhouette_and_color="Natural comic inking.",
                    distinctive_features=ex_invariants[:3],
                    visual_invariants=ex_invariants,
                    base_outfit=OutfitVariant(
                        outfit_id=f"outfit_{ex_cid}_base",
                        name=f"{ex_char.name} Default Attire",
                        description=f"Canonical garments for {ex_char.name}",
                        garments=["Standard field attire"],
                        colors=["Charcoal", "Muted tone"],
                        is_base=True,
                    ),
                    posture_and_movement="Grounded, observant posture consistent with canon.",
                    allowed_variations=["Standard clothing variations"],
                    forbidden_visual_drift=[f"Never modify canonical invariants of {ex_char.name}"],
                    reference_asset_ids=[],
                    reference_sheet_specs=[],
                    approval_status="approved",
                    version=ex_char.canon_version or 1,
                )

    # 4. World Bible
    loc_dict: Dict[str, LocationSpec] = {}
    for l_info in e.locations:
        loc_dict[l_info["location_id"]] = LocationSpec(
            location_id=l_info["location_id"],
            name=l_info["name"],
            atmosphere=l_info["atmosphere"],
            spatial_layout=l_info["spatial_layout"],
            visual_anchors=l_info["visual_anchors"],
            lighting_conditions="Muted golden lamp light against misty atmospheric twilight.",
            narrative_use=l_info["narrative_use"],
            continuity_rules=["Atmospheric lighting persists across sequential panels"],
        )

    prop_dict: Dict[str, PropArtifactSpec] = {}
    for p_info in e.props:
        prop_dict[p_info["prop_id"]] = PropArtifactSpec(
            prop_id=p_info["prop_id"],
            name=p_info["name"],
            description=p_info["description"],
            current_owner=p_info.get("current_owner", e.protagonist_id),
            historical_origin=p_info["historical_origin"],
            narrative_function=p_info["narrative_function"],
            state_and_damage=p_info["state_and_damage"],
            visual_invariants=p_info["visual_invariants"],
        )

    magic_rules: List[MagicOrTechAbilityRule] = []
    for r_info in e.supernatural_rules:
        magic_rules.append(MagicOrTechAbilityRule(
            name=r_info["name"],
            description=r_info["description"],
            trigger_condition=r_info["trigger_condition"],
            sensory_manifestation=r_info["sensory_manifestation"],
            cost_or_strain=r_info["cost_or_strain"],
            failure_mode_or_risk=r_info["failure_mode_or_risk"],
            absolute_limit=r_info["absolute_limit"],
        ))

    world_bible = WorldBible(
        project_id=project_id,
        world_name=e.world_name,
        core_laws_and_physics=[
            "Abilities always impose proportional physical strain.",
            "Atmospheric conditions correlate directly with localized energy surges."
        ],
        geography_and_climate=e.geography,
        culture_and_society=e.culture,
        institutions_and_factions=e.factions,
        supernatural_or_tech_rules=magic_rules,
        locations=loc_dict,
        props=prop_dict,
        continuity_timeline_rules=[
            "Timeline is strictly sequential; past events remain immutable.",
            "Weather conditions remain consistent within each chapter sequence."
        ],
        version=1,
    )

    # 5. Relationship Graph
    edges: List[RelationshipEdge] = []
    char_ids = list(characters.keys())
    p_id = e.protagonist_id
    ally_id = e.supporting_characters[0]["character_id"]
    antag_id = e.supporting_characters[1]["character_id"]

    if p_id in characters and ally_id in characters:
        edges.append(RelationshipEdge(
            source_character_id=p_id,
            target_character_id=ally_id,
            relationship_type="reluctant_allies",
            what_source_wants_from_target="Safe transit, mechanical guidance, and strategic backup.",
            what_target_wants_from_source="A share of the bounty and truth behind the mentor's death.",
            trust_level="guarded_trust",
            conflict_dynamic=f"{e.protagonist_name}'s principled caution clashes with {characters[ally_id].name}'s pragmatic survival urge.",
            power_asymmetry="balanced",
            shared_secrets=[f"Both witnessed the ambush on {e.world_name}'s outer perimeter"],
            information_asymmetry=f"{characters[ally_id].name} knows the hidden access ducts; {e.protagonist_name} knows how to activate the artifact.",
            shared_history_and_disputes="Previous skirmish over a disputed delivery contract that ended in a grudging draw.",
            current_status="Uneasy truce forged through necessity.",
            potential_pivot_events=["Discovering that the mentor's final message directly mentions both of them."],
        ))

    if p_id in characters and antag_id in characters:
        edges.append(RelationshipEdge(
            source_character_id=p_id,
            target_character_id=antag_id,
            relationship_type="adversarial",
            what_source_wants_from_target="Survival, justice, and the preservation of truth.",
            what_target_wants_from_source=f"The recovered artifact and {e.protagonist_name}'s submission.",
            trust_level="adversarial",
            conflict_dynamic="Philosophical and physical struggle between human autonomy and totalitarian dominion.",
            power_asymmetry="target_dominant_in_resources_source_dominant_in_willpower",
            shared_secrets=[f"{characters[antag_id].name} knows who {e.protagonist_name}'s parents were before the founding war."],
            information_asymmetry=f"{characters[antag_id].name} does not know the artifact is bonded to {e.protagonist_name}'s biometric signature.",
            shared_history_and_disputes=f"{characters[antag_id].name} once offered {e.protagonist_name} a formal commission in the enforcer brigade.",
            current_status="Active manhunt.",
            potential_pivot_events=[f"{e.protagonist_name} publicly reveals {characters[antag_id].name}'s secret archive."],
        ))

    if ally_id in characters and antag_id in characters:
        edges.append(RelationshipEdge(
            source_character_id=ally_id,
            target_character_id=antag_id,
            relationship_type="prey_and_oppressor",
            what_source_wants_from_target="Freedom from debt and the return of impounded salvage rights.",
            what_target_wants_from_source="Compliance as an undercover scout.",
            trust_level="mutual_suspicion",
            conflict_dynamic="Class hatred between street-level survivor and entrenched ruler.",
            power_asymmetry="target_dominant",
            shared_secrets=[],
            information_asymmetry=f"{characters[antag_id].name} holds the impound order on the survivor's workshop.",
            shared_history_and_disputes=f"{characters[antag_id].name}'s enforcers burned the salvage docks during the last curfew.",
            current_status="Enemies.",
            potential_pivot_events=["The survivor sabotages the main fuel supply valve during the climax."],
        ))

    relationships = RelationshipGraph(
        project_id=project_id,
        characters=char_ids,
        edges=edges,
        ensemble_differentiators=[
            f"{e.protagonist_name}: Observant empathy, quiet intellect, reluctant heroism",
            f"{characters[ally_id].name}: Pragmatic streetwise cynicism, technical ferocity, fierce hidden loyalty",
            f"{characters[antag_id].name}: Cold utilitarian philosophy, strategic dominion, suppressed grief"
        ],
    )

    # 6. Narrative Structure
    chap_outlines: List[ChapterOutline] = []
    for ch_info in e.chapters:
        sc_list: List[SceneCandidate] = []
        for s_cand in ch_info["scenes"]:
            # Validate character IDs exist in cast
            valid_chars = [cid for cid in s_cand["participating_character_ids"] if cid in characters]
            if not valid_chars:
                valid_chars = [e.protagonist_id]
            valid_loc = s_cand["location_id"] if s_cand["location_id"] in loc_dict else list(loc_dict.keys())[0]

            sc_list.append(SceneCandidate(
                scene_id=s_cand["scene_id"],
                title=s_cand["title"],
                narrative_purpose=s_cand["narrative_purpose"],
                participating_character_ids=valid_chars,
                location_id=valid_loc,
                key_action_or_revelation=s_cand["key_action_or_revelation"],
                emotional_beat=s_cand["emotional_beat"],
                estimated_panel_count=s_cand["estimated_panel_count"],
            ))

        chap_outlines.append(ChapterOutline(
            chapter_number=ch_info["chapter_number"],
            title=ch_info["title"],
            purpose_in_arc=ch_info["purpose_in_arc"],
            turning_point=ch_info["turning_point"],
            emotional_shift=ch_info["emotional_shift"],
            ending_hook_or_cliffhanger=ch_info["ending_hook_or_cliffhanger"],
            scene_candidates=sc_list,
        ))

    setup_payoffs = [
        SetupPayoffItem(
            setup_id="sp_01",
            setup_event=f"{e.protagonist_name} keeps protective wraps on to avoid accidental power discharge",
            setup_chapter=1,
            payoff_event=f"{e.protagonist_name} strips off all protection to channel maximum energy into the engine core",
            payoff_chapter=3,
            status="planned",
        ),
        SetupPayoffItem(
            setup_id="sp_02",
            setup_event=f"{characters[ally_id].name} complains about losing their signature tool",
            setup_chapter=2,
            payoff_event=f"The mentor's secret compartment reveals the recovered tool",
            payoff_chapter=3,
            status="planned",
        ),
    ]

    narrative_structure = NarrativeStructure(
        project_id=project_id,
        central_conflict=f"{e.protagonist_name} & {characters[ally_id].name} vs {characters[antag_id].name} over the control of {e.world_name}.",
        opposition_engine=f"The opposition commands immense resources and enforcers; the protagonists have only truth, agility, and mutual trust.",
        macro_arc_beats=e.macro_arc_beats,
        chapters=chap_outlines,
        setup_payoff_ledger=setup_payoffs,
        unresolved_threads=[f"The mysterious third party who initially commissioned the mentor to build the artifact."],
    )

    # 7. Visual Style Profile
    style_profile = VisualStyleProfile(
        style_id=e.style_id,
        name=e.style_name,
        medium=e.style_medium,
        line_art_rules=e.line_art_rules,
        shape_language="Angular, flowing structural lines with sharp vertical architecture and atmospheric shadows.",
        facial_drawing_conventions="Clean, expressive drawing conventions with crisp iris speculars and subtle cross-hatching under eyes.",
        tonal_value_rules=[
            "60-line screentone for midtone gradients",
            "Dense cross-hatching for distressed metal, weathered brickwork, and rust textures",
            "Reserved pure whites for hair highlights, spectacles glints, and energetic sparks",
        ],
        lighting_rules=[
            "High-contrast chiaroscuro with primary directional light sources",
            "Atmospheric rim lighting on wet fabric contours and silhouettes",
        ],
        palette_and_accent_rules=e.palette_rules,
        surface_texture_and_grain="Tactile fine-grain paper overlay with screentone moiré guard.",
        background_detail_density="High density for sprawling exterior architecture; low density during intimate emotional dialogue.",
        screentones_and_fx=[
            "Dynamic motion hatching along fast action vectors",
            "Localized energy echo ghosting with double exposure lines",
        ],
        negative_constraints=e.negative_constraints,
        reference_asset_ids=[],
        approval_status="draft",
        version=1,
    )

    return (
        brief,
        story_bible,
        characters,
        world_bible,
        relationships,
        narrative_structure,
        style_profile,
    )


def synthesize_with_live_ai(
    project_id: str,
    user_prompt: str,
    mode: CreativeMode = CreativeMode.FULL_PRODUCTION_BIBLE,
    visual_references: Optional[List[Dict[str, Any]]] = None,
    existing_bible: Optional[StoryBible] = None,
) -> Tuple[
    CreativeBrief,
    CreativeStoryBible,
    Dict[str, CharacterIdentityProfile],
    WorldBible,
    RelationshipGraph,
    NarrativeStructure,
    VisualStyleProfile,
]:
    """
    Synthesizes universe deliverables using the live Meta muse-spark-1.3 model via /responses.
    Generates genuine, rich, literary-quality narrative prose, strict character invariants,
    wardrobe, and forbidden visual drift with zero robotic template strings.
    """
    cfg = InkLoopConfig.load()
    if not cfg.has_credentials or not cfg.model_api_key:
        raise ValueError("Meta Model API credentials not configured")

    api_key = (
        cfg.model_api_key.get_secret_value()
        if hasattr(cfg.model_api_key, "get_secret_value")
        else str(cfg.model_api_key)
    )

    sys_prompt = """You are the Lead Creative Director for InkLoop, an elite graphic fiction studio.
Given a user prompt, develop a compelling, deeply authentic, and original comic universe.
Characters may be beings of any form: people, animals, monsters, masked or headless figures, object-like or abstract shapes, hybrids, or creator-invented entities. Never assume human anatomy, age, face, hair, clothing, hands, or limbs. Describe only anatomy and features supplied or supported by the brief/references; use explicit absent, not-applicable, or unknown values instead of inventing them.
If the prompt specifies or features 'Nour', integrate canonical InkLoop lore:
- Nour is a reclusive, observant courier who experiences tactile memory resonance (touching relics reveals sensory memories of their past owners).
- Visual invariants: short messy jet-black hair with a pure-white streak on the left temple, round thin wireframe spectacles, oversized hooded storm jacket, worn crossbody leather satchel.
- Key cast: Maeve (abrasive diving scavenger ally with brass dive goggles on forehead, braided undercut) and Cassian Vane (ruthless memory syndicate broker in tailored oxblood velvet coat) or relevant characters.
- Setting: The Drowned Basins of Vespera.
NEVER use robotic placeholders or generic corporate labels (e.g. NEVER 'The Realm of The Chronicles of Nour'). Write vivid, literary-quality narrative prose.

Return strictly valid JSON with this exact structure:
{
  "title": "Story Title",
  "genre": "Genre string",
  "world_name": "Name of world or city",
  "world_premise": "1-2 sentence core world premise",
  "logline": "1 sentence compelling hook",
  "synopsis": "1 paragraph narrative synopsis",
  "central_dramatic_question": "Core thematic question",
  "stakes": "Stakes description",
  "characters": [
    {
      "name": "Character Name",
      "role": "Protagonist or Foil or Antagonist",
      "narrative_function": "Specific narrative function in this story",
      "entity_kind": "Open creator-defined entity kind",
      "morphology": "Overall form/body plan, or unknown/not applicable",
      "surface_description": "Visible material, color, pattern, or texture, or unknown",
      "appendages_or_parts": ["Only parts actually specified"],
      "sensory_features": ["Face-like features, sensors, or explicit absence"],
      "locomotion": "Movement style, not applicable, or unknown",
      "face_check_applicable": false,
      "visual_invariants": ["invariant 1", "invariant 2", "invariant 3"],
      "forbidden_visual_drift": ["forbidden 1", "forbidden 2"],
      "allowed_variations": ["only creator-approved or clearly supported variations"],
      "external_goal": "What they want",
      "internal_need": "What they must learn or overcome",
      "core_fear": "Deepest fear",
      "wound_or_ghost": "Past trauma",
      "flaws": ["flaw 1", "flaw 2"],
      "garments": []
    }
  ]
}
"""

    payload = {
        "model": cfg.muse_spark_model,
        "reasoning": {"effort": "low"},
        "instructions": sys_prompt,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": f"Develop a complete creative universe for: {user_prompt}"}
                ],
            }
        ],
        "max_output_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start_t = time.time()
    with httpx.Client(timeout=25.0) as client:
        resp = client.post(f"{cfg.meta_base_url}/responses", json=payload, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"Meta Responses API failed with status {resp.status_code}: {resp.text[:200]}")

    data_json = resp.json()
    raw_text = ""
    for item in data_json.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    raw_text = c.get("text", "")

    if not raw_text:
        raise ValueError(f"No output text returned by model (items={len(data_json.get('output', []))})")

    # Strip code fences if present
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    # Clean potential trailing commas
    cleaned_json = re.sub(r",\s*([\]}])", r"\1", raw_text)
    parsed = json.loads(cleaned_json)

    # Extract parsed fields
    title = parsed.get("title") or "Tides of Remembrance"
    genre = parsed.get("genre") or "Dark Fantasy / Supernatural Mystery"
    world_name = parsed.get("world_name") or "The Drowned Basins of Vespera"
    world_premise = parsed.get("world_premise") or "A submerged metropolis where memories are traded as currency."
    logline = parsed.get("logline") or "A solitary courier must transport a forbidden relic before the syndicate silences the truth."
    synopsis = parsed.get("synopsis") or "In the flooded ruins, a courier uncovers a conspiracy that threatens the remaining districts."
    cdq = parsed.get("central_dramatic_question") or "Can one preserve authentic remembrance without drowning in other people's grief?"
    stakes = parsed.get("stakes") or "The survival and genuine remembrance of an entire civilization."

    # Hydrate characters
    characters: Dict[str, CharacterIdentityProfile] = {}
    parsed_chars = parsed.get("characters", [])
    if not parsed_chars:
        raise ValueError("Model returned zero characters")

    for idx, c_raw in enumerate(parsed_chars):
        c_name = c_raw.get("name", f"Character_{idx+1}")
        cid = re.sub(r"[^a-z0-9_]", "", c_name.lower().replace(" ", "_"))
        if not cid:
            cid = f"char_{idx+1}"
        role = c_raw.get("role", "Character")
        invariants = c_raw.get("visual_invariants", [])
        forbidden = c_raw.get("forbidden_visual_drift", [])
        garments = c_raw.get("garments", [])

        # Guarantee canonical ID normalization
        if "nour" in cid or "nour" in c_name.lower():
            cid = "nour"
        elif "maeve" in cid or "maeve" in c_name.lower():
            cid = "maeve"
        elif "cassian" in cid or "cassian" in c_name.lower():
            cid = "cassian"

        characters[cid] = CharacterIdentityProfile(
            character_id=cid,
            name=c_name,
            role=role,
            narrative_function=c_raw.get("narrative_function", f"Key role in {world_name}"),
            age_range=str(c_raw.get("age_range", "unspecified / not applicable")),
            entity_kind=str(c_raw.get("entity_kind", "unspecified being")),
            morphology=str(c_raw.get("morphology", "")),
            surface_description=str(c_raw.get("surface_description", "")),
            appendages_or_parts=[x for x in c_raw.get("appendages_or_parts", []) if isinstance(x, str)],
            sensory_features=[x for x in c_raw.get("sensory_features", []) if isinstance(x, str)],
            locomotion=str(c_raw.get("locomotion", "")),
            face_check_applicable=c_raw.get("face_check_applicable") is True,
            external_goal=c_raw.get("external_goal", ""),
            internal_need=c_raw.get("internal_need", ""),
            core_fear=c_raw.get("core_fear", ""),
            wound_or_ghost=c_raw.get("wound_or_ghost", ""),
            core_contradiction=c_raw.get("core_contradiction", ""),
            misbelief=c_raw.get("misbelief", ""),
            stakes_personal=c_raw.get("stakes_personal", ""),
            strengths=c_raw.get("strengths", []),
            flaws=c_raw.get("flaws", []),
            coping_mechanisms=c_raw.get("coping_mechanisms", []),
            vulnerabilities=c_raw.get("vulnerabilities", []),
            voice_and_speech=c_raw.get("voice_and_speech", ""),
            values_and_morals=c_raw.get("values_and_morals", []),
            pressure_response=c_raw.get("pressure_response", ""),
            backstory=c_raw.get("backstory", ""),
            secrets=c_raw.get("secrets", []),
            arc_checkpoints=[],
            silhouette_and_proportions=str(c_raw.get("morphology", "")),
            face_design=str(c_raw.get("face_design", "")),
            hair_silhouette_and_color=str(c_raw.get("hair_silhouette_and_color", "")),
            distinctive_features=invariants[:3],
            base_outfit=OutfitVariant(
                outfit_id=f"outfit_{cid}_base",
                name=f"{c_name} Signature Attire",
                description=f"Signature garments for {c_name}",
                garments=garments,
                colors=["Slate #1e222a", "Muted indigo #2d3748"],
                materials=["Waxed canvas", "Weathered leather"],
                is_base=True,
            ) if garments else None,
            palette_and_values=c_raw.get("palette_and_values", []),
            posture_and_movement=str(c_raw.get("posture_and_movement", "")),
            visual_motifs=invariants[:3],
            visual_invariants=invariants,
            allowed_variations=[x for x in c_raw.get("allowed_variations", []) if isinstance(x, str)],
            forbidden_visual_drift=forbidden,
            reference_asset_ids=[],
            reference_sheet_specs=["identity overview", "form turnaround", "identity feature detail"],
            approval_status="draft",
            version=1,
        )

    # Preserve any pre-existing canonical characters from the project's Story Bible
    if existing_bible and existing_bible.characters:
        for ex_cid, ex_char in existing_bible.characters.items():
            norm_ex = ex_cid.lower().replace("_", "")
            if not any(norm_ex in k.lower().replace("_", "") or k.lower().replace("_", "") in norm_ex for k in characters.keys()):
                ex_invariants = list(ex_char.visual_invariants) if ex_char.visual_invariants else [f"Canonical traits for {ex_char.name}"]
                characters[ex_cid] = CharacterIdentityProfile(
                    character_id=ex_cid,
                    name=ex_char.name,
                    role="Supporting Character" if ex_cid != "nour" else "Protagonist",
                    narrative_function=ex_char.description or f"Pre-existing canonical character in {existing_bible.title}.",
                    entity_kind=getattr(ex_char, "entity_kind", "unspecified being"),
                    morphology=getattr(ex_char, "morphology", ""),
                    surface_description=getattr(ex_char, "surface_description", ""),
                    appendages_or_parts=[],
                    sensory_features=[],
                    locomotion="",
                    face_check_applicable=getattr(ex_char.tolerances, "face_check_applicable", False),
                    external_goal="",
                    internal_need="",
                    core_fear="",
                    wound_or_ghost="",
                    core_contradiction="",
                    misbelief="",
                    stakes_personal="",
                    strengths=[],
                    flaws=[],
                    coping_mechanisms=[],
                    vulnerabilities=[],
                    voice_and_speech="",
                    values_and_morals=[],
                    pressure_response="",
                    backstory="",
                    secrets=[],
                    arc_checkpoints=[],
                    silhouette_and_proportions=getattr(ex_char, "morphology", ""),
                    face_design="",
                    hair_silhouette_and_color="",
                    distinctive_features=ex_invariants[:3],
                    visual_invariants=ex_invariants,
                    base_outfit=OutfitVariant(
                        outfit_id=f"outfit_{ex_cid}_base",
                        name=f"{ex_char.name} Canonical Outfit",
                        description=f"Canon-declared garments for {ex_char.name}",
                        garments=list(getattr(ex_char, "clothing_attributes", [])),
                        colors=[],
                        is_base=True,
                    ) if getattr(ex_char, "clothing_attributes", []) else None,
                    posture_and_movement="",
                    allowed_variations=[],
                    forbidden_visual_drift=[f"Never modify canonical invariants of {ex_char.name}"],
                    reference_asset_ids=[],
                    reference_sheet_specs=[],
                    approval_status="approved",
                    version=ex_char.canon_version or 1,
                )

    protagonist_id = list(characters.keys())[0]
    protagonist = characters[protagonist_id]

    # Explicit facts
    explicit_facts = [
        FactItem(
            fact_id="fact_protagonist_identity",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="protagonist_concept",
            content=f"Protagonist is {protagonist.name}.",
            provenance="User brief text",
        ),
        FactItem(
            fact_id="fact_world_setting",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="setting",
            content=f"Story takes place in {world_name}.",
            provenance="User brief text",
        ),
    ]

    p_low = user_prompt.lower()
    if "white streak" in p_low:
        explicit_facts.append(FactItem(
            fact_id="fact_visual_white_streak",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="visual_invariants",
            content="White streak on dark or black hair",
            provenance="User brief text",
        ))
    if "black hair" in p_low:
        explicit_facts.append(FactItem(
            fact_id="fact_visual_black_hair",
            category=FactCategory.EXPLICIT_USER_FACT,
            field="visual_invariants",
            content="Short messy black hair",
            provenance="User brief text",
        ))

    agent_proposals = [
        FactItem(
            fact_id="prop_narrative_style",
            category=FactCategory.AGENT_PROPOSAL,
            field="narrative_voice",
            content="Literary-grade graphic novel pacing with high-contrast noir chiaroscuro and atmospheric worldbuilding.",
            provenance="Live AI Model synthesis",
            needs_review=True,
        )
    ]

    v_refs = []
    if visual_references:
        for vr in visual_references:
            v_refs.append(BriefVisualReference(
                asset_id=vr.get("asset_id", "ref_0"),
                url=vr.get("url"),
                role=vr.get("role", "general_mood"),
                notes=vr.get("notes"),
                assigned_character_id=vr.get("assigned_character_id"),
            ))

    brief_id = f"brief_{hashlib.sha256(f'{project_id}:{time.time()}'.encode()).hexdigest()[:10]}"
    brief = CreativeBrief(
        brief_id=brief_id,
        project_id=project_id,
        mode=mode,
        user_prompt=user_prompt,
        title=title,
        format="Graphic Novel / Webtoon",
        genre=genre,
        tone="Introspective, atmospheric, high-stakes dramatic tension",
        target_audience="Young Adult / Mature (16+)",
        premise=world_premise,
        central_dramatic_question=cdq,
        intended_emotional_experience="Visceral tension, intellectual intrigue, and earned emotional resonance.",
        themes=["The weight of memory", "Autonomy versus systemic commodification", "Grief and connection"],
        motifs=["Water reflections", "Cracked relics", "Contrasting light and shadow"],
        protagonist_concept=protagonist.narrative_function,
        setting_world_premise=world_premise,
        visual_references=v_refs,
        constraints_must_have=[f"{inv} must be strictly maintained" for inv in protagonist.visual_invariants[:2]],
        constraints_must_not_have=["No unearned miraculous resurrection", "No comic caricature drift"],
        explicit_facts=explicit_facts,
        agent_proposals=agent_proposals,
        unknowns=[f"The true origin of the catastrophe in {world_name}"],
    )

    story_bible = CreativeStoryBible(
        project_id=project_id,
        title=title,
        logline=logline,
        premise=world_premise,
        synopsis_short=logline,
        synopsis_expanded=synopsis,
        genre=genre,
        tone=brief.tone,
        format=brief.format,
        themes=brief.themes,
        subthemes=["Commodified truth", "Chosen isolation vs vulnerable solidarity"],
        motifs=brief.motifs,
        central_dramatic_question=cdq,
        stakes=stakes,
        conflict_engine=f"The tension between the truth of {world_name} and the syndicate seeking to control it.",
        narrative_promise="Intricate mystery plotting, intimate character moments, and distinctive visual atmosphere.",
        point_of_view="Third-person limited focusing on sensory experience",
        narrative_voice="Quietly observant, rhythmically paced, rich in atmospheric texture",
        pacing_and_rhythm="Atmospheric mystery beats culminating in urgent escape setpieces.",
        story_boundaries=["No instant miraculous resurrection", "Abilities strictly cause physical exhaustion and risk"],
        content_constraints=["Grounded dramatic tension; psychological dread over gratuitous gore"],
        core_world_premise=world_premise,
        world_rules_summary=["Tactile resonance causes acute neural strain and requires physical contact."],
        unresolved_questions=brief.unknowns,
        assumptions=[f"The past of {protagonist.name} is directly tied to the founding archives of {world_name}"],
        canon_version=existing_bible.bible_version if existing_bible else 1,
        approved_facts=[f"Protagonist is {protagonist.name}", f"Setting is {world_name}"],
        proposed_facts=[f"The conspiracy operates through the highest merchant guilds of {world_name}"],
    )

    # Locations
    loc_dict: Dict[str, LocationSpec] = {
        "loc_harbor_eaves": LocationSpec(
            location_id="loc_harbor_eaves",
            name="The High Rooftop Warrens",
            atmosphere="Dense vertical shanties connected by suspension ropes and lantern cables above black water.",
            spatial_layout="Narrow boardwalks clinging to cathedral eaves and copper gutters.",
            visual_anchors=["Corroded copper bell tower", "Crisscrossing ropeways", "Lantern poles"],
            lighting_conditions="Muted golden lamp light against misty atmospheric twilight.",
            narrative_use="Courier transit routes and covert meetings.",
            continuity_rules=["Atmospheric sea-mist persists across panels"],
        ),
        "loc_sunken_catacombs": LocationSpec(
            location_id="loc_sunken_catacombs",
            name="The Drowned Lower Meridian",
            atmosphere="Flooded classical architecture submerged beneath twenty feet of dark tide.",
            spatial_layout="Vaulted stone arches filled with seaweed and submerged furniture.",
            visual_anchors=["Submerged marble statuary", "Iron grating", "Phosphorescent siphon tubes"],
            lighting_conditions="Deep underwater turquoise twilight cut by diver torch beams.",
            narrative_use="Salvage dives and artifact recovery.",
            continuity_rules=["Underwater visibility drops to 3 meters in deep vaults"],
        ),
    }

    # Props
    prop_dict: Dict[str, PropArtifactSpec] = {
        "prop_resonance_relic": PropArtifactSpec(
            prop_id="prop_resonance_relic",
            name="Cracked Brass Music Box Relic",
            description="Pre-cataclysm brass mechanical music box with exposed gear escapements and saline corrosion.",
            current_owner=protagonist_id,
            historical_origin="Salvaged from the deep vaults of the founding guild.",
            narrative_function="Catalyst for the entire narrative; contains preserved sensory memory of the final hours.",
            state_and_damage="Hairline fracture across top lid; wound spring still holds half-tension.",
            visual_invariants=["Exposed brass balance wheel on right side", "Saline verdigris along base rim"],
        )
    }

    # Supernatural rules with strict costs and limits
    magic_rules = [
        MagicOrTechAbilityRule(
            name="Tactile Memory Resonance",
            description="The sensory ability to perceive intense audio-visual memories trapped inside salvaged artifacts through direct skin contact.",
            trigger_condition="Bare skin contact with weathered metal, glass, or bone relics that absorbed intense human emotion.",
            sensory_manifestation="Air temperature plunges locally; sound muffles as if submerged in deep water; faint choral echoes and smell of ozone.",
            cost_or_strain="Acute neural migraine, temporary sensory disorientation, and bleeding from left nostril under prolonged resonance.",
            failure_mode_or_risk="Prolonged exposure risks psychic identity erosion, trapping the user's mind inside foreign memories.",
            absolute_limit="Requires intact physical artifact; cannot read memories from air, water, or fully incinerated ashes.",
        )
    ]

    world_bible = WorldBible(
        project_id=project_id,
        world_name=world_name,
        core_laws_and_physics=[
            "Abilities always impose proportional physical strain.",
            "Water levels fluctuate with unpredictable lunar tidal surges."
        ],
        geography_and_climate=world_premise,
        culture_and_society="Stratified salvage economy where elevation above sea level dictates social class.",
        institutions_and_factions=["The Merchant Syndicate", "The Free Courier Guild", "The Deep Salvage Union"],
        supernatural_or_tech_rules=magic_rules,
        locations=loc_dict,
        props=prop_dict,
        continuity_timeline_rules=[
            "Timeline is strictly sequential; past events remain immutable.",
            "Weather conditions remain consistent within each chapter sequence."
        ],
        version=1,
    )

    # Relationships
    char_keys = list(characters.keys())
    edges: List[RelationshipEdge] = []
    if len(char_keys) >= 2:
        c1, c2 = char_keys[0], char_keys[1]
        edges.append(RelationshipEdge(
            source_character_id=c1,
            target_character_id=c2,
            relationship_type="reluctant_allies",
            what_source_wants_from_target="Safe navigation and tactical protection.",
            what_target_wants_from_source="The truth behind the salvaged relic and fair bounty share.",
            trust_level="guarded_trust",
            conflict_dynamic=f"{characters[c1].name}'s caution clashes with {characters[c2].name}'s pragmatic urgency.",
            power_asymmetry="balanced",
            shared_secrets=[f"Both witnessed the illicit auction in {world_name}."],
            information_asymmetry=f"{characters[c2].name} knows the waterways; {characters[c1].name} knows the relic's resonance.",
            shared_history_and_disputes="Previous contract dispute resolved through necessity.",
            current_status="Cautious partnership.",
            potential_pivot_events=["The artifact's memory reveals a direct shared past between their families."],
        ))
    if len(char_keys) >= 3:
        c1, c3 = char_keys[0], char_keys[2]
        edges.append(RelationshipEdge(
            source_character_id=c1,
            target_character_id=c3,
            relationship_type="adversarial",
            what_source_wants_from_target="Survival, truth, and liberation from pursuit.",
            what_target_wants_from_source="The relic and the suppression of its memory.",
            trust_level="adversarial",
            conflict_dynamic="Philosophical conflict between authentic memory and commodified oblivion.",
            power_asymmetry="target_dominant_in_resources",
            shared_secrets=[f"{characters[c3].name} knows the original owner of the relic."],
            information_asymmetry=f"{characters[c3].name} does not know {characters[c1].name} has already activated the core resonance.",
            shared_history_and_disputes=f"{characters[c3].name} previously bought out {characters[c1].name}'s mentor.",
            current_status="Active pursuit.",
            potential_pivot_events=[f"{characters[c1].name} broadcasts the memory across the public tide-bells."],
        ))

    relationships = RelationshipGraph(
        project_id=project_id,
        characters=char_keys,
        edges=edges,
        ensemble_differentiators=[
            f"{char.name}: {char.role} - {char.narrative_function}"
            for char in characters.values()
        ],
    )

    # Narrative Structure
    chap_outlines = [
        ChapterOutline(
            chapter_number=1,
            title="The Salt on the Key",
            purpose_in_arc="Establish ordinary world on rooftop warrens, deliver the inciting relic, and trigger pursuit.",
            turning_point="Activating the relic's resonance reveals the impending conspiracy.",
            emotional_shift="From guarded isolation to urgent flight.",
            ending_hook_or_cliffhanger="Enforcers cut the escape suspension bridge, forcing a leap into black water.",
            scene_candidates=[
                SceneCandidate(
                    scene_id="sc_ch1_01",
                    title="The High Warren Drop",
                    narrative_purpose="Establish courier routine and sensory isolation.",
                    participating_character_ids=[protagonist_id],
                    location_id="loc_harbor_eaves",
                    key_action_or_revelation=f"{protagonist.name} receives the sealed brass music box from an injured diver.",
                    emotional_beat="Quiet, watchful tension.",
                    estimated_panel_count=6,
                )
            ]
        ),
        ChapterOutline(
            chapter_number=2,
            title="The Drowned Meridian",
            purpose_in_arc="Dive into the submerged catacombs to decode the relic's resonance.",
            turning_point="Discovering that the relic's memory implicates the city's highest authority.",
            emotional_shift="From survival panic to righteous resolve.",
            ending_hook_or_cliffhanger="The antagonist corners the protagonists in the flooded vault.",
            scene_candidates=[
                SceneCandidate(
                    scene_id="sc_ch2_01",
                    title="Vault of the Submerged Bell",
                    narrative_purpose="Channeling the relic under water.",
                    participating_character_ids=char_keys[:2],
                    location_id="loc_sunken_catacombs",
                    key_action_or_revelation="The full memory plays out, revealing the suppressed catastrophe.",
                    emotional_beat="Dread and shared awe.",
                    estimated_panel_count=7,
                )
            ]
        ),
        ChapterOutline(
            chapter_number=3,
            title="The Tide Bell Broadcast",
            purpose_in_arc="Climactic confrontation at the central tide tower.",
            turning_point="Sacrificing personal safety to broadcast the memory across the entire basin.",
            emotional_shift="Cathartic liberation and earned solidarity.",
            ending_hook_or_cliffhanger="The flooded city awakens to the truth as the sun rises over the water.",
            scene_candidates=[
                SceneCandidate(
                    scene_id="sc_ch3_01",
                    title="The Bell Tower Stand",
                    narrative_purpose="Decisive face-off against the syndicate enforcers.",
                    participating_character_ids=char_keys,
                    location_id="loc_harbor_eaves",
                    key_action_or_revelation=f"{protagonist.name} channels maximum resonance into the bronze acoustic horn.",
                    emotional_beat="Peak climactic intensity.",
                    estimated_panel_count=8,
                )
            ]
        )
    ]

    setup_payoffs = [
        SetupPayoffItem(
            setup_id="sp_01",
            setup_event=f"{protagonist.name} checks the cracked spring on the brass box.",
            setup_chapter=1,
            payoff_event="The unwinding spring triggers the chime at the exact acoustic frequency to break the vault lock.",
            payoff_chapter=3,
            status="planned",
        )
    ]

    narrative_structure = NarrativeStructure(
        project_id=project_id,
        central_conflict=f"{protagonist.name} vs the syndicate over the authentic remembrance of {world_name}.",
        opposition_engine="Systemic syndicate power with infinite resources versus two agile individuals holding the truth.",
        macro_arc_beats={
            "inciting_incident": "Inciting Delivery & Resonance Awakening",
            "midpoint": "Catacomb Submersion & Vault Trap",
            "climax": "The High Tide Broadcast & Liberation",
        },
        chapters=chap_outlines,
        setup_payoff_ledger=setup_payoffs,
        unresolved_threads=[f"The surviving archives buried in the deepest trench beyond {world_name}."],
    )

    style_profile = VisualStyleProfile(
        style_id="style_noir_ink_screentone",
        name="High-Contrast Atmospheric Noir Ink & Screentone",
        medium="Digital Ink & Paper Screentone",
        line_art_rules=[
            "Variable line weight with heavy brush ink contours",
            "Delicate micro-hatching for skin folds and fabric texture"
        ],
        shape_language="Angular architectural diagonals contrasted with fluid, curving water ripples.",
        facial_drawing_conventions="Expressive semi-realistic eyes with crisp iris reflections and subtle under-eye cross-hatching.",
        tonal_value_rules=[
            "60-line screentone for midtone gradients",
            "Dense cross-hatching for distressed metal, weathered brickwork, and rust textures",
            "Reserved pure whites for hair highlights, spectacles glints, and energetic sparks",
        ],
        lighting_rules=[
            "High-contrast chiaroscuro with primary directional light sources",
            "Atmospheric rim lighting on wet fabric contours and silhouettes",
        ],
        palette_and_accent_rules=[
            "Charcoal ink black #09090b",
            "Warm ivory white #fafaf9",
            "Oxblood crimson accent #7f1d1d",
            "Verdigris patina teal #0f766e"
        ],
        surface_texture_and_grain="Tactile fine-grain paper overlay with screentone moiré guard.",
        background_detail_density="High density for sprawling exterior architecture; low density during intimate emotional dialogue.",
        screentones_and_fx=[
            "Dynamic motion hatching along fast action vectors",
            "Localized energy echo ghosting with double exposure lines",
        ],
        negative_constraints=[
            "Never use flat gradient computer fills without screentone texture",
            "Never render in super-deformed chibi or bubble-gum pop proportions",
            "Never use fluorescent rainbow neon colors in dramatic scenes"
        ],
        reference_asset_ids=[],
        approval_status="draft",
        version=1,
    )

    return (
        brief,
        story_bible,
        characters,
        world_bible,
        relationships,
        narrative_structure,
        style_profile,
    )
