import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request

from flask import current_app


class GatewayError(Exception):
    pass


def _json_request(url, payload, headers=None, basic_auth=None):
    body = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': 'application/json', **(headers or {})},
        method='POST',
    )
    if basic_auth:
        token = base64.b64encode(f'{basic_auth[0]}:{basic_auth[1]}'.encode('utf-8')).decode('ascii')
        request.add_header('Authorization', f'Basic {token}')
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise GatewayError(detail or str(exc)) from exc
    except urllib.error.URLError as exc:
        raise GatewayError(str(exc)) from exc


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
    def send_otp(mobile):
        # Temporary testing logic: keep this isolated so it can be replaced
        # with the real MSG91 send OTP API without touching registration flow.
        auth_key = current_app.config.get('MSG91_AUTH_KEY')
        template_id = current_app.config.get('MSG91_OTP_TEMPLATE_ID')
        if not auth_key or not template_id:
            return {'request_id': 'test-msg91-otp', 'debug': True}
        return {'request_id': 'test-msg91-otp', 'debug': True}

    @staticmethod
    def resend_otp(mobile):
        return MSG91Gateway.send_otp(mobile)

    @staticmethod
    def verify_otp(mobile, otp):
        test_otp = current_app.config.get('REGISTRATION_TEST_OTP', '1111')
        if str(otp).strip() != test_otp:
            raise GatewayError('Invalid OTP. Use temporary testing OTP 1111.')
        return {'verified': True, 'debug': True}


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
