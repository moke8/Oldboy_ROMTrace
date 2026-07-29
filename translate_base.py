#!/usr/bin/env python3
"""翻译 Provider 统一调度函数。"""

from translate_deepseek import translate as translate_ai
from translate_google import translate as translate_google


def translate(text, target_lang, provider, configs=None, log=None):
    if not text or not target_lang or target_lang.startswith('en'):
        return text
    configs = configs or {}
    if provider == 'google':
        if log:
            return translate_google(text, target_lang, log=log)
        return translate_google(text, target_lang)
    if provider == 'ai':
        if log:
            return translate_ai(
                text, target_lang, configs.get('ai', {}), log=log)
        return translate_ai(text, target_lang, configs.get('ai', {}))
    return text
