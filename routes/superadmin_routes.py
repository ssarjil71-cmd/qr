import json
from datetime import datetime, date

import MySQLdb.cursors
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response

from services.db import get_conn
from werkzeug.security import check_password_hash
from models.organization import OrganizationModel
from models.user import UserModel
from models.card_permission import CardPermissionModel
from models.registration_payment import RegistrationPaymentModel
from services.subscription_service import SubscriptionService

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
    card_stats = CardPermissionModel.get_dashboard_stats()
    stats.update(card_stats)
    recent_activity = OrganizationModel.get_recent_activity()
    latest_organizations = OrganizationModel.get_latest_organizations()
    qr_scan_stats = OrganizationModel.get_qr_scan_statistics()
    return render_template(
        'admin/superadmin/dashboard.html',
        recent_activity=recent_activity,
        latest_organizations=latest_organizations,
        qr_scan_stats=qr_scan_stats,
        PaymentStatusEnum=RegistrationPaymentModel.PaymentStatus,
        RegistrationStatusEnum=RegistrationPaymentModel.RegistrationStatus,
        **stats,
    )


@superadmin_bp.route('/assign-cards')
@admin_login_required
def assign_cards():
    filters = {
        'q': (request.args.get('q') or '').strip(),
        'organization_id': request.args.get('organization_id', type=int),
        'branch_id': request.args.get('branch_id', type=int),
        'department_id': request.args.get('department_id', type=int),
        'user_type': (request.args.get('user_type') or '').strip(),
        'status': (request.args.get('status') or '').strip(),
    }
    users = CardPermissionModel.list_assignment_users(filters)
    return render_template(
        'admin/superadmin/assign_cards.html',
        users=users,
        filters=filters,
        organizations=CardPermissionModel.list_organizations(),
    )


@superadmin_bp.route('/assign-cards/<int:user_id>', methods=['GET', 'POST'])
@admin_login_required
def manage_user_cards(user_id):
    user = CardPermissionModel.get_user_summary(user_id)
    if not user:
        flash('User not found', 'warning')
        return redirect(url_for('superadmin.assign_cards'))
    if request.method == 'POST':
        CardPermissionModel.save_user_permissions(
            user_id,
            request.form,
            changed_by=session.get('super_admin_id'),
            ip_address=request.remote_addr,
        )
        flash('Card permissions updated successfully.', 'success')
        return redirect(url_for('superadmin.manage_user_cards', user_id=user_id))
    cards = CardPermissionModel.list_cards()
    permissions = CardPermissionModel.get_effective_permissions(user_id)
    logs = CardPermissionModel.get_logs_for_user(user_id)
    return render_template('admin/superadmin/manage_user_cards.html', user=user, cards=cards, permissions=permissions, logs=logs)


@superadmin_bp.route('/default-permissions', methods=['GET', 'POST'])
@admin_login_required
def default_permissions():
    if request.method == 'POST':
        CardPermissionModel.set_system_defaults(request.form)
        flash('Default card configuration updated successfully.', 'success')
        return redirect(url_for('superadmin.default_permissions'))
    return render_template('admin/superadmin/default_permissions.html', cards=CardPermissionModel.list_cards())


@superadmin_bp.route('/user-type-cards', methods=['GET', 'POST'])
@admin_login_required
def user_type_cards():
    selected_type = CardPermissionModel.normalize_card_user_type(request.values.get('user_type') or 'student')
    if request.method == 'POST':
        action = request.form.get('action') or 'save'
        if action == 'apply_existing':
            updated = CardPermissionModel.apply_user_type_to_existing_users(
                selected_type,
                mode=request.form.get('apply_mode') or 'without_overrides',
                changed_by=session.get('super_admin_id'),
                ip_address=request.remote_addr,
            )
            flash(f'User type configuration applied to {updated} existing users.', 'success')
        else:
            CardPermissionModel.save_user_type_permissions(selected_type, request.form)
            flash('User type card configuration updated successfully.', 'success')
        return redirect(url_for('superadmin.user_type_cards', user_type=selected_type))
    return render_template(
        'admin/superadmin/user_type_cards.html',
        user_types=CardPermissionModel.list_user_type_summaries(),
        selected_type=selected_type,
        cards=CardPermissionModel.list_cards(),
        permissions=CardPermissionModel.get_user_type_permissions(selected_type),
    )


@superadmin_bp.route('/pricing', methods=['GET', 'POST'])
@admin_login_required
def pricing_management():
    if request.method == 'POST':
        RegistrationPaymentModel.update_prices(request.form, updated_by=session.get('super_admin_id'))
        flash('Registration pricing updated successfully.', 'success')
        return redirect(url_for('superadmin.pricing_management'))
    return render_template('admin/superadmin/pricing_management.html', pricing=RegistrationPaymentModel.list_pricing())


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
    card_features = CardPermissionModel.list_cards()
    org_card_permissions = CardPermissionModel.get_org_permissions(org_id)
    return render_template('admin/superadmin/organization_view.html', org=org, branches=branches, primary_admin=primary_admin, card_features=card_features, org_card_permissions=org_card_permissions)


@superadmin_bp.route('/organizations/<int:org_id>/card-configuration', methods=['POST'])
@admin_login_required
def organization_card_configuration(org_id):
    org = OrganizationModel.get_by_id(org_id)
    if not org:
        flash('Organization not found', 'warning')
        return redirect(url_for('superadmin.organizations_list'))
    CardPermissionModel.save_org_permissions(
        org_id,
        request.form,
        changed_by=session.get('super_admin_id'),
        ip_address=request.remote_addr,
        apply_existing=bool(request.form.get('apply_existing')),
    )
    flash('Organization card configuration updated successfully.', 'success')
    return redirect(url_for('superadmin.organization_view', org_id=org_id))


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


@superadmin_bp.route('/users/<int:uid>/subscription', methods=['GET','POST'])
@admin_login_required
def user_subscription(uid):
    user = UserModel.find_by_id(uid)
    if not user:
        flash('User not found', 'warning')
        return redirect(url_for('superadmin.users'))
    summary = SubscriptionService.get_user_subscription_summary(uid)
    logs = []
    conn = get_conn(); cur = conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    try:
        cur.execute(
            'SELECT previous_expiry_date, new_expiry_date, change_reason, changed_by, changed_at FROM subscription_expiry_audit WHERE user_id=%s ORDER BY changed_at DESC LIMIT 20',
            (uid,),
        )
        logs = cur.fetchall()
    finally:
        cur.close()

    start_date = summary['subscription_start_date'] if summary and summary.get('subscription_start_date') else None
    expiry_date = summary['subscription_expiry_date'] if summary and summary.get('subscription_expiry_date') else None
    valid_quick_action_base = SubscriptionService.get_valid_quick_action_base(start_date, expiry_date)
    can_extend = valid_quick_action_base is not None

    if request.method == 'POST':
        quick = (request.form.get('quick_action') or '').strip()
        expiry_raw = (request.form.get('subscription_expiry_date') or '').strip()

        if quick:
            if not can_extend:
                flash('This user does not have a valid subscription base date. Set an expiry date manually or activate the subscription first.', 'warning')
                return redirect(url_for('superadmin.user_subscription', uid=uid))
            base_date = valid_quick_action_base
            if quick == 'plus_1_month':
                expiry = SubscriptionService.add_calendar_months(base_date, 1)
            elif quick == 'plus_3_months':
                expiry = SubscriptionService.add_calendar_months(base_date, 3)
            elif quick == 'plus_6_months':
                expiry = SubscriptionService.add_calendar_months(base_date, 6)
            elif quick == 'plus_1_year':
                expiry = SubscriptionService.add_calendar_years(base_date, 1)
            else:
                flash('Unsupported quick action.', 'warning')
                return redirect(url_for('superadmin.user_subscription', uid=uid))
        elif expiry_raw:
            try:
                expiry = datetime.strptime(expiry_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Enter a valid expiry date in YYYY-MM-DD format.', 'warning')
                return redirect(url_for('superadmin.user_subscription', uid=uid))
        else:
            flash('Expiry date is required.', 'warning')
            return redirect(url_for('superadmin.user_subscription', uid=uid))

        try:
            result = SubscriptionService.set_manual_expiry_date(uid, expiry, changed_by=session.get('super_admin_id'), reason='superadmin_manual_update')
            flash(f'Subscription expiry updated to {result["subscription_expiry_date"].strftime("%d %b %Y")}.', 'success')
            return redirect(url_for('superadmin.user_subscription', uid=uid))
        except ValueError as exc:
            flash(str(exc), 'warning')
        except Exception:
            flash('Unable to update subscription expiry. Please try again.', 'warning')
    return render_template(
        'admin/superadmin/user_subscription.html',
        user=user,
        summary=summary,
        logs=logs,
        can_extend=can_extend,
        subscription_label='Not Activated' if not expiry_date else ('Active' if summary and summary.get('subscription_status') == 'Active' else (summary.get('subscription_status') if summary else 'Suspended')),
        expiry_label='Not Set' if not expiry_date else expiry_date.strftime('%d %b %Y'),
    )


@superadmin_bp.route('/users/<int:uid>/delete', methods=['POST'])
@admin_login_required
def delete_user(uid):
    row = UserModel.find_by_id(uid)
    if not row:
        flash('User not found', 'warning')
        return redirect(url_for('superadmin.users'))
    UserModel.delete_user(uid)
    flash('User deleted successfully', 'info')
    return redirect(url_for('superadmin.users'))


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


@superadmin_bp.route('/transactions')
@admin_login_required
def transactions():
    page = request.args.get('page', default=1, type=int)
    per_page = 10
    search_query = request.args.get('q', '').strip()
    payment_status_filter = request.args.get('payment_status', 'All')
    registration_status_filter = request.args.get('registration_status', 'All')
    user_type_filter = request.args.get('user_type', 'All')
    date_range_filter = request.args.get('date_range', 'All')
    sort_by = request.args.get('sort_by', 'latest_payment')
    sort_order = request.args.get('sort_order', 'desc')

    filters = {
        'search_query': search_query,
        'payment_status': payment_status_filter,
        'registration_status': registration_status_filter,
        'user_type': user_type_filter,
        'date_range': date_range_filter,
    }
    
    summary = RegistrationPaymentModel.get_transactions_summary()
    pagination = RegistrationPaymentModel.list_transactions_paginated(
        page=page, per_page=per_page, filters=filters, sort_by=sort_by, sort_order=sort_order
    )

    # Get unique user types for filter dropdown
    user_types = RegistrationPaymentModel.get_all_user_types()

    return render_template(
        'transactions.html',
        summary=summary,
        transactions=pagination['items'],
        pagination=pagination,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        user_types=user_types,
        PaymentStatusEnum=RegistrationPaymentModel.PaymentStatus,
        RegistrationStatusEnum=RegistrationPaymentModel.RegistrationStatus,
    )


@superadmin_bp.route('/transactions/<int:transaction_id>')
@admin_login_required
def transaction_details(transaction_id):
    transaction = RegistrationPaymentModel.get_transaction_details(transaction_id)
    if not transaction:
        flash('Transaction not found', 'warning')
        return redirect(url_for('superadmin.transactions'))
    return render_template(
        'transaction_details_modal.html', 
        transaction=transaction, 
        PaymentStatusEnum=RegistrationPaymentModel.PaymentStatus,
        RegistrationStatusEnum=RegistrationPaymentModel.RegistrationStatus,
    )

@superadmin_bp.route('/transactions/export')
@admin_login_required
def export_transactions():
    search_query = request.args.get('q', '').strip()
    payment_status_filter = request.args.get('payment_status', 'All')
    registration_status_filter = request.args.get('registration_status', 'All')
    user_type_filter = request.args.get('user_type', 'All')
    date_range_filter = request.args.get('date_range', 'All')
    sort_by = request.args.get('sort_by', 'latest_payment')
    sort_order = request.args.get('sort_order', 'desc')

    filters = {
        'search_query': search_query,
        'payment_status': payment_status_filter,
        'registration_status': registration_status_filter,
        'user_type': user_type_filter,
        'date_range': date_range_filter,
    }

    csv_buffer = RegistrationPaymentModel.export_transactions_to_csv(filters, sort_by, sort_order)

    response = Response(
        csv_buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=transactions.csv'},
    )
    return response
