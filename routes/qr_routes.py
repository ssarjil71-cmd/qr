from flask import Blueprint, request, current_app, render_template, abort, redirect, url_for
from models.user import UserModel
from models.scan import ScanModel

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
