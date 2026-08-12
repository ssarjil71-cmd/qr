from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.db import get_conn
from werkzeug.security import check_password_hash
from models.organization import OrganizationModel
from models.user import UserModel

superadmin_bp = Blueprint('superadmin', __name__, template_folder='../templates/admin/superadmin')


def admin_login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if 'super_admin_id' not in session:
            flash('Super Admin login required', 'warning')
            return redirect(url_for('superadmin.login'))
        return f(*args, **kwargs)

    return decorated


@superadmin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT id, password_hash, user_type, is_active, name FROM users WHERE email=%s', (email,))
        row = cur.fetchone()
        cur.close()
        if not row:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('superadmin.login'))
        uid, pw_hash, user_type, is_active, name = row
        if user_type != 'admin' or not is_active:
            flash('Not authorized', 'danger')
            return redirect(url_for('superadmin.login'))
        if check_password_hash(pw_hash, password):
            session.clear()
            session['super_admin_id'] = uid
            session['user_id'] = uid
            session['user_type'] = user_type
            session['user_name'] = name
            flash('Logged in as Super Admin', 'success')
            return redirect(url_for('superadmin.dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('admin/superadmin/login.html')


@superadmin_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('superadmin.login'))


@superadmin_bp.route('/dashboard')
@admin_login_required
def dashboard():
    stats = OrganizationModel.get_dashboard_stats()
    recent_activity = OrganizationModel.get_recent_activity()
    latest_users = OrganizationModel.get_latest_users()
    latest_organizations = OrganizationModel.get_latest_organizations()
    qr_scan_stats = OrganizationModel.get_qr_scan_statistics()
    return render_template(
        'admin/superadmin/dashboard.html',
        recent_activity=recent_activity,
        latest_users=latest_users,
        latest_organizations=latest_organizations,
        qr_scan_stats=qr_scan_stats,
        **stats,
    )


# Organization management
@superadmin_bp.route('/organizations')
@admin_login_required
def organizations_list():
    q = (request.args.get('q') or '').strip()
    page = request.args.get('page', default=1, type=int)
    pagination = OrganizationModel.list_paginated(search=q, page=page, per_page=10)
    return render_template('admin/superadmin/organizations_list.html', orgs=pagination['items'], pagination=pagination, q=q)


@superadmin_bp.route('/organizations/create', methods=['GET', 'POST'])
@admin_login_required
def organization_create():
    if request.method == 'POST':
        OrganizationModel.create(request.form)
        flash('Organization created', 'success')
        return redirect(url_for('superadmin.organizations_list'))
    return render_template('admin/superadmin/organization_form.html', org=None, type_options=OrganizationModel.TYPE_OPTIONS)


@superadmin_bp.route('/organizations/<int:org_id>/edit', methods=['GET', 'POST'])
@admin_login_required
def organization_edit(org_id):
    if request.method == 'POST':
        updated = OrganizationModel.update(org_id, request.form)
        if not updated:
            flash('Organization not found', 'warning')
            return redirect(url_for('superadmin.organizations_list'))
        flash('Organization updated', 'success')
        return redirect(url_for('superadmin.organizations_list'))
    org = OrganizationModel.get_by_id(org_id)
    if not org:
        flash('Organization not found', 'warning')
        return redirect(url_for('superadmin.organizations_list'))
    return render_template('admin/superadmin/organization_form.html', org=org, type_options=OrganizationModel.TYPE_OPTIONS)


@superadmin_bp.route('/organizations/<int:org_id>/view')
@admin_login_required
def organization_view(org_id):
    org = OrganizationModel.get_by_id(org_id)
    if not org:
        flash('Organization not found', 'warning')
        return redirect(url_for('superadmin.organizations_list'))
    branches = OrganizationModel.get_branch_summary(org_id)
    primary_admin = UserModel.get_primary_admin(org_id)
    return render_template('admin/superadmin/organization_view.html', org=org, branches=branches, primary_admin=primary_admin)


@superadmin_bp.route('/organizations/<int:org_id>/admin/create', methods=['GET', 'POST'])
@admin_login_required
def organization_admin_create(org_id):
    org = OrganizationModel.get_by_id(org_id)
    if not org:
        flash('Organization not found', 'warning')
        return redirect(url_for('superadmin.organizations_list'))
    if UserModel.organization_has_primary_admin(org_id):
        flash('Primary Organization Admin already exists for this organization', 'warning')
        return redirect(url_for('superadmin.organization_view', org_id=org_id))
    if request.method == 'POST':
        UserModel.create_organization_admin(
            org_id,
            {
                'name': request.form.get('name'),
                'mobile': request.form.get('mobile'),
                'email': request.form.get('email'),
                'password': request.form.get('password'),
                'address': request.form.get('address'),
            },
        )
        flash('Organization Admin created successfully', 'success')
        return redirect(url_for('superadmin.organization_view', org_id=org_id))
    return render_template('admin/superadmin/organization_admin_form.html', org=org)


@superadmin_bp.route('/organizations/<int:org_id>/toggle')
@admin_login_required
def organization_toggle(org_id):
    new_status = OrganizationModel.toggle_status(org_id)
    if new_status is None:
        flash('Organization not found', 'warning')
    elif new_status == 'active':
        flash('Organization activated', 'success')
    else:
        flash('Organization deactivated', 'info')
    return redirect(url_for('superadmin.organizations_list'))


@superadmin_bp.route('/organizations/<int:org_id>/delete', methods=['POST'])
@admin_login_required
def organization_delete(org_id):
    deleted = OrganizationModel.delete(org_id)
    if deleted:
        flash('Organization deleted', 'info')
    else:
        flash('Organization not found', 'warning')
    return redirect(url_for('superadmin.organizations_list'))


@superadmin_bp.route('/users')
@admin_login_required
def users():
    q = request.args.get('q')
    users = UserModel.list_users(search=q)
    return render_template('admin/superadmin/users.html', users=users, q=q)


@superadmin_bp.route('/qr-cards')
@admin_login_required
def qr_cards():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT qt.id, u.name, u.email, qt.token, qt.is_active, qt.created_at
        FROM qr_tokens qt
        LEFT JOIN users u ON u.id = qt.user_id
        ORDER BY qt.id DESC
        LIMIT 50
        '''
    )
    qr_rows = cur.fetchall()
    cur.close()
    return render_template('admin/superadmin/qr_cards.html', qr_rows=qr_rows)


@superadmin_bp.route('/reports')
@admin_login_required
def reports():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT sl.id, u.name, u.email, sl.ip_address, sl.scanned_at
        FROM scan_logs sl
        LEFT JOIN users u ON u.id = sl.user_id
        ORDER BY sl.id DESC
        LIMIT 50
        '''
    )
    scan_rows = cur.fetchall()
    cur.close()
    return render_template('admin/superadmin/reports.html', scan_rows=scan_rows)


@superadmin_bp.route('/settings')
@admin_login_required
def settings():
    return render_template('admin/superadmin/settings.html')


@superadmin_bp.route('/organizations/<int:org_id>/branches/create', methods=['GET', 'POST'])
@admin_login_required
def branch_create(org_id):
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        city = request.form.get('city')
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO org_branches (organization_id, uuid, name, code, address_line1, city) VALUES (%s, UUID(), %s, %s, %s, %s)', (org_id, name, code, None, city))
        conn.commit()
        cur.close()
        flash('Branch created', 'success')
        return redirect(url_for('superadmin.organization_view', org_id=org_id))
    return render_template('admin/superadmin/branch_form.html', org_id=org_id, branch=None)


@superadmin_bp.route('/branches/<int:branch_id>/departments/create', methods=['GET', 'POST'])
@admin_login_required
def department_create(branch_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT organization_id FROM org_branches WHERE id=%s', (branch_id,))
    row = cur.fetchone()
    if not row:
        flash('Branch not found', 'warning')
        return redirect(url_for('superadmin.organizations_list'))
    org_id = row[0]
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        manager_user_id = request.form.get('manager_user_id') or None
        cur.execute('INSERT INTO org_departments (branch_id, uuid, name, code, manager_user_id) VALUES (%s, UUID(), %s, %s, %s)', (branch_id, name, code, manager_user_id))
        conn.commit()
        cur.close()
        flash('Department created', 'success')
        return redirect(url_for('superadmin.organization_view', org_id=org_id))
    cur.close()
    return render_template('admin/superadmin/department_form.html', branch_id=branch_id)


@superadmin_bp.route('/departments/<int:department_id>/divisions/create', methods=['GET', 'POST'])
@admin_login_required
def division_create(department_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT branch_id FROM org_departments WHERE id=%s', (department_id,))
    row = cur.fetchone()
    if not row:
        flash('Department not found', 'warning')
        return redirect(url_for('superadmin.organizations_list'))
    branch_id = row[0]
    cur.execute('SELECT organization_id FROM org_branches WHERE id=%s', (branch_id,))
    org_row = cur.fetchone()
    org_id = org_row[0] if org_row else None
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        lead_user_id = request.form.get('lead_user_id') or None
        cur.execute('INSERT INTO org_divisions (department_id, uuid, name, code, lead_user_id) VALUES (%s, UUID(), %s, %s, %s)', (department_id, name, code, lead_user_id))
        conn.commit()
        cur.close()
        flash('Division created', 'success')
        return redirect(url_for('superadmin.organization_view', org_id=org_id))
    cur.close()
    return render_template('admin/superadmin/division_form.html', department_id=department_id)
