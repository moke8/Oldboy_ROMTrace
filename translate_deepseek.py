#!/usr/bin/env python3
"""OpenAI 兼容 AI 翻译函数。"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _chat_completions_url(base_url):
    url = base_url.strip().rstrip('/')
    if url.endswith('/chat/completions'):
        return url
    if url.endswith('/v1'):
        return f'{url}/chat/completions'
    return f'{url}/v1/chat/completions'


def _emit_error(log, label, reason):
    if log:
        log(f'[翻译] {label}: {reason}')


def _redact(value, secret):
    text = str(value)
    return text.replace(secret, '***') if secret else text


def _http_error_reason(error, api_key):
    try:
        data = json.loads(error.read().decode())
        details = data.get('error', {})
        code = details.get('code', '')
        message = str(details.get('message', '')).strip()
    except Exception:
        code = ''
        message = ''
    if code == 'model_not_found':
        return '该模型不存在，或当前 Key 无权访问。'
    if message:
        if api_key:
            message = message.replace(api_key, '***')
        return f'接口请求失败（HTTP {error.code}）：{message}'
    return f'接口请求失败（HTTP {error.code}）。'


def translate(text, target_lang, config, log=None):
    if not text:
        return text
    model_label = 'AI 翻译'
    api_key = ''
    try:
        config = config or {}
        base_url = config.get('base_url', '').strip()
        model = config.get('model', '').strip()
        api_key = config.get('api_key', '').strip()
        model_label = model or model_label
        if not base_url or not model or not api_key:
            _emit_error(log, model_label, '缺少中转站、模型或 Key 配置。')
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
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
        content = data['choices'][0]['message']['content'].strip()
        if not content:
            _emit_error(log, model_label, '接口未返回译文。')
            return text
        return content
    except HTTPError as error:
        _emit_error(
            log, model_label, _http_error_reason(error, api_key))
        return text
    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            _emit_error(log, model_label, '请求超时。')
        else:
            reason = _redact(error.reason, api_key)
            _emit_error(log, model_label, f'网络连接失败：{reason}。')
        return text
    except TimeoutError:
        _emit_error(log, model_label, '请求超时。')
        return text
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        _emit_error(log, model_label, '接口响应格式无效。')
        return text
    except ValueError:
        _emit_error(log, model_label, '中转站地址或请求配置无效。')
        return text
    except Exception:
        _emit_error(log, model_label, '请求失败。')
        return text
