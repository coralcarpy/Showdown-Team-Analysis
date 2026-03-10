import httpx
import asyncio
from functools import lru_cache
from typing import Optional
import re

PS_DATA_BASE = "https://play.pokemonshowdown.com/data"
SMOGON_STATS_BASE = "https://www.smogon.com/stats"
PKMN_API = "https://pokeapi.co/api/v2"

_cache: dict = {}

async def fetch_ps_pokedex() -> dict:
    """Fetch full Pokémon data from Showdown's bundled data."""
    if "pokedex" in _cache:
        return _cache["pokedex"]
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{PS_DATA_BASE}/pokedex.json")
        data = r.json()
        _cache["pokedex"] = data
        return data

async def fetch_ps_moves() -> dict:
    if "moves" in _cache:
        return _cache["moves"]
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{PS_DATA_BASE}/moves.json")
        data = r.json()
        _cache["moves"] = data
        return data

async def fetch_ps_learnsets() -> dict:
    if "learnsets" in _cache:
        return _cache["learnsets"]
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{PS_DATA_BASE}/learnsets.json")
        data = r.json()
        _cache["learnsets"] = data
        return data

async def fetch_smogon_stats(format: str = "gen9ou", month: str = "latest") -> dict:
    """Fetch Smogon usage stats for a format."""
    cache_key = f"stats_{format}_{month}"
    if cache_key in _cache:
        return _cache[cache_key]

    # Try to get the most recent month's data
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Get available months
            index_r = await client.get(f"{SMOGON_STATS_BASE}/")
            months = re.findall(r'(\d{4}-\d{2})/', index_r.text)
            if not months:
                return {}
            latest = sorted(months)[-1]
            url = f"{SMOGON_STATS_BASE}/{latest}/chaos/{format}-0.json"
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                _cache[cache_key] = data
                return data
    except Exception as e:
        print(f"Failed to fetch Smogon stats: {e}")
    return {}

async def fetch_pokemon_data(name: str) -> dict:
    """Fetch individual Pokémon data from PokeAPI."""
    slug = name.lower().replace(' ', '-').replace('.', '').replace("'", "")
    # Handle common form names
    slug = slug.replace('oinkologne-f', 'oinkologne-female')

    cache_key = f"poke_{slug}"
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{PKMN_API}/pokemon/{slug}")
            if r.status_code == 200:
                data = r.json()
                _cache[cache_key] = data
                return data
    except Exception as e:
        print(f"Failed to fetch {name}: {e}")
    return {}

async def fetch_species_data(name: str) -> dict:
    """Fetch species data (for GXE/tier info)."""
    slug = name.lower().replace(' ', '-').replace('.', '').replace("'", "")
    cache_key = f"species_{slug}"
    if cache_key in _cache:
        return _cache[cache_key]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{PKMN_API}/pokemon-species/{slug}")
            if r.status_code == 200:
                data = r.json()
                _cache[cache_key] = data
                return data
    except Exception:
        pass
    return {}

def to_ps_id(name: str) -> str:
    """Convert a Pokémon name to its Showdown ID format."""
    return re.sub(r'[^a-z0-9]', '', name.lower())
