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
        if not data:
            _emit_error(log, '接口未返回译文。')
            return text
        if (not isinstance(data, list) or not isinstance(data[0], list)
                or not all(isinstance(segment, (list, tuple))
                           and segment and isinstance(segment[0], str)
                           for segment in data[0])):
            _emit_error(log, '接口响应格式无效。')
            return text
        translated = ''.join(segment[0] for segment in data[0] if segment[0])
        if not translated:
            _emit_error(log, '接口未返回译文。')
            return text
        return translated
    except HTTPError as error:
        _emit_error(log, f'接口请求失败（HTTP {error.code}）。')
    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            _emit_error(log, '请求超时。')
        else:
            _emit_error(log, f'网络连接失败：{error.reason}。')
    except TimeoutError:
        _emit_error(log, '请求超时。')
    except (TypeError, ValueError, json.JSONDecodeError):
        _emit_error(log, '接口响应格式无效。')
    except Exception:
        _emit_error(log, '请求失败。')
    return text
