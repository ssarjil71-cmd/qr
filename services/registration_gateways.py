import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request
from urllib.parse import urlencode
from urllib.parse import urlsplit
import logging
import re

from flask import current_app


logger = logging.getLogger(__name__)


class GatewayError(Exception):
    pass


def _json_request(url, payload=None, headers=None, basic_auth=None, method='POST', query=None):
    payload = payload or {}
    if query:
        url = f'{url}?{urlencode(query)}'
    body = json.dumps(payload).encode('utf-8') if method != 'GET' else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': 'application/json', **(headers or {})},
        method=method,
    )
    if basic_auth:
        token = base64.b64encode(f'{basic_auth[0]}:{basic_auth[1]}'.encode('utf-8')).decode('ascii')
        request.add_header('Authorization', f'Basic {token}')
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode('utf-8') or '{}'
            data = json.loads(raw)
            logger.info('External OTP request succeeded: method=%s path=%s status=%s', method, urlsplit(url).path, response.status)
            return data
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        logger.warning('External OTP request failed: method=%s status=%s response=%s', method, exc.code, _safe_error(detail))
        raise GatewayError(detail or str(exc)) from exc
    except urllib.error.URLError as exc:
        logger.warning('External OTP request failed: method=%s network_error=%s', method, _safe_error(str(exc)))
        raise GatewayError(str(exc)) from exc


def _safe_error(value):
    try:
        data = json.loads(value) if isinstance(value, str) else value
        if isinstance(data, dict):
            return str(data.get('message') or data.get('type') or 'request failed')[:240]
    except (TypeError, ValueError):
        pass
    return re.sub(r'(?i)(authkey|authorization|otp|mobile)\s*[:=]\s*[^,\s}]+', r'\1=[redacted]', str(value))[:240]


def _provider_message(data, fallback):
    message = data.get('message') if isinstance(data, dict) else None
    return _safe_error(message or fallback)


def normalize_mobile(mobile):
    digits = re.sub(r'\D', '', str(mobile or ''))
    if len(digits) == 10:
        digits = f'91{digits}'
    if len(digits) != 12 or not digits.startswith('91'):
        raise GatewayError('Enter a valid Indian mobile number with country code')
    return digits


class SurepassGateway:
    @staticmethod
    def send_otp(mobile):
        api_key = current_app.config.get('SUREPASS_API_KEY')
        if not api_key:
            if current_app.debug:
                return {'client_id': 'debug-surepass-client', 'debug': True}
            raise GatewayError('Surepass is not configured')
        base_url = current_app.config.get('SUREPASS_API_BASE', '').rstrip('/')
        url = f'{base_url}/api/v1/telecom/generate-otp'
        data = _json_request(url, {'mobile_number': mobile}, headers={'Authorization': f'Bearer {api_key}'})
        client_id = data.get('data', {}).get('client_id') or data.get('client_id')
        if not client_id:
            raise GatewayError('Surepass did not return an OTP client id')
        return {'client_id': client_id, 'raw': data}

    @staticmethod
    def verify_otp(client_id, otp):
        api_key = current_app.config.get('SUREPASS_API_KEY')
        if not api_key:
            if current_app.debug and otp == '111111':
                return {'verified': True, 'debug': True}
            raise GatewayError('Surepass is not configured')
        base_url = current_app.config.get('SUREPASS_API_BASE', '').rstrip('/')
        url = f'{base_url}/api/v1/telecom/submit-otp'
        data = _json_request(
            url,
            {'client_id': client_id, 'otp': otp},
            headers={'Authorization': f'Bearer {api_key}'},
        )
        status = str(data.get('status') or data.get('data', {}).get('status') or '').lower()
        verified = data.get('success') is True or status in ('success', 'verified', 'completed')
        if not verified:
            raise GatewayError('OTP verification failed')
        return {'verified': True, 'raw': data}


class MSG91Gateway:
    @staticmethod
    def send_sms(mobile, message):
        auth_key = current_app.config.get('MSG91_AUTH_KEY')
        if not auth_key:
            raise GatewayError('MSG91 is not configured')
        mobile = normalize_mobile(mobile)
        base_url = current_app.config.get('MSG91_OTP_BASE', 'https://control.msg91.com/api/v5/otp').rstrip('/')
        data = _json_request(
            f'{base_url}/send',
            {'message': message, 'mobile': mobile, 'sender': current_app.config.get('MSG91_SENDER_ID', ''), 'route': '4'},
            headers={'authkey': auth_key},
            method='POST',
        )
        if str(data.get('type', '')).lower() not in ('success', 'successfully'):
            raise GatewayError(_provider_message(data, 'MSG91 rejected the SMS request'))
        return {'sent': True, 'raw': data}

    @staticmethod
    def send_otp(mobile):
        auth_key = current_app.config.get('MSG91_AUTH_KEY')
        template_id = current_app.config.get('MSG91_OTP_TEMPLATE_ID')
        if not auth_key or not template_id:
            raise GatewayError('MSG91 is not configured')
        mobile = normalize_mobile(mobile)
        base_url = current_app.config.get('MSG91_OTP_BASE', 'https://control.msg91.com/api/v5/otp').rstrip('/')
        data = _json_request(
            base_url,
            {'template_id': template_id, 'mobile': mobile, 'otp_length': 4, 'otp_expiry': 10},
            headers={'authkey': auth_key},
        )
        if str(data.get('type', '')).lower() not in ('success', 'successfully'):
            raise GatewayError(_provider_message(data, 'MSG91 rejected the OTP request'))
        request_id = data.get('request_id') or data.get('requestId')
        if not request_id:
            raise GatewayError('MSG91 did not return an OTP request ID')
        return {'request_id': request_id, 'raw': data}

    @staticmethod
    def resend_otp(mobile):
        auth_key = current_app.config.get('MSG91_AUTH_KEY')
        if not auth_key:
            raise GatewayError('MSG91 is not configured')
        mobile = normalize_mobile(mobile)
        base_url = current_app.config.get('MSG91_OTP_BASE', 'https://control.msg91.com/api/v5/otp').rstrip('/')
        data = _json_request(
            f'{base_url}/retry',
            method='GET',
            query={'authkey': auth_key, 'retrytype': 'text', 'mobile': mobile},
            headers={'authkey': auth_key},
        )
        if str(data.get('type', '')).lower() not in ('success', 'successfully'):
            raise GatewayError(_provider_message(data, 'MSG91 rejected the resend request'))
        request_id = data.get('request_id') or data.get('requestId')
        if not request_id:
            raise GatewayError('MSG91 did not return an OTP request ID')
        return {'request_id': request_id, 'raw': data}

    @staticmethod
    def verify_otp(mobile, otp):
        auth_key = current_app.config.get('MSG91_AUTH_KEY')
        if not auth_key:
            raise GatewayError('MSG91 is not configured')
        mobile = normalize_mobile(mobile)
        if not str(otp or '').strip().isdigit():
            raise GatewayError('Enter the OTP received by SMS')
        base_url = current_app.config.get('MSG91_OTP_BASE', 'https://control.msg91.com/api/v5/otp').rstrip('/')
        data = _json_request(
            f'{base_url}/verify',
            method='GET',
            query={'mobile': mobile, 'otp': str(otp).strip()},
            headers={'authkey': auth_key},
        )
        if str(data.get('type', '')).lower() not in ('success', 'successfully'):
            raise GatewayError(_provider_message(data, 'OTP verification failed'))
        return {'verified': True, 'raw': data}


class RazorpayGateway:
    @staticmethod
    def create_order(amount_paise, receipt):
        key_id = current_app.config.get('RAZORPAY_KEY_ID')
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
        if not key_id or not key_secret:
            if current_app.debug:
                return {'id': f'order_debug_{receipt}', 'amount': amount_paise, 'currency': 'INR'}
            raise GatewayError('Razorpay is not configured')
        return _json_request(
            'https://api.razorpay.com/v1/orders',
            {
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': receipt,
                'payment_capture': 1,
            },
            basic_auth=(key_id, key_secret),
        )

    @staticmethod
    def verify_signature(order_id, payment_id, signature):
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
        if not key_secret:
            if current_app.debug and str(payment_id).startswith('pay_debug_'):
                return True
            raise GatewayError('Razorpay is not configured')
        payload = f'{order_id}|{payment_id}'.encode('utf-8')
        digest = hmac.new(key_secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature or '')
