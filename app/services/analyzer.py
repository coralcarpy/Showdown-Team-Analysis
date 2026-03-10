from app.models.pokemon import Team, Pokemon

# Gen 9 type chart: attacker_type -> {defender_type: multiplier}
TYPE_CHART = {
    "Normal":   {"Rock": 0.5, "Ghost": 0, "Steel": 0.5},
    "Fire":     {"Fire": 0.5, "Water": 0.5, "Grass": 2, "Ice": 2, "Bug": 2, "Rock": 0.5, "Dragon": 0.5, "Steel": 2},
    "Water":    {"Fire": 2, "Water": 0.5, "Grass": 0.5, "Ground": 2, "Rock": 2, "Dragon": 0.5},
    "Electric": {"Water": 2, "Electric": 0.5, "Grass": 0.5, "Ground": 0, "Flying": 2, "Dragon": 0.5},
    "Grass":    {"Fire": 0.5, "Water": 2, "Grass": 0.5, "Poison": 0.5, "Ground": 2, "Flying": 0.5, "Bug": 0.5, "Rock": 2, "Dragon": 0.5, "Steel": 0.5},
    "Ice":      {"Fire": 0.5, "Water": 0.5, "Grass": 2, "Ice": 0.5, "Ground": 2, "Flying": 2, "Dragon": 2, "Steel": 0.5},
    "Fighting": {"Normal": 2, "Ice": 2, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2, "Ghost": 0, "Dark": 2, "Steel": 2, "Fairy": 0.5},
    "Poison":   {"Grass": 2, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0, "Fairy": 2},
    "Ground":   {"Fire": 2, "Electric": 2, "Grass": 0.5, "Poison": 2, "Flying": 0, "Bug": 0.5, "Rock": 2, "Steel": 2},
    "Flying":   {"Electric": 0.5, "Grass": 2, "Fighting": 2, "Bug": 2, "Rock": 0.5, "Steel": 0.5},
    "Psychic":  {"Fighting": 2, "Poison": 2, "Psychic": 0.5, "Dark": 0, "Steel": 0.5},
    "Bug":      {"Fire": 0.5, "Grass": 2, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Psychic": 2, "Ghost": 0.5, "Dark": 2, "Steel": 0.5, "Fairy": 0.5},
    "Rock":     {"Fire": 2, "Ice": 2, "Fighting": 0.5, "Ground": 0.5, "Flying": 2, "Bug": 2, "Steel": 0.5},
    "Ghost":    {"Normal": 0, "Psychic": 2, "Ghost": 2, "Dark": 0.5},
    "Dragon":   {"Dragon": 2, "Steel": 0.5, "Fairy": 0},
    "Dark":     {"Fighting": 0.5, "Psychic": 2, "Ghost": 2, "Dark": 0.5, "Fairy": 0.5},
    "Steel":    {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2, "Rock": 2, "Steel": 0.5, "Fairy": 2, "Poison": 0, "Grass": 0.5, "Psychic": 0.5, "Flying": 0.5, "Normal": 0.5, "Bug": 0.5, "Dragon": 0.5, "Dark": 0.5, "Ground": 2, "Fighting": 2},
    "Fairy":    {"Fighting": 2, "Poison": 0.5, "Bug": 0.5, "Dragon": 2, "Dark": 2, "Steel": 0.5, "Fire": 0.5},
}

ALL_TYPES = list(TYPE_CHART.keys())

HAZARD_DAMAGE = {
    "Stealth Rock": {
        # multiplier based on rock weakness of defender
        "weakness_map": True,  # calculated dynamically
    },
    "Spikes": {
        1: 12.5,  # 1 layer = 1/8
        2: 16.67, # 2 layers = 1/6
        3: 25.0,  # 3 layers = 1/4
    },
    "Toxic Spikes": "poison",
}

BOOTS_ITEMS = {"Heavy-Duty Boots", "Heavy Duty Boots"}

REMOVAL_MOVES = {
    "Rapid Spin": "rapid_spin",
    "Defog": "defog",
    "Mortal Spin": "rapid_spin",
    "Tidy Up": "tidy_up",
}

STATUS_MOVES = {
    "Thunder Wave": "paralysis",
    "Toxic": "poison",
    "Will-O-Wisp": "burn",
    "Spore": "sleep",
    "Sleep Powder": "sleep",
    "Hypnosis": "sleep",
    "Sing": "sleep",
    "Yawn": "sleep",
    "Glare": "paralysis",
    "Nuzzle": "paralysis",
    "Stun Spore": "paralysis",
}


def get_type_effectiveness(attacking_type: str, defending_types: list[str]) -> float:
    """Calculate type effectiveness multiplier."""
    mult = 1.0
    chart = TYPE_CHART.get(attacking_type, {})
    for def_type in defending_types:
        mult *= chart.get(def_type, 1.0)
    return mult


def get_pokemon_weaknesses(types: list[str]) -> dict[str, float]:
    """Return all attacking types and their effectiveness against a type combo."""
    result = {}
    for atk_type in ALL_TYPES:
        eff = get_type_effectiveness(atk_type, types)
        result[atk_type] = eff
    return result


def analyze_team_defensive_coverage(team_types: list[list[str]]) -> dict:
    """
    For each attacking type, find the minimum effectiveness across the team.
    Returns coverage info: which types have a resist/immunity, which are weak points.
    """
    coverage = {}
    for atk_type in ALL_TYPES:
        effs = [get_type_effectiveness(atk_type, poke_types) for poke_types in team_types]
        coverage[atk_type] = {
            "min": min(effs),
            "max": max(effs),
            "values": effs,
            "has_resist": any(e <= 0.5 for e in effs),
            "has_immunity": any(e == 0 for e in effs),
            "all_neutral_or_weak": all(e >= 1.0 for e in effs),
            "weak_count": sum(1 for e in effs if e >= 2.0),
        }
    return coverage


def analyze_hazard_weakness(team: list[dict]) -> dict:
    """
    Analyze how much each Pokémon is hurt by Stealth Rock and Spikes.
    team: list of {name, types, item}
    Returns per-pokemon and team totals.
    """
    results = []
    for poke in team:
        types = poke.get("types", [])
        item = poke.get("item", "")
        has_boots = item in BOOTS_ITEMS

        # Stealth Rock damage (based on rock effectiveness)
        rock_mult = get_type_effectiveness("Rock", types)
        sr_damage = 12.5 * rock_mult  # base is 1/8 = 12.5%

        # Spikes (only ground-types are immune, flying types and levitate too)
        rock_immune = get_type_effectiveness("Ground", types) == 0
        spikes_immune = "Flying" in types or rock_immune
        spikes_1 = 0 if spikes_immune else 12.5
        spikes_3 = 0 if spikes_immune else 25.0

        results.append({
            "name": poke["name"],
            "item": item,
            "has_boots": has_boots,
            "sr_damage": sr_damage,
            "sr_damage_with_boots": 0 if has_boots else sr_damage,
            "spikes_3_damage": spikes_3,
            "spikes_3_with_boots": 0 if has_boots else spikes_3,
            "rock_mult": rock_mult,
            "spikes_immune": spikes_immune,
        })
    return results


def analyze_removal(team_moves: list[dict]) -> dict:
    """Check what hazard removal the team has."""
    has_rapid_spin = False
    has_defog = False
    removers = []

    for poke in team_moves:
        moves = poke.get("moves", [])
        for move in moves:
            if move in ("Rapid Spin", "Mortal Spin", "Tidy Up"):
                has_rapid_spin = True
                removers.append({"name": poke["name"], "move": move, "type": "spin"})
            elif move == "Defog":
                has_defog = True
                removers.append({"name": poke["name"], "move": move, "type": "defog"})

    return {
        "has_removal": has_rapid_spin or has_defog,
        "has_rapid_spin": has_rapid_spin,
        "has_defog": has_defog,
        "removers": removers,
    }


def analyze_status_absorption(team_moves: list[dict], team_types: list[dict]) -> dict:
    """Check if team has ways to handle status conditions."""
    status_coverage = {
        "burn": False,
        "poison": False,
        "paralysis": False,
        "sleep": False,
    }

    status_resistors = []

    for i, poke in enumerate(team_moves):
        moves = poke.get("moves", [])
        types = team_types[i].get("types", []) if i < len(team_types) else []
        item = poke.get("item", "")

        # Fire-types can't be burned
        if "Fire" in types:
            status_coverage["burn"] = True
            status_resistors.append({"name": poke["name"], "resists": "burn", "reason": "Fire-type"})
        # Poison/Steel types immune to poison
        if "Poison" in types or "Steel" in types:
            status_coverage["poison"] = True
            reason = "Poison-type" if "Poison" in types else "Steel-type"
            status_resistors.append({"name": poke["name"], "resists": "poison", "reason": reason})
        # Ground immune to Thunder Wave
        if "Ground" in types:
            status_coverage["paralysis"] = True
            status_resistors.append({"name": poke["name"], "resists": "paralysis", "reason": "Ground-type"})

        # Lum Berry / Aromatherapy / Heal Bell etc.
        if item == "Lum Berry":
            for s in status_coverage:
                status_coverage[s] = True
            status_resistors.append({"name": poke["name"], "resists": "all", "reason": "Lum Berry"})
        if "Aromatherapy" in moves or "Heal Bell" in moves:
            for s in status_coverage:
                status_coverage[s] = True
            status_resistors.append({"name": poke["name"], "resists": "all", "reason": "Cleric move"})

    return {
        "coverage": status_coverage,
        "all_covered": all(status_coverage.values()),
        "resistors": status_resistors,
        "uncovered": [s for s, v in status_coverage.items() if not v],
    }


def analyze_speed_tiers(team_pokemon: list[dict]) -> list[dict]:
    """
    Analyze speed tiers. Requires base stats.
    Returns sorted list with speed context.
    """
    results = []
    for poke in team_pokemon:
        base_spe = poke.get("base_stats", {}).get("spe", 0)
        evs_spe = poke.get("evs", {}).get("spe", 0)
        nature_mod = poke.get("nature_spe_mod", 1.0)
        level = poke.get("level", 100)

        # Calculate actual speed stat
        if base_spe > 0:
            stat = int(((2 * base_spe + 31 + evs_spe // 4) * level // 100 + 5) * nature_mod)
        else:
            stat = 0

        # Common speed benchmarks
        benchmarks = {
            252: "Max Jolly Landorus-T / Garchomp (102 base)",
            251: "Max Jolly Dragapult at 142 base",
            205: "Max Jolly Weavile (125 base)",
            201: "Max Jolly Great Tusk (87→98 base)",
            167: "Max Jolly Garchomp (102 base)",
            145: "Max Jolly Gliscor (95 base)",
        }

        results.append({
            "name": poke["name"],
            "base_speed": base_spe,
            "calculated_speed": stat,
            "ev_investment": evs_spe,
            "nature_mod": nature_mod,
        })

    results.sort(key=lambda x: x["calculated_speed"], reverse=True)
    return results


def analyze_offensive_coverage(team_pokemon: list[dict]) -> dict:
    """
    Check what types the team can hit super effectively.
    """
    covered_types = set()
    coverage_by_pokemon = {}

    for poke in team_pokemon:
        moves = poke.get("moves", [])
        move_types = poke.get("move_types", {})  # move_name -> type
        poke_coverage = set()

        for move in moves:
            mtype = move_types.get(move)
            if mtype:
                for def_type in ALL_TYPES:
                    eff = get_type_effectiveness(mtype, [def_type])
                    if eff >= 2.0:
                        covered_types.add(def_type)
                        poke_coverage.add(def_type)

        coverage_by_pokemon[poke["name"]] = list(poke_coverage)

    uncovered = [t for t in ALL_TYPES if t not in covered_types]

    return {
        "covered_types": list(covered_types),
        "uncovered_types": uncovered,
        "coverage_by_pokemon": coverage_by_pokemon,
        "coverage_percentage": round(len(covered_types) / len(ALL_TYPES) * 100, 1),
    }
