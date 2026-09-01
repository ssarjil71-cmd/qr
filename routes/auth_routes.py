from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file, abort
import werkzeug
import time
from datetime import date
from models.user import UserModel
from models.registration import RegistrationModel
from models.registration_payment import RegistrationPaymentModel
from models.student_profile import StudentProfileModel
from models.employee_profile import EmployeeProfileModel
from services.db import get_db
from services.profile_engine import ProfileEngine
from services.qrcode_service import generate_qr_for_user, render_premium_card
from services.registration_gateways import GatewayError, MSG91Gateway, RazorpayGateway, normalize_mobile
from models.card_permission import CardPermissionModel
from models.qr_identity import QRIdentityModel
from services.subscription_service import SubscriptionService
import os
import secrets
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')


REGISTRATION_TYPE_ROUTES = {
    'student': 'auth.register_student',
    'employee': 'auth.register_employee',
    'general_user': 'auth.register_general',
    'organization': 'auth.register_organization',
}

REGISTRATION_USER_TYPE_MAP = {
    'student': ('student', 'student'),
    'employee': ('employee', 'employee'),
    'general_user': ('emergency', 'general_user'),
    'organization': ('employee', 'organization'),
}


def _get_profile_completion(user):
    if not user:
        return 0

    basic_info = bool(user[2] and user[3] and user[4])
    contact_info = bool(user[3] and user[4] and user[17])
    emergency_info = bool(user[14])
    profile_photo = bool(user[6])
    category_details = bool(user[6] or user[7] or user[8] or user[9] or user[10] or user[11] or user[12] or user[13] or user[15] or user[16] or user[18] or user[19] or user[20])
    documents = bool(user[8] or user[9] or user[10])

    completed = sum([
        basic_info * 20,
        contact_info * 20,
        emergency_info * 15,
        profile_photo * 10,
        category_details * 20,
        documents * 15,
    ])
    return min(100, completed)


def _get_profile_checklist(user):
    complete_profile_url = url_for('auth.complete_profile')
    return [
        {
            'label': 'Basic Information',
            'done': bool(user[2] and user[3] and user[4]),
            'detail': 'Name, mobile, and email',
            'view_url': f'{complete_profile_url}#basic-information',
            'edit_url': f'{complete_profile_url}#basic-information',
        },
        {
            'label': 'Contact Information',
            'done': bool(user[3] and user[4] and user[17]),
            'detail': 'Contact details and address',
            'view_url': f'{complete_profile_url}#contact-information',
            'edit_url': f'{complete_profile_url}#contact-information',
        },
        {
            'label': 'Emergency Information',
            'done': bool(user[14]),
            'detail': 'Emergency contact saved',
            'view_url': f'{complete_profile_url}#emergency-information',
            'edit_url': f'{complete_profile_url}#emergency-information',
        },
        {
            'label': 'Profile Photo',
            'done': bool(user[6]),
            'detail': 'Photo uploaded',
            'view_url': f'{complete_profile_url}#profile-photo',
            'edit_url': f'{complete_profile_url}#profile-photo',
        },
        {
            'label': 'Category Details',
            'done': bool(user[6] or user[7] or user[8] or user[9] or user[10] or user[11] or user[12] or user[13] or user[15] or user[16] or user[18] or user[19] or user[20]),
            'detail': 'Role-specific profile details',
            'view_url': f'{complete_profile_url}#professional-information',
            'edit_url': f'{complete_profile_url}#professional-information',
        },
        {
            'label': 'Documents',
            'done': bool(user[8] or user[9] or user[10]),
            'detail': 'Resume, certificates or files uploaded',
            'view_url': f'{complete_profile_url}#uploads',
            'edit_url': f'{complete_profile_url}#uploads',
        },
    ]


def _create_public_user(user_type, full_name, mobile, email, password):
    uid = UserModel.create(
        {
            'user_type': user_type,
            'name': full_name,
            'mobile': mobile,
            'email': email,
            'password': password,
            'photo': None,
            'education': None,
            'skills': None,
            'resume': None,
            'certificates': None,
            'company_name': None,
            'designation': None,
            'experience': None,
            'emergency_contact': None,
            'blood_group': None,
            'medical_notes': None,
            'address': None,
            'vehicle_number': None,
            'qr_token': None,
            'qr_path': None,
        }
    )
    CardPermissionModel.set_user_card_type(uid, user_type)
    CardPermissionModel.assign_defaults_for_user(uid)
    return uid


def _clear_forgot_password_session():
    for key in [
        'forgot_password_mobile',
        'forgot_password_verified',
        'forgot_password_otp_time',
        'forgot_password_account_id',
        'forgot_password_accounts',
    ]:
        session.pop(key, None)


def _normalize_forgot_password_accounts(accounts):
    normalized = []
    for account in accounts or []:
        if hasattr(account, 'keys'):
            item = dict(account)
            normalized.append({
                'id': item.get('id'),
                'name': item.get('name') or 'Unknown User',
                'email': item.get('email') or 'No email',
                'user_type': item.get('user_type') or 'user',
                'is_active': item.get('is_active', True),
            })
            continue

        row = list(account) if isinstance(account, (list, tuple)) else []
        normalized.append({
            'id': row[0] if len(row) > 0 else getattr(account, 'id', None),
            'name': row[1] if len(row) > 1 else getattr(account, 'name', 'Unknown User') or 'Unknown User',
            'email': row[2] if len(row) > 2 else getattr(account, 'email', 'No email') or 'No email',
            'user_type': row[3] if len(row) > 3 else getattr(account, 'user_type', 'user') or 'user',
            'is_active': row[4] if len(row) > 4 else getattr(account, 'is_active', True),
        })
    return normalized


@auth_bp.route('/register/select')
def register_select():
    return render_template('auth/register_select.html', pricing=RegistrationPaymentModel.list_pricing())


@auth_bp.route('/register/start/<user_type>')
def register_start(user_type):
    user_type = RegistrationPaymentModel.normalize_user_type(user_type)
    if not user_type:
        abort(404)
    amount = RegistrationPaymentModel.get_price(user_type)
    if amount is None:
        flash('Registration pricing is not active for this user type', 'warning')
        return redirect(url_for('auth.register_select'))
    token = secrets.token_urlsafe(32)
    session['registration_payment_token'] = token
    session['registration_payment_user_type'] = user_type
    return redirect(url_for('auth.registration_mobile'))


@auth_bp.route('/register/mobile', methods=['GET', 'POST'])
def registration_mobile():
    token = session.get('registration_payment_token')
    user_type = RegistrationPaymentModel.normalize_user_type(session.get('registration_payment_user_type'))
    if not token or not user_type:
        return redirect(url_for('auth.register_select'))
    amount = RegistrationPaymentModel.get_price(user_type)
    if amount is None:
        flash('Registration pricing is not active for this user type', 'warning')
        return redirect(url_for('auth.register_select'))
    if request.method == 'POST':
        mobile = (request.form.get('mobile') or '').strip()
        if not mobile:
            flash('Mobile number is required', 'warning')
            return redirect(url_for('auth.registration_mobile'))
        try:
            mobile = normalize_mobile(mobile)
            otp_response = MSG91Gateway.send_otp(mobile)
        except GatewayError as exc:
            return render_template(
                'auth/register_mobile.html',
                user_type=user_type,
                user_label=RegistrationPaymentModel.LABELS[user_type],
                amount=amount,
                status='Mobile Number',
                error_message=str(exc),
            )
        RegistrationPaymentModel.create_attempt(token, user_type, mobile, amount)
        RegistrationPaymentModel.update_attempt(
            token,
            otp_status='sent',
            surepass_client_id=otp_response.get('request_id'),
            status='otp_sent',
            metadata={'otp_sent': True, 'provider': 'msg91'},
        )
        flash('OTP sent successfully', 'success')
        return redirect(url_for('auth.registration_verify_otp'))
    return render_template(
        'auth/register_mobile.html',
        user_type=user_type,
        user_label=RegistrationPaymentModel.LABELS[user_type],
        amount=amount,
        status='Mobile Number',
    )


@auth_bp.route('/register/verify-mobile', methods=['GET', 'POST'])
def registration_verify_otp():
    token = session.get('registration_payment_token')
    attempt = RegistrationPaymentModel.get_attempt(token) if token else None
    if not attempt:
        return redirect(url_for('auth.register_select'))
    if request.method == 'POST':
        otp = (request.form.get('otp') or '').strip()
        if not otp:
            flash('OTP is required', 'warning')
            return redirect(url_for('auth.registration_verify_otp'))
        try:
            MSG91Gateway.verify_otp(attempt.get('mobile'), otp)
        except GatewayError as exc:
            RegistrationPaymentModel.update_attempt(token, otp_status='failed', status='otp_failed')
            return render_template(
                'auth/register_verify_payment_otp.html',
                attempt=attempt,
                user_label=RegistrationPaymentModel.LABELS[attempt['user_type']],
                error_message=str(exc),
            )
        RegistrationPaymentModel.update_attempt(token, otp_status='verified', status='otp_verified')
        flash('OTP verified successfully', 'success')
        return redirect(url_for('auth.registration_payment'))
    return render_template(
        'auth/register_verify_payment_otp.html',
        attempt=attempt,
        user_label=RegistrationPaymentModel.LABELS[attempt['user_type']],
    )


@auth_bp.route('/register/resend-otp', methods=['POST'])
def registration_resend_otp():
    token = session.get('registration_payment_token')
    attempt = RegistrationPaymentModel.get_attempt(token) if token else None
    if not attempt:
        return redirect(url_for('auth.register_select'))
    if attempt['otp_status'] == 'verified':
        flash('Mobile number is already verified', 'info')
        return redirect(url_for('auth.registration_payment'))
    try:
        otp_response = MSG91Gateway.resend_otp(attempt['mobile'])
    except GatewayError as exc:
        return render_template(
            'auth/register_verify_payment_otp.html',
            attempt=attempt,
            user_label=RegistrationPaymentModel.LABELS[attempt['user_type']],
            error_message=str(exc),
        )
    RegistrationPaymentModel.update_attempt(
        token,
        otp_status='sent',
        surepass_client_id=otp_response.get('request_id'),
        status='otp_sent',
        metadata={'otp_resent': True, 'provider': 'msg91'},
    )
    flash('OTP resent successfully', 'success')
    return redirect(url_for('auth.registration_verify_otp'))


@auth_bp.route('/register/payment')
def registration_payment():
    token = session.get('registration_payment_token')
    attempt = RegistrationPaymentModel.get_attempt(token) if token else None
    if not attempt:
        return redirect(url_for('auth.register_select'))
    if attempt['otp_status'] != 'verified':
        flash('Verify OTP before payment', 'warning')
        return redirect(url_for('auth.registration_verify_otp'))
    if attempt['payment_status'] == 'paid':
        return redirect(url_for(REGISTRATION_TYPE_ROUTES[attempt['user_type']]))
    return render_template(
        'auth/register_payment.html',
        attempt=attempt,
        user_label=RegistrationPaymentModel.LABELS[attempt['user_type']],
        razorpay_key_id=current_app.config.get('RAZORPAY_KEY_ID', ''),
    )


@auth_bp.route('/register/payment/create-order', methods=['POST'])
def registration_create_order():
    token = session.get('registration_payment_token')
    attempt = RegistrationPaymentModel.get_attempt(token) if token else None
    if not attempt or attempt['otp_status'] != 'verified':
        return {'ok': False, 'message': 'OTP verification required'}, 403
    if attempt['payment_status'] == 'paid':
        return {'ok': True, 'order_id': attempt['razorpay_order_id'], 'amount': attempt['amount_paise'], 'already_paid': True}

    current_amount = RegistrationPaymentModel.get_price(attempt['user_type'])
    if current_amount is None or int(round(current_amount * 100)) != attempt['amount_paise']:
        return {'ok': False, 'message': 'Registration price changed. Please restart registration.'}, 409

    if attempt['razorpay_order_id']:
        return {'ok': True, 'order_id': attempt['razorpay_order_id'], 'amount': attempt['amount_paise']}

    try:
        order = RazorpayGateway.create_order(attempt['amount_paise'], f'reg_{attempt["id"]}')
    except GatewayError as exc:
        return {'ok': False, 'message': str(exc)}, 502

    order_id = order.get('id') if isinstance(order, dict) else None
    if not order_id:
        return {'ok': False, 'message': 'Razorpay did not return a valid order ID.'}, 502

    RegistrationPaymentModel.update_attempt(
        token,
        razorpay_order_id=order_id,
        payment_status='pending',
        status='payment_pending',
    )
    return {'ok': True, 'order_id': order_id, 'amount': attempt['amount_paise']}


@auth_bp.route('/register/payment/verify', methods=['POST'])
def registration_verify_payment():
    token = session.get('registration_payment_token')
    attempt = RegistrationPaymentModel.get_attempt(token) if token else None
    if not attempt or attempt['otp_status'] != 'verified':
        return {'ok': False, 'message': 'OTP verification required'}, 403
    if attempt['payment_status'] == 'paid':
        return {'ok': True, 'redirect_url': url_for(REGISTRATION_TYPE_ROUTES[attempt['user_type']])}

    payload = request.get_json(silent=True) or request.form
    order_id = (payload.get('razorpay_order_id') or '').strip()
    payment_id = (payload.get('razorpay_payment_id') or '').strip()
    signature = (payload.get('razorpay_signature') or '').strip()

    if not order_id or not payment_id or not signature:
        RegistrationPaymentModel.update_attempt(token, payment_status='failed', status='payment_failed')
        return {'ok': False, 'message': 'Payment verification data is incomplete.'}, 400
    if order_id != attempt['razorpay_order_id']:
        RegistrationPaymentModel.update_attempt(token, payment_status='failed', status='payment_failed')
        return {'ok': False, 'message': 'Payment order mismatch. Please try again.'}, 400

    try:
        valid = RazorpayGateway.verify_signature(order_id, payment_id, signature)
    except GatewayError as exc:
        RegistrationPaymentModel.update_attempt(token, payment_status='failed', status='payment_failed')
        return {'ok': False, 'message': str(exc)}, 502

    if not valid:
        RegistrationPaymentModel.update_attempt(token, payment_status='failed', status='payment_failed')
        return {'ok': False, 'message': 'Payment verification failed. Signature did not match.'}, 400

    RegistrationPaymentModel.update_attempt(
        token,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
        payment_status='paid',
        status='payment_successful',
    )
    return {'ok': True, 'redirect_url': url_for(REGISTRATION_TYPE_ROUTES[attempt['user_type']])}


@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    return _public_registration_handler('student')


@auth_bp.route('/register/employee', methods=['GET', 'POST'])
def register_employee():
    return _public_registration_handler('employee')


@auth_bp.route('/register/general', methods=['GET', 'POST'])
def register_general():
    return _public_registration_handler('emergency', card_user_type='general_user')


@auth_bp.route('/register/organization', methods=['GET', 'POST'])
def register_organization():
    return _public_registration_handler('employee', card_user_type='organization')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    flash('Select your user type to start mobile verification and payment.', 'info')
    return redirect(url_for('auth.register_select'))
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        mobile = attempt['mobile']
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        if not full_name or not mobile or not email or not password or not confirm_password:
            flash('All fields are required', 'warning')
            return redirect(url_for('auth.register'))
        if password != confirm_password:
            flash('Password and Confirm Password must match', 'warning')
            return redirect(url_for('auth.register'))
        if UserModel.find_by_email(email):
            flash('Email already registered', 'warning')
            return redirect(url_for('auth.register'))

        uid = UserModel.create(
            {
                'user_type': 'citizen',
                'name': full_name,
                'mobile': mobile,
                'email': email,
                'password': password,
                'photo': None,
                'education': None,
                'skills': None,
                'resume': None,
                'certificates': None,
                'company_name': None,
                'designation': None,
                'experience': None,
                'emergency_contact': None,
                'blood_group': None,
                'medical_notes': None,
                'address': None,
                'vehicle_number': None,
                'qr_token': None,
                'qr_path': None,
            }
        )
        CardPermissionModel.set_user_card_type(uid, 'general_user')
        CardPermissionModel.assign_defaults_for_user(uid)
        session['registration_user_id'] = uid
        flash('Registration Step 1 completed. Choose your profile.', 'success')
        return redirect(url_for('auth.choose_profiles'))
    return render_template('auth/register.html')


def _registration_target_user_id(allow_logged_in=False):
    if session.get('registration_user_id'):
        return session['registration_user_id']
    if allow_logged_in and session.get('user_id'):
        return session['user_id']
    return None


@auth_bp.route('/register/profiles', methods=['GET', 'POST'])
def choose_profiles():
    user_id = _registration_target_user_id(allow_logged_in=True)
    if not user_id:
        flash('Please complete registration step 1 first', 'warning')
        return redirect(url_for('auth.register'))

    selected_profiles = RegistrationModel.get_selected_profiles(user_id)
    if request.method == 'POST':
        profiles = request.form.getlist('profiles')
        if not profiles:
            flash('Select at least one profile', 'warning')
            return redirect(url_for('auth.choose_profiles'))
        RegistrationModel.save_selected_profiles(user_id, profiles)
        flash('Profile selections saved', 'success')
        return redirect(url_for('auth.profile_details'))

    return render_template(
        'auth/choose_profiles.html',
        profile_options=RegistrationModel.PROFILE_OPTIONS,
        profile_labels=RegistrationModel.PROFILE_LABELS,
        selected_profiles=selected_profiles,
    )


@auth_bp.route('/register/profile-details', methods=['GET', 'POST'])
def profile_details():
    user_id = _registration_target_user_id(allow_logged_in=True)
    if not user_id:
        flash('Please complete registration step 1 first', 'warning')
        return redirect(url_for('auth.register'))

    selected_profiles = RegistrationModel.get_selected_profiles(user_id)
    if not selected_profiles:
        flash('Choose your profile first', 'warning')
        return redirect(url_for('auth.choose_profiles'))

    existing_data = RegistrationModel.get_profile_data_map(user_id)
    if request.method == 'POST':
        details_by_profile = {}
        for profile in selected_profiles:
            if profile == 'student':
                details_by_profile[profile] = {
                    'college': request.form.get('student_college', ''),
                    'branch': request.form.get('student_branch', ''),
                    'year': request.form.get('student_year', ''),
                    'roll_number': request.form.get('student_roll_number', ''),
                }
            elif profile == 'employee':
                details_by_profile[profile] = {
                    'company': request.form.get('employee_company', ''),
                    'designation': request.form.get('employee_designation', ''),
                    'experience': request.form.get('employee_experience', ''),
                }
            elif profile == 'intern':
                details_by_profile[profile] = {
                    'company': request.form.get('intern_company', ''),
                    'department': request.form.get('intern_department', ''),
                    'duration': request.form.get('intern_duration', ''),
                }
            elif profile == 'freelancer':
                details_by_profile[profile] = {
                    'profession': request.form.get('freelancer_profession', ''),
                    'portfolio_link': request.form.get('freelancer_portfolio_link', ''),
                }
            elif profile == 'business_owner':
                details_by_profile[profile] = {
                    'business_name': request.form.get('business_owner_business_name', ''),
                    'business_type': request.form.get('business_owner_business_type', ''),
                    'website': request.form.get('business_owner_website', ''),
                }
            elif profile == 'emergency':
                details_by_profile[profile] = {
                    'blood_group': request.form.get('emergency_blood_group', ''),
                    'emergency_contact': request.form.get('emergency_contact', ''),
                    'medical_notes': request.form.get('emergency_medical_notes', ''),
                }
            elif profile == 'visitor':
                details_by_profile[profile] = {
                    'visit_purpose': request.form.get('visitor_visit_purpose', ''),
                    'host_name': request.form.get('visitor_host_name', ''),
                }
            elif profile == 'citizen':
                details_by_profile[profile] = {
                    'city': request.form.get('citizen_city', ''),
                    'occupation': request.form.get('citizen_occupation', ''),
                }

        RegistrationModel.save_profile_details(user_id, details_by_profile)
        RegistrationModel.sync_user_summary_fields(user_id, details_by_profile)
        if session.get('user_id') == user_id:
            refreshed_user = UserModel.find_by_id(user_id)
            if refreshed_user:
                session['user_type'] = refreshed_user[1]
        if session.get('registration_user_id'):
            session.pop('registration_user_id', None)
            flash('Your account has been created successfully. Please log in to complete your profile details.', 'success')
            return redirect(url_for('auth.login'))
        flash('Profile details updated successfully', 'success')
        return redirect(url_for('auth.profile_details'))

    return render_template(
        'auth/profile_details.html',
        selected_profiles=selected_profiles,
        profile_labels=RegistrationModel.PROFILE_LABELS,
        existing_data=existing_data,
    )


@auth_bp.route('/register/profiles/edit')
def edit_profiles():
    if 'user_id' not in session:
        flash('Login required', 'warning')
        return redirect(url_for('auth.login'))
    return redirect(url_for('auth.choose_profiles'))


def _public_registration_handler(user_type, card_user_type=None):
    gate_user_type = card_user_type or user_type
    token = session.get('registration_payment_token')
    attempt = RegistrationPaymentModel.get_attempt(token) if token else None
    if not attempt or attempt['user_type'] != gate_user_type:
        flash('Please verify your mobile and complete payment first', 'warning')
        return redirect(url_for('auth.register_select'))
    if attempt['otp_status'] != 'verified':
        flash('Verify OTP before registration', 'warning')
        return redirect(url_for('auth.registration_verify_otp'))
    if attempt['payment_status'] != 'paid':
        flash('Complete payment before registration', 'warning')
        return redirect(url_for('auth.registration_payment'))

    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        mobile = (request.form.get('mobile') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        if not full_name or not mobile or not email or not password or not confirm_password:
            flash('All fields are required', 'warning')
            return redirect(request.url)
        if password != confirm_password:
            flash('Password and Confirm Password must match', 'warning')
            return redirect(request.url)
        if UserModel.find_by_email(email):
            flash('Email already registered', 'warning')
            return redirect(request.url)

        uid = _create_public_user(user_type, full_name, mobile, email, password)
        CardPermissionModel.set_user_card_type(uid, card_user_type or user_type)
        SubscriptionService.apply_subscription_for_registration(uid, date.today())
        RegistrationPaymentModel.update_attempt(token, user_id=uid, status='registration_created')
        session.pop('registration_payment_token', None)
        session.pop('registration_payment_user_type', None)
        flash('Your account has been created successfully. Please log in to complete your profile details.', 'success')
        return redirect(url_for('auth.login'))

    return render_template(
        'auth/register_public.html',
        paid_attempt=attempt,
        user_label=RegistrationPaymentModel.LABELS[gate_user_type],
    )


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = (request.form.get('otp') or '').strip()
        if entered_otp == session.get('registration_otp'):
            user_id = session.get('registration_user_id')
            if user_id:
                from services.db import get_conn
                conn = get_conn()
                cur = conn.cursor()
                cur.execute('UPDATE users SET is_active=1 WHERE id=%s', (user_id,))
                conn.commit()
                cur.close()
            session.pop('registration_otp', None)
            session.pop('registration_mobile', None)
            session.pop('registration_user_type', None)
            flash('OTP verified. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        flash('Invalid OTP', 'warning')
        return redirect(url_for('auth.verify_otp'))
    return render_template('auth/verify_otp.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        mobile = (request.form.get('mobile') or '').strip()
        if not mobile:
            flash('Enter your registered mobile number', 'warning')
            return redirect(url_for('auth.forgot_password'))
        try:
            normalized_mobile = normalize_mobile(mobile)
        except GatewayError as exc:
            flash(str(exc), 'warning')
            return redirect(url_for('auth.forgot_password'))
        accounts = UserModel.find_accounts_by_mobile(normalized_mobile)
        if not accounts:
            flash('This mobile number is not registered.', 'warning')
            return redirect(url_for('auth.forgot_password'))
        try:
            MSG91Gateway.send_otp(normalized_mobile)
        except GatewayError as exc:
            flash(f'Unable to send OTP: {exc}', 'warning')
            return redirect(url_for('auth.forgot_password'))
        normalized_accounts = _normalize_forgot_password_accounts(accounts)
        session['forgot_password_mobile'] = normalized_mobile
        session['forgot_password_otp_time'] = time.time()
        session['forgot_password_verified'] = False
        session['forgot_password_accounts'] = normalized_accounts
        session['forgot_password_account_id'] = normalized_accounts[0]['id'] if len(normalized_accounts) == 1 else None
        flash('OTP sent to your registered mobile number.', 'success')
        return redirect(url_for('auth.forgot_password_verify'))
    return render_template('auth/forgot_password.html')


@auth_bp.route('/forgot-password/verify', methods=['GET', 'POST'])
def forgot_password_verify():
    mobile = session.get('forgot_password_mobile')
    if not mobile:
        flash('Please start the forgot password flow again.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        otp = (request.form.get('otp') or '').strip()
        otp_time = session.get('forgot_password_otp_time', 0)
        if time.time() - float(otp_time) > 600:
            _clear_forgot_password_session()
            flash('OTP has expired. Please request a new one.', 'warning')
            return redirect(url_for('auth.forgot_password'))
        try:
            MSG91Gateway.verify_otp(mobile, otp)
        except GatewayError as exc:
            flash(str(exc), 'warning')
            return redirect(url_for('auth.forgot_password_verify'))
        accounts = session.get('forgot_password_accounts') or []
        session['forgot_password_verified'] = True
        if len(accounts) == 1:
            session['forgot_password_account_id'] = accounts[0]['id']
            flash('OTP verified successfully.', 'success')
            return redirect(url_for('auth.forgot_password_reset'))
        flash('OTP verified successfully. Which account do you want to reset?', 'success')
        return redirect(url_for('auth.forgot_password_select_account'))
    return render_template('auth/forgot_password_verify.html', mobile=mobile)


@auth_bp.route('/forgot-password/select-account', methods=['GET', 'POST'])
def forgot_password_select_account():
    mobile = session.get('forgot_password_mobile')
    if not mobile or session.get('forgot_password_verified') is not True:
        flash('Please verify your OTP before selecting an account.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    accounts = session.get('forgot_password_accounts') or []
    if len(accounts) <= 1:
        if accounts:
            session['forgot_password_account_id'] = accounts[0]['id']
        return redirect(url_for('auth.forgot_password_reset'))
    if request.method == 'POST':
        selected_id = request.form.get('account_id')
        if not selected_id:
            flash('Please select the account you want to reset.', 'warning')
            return redirect(url_for('auth.forgot_password_select_account'))
        selected_account = next((account for account in accounts if str(account['id']) == str(selected_id)), None)
        if not selected_account:
            flash('Invalid account selection.', 'warning')
            return redirect(url_for('auth.forgot_password_select_account'))
        session['forgot_password_account_id'] = selected_account['id']
        return redirect(url_for('auth.forgot_password_reset'))
    return render_template('auth/forgot_password_select_account.html', mobile=mobile, accounts=accounts)


@auth_bp.route('/forgot-password/resend', methods=['POST'])
def forgot_password_resend():
    mobile = session.get('forgot_password_mobile')
    if not mobile:
        flash('Please start the forgot password flow again.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    try:
        MSG91Gateway.send_otp(mobile)
        session['forgot_password_otp_time'] = time.time()
        flash('A new OTP has been sent.', 'success')
    except GatewayError as exc:
        flash(f'Unable to send OTP: {exc}', 'warning')
    return redirect(url_for('auth.forgot_password_verify'))


@auth_bp.route('/forgot-password/reset', methods=['GET', 'POST'])
def forgot_password_reset():
    mobile = session.get('forgot_password_mobile')
    if not mobile or session.get('forgot_password_verified') is not True:
        flash('Please verify your OTP before resetting the password.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    account_id = session.get('forgot_password_account_id')
    if account_id is None:
        accounts = session.get('forgot_password_accounts') or []
        if len(accounts) == 1:
            session['forgot_password_account_id'] = accounts[0]['id']
            account_id = accounts[0]['id']
        else:
            flash('Please select the account you want to reset.', 'warning')
            return redirect(url_for('auth.forgot_password_select_account'))
    if request.method == 'POST':
        new_password = request.form.get('new_password') or ''
        confirm_password = request.form.get('confirm_password') or ''
        if not new_password or not confirm_password:
            flash('Both password fields are required.', 'warning')
            return redirect(url_for('auth.forgot_password_reset'))
        if new_password != confirm_password:
            flash('New password and confirm password must match.', 'warning')
            return redirect(url_for('auth.forgot_password_reset'))
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return redirect(url_for('auth.forgot_password_reset'))
        UserModel.update_password_by_id(account_id, new_password)
        _clear_forgot_password_session()
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    selected_account = None
    for account in session.get('forgot_password_accounts') or []:
        if str(account['id']) == str(account_id):
            selected_account = account
            break
    return render_template('auth/forgot_password_reset.html', mobile=mobile, selected_account=selected_account)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        row = None
        if '@' in identifier:
            row = UserModel.find_by_email(identifier)
        else:
            db_conn, cur = UserModel._get_conn_and_cursor()
            cur.execute('SELECT id, email, password_hash, is_active, user_type, name FROM users WHERE mobile=%s', (identifier,))
            row = cur.fetchone()
            cur.close()
        if not row:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('auth.login'))
        uid, db_email, pw_hash, is_active, user_type, name = row
        if not is_active:
            flash('Account inactive', 'warning')
            return redirect(url_for('auth.login'))
        from werkzeug.security import check_password_hash
        if check_password_hash(pw_hash, password):
            session['user_id'] = uid
            session['user_type'] = user_type
            session['user_name'] = name
            if user_type == 'admin':
                session['super_admin_id'] = uid
                flash('Logged in as Admin', 'success')
                return redirect(url_for('superadmin.dashboard'))
            flash('Logged in', 'success')
            return redirect(url_for('auth.dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/complete-profile', methods=['GET', 'POST'])
def complete_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = UserModel.find_by_id(session['user_id'])

    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        mobile = (request.form.get('mobile') or '').strip()
        email = (request.form.get('email') or '').strip()
        address = (request.form.get('address') or '').strip()
        emergency_contact = (request.form.get('emergency_contact') or '').strip()
        education = (request.form.get('education') or '').strip()
        skills = (request.form.get('skills') or '').strip()
        photo_path = None

        if 'profile_photo' in request.files:
            photo_file = request.files['profile_photo']
            if photo_file and photo_file.filename:
                allowed = {'jpg', 'jpeg', 'png', 'webp'}
                name = (photo_file.filename or '').lower()
                if '.' not in name or name.rsplit('.', 1)[1] not in allowed:
                    flash('Only JPG, PNG, and WEBP images are allowed', 'warning')
                    return redirect(url_for('auth.complete_profile'))
                if photo_file.content_length and photo_file.content_length > 2 * 1024 * 1024:
                    flash('Image size must be 2 MB or less', 'warning')
                    return redirect(url_for('auth.complete_profile'))
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
                os.makedirs(upload_dir, exist_ok=True)
                filename = f"user_{session['user_id']}_{os.path.splitext(os.path.basename(photo_file.filename))[0]}_{os.urandom(4).hex()}{os.path.splitext(photo_file.filename)[1]}"
                save_path = os.path.join(upload_dir, filename)
                photo_file.save(save_path)
                photo_path = os.path.join('static', 'uploads', 'profiles', filename)

        db_conn, cur = UserModel._get_conn_and_cursor()
        cur.execute(
            '''
            UPDATE users
            SET name=%s, mobile=%s, email=%s, address=%s, emergency_contact=%s, education=%s, skills=%s, photo=%s
            WHERE id=%s
            ''',
            (full_name, mobile, email, address, emergency_contact, education, skills, photo_path or user[6], session['user_id']),
        )
        db_conn.commit()
        cur.close()
        session['user_name'] = full_name
        flash('Profile updated successfully', 'success')
        profile_completion = _get_profile_completion(UserModel.find_by_id(session['user_id']))
        if profile_completion >= 100:
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('auth.dashboard'))

    return render_template('auth/complete_profile.html', user=user)


@auth_bp.route('/dashboard-public')
def dashboard_public():
    qr_token = (request.args.get('token') or '').strip()
    if not qr_token:
        if session.get('user_id'):
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('auth.login'))

    user = UserModel.find_by_qr_token(qr_token)
    if not user:
        profile_card = QRIdentityModel.find_by_token_and_type(qr_token, QRIdentityModel.PROFILE)
        if profile_card:
            user = UserModel.find_by_id(profile_card[1])

    if not user:
        abort(404)

    if user[1] == 'student':
        student_data = StudentProfileModel.get_student_dashboard_data(user[0])
        if not student_data:
            abort(404)
        data = ProfileEngine.build_dashboard_context('student', student_data)
        visible_section_keys = data.get('visible_section_keys', set())
        data['profile_sections'] = [
            section for section in data.get('profile_sections', [])
            if section.get('key') in visible_section_keys and section.get('key') != 'emergency_contact'
        ]
        return render_template('profile/public_dashboard.html', hide_navbar=True, public_qr_token=qr_token, **data)

    profile_completion = _get_profile_completion(user)
    checklist = _get_profile_checklist(user)
    return render_template(
        'auth/dashboard_public.html',
        profile_completion=profile_completion,
        profile_complete=profile_completion >= 100,
        checklist=checklist,
        user=user,
        is_public_view=True,
        hide_navbar=True,
    )


@auth_bp.route('/generate-qr')
def generate_qr():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    row = UserModel.find_by_id(user_id)
    if not row:
        flash('User not found', 'warning')
        return redirect(url_for('auth.dashboard'))
    if _get_profile_completion(row) < 100:
        flash('Complete your profile to unlock QR generation', 'warning')
        return redirect(url_for('auth.dashboard'))
    if row[19] and row[20]:
        return redirect(url_for('auth.qr_view'))
    # Generate QR with actual server URL
    scan_url_template = url_for('qr.profile', token='__TOKEN__', _external=True)
    token, path = generate_qr_for_user(user_id, scan_url_template, qr_type=QRIdentityModel.PROFILE)
    UserModel.update_qr(user_id, token, path)
    flash('QR generated successfully', 'success')
    return redirect(url_for('auth.qr_view'))


@auth_bp.route('/qr-view')
def qr_view():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = UserModel.find_by_id(session['user_id'])
    if not user:
        flash('User not found', 'warning')
        return redirect(url_for('auth.dashboard'))

    profile_card = QRIdentityModel.ensure_for_user(
        user[0],
        QRIdentityModel.PROFILE,
        url_for('qr.profile', token='__TOKEN__', _external=True),
    )
    emergency_card = QRIdentityModel.ensure_for_user(
        user[0],
        QRIdentityModel.EMERGENCY,
        url_for('qr.emergency', token='__TOKEN__', _external=True),
    )
    if not user[19] or not user[20]:
        UserModel.update_qr(user[0], profile_card['token'], profile_card['path'])

    qr_cards = {
        'emergency': {
            'title': 'Emergency QR',
            'label': 'EMERGENCY IDENTITY',
            'badge': 'Emergency Only',
            'description': 'Scan to access emergency contact information',
            'scan_url': url_for('qr.emergency', token=emergency_card['token'], _external=True),
            'path': emergency_card['path'],
            'download_png': url_for('auth.download_png', qr_type='emergency'),
            'download_pdf': url_for('auth.download_pdf', qr_type='emergency'),
        },
        'profile': {
            'title': 'QR-NexID Digital Identity',
            'label': 'DIGITAL IDENTITY',
            'badge': 'Verified Digital Identity',
            'description': 'Scan to view complete digital identity',
            'scan_url': url_for('qr.profile', token=profile_card['token'], _external=True),
            'path': profile_card['path'],
            'download_png': url_for('auth.download_png', qr_type='profile'),
            'download_pdf': url_for('auth.download_pdf', qr_type='profile'),
        },
    }
    return render_template('auth/qr_view.html', user=user, qr_cards=qr_cards)


@auth_bp.route('/download-png')
def download_png():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = UserModel.find_by_id(session['user_id'])
    qr_type = request.args.get('qr_type') or QRIdentityModel.PROFILE
    if qr_type not in (QRIdentityModel.PROFILE, QRIdentityModel.EMERGENCY):
        abort(404)
    card = QRIdentityModel.ensure_for_user(
        user[0],
        qr_type,
        url_for(f'qr.{qr_type}', token='__TOKEN__', _external=True),
    ) if user else None
    if not user or not card or not card.get('path'):
        flash('Generate QR first', 'warning')
        return redirect(url_for('auth.qr_view'))
    file_path = QRIdentityModel.file_path(card['path'])
    card_image = render_premium_card(file_path, user[2], qr_type)
    buf = BytesIO()
    card_image.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f'qr-nexid-{qr_type}-card.png')


@auth_bp.route('/download-pdf')
def download_pdf():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = UserModel.find_by_id(session['user_id'])
    qr_type = request.args.get('qr_type') or QRIdentityModel.PROFILE
    if qr_type not in (QRIdentityModel.PROFILE, QRIdentityModel.EMERGENCY):
        abort(404)
    card = QRIdentityModel.ensure_for_user(
        user[0],
        qr_type,
        url_for(f'qr.{qr_type}', token='__TOKEN__', _external=True),
    ) if user else None
    if not user or not card or not card.get('path'):
        flash('Generate QR first', 'warning')
        return redirect(url_for('auth.qr_view'))

    file_path = QRIdentityModel.file_path(card['path'])
    canvas = render_premium_card(file_path, user[2], qr_type)
    buf = BytesIO()
    canvas.save(buf, format='PDF', resolution=150.0)
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f'qr-nexid-{qr_type}.pdf')


@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    subscription = SubscriptionService.get_user_subscription_summary(session['user_id'])
    if subscription and subscription['is_expired']:
        flash('Subscription expired. Please contact support to renew access.', 'warning')
    if EmployeeProfileModel.has_employee_profile(session['user_id']) or session.get('user_type') == 'employee':
        return redirect(url_for('employee.employee_dashboard'))
    if StudentProfileModel.has_student_profile(session['user_id']):
        return redirect(url_for('user.student_dashboard'))
    return render_template('auth/dashboard.html', hide_navbar=True, subscription=subscription)
