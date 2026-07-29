import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import translate_base
import translate_deepseek
import translate_google


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self._data).encode()


class GoogleTranslateTests(unittest.TestCase):
    def test_uses_automatic_source_detection(self):
        requests = []

        def fake_urlopen(request, timeout):
            requests.append((request, timeout))
            return _FakeResponse([[['宝可梦 心金', None]]])

        with patch('translate_google.urlopen', side_effect=fake_urlopen):
            result = translate_google.translate(
                'ポケットモンスター ハートゴールド', 'zh-CN')

        query = parse_qs(urlsplit(requests[0][0].full_url).query)
        self.assertEqual(query['sl'], ['auto'])
        self.assertEqual(query['tl'], ['zh-CN'])
        self.assertEqual(result, '宝可梦 心金')


class DeepSeekTranslateTests(unittest.TestCase):
    def test_builds_openai_compatible_request(self):
        requests = []

        def fake_urlopen(request, timeout):
            requests.append((request, timeout))
            return _FakeResponse({
                'choices': [{'message': {'content': '中文译文'}}],
            })

        config = {
            'base_url': 'https://api.example.com/v1',
            'model': 'deepseek-chat',
            'api_key': 'secret-key',
        }
        with patch('translate_deepseek.urlopen', side_effect=fake_urlopen):
            result = translate_deepseek.translate('English text', 'zh-CN', config)

        request, timeout = requests[0]
        payload = json.loads(request.data.decode())
        self.assertEqual(
            request.full_url,
            'https://api.example.com/v1/chat/completions',
        )
        self.assertEqual(request.get_header('Authorization'), 'Bearer secret-key')
        self.assertEqual(payload['model'], 'deepseek-chat')
        self.assertIn('zh-CN', payload['messages'][0]['content'])
        self.assertEqual(payload['messages'][1]['content'], 'English text')
        self.assertEqual(timeout, 30)
        self.assertEqual(result, '中文译文')

    def test_accepts_complete_chat_completions_url(self):
        requests = []

        def fake_urlopen(request, timeout):
            requests.append(request)
            return _FakeResponse({
                'choices': [{'message': {'content': '译文'}}],
            })

        config = {
            'base_url': 'https://relay.example.com/chat/completions',
            'model': 'model-name',
            'api_key': 'key',
        }
        with patch('translate_deepseek.urlopen', side_effect=fake_urlopen):
            translate_deepseek.translate('text', 'zh-CN', config)

        self.assertEqual(
            requests[0].full_url,
            'https://relay.example.com/chat/completions',
        )

    def test_root_url_adds_v1_chat_completions_path(self):
        requests = []

        def fake_urlopen(request, timeout):
            requests.append(request)
            return _FakeResponse({
                'choices': [{'message': {'content': '译文'}}],
            })

        config = {
            'base_url': 'https://relay.example.com',
            'model': 'model-name',
            'api_key': 'key',
        }
        with patch('translate_deepseek.urlopen', side_effect=fake_urlopen):
            translate_deepseek.translate('text', 'zh-CN', config)

        self.assertEqual(
            requests[0].full_url,
            'https://relay.example.com/v1/chat/completions',
        )

    def test_missing_config_returns_original_text(self):
        self.assertEqual(
            translate_deepseek.translate('Original', 'zh-CN', {}),
            'Original',
        )

    def test_invalid_response_returns_original_text(self):
        with patch(
                'translate_deepseek.urlopen',
                return_value=_FakeResponse({'choices': []})):
            result = translate_deepseek.translate('Original', 'zh-CN', {
                'base_url': 'https://api.example.com',
                'model': 'model-name',
                'api_key': 'key',
            })

        self.assertEqual(result, 'Original')

    def test_invalid_base_url_returns_original_text(self):
        result = translate_deepseek.translate('Original', 'zh-CN', {
            'base_url': 'not a url',
            'model': 'model-name',
            'api_key': 'key',
        })

        self.assertEqual(result, 'Original')


class TranslateDispatcherTests(unittest.TestCase):
    def test_off_returns_original_without_provider_call(self):
        with patch('translate_base.translate_google') as google_mock:
            result = translate_base.translate(
                'Original', 'zh-CN', 'off', {'google': {}})

        self.assertEqual(result, 'Original')
        google_mock.assert_not_called()

    def test_google_dispatches_to_google_provider(self):
        with patch('translate_base.translate_google', return_value='译文') as mock:
            result = translate_base.translate(
                'Original', 'zh-CN', 'google', {'google': {'unused': True}})

        mock.assert_called_once_with('Original', 'zh-CN')
        self.assertEqual(result, '译文')

    def test_ai_dispatches_with_ai_config(self):
        configs = {'ai': {'model': 'deepseek-chat'}}
        with patch('translate_base.translate_ai', return_value='译文') as mock:
            result = translate_base.translate('Original', 'zh-CN', 'ai', configs)

        mock.assert_called_once_with('Original', 'zh-CN', configs['ai'])
        self.assertEqual(result, '译文')

    def test_unknown_provider_returns_original(self):
        self.assertEqual(
            translate_base.translate('Original', 'zh-CN', 'unknown', {}),
            'Original',
        )

    def test_english_target_skips_all_providers(self):
        with (
            patch('translate_base.translate_google') as google_mock,
            patch('translate_base.translate_ai') as ai_mock,
        ):
            google_result = translate_base.translate(
                'Original', 'en', 'google', {'google': {}})
            ai_result = translate_base.translate(
                'Original', 'en-US', 'ai', {'ai': {'api_key': 'key'}})

        self.assertEqual(google_result, 'Original')
        self.assertEqual(ai_result, 'Original')
        google_mock.assert_not_called()
        ai_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
