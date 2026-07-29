#!/usr/bin/env python3
"""生成 PS1 游戏序列号到英文游戏名的映射表。

数据来源：DuckStation 官方游戏数据库 gamedb.yaml
仓库：https://github.com/stenzek/duckstation
原始文件：https://raw.githubusercontent.com/stenzek/duckstation/master/data/resources/gamedb.yaml

选择该来源是因为 Redump 官方 DAT 仅包含光轨哈希和游戏名，不包含
SLPS、SLUS、SLES 等游戏序列号，无法直接生成序列号映射。
"""

import argparse
import ast
import re
import urllib.request
from pathlib import Path


SOURCE_URL = (
    'https://raw.githubusercontent.com/stenzek/duckstation/'
    'master/data/resources/gamedb.yaml'
)
DEFAULT_OUTPUT = Path('ps1_game_db.py')
SERIAL_PATTERN = re.compile(r'^([A-Z0-9]+-[A-Z0-9.-]+):$')


def download_database(url=SOURCE_URL):
    with urllib.request.urlopen(url) as response:
        return response.read().decode('utf-8')


def _parse_name(value):
    value = value.strip()
    if value.startswith(('"', "'")):
        return ast.literal_eval(value)
    return value


def extract_serial_map(content):
    serial_map = {}
    current_serial = None
    for line in content.splitlines():
        if line and not line[0].isspace():
            match = SERIAL_PATTERN.fullmatch(line.strip())
            current_serial = match.group(1) if match else None
            continue
        if current_serial and line.startswith('  name: '):
            name = _parse_name(line.split(':', 1)[1])
            if name:
                serial_map.setdefault(current_serial, name)
            current_serial = None
    return serial_map


def write_database(serial_map, output_path, source_name):
    lines = [
        '#!/usr/bin/env python3',
        '"""PS1 游戏序列号 → 英文游戏名映射表（自动生成，勿手动编辑）。"""',
        '',
        f'# 来源文件: {source_name}',
        '# 数据来源: DuckStation 官方游戏数据库',
        '# 项目地址: https://github.com/stenzek/duckstation',
        f'# 条目数: {len(serial_map)}',
        '',
        'PS1_GAME_DB = {',
    ]
    for serial, name in sorted(serial_map.items()):
        escaped = name.replace('\\', '\\\\').replace("'", "\\'")
        lines.append(f"    '{serial}': '{escaped}',")
    lines.extend(['}', ''])
    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='生成 PS1 游戏名称映射表')
    parser.add_argument(
        '--input', type=Path,
        help='本地 DuckStation gamedb.yaml；省略时从官方仓库下载',
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

    serial_map = extract_serial_map(content)
    write_database(serial_map, args.output, source_name)
    print(f'共提取 {len(serial_map)} 个 serial → name 映射')
    print(f'已写入 {args.output}')


if __name__ == '__main__':
    main()
