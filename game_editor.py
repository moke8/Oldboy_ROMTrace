import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from scrape import (
    _write_pegasus_document,
    anbernic_cover_path,
    backup_file,
    parse_pegasus_meta,
    sanitize_filename,
    standard_cover_path,
    standard_logo_path,
)


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


def standard_media_path(filename, kind, suffix):
    suffix = suffix if str(suffix).startswith('.') else f'.{suffix}'
    if kind == 'boxfront':
        return standard_cover_path(filename, suffix)
    if kind == 'logo':
        return standard_logo_path(filename, suffix)
    if kind == 'video':
        name = sanitize_filename(Path(filename).stem)
        return f'media/{name}/video{suffix.lower()}'
    raise ValueError(f'未知媒体类型: {kind}')


def _is_within(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _relative_media_path(value, root):
    if not value:
        return ''
    text = str(value)
    if text.startswith(('http://', 'https://')):
        return text
    path = Path(text)
    if not path.is_absolute():
        return path.as_posix().lstrip('./')
    if _is_within(path, root):
        return path.resolve().relative_to(Path(root).resolve()).as_posix()
    return text


def _snapshot_file(path, snapshot_dir, label):
    path = Path(path)
    if not path.exists():
        return None
    snapshot = Path(snapshot_dir) / label
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, snapshot)
    return snapshot


def _restore_snapshot(path, snapshot):
    path = Path(path)
    if snapshot is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snapshot, path)


def _collect_pegasus_media_references(root):
    references = set()
    _, games = parse_pegasus_meta(Path(root) / 'metadata.pegasus.txt')
    pattern = re.compile(
        r'^assets\.(?:boxFront|box_front|logo|Logo|video|Video):\s*(.+)$',
        re.MULTILINE,
    )
    for game in games:
        for value in pattern.findall(game['lines']):
            path = Path(value.strip())
            if not path.is_absolute():
                path = Path(root) / path
            references.add(path.resolve())
    return references


def _collect_gamelist_media_references(root):
    references = set()
    path = Path(root) / 'gamelist.xml'
    if not path.exists():
        return references
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return references
    for game in tree.findall('game'):
        for tag in ('image', 'marquee', 'video'):
            value = game.findtext(tag)
            if not value or value.startswith(('http://', 'https://')):
                continue
            media = Path(value.lstrip('./'))
            if not media.is_absolute():
                media = Path(root) / media
            references.add(media.resolve())
    return references


def collect_all_index_media_references(root):
    return (_collect_pegasus_media_references(root)
            | _collect_gamelist_media_references(root))


def _edited_index_game(root, original, edited, relative_paths):
    return {
        'filename': original.get('file') or original.get('filename'),
        'title': edited.get('title', ''),
        'game_id': edited.get('game_id', ''),
        'developer': edited.get('developer', ''),
        'publisher': edited.get('publisher', ''),
        'genres': edited.get('genres', edited.get('genre', '')),
        'players': edited.get('players', ''),
        'release': edited.get('release', ''),
        'rating': edited.get('rating', ''),
        'description': edited.get('description', ''),
        'boxfront_rel_path': relative_paths['boxfront'],
        'logo_rel_path': relative_paths['logo'],
        'video_rel_path': relative_paths['video'],
    }


def _prepare_media(root, original, edited, temp_dir):
    filename = original.get('file') or original.get('filename')
    prepared = {}
    relative_paths = {}
    final_paths = set()
    for kind in ('boxfront', 'logo', 'video'):
        if edited.get(f'{kind}_removed'):
            relative_paths[kind] = ''
            continue
        upload = edited.get(f'{kind}_upload')
        if upload:
            source = Path(upload)
            if not source.is_file():
                raise ValueError(f'媒体文件不存在: {source}')
            relative = Path(standard_media_path(
                filename, kind, source.suffix.lower()))
            staged = Path(temp_dir) / f'{kind}{source.suffix.lower()}'
            shutil.copy2(source, staged)
            destination = Path(root) / relative
            prepared[kind] = (staged, destination)
            relative_paths[kind] = relative.as_posix()
            final_paths.add(destination.resolve())
        else:
            value = edited.get(kind, original.get(kind, ''))
            relative_paths[kind] = _relative_media_path(value, root)
            if relative_paths[kind] and not relative_paths[kind].startswith(
                    ('http://', 'https://')):
                path = Path(relative_paths[kind])
                if not path.is_absolute():
                    path = Path(root) / path
                final_paths.add(path.resolve())
    return prepared, relative_paths, final_paths


def _sync_anbernic_cover(root, filename, cover_path):
    imgs_dir = Path(root) / 'Imgs'
    stem = sanitize_filename(Path(filename).stem)
    if cover_path:
        source = Path(root) / cover_path
        destination = Path(root) / anbernic_cover_path(
            filename, source.suffix)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        for old in imgs_dir.glob(f'{stem}.*'):
            if old != destination:
                old.unlink()
    elif imgs_dir.exists():
        for old in imgs_dir.glob(f'{stem}.*'):
            old.unlink()


def _remove_unreferenced_old_media(root, original, final_paths):
    references = collect_all_index_media_references(root)
    for kind in ('boxfront', 'logo', 'video'):
        value = original.get(kind)
        if not value or str(value).startswith(('http://', 'https://')):
            continue
        old = Path(value)
        if not old.is_absolute():
            old = Path(root) / old
        resolved = old.resolve()
        if (_is_within(resolved, root)
                and resolved not in final_paths
                and resolved not in references):
            old.unlink(missing_ok=True)


def save_game_edits(root, original, edited, targets):
    root = Path(root).resolve()
    if not any(targets.get(key) for key in ('pegasus', 'gamelist', 'imgs')):
        raise ValueError('至少启用一个保存目标')
    if not root.is_dir():
        raise ValueError(f'游戏目录不存在: {root}')
    filename = original.get('file') or original.get('filename')
    if not filename:
        raise ValueError('游戏缺少 ROM 文件名')

    with tempfile.TemporaryDirectory(dir=root) as temp_dir:
        prepared, relative_paths, final_paths = _prepare_media(
            root, original, edited, temp_dir)
        index_game = _edited_index_game(
            root, original, edited, relative_paths)
        index_paths = {
            'pegasus': root / 'metadata.pegasus.txt',
            'gamelist': root / 'gamelist.xml',
        }
        snapshots = {
            key: _snapshot_file(path, temp_dir, f'{key}.snapshot')
            for key, path in index_paths.items() if targets.get(key)
        }
        media_snapshots = {}
        installed = []
        imgs_stem = sanitize_filename(Path(filename).stem)
        imgs_snapshots = []
        if targets.get('imgs'):
            for index, image in enumerate((root / 'Imgs').glob(
                    f'{imgs_stem}.*')):
                snapshot = _snapshot_file(
                    image, temp_dir, f'imgs/{index}{image.suffix}')
                imgs_snapshots.append((image, snapshot))
        try:
            if targets.get('pegasus'):
                update_pegasus_game(root, index_game)
            if targets.get('gamelist'):
                update_gamelist_game(root, index_game)
            for kind, (staged, destination) in prepared.items():
                media_snapshots[kind] = _snapshot_file(
                    destination, temp_dir, f'{kind}.old')
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, destination)
                installed.append((kind, destination))
            if targets.get('imgs'):
                _sync_anbernic_cover(
                    root, filename, relative_paths['boxfront'])
        except Exception:
            for key, snapshot in snapshots.items():
                _restore_snapshot(index_paths[key], snapshot)
            for kind, destination in installed:
                _restore_snapshot(destination, media_snapshots[kind])
            if targets.get('imgs'):
                for image in (root / 'Imgs').glob(f'{imgs_stem}.*'):
                    image.unlink()
                for image, snapshot in imgs_snapshots:
                    _restore_snapshot(image, snapshot)
            raise

    _remove_unreferenced_old_media(root, original, final_paths)
    result = dict(edited)
    result['file'] = filename
    result['filename'] = filename
    result['path'] = original.get('path', str(root / filename))
    for kind, relative in relative_paths.items():
        if relative and not relative.startswith(('http://', 'https://')):
            path = Path(relative)
            result[kind] = str(path if path.is_absolute() else root / path)
        else:
            result[kind] = relative
    result['cover'] = result.get('boxfront') or result.get('logo', '')
    return result
