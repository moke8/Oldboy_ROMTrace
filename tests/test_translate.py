import json
import io
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
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

    def test_network_error_logs_readable_reason(self):
        messages = []

        with patch(
                'translate_google.urlopen',
                side_effect=URLError('connection refused')):
            result = translate_google.translate(
                'Original', 'zh-CN', log=messages.append)

        self.assertEqual(result, 'Original')
        self.assertEqual(messages, [
            '[翻译] Google 翻译: 网络连接失败：connection refused。',
        ])

    def test_empty_response_logs_missing_translation(self):
        messages = []
        with patch(
                'translate_google.urlopen',
                return_value=_FakeResponse([])):
            result = translate_google.translate(
                'Original', 'zh-CN', log=messages.append)

        self.assertEqual(result, 'Original')
        self.assertEqual(messages, [
            '[翻译] Google 翻译: 接口未返回译文。',
        ])

    def test_invalid_response_does_not_produce_garbage_translation(self):
        messages = []
        with patch(
                'translate_google.urlopen',
                return_value=_FakeResponse([{'error': 'x'}])):
            result = translate_google.translate(
                'Original', 'zh-CN', log=messages.append)

        self.assertEqual(result, 'Original')
        self.assertEqual(messages, [
            '[翻译] Google 翻译: 接口响应格式无效。',
        ])


class DeepSeekTranslateTests(unittest.TestCase):
    def test_model_not_found_logs_readable_reason_without_key(self):
        error_body = json.dumps({
            'error': {
                'message': (
                    'The model `MiniMax-M2.7` does not exist or you do not '
                    'have access to it.'),
                'code': 'model_not_found',
            },
        }).encode()
        http_error = HTTPError(
            'https://api.example.com/v1/chat/completions',
            404,
            'Not Found',
            {},
            io.BytesIO(error_body),
        )
        messages = []
        config = {
            'base_url': 'https://api.example.com/v1',
            'model': 'MiniMax-M2.7',
            'api_key': 'super-secret-key',
        }

        with patch('translate_deepseek.urlopen', side_effect=http_error):
            result = translate_deepseek.translate(
                'English description', 'zh-CN', config, log=messages.append)

        self.assertEqual(result, 'English description')
        self.assertEqual(messages, [
            '[翻译] MiniMax-M2.7: 该模型不存在，或当前 Key 无权访问。',
        ])
        self.assertNotIn('super-secret-key', '\n'.join(messages))

    def test_missing_config_logs_specific_reason(self):
        messages = []

        result = translate_deepseek.translate(
            'Original', 'zh-CN', {}, log=messages.append)

        self.assertEqual(result, 'Original')
        self.assertEqual(messages, [
            '[翻译] AI 翻译: 缺少中转站、模型或 Key 配置。',
        ])

    def test_network_error_logs_specific_reason(self):
        messages = []
        config = {
            'base_url': 'https://api.example.com/v1',
            'model': 'model-name',
            'api_key': 'key',
        }

        with patch(
                'translate_deepseek.urlopen',
                side_effect=URLError('connection refused')):
            result = translate_deepseek.translate(
                'Original', 'zh-CN', config, log=messages.append)

        self.assertEqual(result, 'Original')
        self.assertEqual(messages, [
            '[翻译] model-name: 网络连接失败：connection refused。',
        ])

    def test_wrapped_timeout_is_logged_as_timeout(self):
        messages = []
        config = {
            'base_url': 'https://api.example.com/v1',
            'model': 'model-name',
            'api_key': 'key',
        }
        with patch(
                'translate_deepseek.urlopen',
                side_effect=URLError(TimeoutError('timed out'))):
            translate_deepseek.translate(
                'Original', 'zh-CN', config, log=messages.append)

        self.assertEqual(messages, ['[翻译] model-name: 请求超时。'])

    def test_network_error_redacts_key_from_reason(self):
        messages = []
        config = {
            'base_url': 'https://api.example.com/v1',
            'model': 'model-name',
            'api_key': 'leak-me',
        }
        with patch(
                'translate_deepseek.urlopen',
                side_effect=URLError('connection failed leak-me')):
            translate_deepseek.translate(
                'Original', 'zh-CN', config, log=messages.append)

        self.assertEqual(messages, [
            '[翻译] model-name: 网络连接失败：connection failed ***。',
        ])

    def test_empty_ai_content_logs_missing_translation(self):
        messages = []
        config = {
            'base_url': 'https://api.example.com/v1',
            'model': 'model-name',
            'api_key': 'key',
        }
        with patch('translate_deepseek.urlopen', return_value=_FakeResponse({
                'choices': [{'message': {'content': '  '}}]})):
            result = translate_deepseek.translate(
                'Original', 'zh-CN', config, log=messages.append)

        self.assertEqual(result, 'Original')
        self.assertEqual(messages, [
            '[翻译] model-name: 接口未返回译文。',
        ])

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

    def test_ai_dispatches_log_callback(self):
        configs = {'ai': {'model': 'deepseek-chat'}}
        logger = Mock()
        with patch('translate_base.translate_ai', return_value='译文') as mock:
            translate_base.translate(
                'Original', 'zh-CN', 'ai', configs, log=logger)

        mock.assert_called_once_with(
            'Original', 'zh-CN', configs['ai'], log=logger)

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
