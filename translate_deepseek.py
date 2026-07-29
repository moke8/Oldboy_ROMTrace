#!/usr/bin/env python3
"""OpenAI 兼容 AI 翻译函数。"""

import json
from urllib.request import Request, urlopen


def _chat_completions_url(base_url):
    url = base_url.strip().rstrip('/')
    if url.endswith('/chat/completions'):
        return url
    if url.endswith('/v1'):
        return f'{url}/chat/completions'
    return f'{url}/v1/chat/completions'


def translate(text, target_lang, config):
    if not text:
        return text
    config = config or {}
    base_url = config.get('base_url', '').strip()
    model = config.get('model', '').strip()
    api_key = config.get('api_key', '').strip()
    if not base_url or not model or not api_key:
        return text

    payload = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': (
                    f'将用户提供的文本翻译为 {target_lang}。'
                    '只返回译文，不要添加解释或 Markdown。'
                ),
            },
            {'role': 'user', 'content': text},
        ],
    }
    request = Request(
        _chat_completions_url(base_url),
        data=json.dumps(payload).encode(),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Game-Cover-Extractor/1.0',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
        content = data['choices'][0]['message']['content'].strip()
        return content or text
    except Exception:
        return text
