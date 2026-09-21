#!/usr/bin/env python3
"""Nintendo Wii - 平台模块"""

import struct
import re
from pathlib import Path

from game_wii_db import WII_GAME_DB

PLATFORM_TITLE = "Nintendo Wii"
CONFIG_FILENAME = "wii_config.json"
TGDB_PLATFORM_ID = 9

COLLECTION_DEFAULTS = {
    'collection': 'Nintendo Wii',
    'shortname': 'wii',
    'extensions': 'wbfs iso wad',
}


# ===== Wii ROM 解析 =====

def _filename_title(path):
    """从文件名去掉 [ID]/(ID) 后作为显示标题。"""
    p = Path(path)
    return re.sub(r'\s*[\[\(][^\]\)]*[\]\)]', '', p.stem).strip() or p.stem


def _decode_disc_title(title_raw):
    """严格解码碟片标题；截断/非法字节返回空串，避免留下半截中文。"""
    if not title_raw:
        return ''
    for enc in ('utf-8', 'gbk', 'shift_jis'):
        try:
            title = title_raw.decode(enc).strip()
        except (UnicodeDecodeError, ValueError):
            continue
        if title:
            return title
    return ''


def _read_disc_header(f, offset=0):
    """读取 Wii/GC disc header，返回 (game_id, title)"""
    f.seek(offset)
    header = f.read(0x60)
    if len(header) < 0x60:
        return None, None
    game_id = header[0:6].decode('ascii', errors='replace').strip('\x00')
    title_raw = header[0x20:0x60].split(b'\x00', 1)[0]
    return game_id, _decode_disc_title(title_raw)


def _resolve_title_en(game_id, fallback_title):
    return WII_GAME_DB.get(game_id) or fallback_title


def extract_wii_info(file_path, lang_code='en', log=print):
    """从 Wii ROM 提取游戏 ID 和标题"""
    p = Path(file_path)
    suffix = p.suffix.lower()
    try:
        with open(file_path, 'rb') as f:
            if suffix == '.wbfs':
                magic = f.read(4)
                if magic != b'WBFS':
                    log("[游戏解析] 跳过非有效 WBFS 文件")
                    return None
                game_id, title = _read_disc_header(f, 0x200)
            elif suffix == '.iso':
                game_id, title = _read_disc_header(f, 0)
            elif suffix == '.wad':
                f.seek(0)
                wad_header = f.read(0x40)
                if len(wad_header) < 0x40:
                    return None
                header_size = struct.unpack('>I', wad_header[0x00:0x04])[0]
                cert_size = struct.unpack('>I', wad_header[0x08:0x0C])[0]
                ticket_size = struct.unpack('>I', wad_header[0x10:0x14])[0]
                tmd_size = struct.unpack('>I', wad_header[0x14:0x18])[0]
                def align64(x):
                    return (x + 63) & ~63
                tmd_offset = align64(header_size) + align64(cert_size) + align64(ticket_size)
                f.seek(tmd_offset + 0x190)
                title_id_bytes = f.read(8)
                if len(title_id_bytes) < 8:
                    return None
                game_id = title_id_bytes[4:8].decode('ascii', errors='replace').strip('\x00')
                title = _filename_title(p)
                return {
                    'title': title,
                    'title_en': title,
                    'game_id': game_id,
                    'publisher': '',
                    'filename': p.name,
                }
            else:
                return None

            if not game_id:
                return None
            if not title:
                title = _filename_title(p)

        return {
            'title': title,
            'title_en': _resolve_title_en(game_id, title),
            'game_id': game_id,
            'publisher': '',
            'filename': p.name,
        }
    except Exception as e:
        log(f"[游戏解析] Wii 解析错误: {e}")
        return None
