from app.services.data_fetcher import fetch_smogon_stats, fetch_ps_pokedex, to_ps_id
from app.services.analyzer import get_type_effectiveness

# Map our format strings to PS tier labels
FORMAT_TO_TIER = {
    "gen9ou": "OU",
    "gen9uu": "UU",
    "gen9nu": "NU",
}

# How many top threats to analyse per format
TOP_N_THREATS = 20

# Suggested checks by type weakness — used to generate check suggestions dynamically
TYPE_CHECKS = {
    "Fire":     ["Water-type", "Ground-type", "Rock-type"],
    "Water":    ["Electric-type", "Grass-type"],
    "Grass":    ["Fire-type", "Flying-type", "Poison-type", "Bug-type", "Ice-type"],
    "Electric": ["Ground-type"],
    "Ice":      ["Fire-type", "Fighting-type", "Rock-type", "Steel-type"],
    "Fighting": ["Psychic-type", "Flying-type", "Fairy-type"],
    "Poison":   ["Ground-type", "Psychic-type"],
    "Ground":   ["Water-type", "Grass-type", "Ice-type"],
    "Flying":   ["Electric-type", "Rock-type", "Ice-type"],
    "Psychic":  ["Dark-type", "Ghost-type", "Bug-type"],
    "Bug":      ["Fire-type", "Flying-type", "Rock-type"],
    "Rock":     ["Water-type", "Grass-type", "Fighting-type", "Ground-type", "Steel-type"],
    "Ghost":    ["Dark-type", "Ghost-type"],
    "Dragon":   ["Ice-type", "Dragon-type", "Fairy-type"],
    "Dark":     ["Fighting-type", "Fairy-type", "Bug-type"],
    "Steel":    ["Fire-type", "Ground-type", "Fighting-type"],
    "Fairy":    ["Poison-type", "Steel-type"],
    "Normal":   ["Fighting-type"],
}

GROUND_IMMUNE_ABILITIES = {"Levitate", "Air Lock"}
GROUND_IMMUNE_ITEMS = {"Air Balloon"}


def is_immune_to_ground(poke: dict) -> bool:
    types = poke.get("types", [])
    ability = poke.get("ability", "")
    item = poke.get("item", "")
    if "Flying" in types:
        return True
    if ability in GROUND_IMMUNE_ABILITIES:
        return True
    if item in GROUND_IMMUNE_ITEMS:
        return True
    return False


def get_checks_for_types(types: list[str]) -> list[str]:
    """Generate suggested checks based on what beats a given type combo."""
    checks = set()
    for t in types:
        for check in TYPE_CHECKS.get(t, []):
            checks.add(check)
    return list(checks)[:4]  # return top 4 suggestions


async def build_threat_list(format: str, pokedex: dict, usage_stats: dict) -> list[dict]:
    """
    Dynamically build a threat list by:
    1. Finding all Pokémon in the correct tier from PS pokedex
    2. Ranking them by Smogon usage stats
    3. Taking the top N
    4. Building type profiles from their pokedex entries
    """
    tier_label = FORMAT_TO_TIER.get(format.lower(), "OU")

    # Collect all Pokémon in this tier from PS pokedex
    tier_pokemon = []
    for ps_id, entry in pokedex.items():
        poke_tier = entry.get("tier", "")
        # Match tier — also include UUBL in UU, RUBL in RU etc.
        bl_tier = tier_label + "BL"
        if poke_tier == tier_label or poke_tier == bl_tier:
            name = entry.get("name", ps_id)
            types = entry.get("types", [])

            # Get usage from Smogon stats
            usage = 0
            for stat_key, stat_val in usage_stats.items():
                if to_ps_id(stat_key) == ps_id:
                    raw = stat_val.get("usage", 0)
                    usage = raw.get("weighted", 0) if isinstance(raw, dict) else raw
                    break

            tier_pokemon.append({
                "name": name,
                "ps_id": ps_id,
                "types": types,
                "usage": usage,
            })

    # Sort by usage descending, take top N
    tier_pokemon.sort(key=lambda x: x["usage"], reverse=True)
    top_threats = tier_pokemon[:TOP_N_THREATS]

    print(f"[INFO] Dynamic threats for {format} (tier={tier_label}): {[t['name'] for t in top_threats]}")

    # Build threat profiles
    profiles = []
    for poke in top_threats:
        profiles.append({
            "threat": poke["name"],
            "types": poke["types"],
            "usage_rate": round(poke["usage"] * 100, 1) if poke["usage"] else None,
            "checks": get_checks_for_types(poke["types"]),
        })

    return profiles


async def analyze_threats(team_pokemon: list[dict], format: str = "gen9ou") -> dict:
    """
    Dynamically fetch top threats for the given format from PS pokedex + Smogon stats,
    then check how many team members are weak to each threat's STAB types.
    """
    # Fetch both data sources (pokedex already cached after first analysis)
    from app.services.data_fetcher import fetch_ps_pokedex
    pokedex, stats_data = await __import__('asyncio').gather(
        fetch_ps_pokedex(),
        fetch_smogon_stats(format),
    )
    usage_stats = stats_data.get("data", {}) if stats_data else {}

    # If no usage stats from Smogon, fall back to just tier-based list unranked
    threat_profiles = await build_threat_list(format, pokedex, usage_stats)

    if not threat_profiles:
        print(f"[WARNING] No threats found for format {format}, tier list may be empty")
        return {"threats": [], "critical_weaknesses": [], "format": format}

    threat_analysis = []

    for profile in threat_profiles:
        threat_types = profile["types"]

        threatened_pokemon = []
        for poke in team_pokemon:
            poke_types = poke.get("types", [])
            max_weakness = 0

            for threat_type in threat_types:
                if threat_type == "Ground" and is_immune_to_ground(poke):
                    continue
                eff = get_type_effectiveness(threat_type, poke_types)
                if eff == 0:
                    continue
                if eff > max_weakness:
                    max_weakness = eff

            if max_weakness >= 2.0:
                threatened_pokemon.append({
                    "name": poke["name"],
                    "weakness": max_weakness,
                })

        if len(threatened_pokemon) >= 2:
            threat_analysis.append({
                "threat": profile["threat"],
                "types": threat_types,
                "threatened_count": len(threatened_pokemon),
                "threatened_pokemon": threatened_pokemon,
                "usage_rate": profile["usage_rate"],
                "checks": profile["checks"],
            })

    threat_analysis.sort(key=lambda x: (x["threatened_count"], x.get("usage_rate") or 0), reverse=True)

    return {
        "threats": threat_analysis,
        "critical_weaknesses": [t for t in threat_analysis if t["threatened_count"] >= 3],
        "format": format,
        "total_threats_checked": len(threat_profiles),
    }


async def analyze_win_conditions(team_pokemon: list[dict]) -> dict:
    WIN_CON_MOVES = {
        "setup": ["Swords Dance", "Nasty Plot", "Dragon Dance", "Calm Mind",
                  "Quiver Dance", "Shell Smash", "Bulk Up", "Coil", "Curse",
                  "Tail Glow", "Geomancy", "Clangorous Soul"],
        "hazard_setter": ["Stealth Rock", "Spikes", "Toxic Spikes", "Stone Axe"],
        "weather": ["Sunny Day", "Rain Dance", "Sandstorm", "Snowscape", "Hail"],
        "trick_room": ["Trick Room"],
        "pivot": ["U-turn", "Volt Switch", "Flip Turn", "Parting Shot", "Teleport"],
        "wallbreaker_moves": ["Knock Off", "Close Combat", "Flare Blitz", "Head Smash",
                              "Superpower", "V-create", "Bolt Strike"],
        "recovery": ["Recover", "Roost", "Slack Off", "Soft-Boiled", "Moonlight",
                     "Morning Sun", "Synthesis", "Shore Up", "Wish", "Heal Order"],
        "phazing": ["Whirlwind", "Roar", "Dragon Tail", "Circle Throw"],
        "priority": ["Extreme Speed", "Bullet Punch", "Ice Shard", "Aqua Jet",
                     "Mach Punch", "Shadow Sneak", "Accelerock", "Quick Attack",
                     "Sucker Punch", "Water Shuriken", "Grassy Glide"],
    }

    identified = {k: [] for k in WIN_CON_MOVES}

    for poke in team_pokemon:
        moves = poke.get("moves", [])
        item = poke.get("item", "")
        for category, move_list in WIN_CON_MOVES.items():
            matching = [m for m in moves if m in move_list]
            if matching:
                identified[category].append({
                    "pokemon": poke["name"],
                    "moves": matching,
                    "item": item,
                })

    setup_count = len(identified["setup"])
    has_hazards = bool(identified["hazard_setter"])
    has_pivots = bool(identified["pivot"])
    has_tr = bool(identified["trick_room"])
    has_recovery = bool(identified["recovery"])
    has_phazing = bool(identified["phazing"])
    has_priority = bool(identified["priority"])
    has_weather = bool(identified["weather"])

    ho_items = {"Focus Sash", "Life Orb", "Choice Band", "Choice Specs",
                "Choice Scarf", "Loaded Dice", "Weakness Policy"}
    def_items = {"Leftovers", "Rocky Helmet", "Assault Vest", "Eviolite",
                 "Heavy-Duty Boots", "Black Sludge", "Shed Shell"}

    ho_item_count = sum(1 for p in team_pokemon if p.get("item", "") in ho_items)
    def_item_count = sum(1 for p in team_pokemon if p.get("item", "") in def_items)

    if has_tr:
        archetype = "Trick Room"
    elif has_weather:
        archetype = "Weather Team"
    elif ho_item_count >= 4 and setup_count >= 2 and not has_recovery:
        archetype = "Hyper Offense"
    elif ho_item_count >= 4 and setup_count >= 1 and has_hazards and not has_recovery:
        archetype = "Offensive Hazard Stack"
    elif setup_count >= 2 and has_hazards and has_pivots:
        archetype = "Bulky Offense"
    elif setup_count >= 2 and has_hazards and not has_pivots:
        archetype = "Hazard Offense"
    elif setup_count >= 1 and has_pivots:
        archetype = "Volt-Turn + Setup"
    elif setup_count >= 1 and has_hazards:
        archetype = "Balance"
    elif has_recovery and has_phazing and def_item_count >= 3:
        archetype = "Stall"
    elif has_recovery and def_item_count >= 2:
        archetype = "Bulky / Semi-Stall"
    elif has_pivots:
        archetype = "Pivot Offense"
    elif setup_count >= 1:
        archetype = "Setup Offense"
    else:
        archetype = "Hyper Offense"

    return {
        "win_conditions": identified,
        "team_archetype": archetype,
        "has_setup_sweeper": bool(identified["setup"]),
        "has_hazard_setter": has_hazards,
        "has_pivot": has_pivots,
        "has_trick_room": has_tr,
        "has_priority": has_priority,
        "offensive_item_count": ho_item_count,
    }
