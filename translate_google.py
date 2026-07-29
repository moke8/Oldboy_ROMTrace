#!/usr/bin/env python3
"""Google 翻译函数。"""

import json
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _emit_error(log, reason):
    if log:
        log(f'[翻译] Google 翻译: {reason}')


def translate(text, target_lang, log=None):
    if not text or target_lang.startswith('en'):
        return text
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=auto&tl={target_lang}&dt=t"
        f"&q={quote(text[:4000])}"
    )
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode())
        if data and isinstance(data, list) and data[0]:
            return ''.join(segment[0] for segment in data[0] if segment[0])
    except HTTPError as error:
        _emit_error(log, f'接口请求失败（HTTP {error.code}）。')
    except URLError as error:
        _emit_error(log, f'网络连接失败：{error.reason}。')
    except TimeoutError:
        _emit_error(log, '请求超时。')
    except (TypeError, ValueError, json.JSONDecodeError):
        _emit_error(log, '接口响应格式无效。')
    except Exception:
        _emit_error(log, '请求失败。')
    return text
