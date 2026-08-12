from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file, abort
import werkzeug
from models.user import UserModel
from models.registration import RegistrationModel
from models.student_profile import StudentProfileModel
from models.employee_profile import EmployeeProfileModel
from services.db import get_db
from services.profile_engine import ProfileEngine
from services.qrcode_service import generate_qr_for_user
import os
import secrets
import qrcode
from io import BytesIO
from PIL import Image

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')


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
    return uid


@auth_bp.route('/register/select')
def register_select():
    return render_template('auth/register_select.html')


@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    return _public_registration_handler('student')


@auth_bp.route('/register/employee', methods=['GET', 'POST'])
def register_employee():
    return _public_registration_handler('employee')


@auth_bp.route('/register/general', methods=['GET', 'POST'])
def register_general():
    return _public_registration_handler('emergency')


@auth_bp.route('/register/organization', methods=['GET', 'POST'])
def register_organization():
    return _public_registration_handler('employee')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        mobile = (request.form.get('mobile') or '').strip()
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
            flash('Registration completed successfully. Please log in.', 'success')
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


def _public_registration_handler(user_type):
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
        session['registration_user_id'] = uid
        session['registration_user_type'] = user_type
        session['registration_mobile'] = mobile
        session['registration_otp'] = '1111'
        flash('Registration successful. Please verify your OTP.', 'success')
        return redirect(url_for('auth.verify_otp'))

    return render_template('auth/register_public.html')


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
        abort(404)

    if user[1] == 'student':
        student_data = StudentProfileModel.get_student_dashboard_data(user[0])
        if not student_data:
            abort(404)
        data = ProfileEngine.build_dashboard_context('student', student_data)
        visible_section_keys = data.get('visible_section_keys', set())
        data['profile_sections'] = [
            section for section in data.get('profile_sections', [])
            if section.get('key') in visible_section_keys
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
    scan_url_template = url_for('qr.scan', token='__TOKEN__', _external=True)
    token, path = generate_qr_for_user(user_id, scan_url_template)
    UserModel.update_qr(user_id, token, path)
    flash('QR generated successfully', 'success')
    return redirect(url_for('auth.qr_view'))


@auth_bp.route('/qr-view')
def qr_view():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = UserModel.find_by_id(session['user_id'])
    qr_path = user[20] if user and len(user) > 20 else None
    scan_url = url_for('qr.scan', token=user[19], _external=True) if user and user[19] else None
    return render_template('auth/qr_view.html', qr_path=qr_path, scan_url=scan_url)


@auth_bp.route('/download-png')
def download_png():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = UserModel.find_by_id(session['user_id'])
    if not user or not user[20]:
        flash('Generate QR first', 'warning')
        return redirect(url_for('auth.qr_view'))
    file_path = os.path.join(current_app.root_path, user[20])
    return send_file(file_path, mimetype='image/png', as_attachment=True, download_name='lifeshield_qr.png')


@auth_bp.route('/download-pdf')
def download_pdf():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = UserModel.find_by_id(session['user_id'])
    if not user or not user[20]:
        flash('Generate QR first', 'warning')
        return redirect(url_for('auth.qr_view'))

    pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 420 220] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 110 >>
stream
BT /F1 18 Tf 40 180 Td (LifeShield QR Card) Tj 0 -28 Td /F1 12 Tf ({user[2]}) Tj 0 -20 Td (Token: {user[19]}) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000062 00000 n 
0000000119 00000 n 
0000000207 00000 n 
0000000302 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""
    buf = BytesIO(pdf_content.encode('latin-1'))
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='lifeshield_qr.pdf')


@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if EmployeeProfileModel.has_employee_profile(session['user_id']) or session.get('user_type') == 'employee':
        return redirect(url_for('employee.employee_dashboard'))
    if StudentProfileModel.has_student_profile(session['user_id']):
        return redirect(url_for('user.student_dashboard'))
    return render_template('auth/dashboard.html')
