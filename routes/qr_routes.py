from flask import Blueprint, request, current_app, render_template, abort, redirect, url_for
from models.user import UserModel
from models.scan import ScanModel
from models.qr_identity import QRIdentityModel

qr_bp = Blueprint('qr', __name__, template_folder='../templates')


@qr_bp.route('/scan/<token>')
def scan(token):
    # find user by qr_token
    user_row = UserModel.find_by_qr_token(token)
    if not user_row:
        abort(404)

    user = {
        'id': user_row[0],
        'user_type': user_row[1],
        'name': user_row[2],
        'mobile': user_row[3],
        'email': user_row[4],
        'photo': user_row[6],
        'education': user_row[7],
        'skills': user_row[8],
        'resume': user_row[9],
        'company_name': user_row[11],
        'designation': user_row[12],
        'experience': user_row[13],
        'emergency_contact': user_row[14],
        'blood_group': user_row[15],
        'medical_notes': user_row[16],
        'address': user_row[17],
        'vehicle_number': user_row[18],
    }

    # log scan using ScanModel
    ScanModel.log_scan(user['id'], request.remote_addr, request.headers.get('User-Agent'))

    return redirect(url_for('auth.dashboard_public', token=token))


@qr_bp.route('/profile/<token>')
def profile(token):
    card = QRIdentityModel.find_by_token_and_type(token, QRIdentityModel.PROFILE)
    if not card:
        user_row = UserModel.find_by_qr_token(token)
        if not user_row:
            abort(404)
        user_id = user_row[0]
    else:
        user_id = card[1]
        user_row = UserModel.find_by_id(user_id)
        if not user_row:
            abort(404)
        QRIdentityModel.increment_scan(token, QRIdentityModel.PROFILE)

    ScanModel.log_scan(user_id, request.remote_addr, request.headers.get('User-Agent'))
    return redirect(url_for('auth.dashboard_public', token=token))


@qr_bp.route('/emergency/<token>')
def emergency(token):
    card = QRIdentityModel.find_by_token_and_type(token, QRIdentityModel.EMERGENCY)
    if not card:
        abort(404)
    user_row = UserModel.find_by_id(card[1])
    if not user_row:
        abort(404)

    QRIdentityModel.increment_scan(token, QRIdentityModel.EMERGENCY)
    ScanModel.log_scan(user_row[0], request.remote_addr, request.headers.get('User-Agent'))
    user = {
        'name': user_row[2],
        'user_type': user_row[1],
        'photo': user_row[6],
        'emergency_contact': user_row[14],
        'blood_group': user_row[15],
        'emergency_primary_contact_name': user_row[24] if len(user_row) > 24 else None,
        'emergency_primary_contact_relation': user_row[25] if len(user_row) > 25 else None,
        'emergency_primary_contact_mobile': user_row[26] if len(user_row) > 26 else None,
        'emergency_primary_contact_whatsapp': user_row[27] if len(user_row) > 27 else None,
        'emergency_secondary_contact_name': user_row[28] if len(user_row) > 28 else None,
        'emergency_secondary_contact_relation': user_row[29] if len(user_row) > 29 else None,
        'emergency_secondary_contact_mobile': user_row[30] if len(user_row) > 30 else None,
        'emergency_doctor_name': user_row[31] if len(user_row) > 31 else None,
        'emergency_doctor_phone': user_row[32] if len(user_row) > 32 else None,
        'emergency_address': user_row[33] if len(user_row) > 33 else None,
        'emergency_note': user_row[34] if len(user_row) > 34 else None,
    }
    return render_template('qr/emergency_public.html', user=user, hide_navbar=True)
