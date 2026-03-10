# PokéBuilder — Pokémon Showdown Team Analysis Tool

A FastAPI-powered team analysis app for Pokémon Showdown. Paste in a PokéPaste and get instant competitive insights.

## Features

- **Defensive Coverage** — Visualizes which types your team resists/is immune to
- **Hazard Weakness** — Shows Stealth Rock % damage per mon, with vs without Heavy-Duty Boots
- **Hazard Removal** — Checks for Rapid Spin / Defog / Mortal Spin
- **Threat Analysis** — Uses Smogon stats to identify common threats that 2+ mons are weak to
- **Speed Tiers** — Calculates real speed stats from EVs, nature, and base stat
- **Offensive Coverage** — Maps which types your team hits super effectively
- **Status Coverage** — Checks burn/poison/paralysis/sleep resistances
- **Win Condition Identifier** — Detects team archetype (setup, pivot, hazard stack, etc.)
- **Export Report** — Downloads a Markdown summary

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
uvicorn main:app --reload --port 8000

# 3. Open in browser
http://localhost:8000
```

## Project Structure

```
pokebuilder/
├── main.py                    # FastAPI app entry point
├── requirements.txt
├── templates/
│   └── index.html             # Pokémon-themed frontend
├── static/                    # Static assets
└── app/
    ├── models/
    │   └── pokemon.py         # Pydantic data models
    ├── routers/
    │   ├── analysis.py        # Main analysis endpoint (/api/analysis/analyze)
    │   └── team.py            # Team parse endpoint (/api/team/parse)
    └── services/
        ├── parser.py          # PokePaste → Team parser
        ├── data_fetcher.py    # Live data from PS/Smogon/PokeAPI (with caching)
        ├── analyzer.py        # Core analysis: types, hazards, speed, coverage
        └── meta_analysis.py   # Threat & win condition analysis
```

## API Endpoints

### `POST /api/analysis/analyze`
Main analysis endpoint. Accepts a PokePaste and returns full analysis.

**Request:**
```json
{
  "pokepaste": "Gholdengo @ Choice Specs\n...",
  "format": "gen9ou"
}
```

**Response:** Full analysis object with team data and all analysis modules.

### `POST /api/team/parse`
Parses a PokePaste into structured data without running analysis.

## Data Sources

- **Pokémon Showdown** (`play.pokemonshowdown.com/data`) — Pokédex, moves, learnsets
- **Smogon Stats** (`smogon.com/stats`) — Usage rates for threat weighting
- **PokeAPI** (`pokeapi.co`) — Base stats, sprite URLs

All data is cached in-memory per session for performance.

## Expanding to Other Formats

The format selector in the UI maps directly to Smogon's stat URLs. Any format Smogon tracks (gen9uu, gen8ou, etc.) will work for stats fetching. The type chart and analysis logic is generation-agnostic.

To add format-specific threat lists, extend `TOP_THREATS` and `THREAT_PROFILES` in `app/services/meta_analysis.py`.

## Roadmap

- [ ] GXE fetching from Showdown ladder API
- [ ] Tera Type coverage analysis
- [ ] Item synergy checks (e.g., Booster Energy users)
- [ ] Matchup matrix vs specific opponent teams
- [ ] Per-mon suggested improvements
- [ ] Save/compare multiple teams
