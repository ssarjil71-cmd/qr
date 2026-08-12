from functools import wraps

import os
import secrets

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from models.user import UserModel
from services.db import get_conn
from services.qrcode_service import generate_qr_for_user

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')


def org_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_user_id' not in session or 'organization_id' not in session:
            flash('Organization Admin login required', 'warning')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)

    return decorated


def _current_org_id():
    return session.get('organization_id')


def _current_org_context():
    org_row = UserModel.get_org_context(_current_org_id())
    return {
        'organization_id': org_row[0] if org_row else None,
        'organization_name': org_row[1] if org_row else 'Organization',
    }


def _endpoint_for_user_type(user_type):
    if user_type == 'student':
        return 'admin.students'
    if user_type == 'employee':
        return 'admin.employees'
    if user_type == 'freelancer':
        return 'admin.freelancers'
    if user_type == 'visitor':
        return 'admin.visitors'
    if user_type == 'citizen':
        return 'admin.citizens'
    return 'admin.emergency_profiles'


def _page_title_for_user_type(user_type):
    mapping = {
        'student': 'Students',
        'employee': 'Employees',
        'emergency': 'Emergency Profiles',
        'freelancer': 'Freelancers',
        'visitor': 'Visitors',
        'citizen': 'Citizens',
    }
    return mapping.get(user_type, 'Users')


def _save_photo(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    token = secrets.token_hex(8)
    final_name = f'{token}_{filename}'
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, final_name)
    file_storage.save(save_path)
    return final_name


def _build_qr_for_user(uid):
    token, rel_path = generate_qr_for_user(uid, request.url_root.rstrip('/') + url_for('qr.scan', token='__TOKEN__'))
    UserModel.update_qr(uid, token, rel_path)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM qr_tokens WHERE user_id=%s', (uid,))
    exists = cur.fetchone()[0]
    if exists:
        cur.execute('UPDATE qr_tokens SET token=%s, qr_path=%s, is_active=1 WHERE user_id=%s', (token, rel_path, uid))
    else:
        cur.execute('INSERT INTO qr_tokens (user_id, token, qr_path, is_active) VALUES (%s, %s, %s, 1)', (uid, token, rel_path))
    conn.commit()
    cur.close()
    return token, rel_path


@admin_bp.route('/')
def index():
    if 'admin_user_id' in session:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.login'))


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        row = UserModel.find_org_admin_by_email(email)
        if not row:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('admin.login'))
        uid, db_email, pw_hash, is_active, user_type, name, organization_id, organization_name = row
        if not is_active:
            flash('Account inactive', 'warning')
            return redirect(url_for('admin.login'))
        if check_password_hash(pw_hash, password):
            session.clear()
            session['admin_user_id'] = uid
            session['organization_id'] = organization_id
            session['user_name'] = name
            session['organization_name'] = organization_name
            flash('Logged in as Organization Admin', 'success')
            return redirect(url_for('admin.dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
@org_admin_required
def dashboard():
    org_id = _current_org_id()
    stats = UserModel.get_org_dashboard_stats(org_id)
    recent_registrations = UserModel.get_recent_org_registrations(org_id)
    qr_scan_stats = UserModel.get_org_scan_statistics(org_id)
    return render_template(
        'admin/dashboard.html',
        recent_registrations=recent_registrations,
        qr_scan_stats=qr_scan_stats,
        org_context=_current_org_context(),
        **stats,
    )


@admin_bp.route('/students')
@org_admin_required
def students():
    return redirect(url_for('admin.users', user_type='student'))


@admin_bp.route('/employees')
@org_admin_required
def employees():
    return redirect(url_for('admin.users', user_type='employee'))


@admin_bp.route('/emergency-profiles')
@org_admin_required
def emergency_profiles():
    return redirect(url_for('admin.users', user_type='emergency'))


@admin_bp.route('/freelancers')
@org_admin_required
def freelancers():
    return redirect(url_for('admin.users', user_type='freelancer'))


@admin_bp.route('/visitors')
@org_admin_required
def visitors():
    return redirect(url_for('admin.users', user_type='visitor'))


@admin_bp.route('/citizens')
@org_admin_required
def citizens():
    return redirect(url_for('admin.users', user_type='citizen'))


@admin_bp.route('/users')
@org_admin_required
def users():
    org_id = _current_org_id()
    q = (request.args.get('q') or '').strip()
    selected_type = (request.args.get('user_type') or '').strip() or None
    status = (request.args.get('status') or '').strip() or None
    qr_status = (request.args.get('qr_status') or '').strip() or None
    page = request.args.get('page', default=1, type=int)
    pagination = UserModel.list_org_users_paginated(
        org_id,
        user_type=selected_type,
        search=q,
        status=status,
        qr_status=qr_status,
        page=page,
        per_page=10,
    )
    return render_template(
        'admin/users.html',
        users=pagination['items'],
        pagination=pagination,
        q=q,
        current_type=selected_type,
        current_status=status,
        current_qr_status=qr_status,
        page_title=_page_title_for_user_type(selected_type) if selected_type else 'Users',
        org_context=_current_org_context(),
        user_types=UserModel.MANAGED_USER_TYPES,
        display_code=UserModel.user_display_code,
    )


@admin_bp.route('/<user_type>/create', methods=['GET', 'POST'])
@org_admin_required
def create_user(user_type):
    if user_type not in UserModel.MANAGED_USER_TYPES:
        flash('Invalid user type', 'warning')
        return redirect(url_for('admin.dashboard'))
    org_id = _current_org_id()
    branches = UserModel.get_org_branches(org_id)
    departments = UserModel.get_org_departments(org_id)
    if request.method == 'POST':
        photo_name = _save_photo(request.files.get('photo'))
        branch_name = request.form.get('branch_name') or ''
        department_name = request.form.get('department_name') or ''
        user = {
            'user_type': user_type,
            'name': request.form.get('name'),
            'mobile': request.form.get('mobile'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'education': request.form.get('education'),
            'skills': None,
            'resume': None,
            'certificates': None,
            'company_name': branch_name,
            'designation': department_name,
            'experience': request.form.get('experience'),
            'emergency_contact': request.form.get('emergency_contact'),
            'blood_group': request.form.get('blood_group'),
            'medical_notes': request.form.get('medical_notes'),
            'address': request.form.get('address'),
            'vehicle_number': request.form.get('vehicle_number'),
            'qr_token': None,
            'qr_path': None,
            'photo': photo_name,
        }
        uid = UserModel.create_org_user(org_id, user)
        _build_qr_for_user(uid)
        flash(f'{user_type.title()} created successfully', 'success')
        return redirect(url_for(_endpoint_for_user_type(user_type)))
    return render_template(
        'admin/user_form.html',
        user=None,
        user_type=user_type,
        page_title=f'Create {_page_title_for_user_type(user_type)[:-1] if _page_title_for_user_type(user_type).endswith("s") else _page_title_for_user_type(user_type)}',
        branches=branches,
        departments=departments,
        org_context=_current_org_context(),
        display_code=None,
    )


@admin_bp.route('/users/<int:uid>/edit', methods=['GET', 'POST'])
@org_admin_required
def edit_user(uid):
    org_id = _current_org_id()
    row = UserModel.get_org_user(org_id, uid)
    if not row:
        flash('User not found for this organization', 'warning')
        return redirect(url_for('admin.dashboard'))
    user = {
        'id': row[0],
        'user_type': row[1],
        'name': row[2],
        'mobile': row[3],
        'email': row[4],
        'education': row[7],
        'company_name': row[11],
        'designation': row[12],
        'experience': row[13],
        'emergency_contact': row[14],
        'blood_group': row[15],
        'medical_notes': row[16],
        'address': row[17],
        'vehicle_number': row[18],
        'photo': row[6],
        'is_active': row[21],
        'qr_token': row[19],
    }
    branches = UserModel.get_org_branches(org_id)
    departments = UserModel.get_org_departments(org_id)
    if request.method == 'POST':
        photo_name = _save_photo(request.files.get('photo')) or user.get('photo')
        updated = UserModel.update_org_user(
            org_id,
            uid,
            {
                'name': request.form.get('name'),
                'mobile': request.form.get('mobile'),
                'email': request.form.get('email'),
                'password': request.form.get('password'),
                'education': request.form.get('education'),
                'company_name': request.form.get('branch_name'),
                'designation': request.form.get('department_name'),
                'experience': request.form.get('experience'),
                'emergency_contact': request.form.get('emergency_contact'),
                'blood_group': request.form.get('blood_group'),
                'medical_notes': request.form.get('medical_notes'),
                'address': request.form.get('address'),
                'vehicle_number': request.form.get('vehicle_number'),
                'photo': photo_name,
            },
        )
        if updated:
            flash('User updated successfully', 'success')
        else:
            flash('Unable to update user', 'warning')
        return redirect(url_for(_endpoint_for_user_type(user['user_type'])))
    return render_template(
        'admin/user_form.html',
        user=user,
        user_type=user['user_type'],
        page_title=f'Edit {user["user_type"].title()}',
        branches=branches,
        departments=departments,
        org_context=_current_org_context(),
        display_code=UserModel.user_display_code(uid),
    )


@admin_bp.route('/users/<int:uid>')
@org_admin_required
def view_user(uid):
    row = UserModel.get_org_user(_current_org_id(), uid)
    if not row:
        flash('User not found for this organization', 'warning')
        return redirect(url_for('admin.users'))
    user = {
        'id': row[0],
        'user_type': row[1],
        'name': row[2],
        'mobile': row[3],
        'email': row[4],
        'photo': row[6],
        'education': row[7],
        'company_name': row[11],
        'designation': row[12],
        'experience': row[13],
        'emergency_contact': row[14],
        'blood_group': row[15],
        'medical_notes': row[16],
        'address': row[17],
        'vehicle_number': row[18],
        'qr_token': row[19],
        'qr_path': row[20],
        'is_active': row[21],
        'created_at': row[23],
    }
    return render_template('admin/user_view.html', user=user, org_context=_current_org_context(), display_code=UserModel.user_display_code(uid))


@admin_bp.route('/users/<int:uid>/delete', methods=['POST'])
@org_admin_required
def delete_user(uid):
    row = UserModel.get_org_user(_current_org_id(), uid)
    if not row:
        flash('User not found for this organization', 'warning')
        return redirect(url_for('admin.dashboard'))
    user_type = row[1]
    UserModel.delete_org_user(_current_org_id(), uid)
    flash('User deleted successfully', 'info')
    return redirect(url_for(_endpoint_for_user_type(user_type)))


@admin_bp.route('/users/<int:uid>/toggle')
@org_admin_required
def toggle_user(uid):
    row = UserModel.get_org_user(_current_org_id(), uid)
    if not row:
        flash('User not found for this organization', 'warning')
        return redirect(url_for('admin.users'))
    new_status = 0 if row[21] else 1
    UserModel.set_active_status(_current_org_id(), uid, new_status)
    flash('User status updated successfully', 'success')
    return redirect(url_for(_endpoint_for_user_type(row[1])))


@admin_bp.route('/qr-cards')
@org_admin_required
def qr_cards():
    qr_rows = UserModel.list_org_qr_cards(_current_org_id())
    return render_template('admin/qr_cards.html', qr_rows=qr_rows, org_context=_current_org_context(), display_code=UserModel.user_display_code)


@admin_bp.route('/users/<int:uid>/generate-qr')
@org_admin_required
def generate_user_qr(uid):
    row = UserModel.get_org_user(_current_org_id(), uid)
    if not row:
        flash('User not found for this organization', 'warning')
        return redirect(url_for('admin.qr_cards'))
    _build_qr_for_user(uid)
    flash('QR card generated successfully', 'success')
    return redirect(url_for('admin.qr_cards'))
