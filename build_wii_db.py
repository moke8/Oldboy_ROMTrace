#!/usr/bin/env python3
"""生成 Wii 游戏 ID 到英文游戏名的映射表。

数据来源：Dolphin 同步的 GameTDB wiitdb-en.txt
仓库：https://github.com/dolphin-emu/dolphin
原始文件：https://raw.githubusercontent.com/dolphin-emu/dolphin/master/Data/Sys/wiitdb-en.txt

Wii 零售光盘由 Redump 收录，但盒标序列号是 RVL-SMNP-USA 形式，
不能直接对应碟片头 6 位 ID。GameTDB 使用 SMNP01 这种 ID，
与 platform_wii 已解析出的 game_id 一致。
"""

import argparse
import re
import urllib.request
from pathlib import Path

from build_db_utils import clean_db_title


SOURCE_URL = (
    'https://raw.githubusercontent.com/dolphin-emu/dolphin/'
    'master/Data/Sys/wiitdb-en.txt'
)
DEFAULT_OUTPUT = Path('game_wii_db.py')
ID_PATTERN = re.compile(r'^([A-Z0-9]{6})\s*=\s*(.+)$')


def download_database(url=SOURCE_URL):
    with urllib.request.urlopen(url) as response:
        return response.read().decode('utf-8')


def extract_id_map(content):
    id_map = {}
    for line in content.splitlines():
        match = ID_PATTERN.fullmatch(line.strip())
        if not match:
            continue
        game_id, name = match.group(1), match.group(2).strip()
        if game_id == 'TITLES' or not name:
            continue
        id_map.setdefault(game_id, name)
    return id_map


def write_database(id_map, output_path, source_name):
    lines = [
        '#!/usr/bin/env python3',
        '"""Wii game_id → 英文游戏名映射表（自动生成，勿手动编辑）。"""',
        '',
        f'# 来源文件: {source_name}',
        '# 数据来源: GameTDB / Dolphin wiitdb-en.txt',
        '# 项目地址: https://www.gametdb.com',
        f'# 条目数: {len(id_map)}',
        '',
        'WII_GAME_DB = {',
    ]
    for game_id, name in sorted(id_map.items()):
        escaped = clean_db_title(name).replace('\\', '\\\\').replace(
            "'", "\\'"
        )
        lines.append(f"    '{game_id}': '{escaped}',")
    lines.extend(['}', ''])
    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='生成 Wii 游戏名称映射表')
    parser.add_argument(
        '--input', type=Path,
        help='本地 wiitdb-en.txt；省略时从 Dolphin 仓库下载',
    )
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.input:
        content = args.input.read_text(encoding='utf-8')
        source_name = args.input.name
    else:
        print(f'正在下载 {SOURCE_URL}')
        content = download_database()
        source_name = SOURCE_URL

    id_map = extract_id_map(content)
    write_database(id_map, args.output, source_name)
    print(f'共提取 {len(id_map)} 个 game_id → name 映射')
    print(f'已写入 {args.output}')


if __name__ == '__main__':
    main()
