import re
from app.models.pokemon import Pokemon, Team

def parse_pokepaste(paste: str, format: str = "gen9ou") -> Team:
    """Parse a PokePaste string into a Team object."""
    pokemon_list = []
    blocks = re.split(r'\n\s*\n', paste.strip())

    for block in blocks:
        if not block.strip():
            continue
        poke = parse_pokemon_block(block.strip())
        if poke:
            pokemon_list.append(poke)

    return Team(pokemon=pokemon_list, format=format, raw_paste=paste)


def parse_pokemon_block(block: str) -> Pokemon | None:
    lines = block.strip().split('\n')
    if not lines:
        return None

    # First line: Name @ Item  OR  Name (Nickname) @ Item
    first_line = lines[0].strip()
    name = ""
    item = None

    if '@' in first_line:
        parts = first_line.split('@')
        name_part = parts[0].strip()
        item = parts[1].strip()
    else:
        name_part = first_line.strip()

    # Handle nickname: "Nickname (Species)" or just "Species"
    nickname_match = re.search(r'\(([^)]+)\)\s*$', name_part)
    if nickname_match:
        name = nickname_match.group(1).strip()
    else:
        name = name_part.strip()

    # Remove gender markers
    name = re.sub(r'\s*\(M\)\s*$|\s*\(F\)\s*$', '', name).strip()

    ability = None
    tera_type = None
    nature = None
    evs = {}
    moves = []

    for line in lines[1:]:
        line = line.strip()
        if line.startswith('Ability:'):
            ability = line.replace('Ability:', '').strip()
        elif line.startswith('Tera Type:'):
            tera_type = line.replace('Tera Type:', '').strip()
        elif line.startswith('EVs:'):
            evs = parse_evs(line.replace('EVs:', '').strip())
        elif line.endswith('Nature'):
            nature = line.replace('Nature', '').strip()
        elif line.startswith('- '):
            move = line[2:].strip()
            if move:
                moves.append(move)

    if not name:
        return None

    return Pokemon(
        name=name,
        item=item,
        ability=ability,
        tera_type=tera_type,
        evs=evs,
        nature=nature,
        moves=moves,
    )


def parse_evs(ev_string: str) -> dict:
    evs = {}
    parts = ev_string.split('/')
    stat_map = {
        'HP': 'hp', 'Atk': 'atk', 'Def': 'def',
        'SpA': 'spa', 'SpD': 'spd', 'Spe': 'spe'
    }
    for part in parts:
        part = part.strip()
        match = re.match(r'(\d+)\s+(\w+)', part)
        if match:
            value = int(match.group(1))
            stat = stat_map.get(match.group(2), match.group(2))
            evs[stat] = value
    return evs
