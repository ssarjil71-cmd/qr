from unittest.mock import patch
from app import create_app

app = create_app()
client = app.test_client()
with client.session_transaction() as sess:
    sess['registration_payment_token'] = 'abc'
    sess['registration_payment_user_type'] = 'student'

fake_attempt = {
    'user_type': 'student',
    'otp_status': 'verified',
    'payment_status': 'paid',
    'mobile': '9876543210',
    'amount_rupees': 1,
}

with patch('routes.auth_routes.RegistrationPaymentModel.get_attempt', return_value=fake_attempt):
    resp = client.get('/register/student')
    html = resp.get_data(as_text=True)
    checks = {
        'status': resp.status_code,
        'modal': 'legalModalBackdrop' in html,
        'terms_button': 'data-legal-target="terms"' in html,
        'privacy_button': 'data-legal-target="privacy"' in html,
        'close_button': 'legal-modal-close' in html,
        'submit_disabled': 'id="submitRegistration" disabled' in html,
        'no_direct_terms_link': 'auth.terms_and_conditions' not in html,
        'checkbox_required': 'id="terms" name="terms_accepted" required' in html,
    }
    for name, value in checks.items():
        print(f'{name}={value}')
