import xml.etree.ElementTree as ET
from pathlib import Path

from scrape import backup_file, parse_pegasus_meta, _write_pegasus_document


def _append_pegasus_field(lines, key, value):
    if value not in (None, ''):
        text = str(value).replace('\r', '').replace('\n', ' ')
        lines.append(f'{key}: {text}')


def build_edited_pegasus_entry(game):
    lines = [f"game: {game.get('title') or Path(game['filename']).stem}"]
    lines.append(f"file: {game['filename']}")
    fields = (
        ('x-id', 'game_id'),
        ('developer', 'developer'),
        ('publisher', 'publisher'),
        ('genre', 'genres'),
        ('players', 'players'),
        ('release', 'release'),
        ('rating', 'rating'),
        ('description', 'description'),
        ('assets.boxFront', 'boxfront_rel_path'),
        ('assets.logo', 'logo_rel_path'),
        ('assets.video', 'video_rel_path'),
    )
    for pegasus_key, game_key in fields:
        _append_pegasus_field(lines, pegasus_key, game.get(game_key))
    return '\n'.join(lines)


def update_pegasus_game(root, game):
    meta_path = Path(root) / 'metadata.pegasus.txt'
    collection_lines, existing_games = parse_pegasus_meta(meta_path)
    entry = build_edited_pegasus_entry(game)
    for record in existing_games:
        if record.get('file') == game['filename']:
            record['lines'] = entry
            break
    else:
        existing_games.append({'file': game['filename'], 'lines': entry})
    backup_file(meta_path)
    _write_pegasus_document(meta_path, collection_lines, existing_games)


def _set_or_remove(element, tag, value):
    child = element.find(tag)
    if value in (None, ''):
        if child is not None:
            element.remove(child)
        return
    if child is None:
        child = ET.SubElement(element, tag)
    child.text = str(value)


def _gamelist_release(value):
    if not value:
        return ''
    compact = str(value).replace('-', '')
    return compact if 'T' in compact else f'{compact}T000000'


def _gamelist_rating(value):
    if not value:
        return ''
    try:
        text = str(value)
        number = float(text.rstrip('%'))
        if text.endswith('%') or number > 1:
            number /= 100.0
        return f'{number:.2f}'
    except (TypeError, ValueError):
        return str(value)


def update_gamelist_game(root, game):
    gamelist_path = Path(root) / 'gamelist.xml'
    if gamelist_path.exists():
        try:
            tree = ET.parse(gamelist_path)
            document = tree.getroot()
        except ET.ParseError:
            document = ET.Element('gameList')
            tree = ET.ElementTree(document)
    else:
        document = ET.Element('gameList')
        tree = ET.ElementTree(document)

    game_path = f"./{game['filename']}"
    game_element = next(
        (item for item in document.findall('game')
         if item.findtext('path') == game_path),
        None,
    )
    if game_element is None:
        game_element = ET.SubElement(document, 'game')

    values = {
        'path': game_path,
        'name': game.get('title') or Path(game['filename']).stem,
        'id': game.get('game_id'),
        'developer': game.get('developer'),
        'publisher': game.get('publisher'),
        'genre': game.get('genres'),
        'players': game.get('players'),
        'releasedate': _gamelist_release(game.get('release')),
        'rating': _gamelist_rating(game.get('rating')),
        'desc': game.get('description'),
        'image': (f"./{game['boxfront_rel_path']}"
                  if game.get('boxfront_rel_path') else ''),
        'marquee': (f"./{game['logo_rel_path']}"
                    if game.get('logo_rel_path') else ''),
        'video': (f"./{game['video_rel_path']}"
                  if game.get('video_rel_path') else ''),
    }
    for tag, value in values.items():
        _set_or_remove(game_element, tag, value)

    backup_file(gamelist_path)
    ET.indent(tree, space='  ')
    tree.write(str(gamelist_path), encoding='utf-8', xml_declaration=True)
