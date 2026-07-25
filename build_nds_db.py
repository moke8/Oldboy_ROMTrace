#!/usr/bin/env python3
"""从 No-Intro NDS DAT 提取 Game Code → 游戏名映射。"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_INPUT = Path(
    'Nintendo - Nintendo DS (Decrypted) (20260724-122857).dat'
)
DEFAULT_OUTPUT = Path('nds_game_db.py')


def extract_serial_map(input_path):
    root = ET.parse(input_path).getroot()
    serial_map = {}
    for game in root.iter('game'):
        name = game.get('name', '')
        if not name:
            continue
        for rom in game.iter('rom'):
            serial = rom.get('serial', '')
            if (len(serial) == 4 and serial.isalnum()
                    and serial not in serial_map):
                serial_map[serial] = name
    return serial_map


def write_database(serial_map, output_path, source_name):
    lines = [
        '#!/usr/bin/env python3',
        '"""NDS game_code(serial) → 完整游戏名映射表（自动生成，勿手动编辑）。"""',
        '',
        f'# 来源: {source_name}',
        f'# 条目数: {len(serial_map)}',
        '',
        'NDS_GAME_DB = {',
    ]
    for serial, name in sorted(serial_map.items()):
        escaped = name.replace('\\', '\\\\').replace("'", "\\'")
        lines.append(f"    '{serial}': '{escaped}',")
    lines.extend(['}', ''])
    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='生成 NDS Game Code 映射表')
    parser.add_argument('input', nargs='?', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('output', nargs='?', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    serial_map = extract_serial_map(args.input)
    write_database(serial_map, args.output, args.input.name)
    print(f'共提取 {len(serial_map)} 个 serial → name 映射')
    print(f'已写入 {args.output}')


if __name__ == '__main__':
    main()
