from fastapi import APIRouter, HTTPException
from app.models.pokemon import AnalysisRequest
from app.services.parser import parse_pokepaste
from app.services.data_fetcher import fetch_ps_pokedex, fetch_ps_moves, to_ps_id, fetch_pokemon_data
from app.services.analyzer import (
    analyze_team_defensive_coverage,
    analyze_hazard_weakness,
    analyze_removal,
    analyze_status_absorption,
    analyze_speed_tiers,
    analyze_offensive_coverage,
)
from app.services.meta_analysis import analyze_threats, analyze_win_conditions
import asyncio

router = APIRouter()

NATURE_MODS = {
    "Adamant": {"atk": 1.1, "spa": 0.9},
    "Modest": {"spa": 1.1, "atk": 0.9},
    "Jolly": {"spe": 1.1, "spa": 0.9},
    "Timid": {"spe": 1.1, "atk": 0.9},
    "Careful": {"spd": 1.1, "spa": 0.9},
    "Calm": {"spd": 1.1, "atk": 0.9},
    "Impish": {"def": 1.1, "spa": 0.9},
    "Bold": {"def": 1.1, "atk": 0.9},
    "Brave": {"atk": 1.1, "spe": 0.9},
    "Quiet": {"spa": 1.1, "spe": 0.9},
    "Sassy": {"spd": 1.1, "spe": 0.9},
    "Relaxed": {"def": 1.1, "spe": 0.9},
    "Naughty": {"atk": 1.1, "spd": 0.9},
    "Rash": {"spa": 1.1, "spd": 0.9},
    "Lax": {"def": 1.1, "spd": 0.9},
    "Mild": {"spa": 1.1, "def": 0.9},
    "Lonely": {"atk": 1.1, "def": 0.9},
    "Hasty": {"spe": 1.1, "def": 0.9},
    "Naive": {"spe": 1.1, "spd": 0.9},
    "Hardy": {}, "Docile": {}, "Serious": {}, "Bashful": {}, "Quirky": {},
}

FALLBACK_BASE_SPEED = {
    "gholdengo": 84, "greattusk": 81, "kingambit": 50, "dragapult": 142,
    "landorustherian": 91, "ironvaliant": 116, "volcarona": 100, "roaringmoon": 119,
    "garchomp": 102, "weavile": 125, "gliscor": 95, "toxapex": 35,
    "hatterene": 29, "zamazenta": 138, "tinglu": 45, "ironmoth": 110,
    "ragingbolt": 75, "ogerponwellspring": 110, "primarina": 60, "darkrai": 125,
    "corviknight": 65, "ferrothorn": 20, "slowbro": 30, "hippowdon": 47,
    "clefable": 60, "dondozo": 30, "garganacl": 62, "skeledirge": 66,
    "annihilape": 90, "sneasler": 120, "palafin": 100, "revavroom": 90,
    "cyclizar": 121, "glimmora": 86, "armarouge": 60, "ceruledge": 88,
    "lycanroc": 110, "mimikyu": 96, "feraligatr": 78, "krookodile": 92,
    "gengar": 110, "tyranitar": 61, "excadrill": 88, "breloom": 70,
    "scizor": 65, "metagross": 70, "salamence": 100, "hydreigon": 98,
    "dragonite": 80, "togekiss": 80, "lucario": 90, "rotomwash": 86,
    "urshifu": 97, "miraidon": 135, "koraidon": 135,
    "fluttermane": 135, "ironbundle": 136, "irontreads": 110,
    "chienpal": 135, "chiyu": 116,
}


async def get_base_stats_from_pokeapi(name: str) -> dict:
    data = await fetch_pokemon_data(name)
    if not data or "stats" not in data:
        return {}
    stat_map = {
        "hp": "hp", "attack": "atk", "defense": "def",
        "special-attack": "spa", "special-defense": "spd", "speed": "spe"
    }
    result = {}
    for stat_entry in data.get("stats", []):
        stat_name = stat_entry.get("stat", {}).get("name", "")
        if stat_name in stat_map:
            result[stat_map[stat_name]] = stat_entry.get("base_stat", 0)
    return result


async def enrich_pokemon(poke, pokedex: dict, moves_data: dict) -> dict:
    ps_id = to_ps_id(poke.name)
    dex_entry = pokedex.get(ps_id, {})

    types = dex_entry.get("types", [])

    base_stats_raw = dex_entry.get("baseStats", {})
    base_stats_mapped = {
        "hp": base_stats_raw.get("hp", 0),
        "atk": base_stats_raw.get("atk", 0),
        "def": base_stats_raw.get("def", 0),
        "spa": base_stats_raw.get("spa", 0),
        "spd": base_stats_raw.get("spd", 0),
        "spe": base_stats_raw.get("spe", 0),
    }

    # If PS pokedex gave nothing, try PokeAPI then hardcoded fallback
    if base_stats_mapped["spe"] == 0:
        print(f"[DEBUG] PS miss for {poke.name} (ps_id={ps_id}), trying PokeAPI...")
        pokeapi_stats = await get_base_stats_from_pokeapi(poke.name)
        if pokeapi_stats and pokeapi_stats.get("spe", 0) > 0:
            base_stats_mapped = pokeapi_stats
            print(f"[DEBUG] PokeAPI hit for {poke.name}: spe={pokeapi_stats.get('spe')}")
        elif ps_id in FALLBACK_BASE_SPEED:
            base_stats_mapped["spe"] = FALLBACK_BASE_SPEED[ps_id]
            print(f"[DEBUG] Hardcoded fallback for {poke.name}: spe={FALLBACK_BASE_SPEED[ps_id]}")
        else:
            print(f"[WARNING] No speed data found for {poke.name} (ps_id={ps_id})")

    # Types fallback via PokeAPI
    if not types:
        poke_data = await fetch_pokemon_data(poke.name)
        if poke_data and "types" in poke_data:
            types = [t["type"]["name"].capitalize() for t in poke_data["types"]]

    move_types = {}
    for move_name in poke.moves:
        move_id = to_ps_id(move_name)
        move_entry = moves_data.get(move_id, {})
        if move_entry:
            move_types[move_name] = move_entry.get("type", "Normal")

    nature_mod_spe = 1.0
    if poke.nature and poke.nature in NATURE_MODS:
        nature_mod_spe = NATURE_MODS[poke.nature].get("spe", 1.0)

    print(f"[INFO] {poke.name}: types={types}, base_spe={base_stats_mapped.get('spe')}, nat={nature_mod_spe}, evs_spe={poke.evs.get('spe', 0) if poke.evs else 0}")

    return {
        "name": poke.name,
        "types": types,
        "item": poke.item or "",
        "ability": poke.ability or "",
        "tera_type": poke.tera_type,
        "evs": poke.evs or {},
        "nature": poke.nature,
        "moves": poke.moves,
        "move_types": move_types,
        "base_stats": base_stats_mapped,
        "nature_spe_mod": nature_mod_spe,
        "level": poke.level,
        "sprite_url": f"https://play.pokemonshowdown.com/sprites/ani/{ps_id}.gif",
        "sprite_static": f"https://play.pokemonshowdown.com/sprites/gen5/{ps_id}.png",
    }


@router.post("/analyze")
async def analyze_team(request: AnalysisRequest):
    try:
        team = parse_pokepaste(request.pokepaste, request.format)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PokePaste: {str(e)}")

    if not team.pokemon:
        raise HTTPException(status_code=400, detail="No Pokémon found in paste")

    print(f"\n[INFO] Analyzing {len(team.pokemon)} Pokémon | format: {request.format}")

    pokedex, moves_data = await asyncio.gather(
        fetch_ps_pokedex(),
        fetch_ps_moves(),
    )
    print(f"[INFO] PS Pokedex entries: {len(pokedex)}")

    enriched = await asyncio.gather(*[
        enrich_pokemon(poke, pokedex, moves_data) for poke in team.pokemon
    ])
    enriched = list(enriched)

    team_types = [{"name": p["name"], "types": p["types"]} for p in enriched]

    defensive_coverage = analyze_team_defensive_coverage([p["types"] for p in enriched])
    hazard_analysis = analyze_hazard_weakness(enriched)
    removal_analysis = analyze_removal(enriched)
    status_analysis = analyze_status_absorption(enriched, team_types)
    speed_tiers = analyze_speed_tiers(enriched)
    offensive_coverage = analyze_offensive_coverage(enriched)

    threats, win_conditions = await asyncio.gather(
        analyze_threats(enriched, request.format),
        analyze_win_conditions(enriched),
    )

    return {
        "team": enriched,
        "format": request.format,
        "analysis": {
            "defensive_coverage": defensive_coverage,
            "hazard_weakness": hazard_analysis,
            "hazard_removal": removal_analysis,
            "status_coverage": status_analysis,
            "speed_tiers": speed_tiers,
            "offensive_coverage": offensive_coverage,
            "threat_analysis": threats,
            "win_conditions": win_conditions,
        },
    }


@router.get("/debug/pokedex/{name}")
async def debug_pokedex(name: str):
    """Check if a Pokémon is found correctly. Visit /api/analysis/debug/pokedex/Garchomp"""
    pokedex = await fetch_ps_pokedex()
    ps_id = to_ps_id(name)
    entry = pokedex.get(ps_id, {})
    pokeapi = await fetch_pokemon_data(name)
    return {
        "name": name,
        "ps_id": ps_id,
        "ps_found": bool(entry),
        "ps_base_stats": entry.get("baseStats", {}),
        "ps_types": entry.get("types", []),
        "pokeapi_found": bool(pokeapi),
        "pokeapi_speed": next((s["base_stat"] for s in pokeapi.get("stats", []) if s["stat"]["name"] == "speed"), None) if pokeapi else None,
    }