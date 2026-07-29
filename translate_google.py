#!/usr/bin/env python3
"""Google 翻译函数。"""

import json
from urllib.parse import quote
from urllib.request import Request, urlopen


def translate(text, target_lang):
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
    except Exception:
        pass
    return text
