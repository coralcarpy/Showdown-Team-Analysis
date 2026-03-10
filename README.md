# PokéBuilder — Pokémon Showdown Team Analysis Tool

A FastAPI-powered team analysis tool for Pokémon Showdown. Paste in a PokéPaste and get instant competitive insights.

## Features

- **Defensive Coverage** — Visualizes which types your team resists or is immune to
- **Offensive Coverage** — Maps which types your team can hit super effectively
- **Stealth Rock Damage** — Calculates SR % damage per Pokémon, with and without Heavy-Duty Boots
- **Hazard Removal** — Checks for Rapid Spin, Defog, and Mortal Spin
- **Status Coverage** — Checks burn, poison, paralysis, and sleep resistances based on typing, ability, and item
- **Speed Tiers** — Calculates real speed stats from base stat, EVs, and nature
- **Threat Analysis** — Dynamically fetches top threats for the selected format using PS pokedex tier data + Smogon usage stats, then checks how many team members are weak to each threat
- **Win Condition Identifier** — Detects setup sweepers, hazard setters, pivots, and priority users, then labels the team archetype (Hyper Offense, Balance, Stall, etc.)
- **Full Report Page** — Opens in a new tab with all analysis rendered, with a download as `.txt` option

## Supported Formats

- Gen 9 OU
- Gen 9 UU
- Gen 9 NU

## Setup

```bash
# 1. Install dependencies (requires Python 3.12)
pip install -r requirements.txt

# 2. Run the server
python -m uvicorn main:app --reload --port 8000

# 3. Open in browser
http://localhost:8000
```

## Project Structure

```
pokebuilder/
├── main.py                    # FastAPI app entry point
├── requirements.txt
├── templates/
│   ├── index.html             # Main UI
│   └── report.html            # Full report page (opens in new tab)
├── static/                    # Static assets
└── app/
    ├── models/
    │   └── pokemon.py         # Pydantic data models
    ├── routers/
    │   ├── analysis.py        # Main analysis endpoint (/api/analysis/analyze)
    │   └── team.py            # Team parse endpoint (/api/team/parse)
    └── services/
        ├── parser.py          # PokePaste → Team parser
        ├── data_fetcher.py    # Live data from PS/Smogon/PokeAPI (with in-memory caching)
        ├── analyzer.py        # Core analysis: types, hazards, speed, coverage
        └── meta_analysis.py   # Dynamic threat & win condition analysis
```

## API Endpoints

### `POST /api/analysis/analyze`
Main analysis endpoint. Accepts a PokéPaste and returns full analysis.

**Request:**
```json
{
  "pokepaste": "Gholdengo @ Choice Specs\n...",
  "format": "gen9ou"
}
```

**Response:** Full analysis object with team data and all analysis modules.

### `POST /api/team/parse`
Parses a PokéPaste into structured data without running analysis.

### `GET /report`
Full report page — reads analysis data from sessionStorage and renders it.

## Data Sources

- **Pokémon Showdown** (`play.pokemonshowdown.com/data`) — Pokédex, moves, and tier data
- **Smogon Stats** (`smogon.com/stats`) — Usage rates, auto-fetches latest available month
- **PokeAPI** (`pokeapi.co`) — Base stats fallback if PS data is unavailable

All data is cached in-memory per session. No database or external storage required.

## How Threat Analysis Works

Instead of hardcoded threat lists, the app dynamically:
1. Reads each Pokémon's `tier` field from the PS Pokédex
2. Filters to only Pokémon in the correct tier for the selected format
3. Ranks them by Smogon usage stats for that format
4. Takes the top 20 and checks how many team members are weak to their STAB types
5. Respects immunities — Flying types, Levitate, and Air Balloon are excluded from Ground-type threat checks

This means the threat list stays accurate automatically as Smogon tier shifts happen.

## Roadmap

- [ ] GXE lookup from Showdown ladder
- [ ] Tera Type coverage analysis
- [ ] Per-mon improvement suggestions
- [ ] More format support
