from app import create_app
from routes import auth_routes
from models.user import UserModel


auth_routes.MSG91Gateway.send_otp = lambda mobile: {'status': 'success'}
auth_routes.MSG91Gateway.verify_otp = lambda mobile, otp: None

UserModel.find_accounts_by_mobile = staticmethod(lambda mobile: [
    {'id': 1, 'name': 'Alice', 'email': 'alice@example.com', 'user_type': 'student', 'is_active': 1},
    {'id': 2, 'name': 'Bob', 'email': 'bob@example.com', 'user_type': 'employee', 'is_active': 1},
])
UserModel.update_password_by_id = staticmethod(lambda user_id, new_password: print('RESET_ID', user_id, new_password))

app = create_app()
app.config['TESTING'] = True

with app.test_client() as client:
    r = client.post('/forgot-password', data={'mobile': '9876543210'}, follow_redirects=False)
    print('forgot', r.status_code, r.headers.get('Location'))
    assert r.status_code == 302

    r = client.post('/forgot-password/verify', data={'otp': '123456'}, follow_redirects=False)
    print('verify', r.status_code, r.headers.get('Location'))
    assert '/forgot-password/select-account' in (r.headers.get('Location') or '')

    r = client.post('/forgot-password/select-account', data={'account_id': '2'}, follow_redirects=False)
    print('select', r.status_code, r.headers.get('Location'))
    assert '/forgot-password/reset' in (r.headers.get('Location') or '')

    r = client.post('/forgot-password/reset', data={'new_password': 'secret123', 'confirm_password': 'secret123'}, follow_redirects=False)
    print('reset', r.status_code, r.headers.get('Location'))
    assert '/login' in (r.headers.get('Location') or '')

UserModel.find_accounts_by_mobile = staticmethod(lambda mobile: [
    {'id': 3, 'name': 'Carol', 'email': 'carol@example.com', 'user_type': 'admin', 'is_active': 1},
])

with app.test_client() as client:
    r = client.post('/forgot-password', data={'mobile': '9876543211'}, follow_redirects=False)
    assert r.status_code == 302

    r = client.post('/forgot-password/verify', data={'otp': '654321'}, follow_redirects=False)
    print('single', r.status_code, r.headers.get('Location'))
    assert '/forgot-password/reset' in (r.headers.get('Location') or '')

print('forgot_password_flow_ok')
