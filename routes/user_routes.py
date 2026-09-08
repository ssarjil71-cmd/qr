import os
import textwrap
from datetime import date
from io import BytesIO
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, current_app, send_file, send_from_directory, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from services.auth import login_required
from models.user import UserModel
from models.student_profile import (
    CertificateModel,
    DocumentModel,
    ProjectModel,
    QualificationModel,
    ResumeProfileModel,
    SocialLinkModel,
    StudentProfileModel,
)
from models.employee_profile import EmployeeProfileModel
from services.profile_engine import ProfileEngine
from services.db import get_conn
from models.card_permission import CardPermissionModel, card_permission_required

user_bp = Blueprint('user', __name__, template_folder='../templates')


def _clean_photo(value):
    if not value or str(value).startswith('scrypt:'):
        return None
    cleaned = str(value)
    if cleaned.startswith('static/uploads/'):
        cleaned = cleaned.replace('static/uploads/', '', 1)
    return cleaned


CERTIFICATE_ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
CERTIFICATE_ALLOWED_MIMETYPES = {
    '.pdf': {'application/pdf', 'application/x-pdf'},
    '.jpg': {'image/jpeg'},
    '.jpeg': {'image/jpeg'},
    '.png': {'image/png'},
}
CERTIFICATE_MAX_FILE_SIZE = 5 * 1024 * 1024


def _certificate_file_info(file_storage):
    if not file_storage or not file_storage.filename:
        return None, 'Please choose a certificate document.'
    extension = os.path.splitext(file_storage.filename)[1].lower()
    if extension not in CERTIFICATE_ALLOWED_EXTENSIONS or file_storage.mimetype not in CERTIFICATE_ALLOWED_MIMETYPES[extension]:
        return None, 'Invalid file type. Upload a PDF, JPG, JPEG, or PNG file.'
    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    if size > CERTIFICATE_MAX_FILE_SIZE:
        return None, 'File size exceeds the allowed limit of 5 MB.'
    return extension, None


def _remove_certificate_file(file_path):
    if not file_path:
        return
    relative_path = str(file_path).replace('\\', '/').replace('static/uploads/', '', 1)
    upload_root = os.path.realpath(current_app.config['UPLOAD_FOLDER'])
    full_path = os.path.realpath(os.path.join(upload_root, relative_path))
    if os.path.commonpath([upload_root, full_path]) == upload_root and os.path.isfile(full_path):
        os.remove(full_path)


def _certificate_payload_from_request():
    title = (request.form.get('title') or '').strip()
    issuer = (request.form.get('issuer') or '').strip()
    issue_date = (request.form.get('issue_date') or '').strip()
    expiry_date = (request.form.get('expiry_date') or '').strip()
    credential_url = (request.form.get('credential_url') or '').strip()
    if not title or not issuer or not issue_date:
        return None, 'Title, issuer, and issue date are required.'
    try:
        issue = date.fromisoformat(issue_date)
        expiry = date.fromisoformat(expiry_date) if expiry_date else None
    except ValueError:
        return None, 'Enter valid issue and expiry dates.'
    if expiry and expiry < issue:
        return None, 'Expiry date cannot be earlier than issue date.'
    if credential_url:
        parsed = urlparse(credential_url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            return None, 'Enter a valid credential URL.'
    return {
        'title': title,
        'issuer': issuer,
        'issue_date': issue_date,
        'expiry_date': expiry_date,
        'credential_id': (request.form.get('credential_id') or '').strip(),
        'credential_url': credential_url,
        'description': (request.form.get('description') or '').strip(),
    }, None


def _pdf_escape(value):
    return str(value or '').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _resume_pdf(data):
    user = data.get('user') or {}
    student_profile = data.get('student_profile') or {}
    resume_profile = data.get('resume_profile') or {}
    projects = data.get('projects') or []
    certificates = data.get('certificates') or []
    social_links = data.get('social_links') or []
    lines = [
        user.get('name') or 'Resume',
        resume_profile.get('headline') or resume_profile.get('preferred_role') or '',
        f"Email: {user.get('email') or '-'}   Mobile: {user.get('mobile') or '-'}",
        f"Location: {resume_profile.get('current_city') or user.get('address') or '-'}",
        '',
        'Professional Summary',
        resume_profile.get('summary') or '-',
        '',
        'Education',
        f"{student_profile.get('college') or '-'} | {student_profile.get('branch') or '-'} | {student_profile.get('year') or '-'}",
        f"Roll Number: {student_profile.get('roll_number') or '-'}",
        '',
        'Skills',
        user.get('skills') or '-',
        '',
        'Projects',
    ]
    if projects:
        for project in projects[:5]:
            lines.append(f"- {project.get('title') or '-'}: {project.get('technologies') or ''}")
    else:
        lines.append('- No projects added')
    lines.extend(['', 'Certificates'])
    if certificates:
        for certificate in certificates[:5]:
            lines.append(f"- {certificate.get('title') or '-'} ({certificate.get('issuer') or '-'})")
    else:
        lines.append('- No certificates added')
    lines.extend(['', 'Links'])
    if social_links:
        for link in social_links[:5]:
            lines.append(f"- {link.get('platform') or '-'}: {link.get('profile_url') or '-'}")
    else:
        lines.append('- No links added')

    wrapped = []
    for line in lines:
        wrapped.extend(textwrap.wrap(str(line), width=82) or [''])
    wrapped = wrapped[:45]

    stream_lines = ['BT', '/F1 18 Tf 40 790 Td']
    first = True
    for line in wrapped:
        if first:
            stream_lines.append(f"({_pdf_escape(line)}) Tj")
            first = False
        else:
            stream_lines.append(f"0 -16 Td ({_pdf_escape(line)}) Tj")
        stream_lines.append('/F1 12 Tf')
    stream_lines.append('ET')
    stream = '\n'.join(stream_lines)
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(stream.encode('latin-1', errors='replace'))} >>
stream
{stream}
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
0000000241 00000 n 
0000000000 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""
    return pdf.encode('latin-1', errors='replace')


@user_bp.route('/profile/<int:user_id>')
def profile(user_id):
    row = UserModel.find_by_id(user_id)
    if not row:
        return 'User not found', 404
    user = {
        'id': row[0],
        'user_type': row[1],
        'name': row[2],
        'mobile': row[3],
        'email': row[4],
        'photo': _clean_photo(row[6]),
    }
    return render_template('user/profile.html', user=user)


@user_bp.route('/uploads/<path:filename>')
def uploads(filename):
    if str(filename).replace('\\', '/').startswith('certificate_documents/'):
        return 'Not found', 404
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@user_bp.route('/api/states')
def api_states():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('SELECT id, name FROM states ORDER BY name ASC')
        rows = cur.fetchall()
        items = [{'id': r[0], 'name': r[1]} for r in rows]
        return jsonify(items)
    finally:
        cur.close()


@user_bp.route('/api/districts/<int:state_id>')
def api_districts(state_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('SELECT id, name FROM districts WHERE state_id=%s ORDER BY name ASC', (state_id,))
        rows = cur.fetchall()
        items = [{'id': r[0], 'name': r[1]} for r in rows]
        return jsonify(items)
    finally:
        cur.close()


@user_bp.route('/api/talukas/<int:district_id>')
def api_talukas(district_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('SELECT id, name FROM talukas WHERE district_id=%s ORDER BY name ASC', (district_id,))
        rows = cur.fetchall()
        items = [{'id': r[0], 'name': r[1]} for r in rows]
        return jsonify(items)
    finally:
        cur.close()


@user_bp.route('/student/dashboard')
@login_required
def student_dashboard():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    data = ProfileEngine.build_dashboard_context('student', StudentProfileModel.get_student_dashboard_data(user_id))
    if not data:
        flash('Student profile not found', 'warning')
        return redirect(url_for('auth.dashboard'))
    permissions = CardPermissionModel.get_effective_permissions(user_id)
    data['profile_sections'] = [
        section for section in data.get('profile_sections', [])
        if permissions.get(section.get('key'), {}).get('is_enabled')
    ]
    data['profile_sections'].sort(key=lambda section: permissions.get(section.get('key'), {}).get('display_order', 0))
    return render_template('profile/dashboard.html', hide_navbar=True, **data)


@user_bp.route('/student/dashboard/<section_key>')
@login_required
def student_section_detail(section_key):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    data = ProfileEngine.build_dashboard_context('student', StudentProfileModel.get_student_dashboard_data(user_id))
    if not CardPermissionModel.is_enabled(user_id, section_key):
        flash('Feature not available for this account', 'warning')
        return redirect(url_for('user.student_dashboard'))
    section = next((item for item in data.get('profile_sections', []) if item.get('key') == section_key), None)
    if not section:
        flash('Profile section not found', 'warning')
        return redirect(url_for('user.student_dashboard'))
    certificate_form_mode = request.args.get('certificate_form') if section_key == 'certificates' else None
    certificate_form_certificate = None
    if certificate_form_mode == 'edit':
        certificate_id = request.args.get('certificate_id', type=int)
        certificate_form_certificate = next(
            (item for item in data.get('certificates', []) if item.get('id') == certificate_id),
            None,
        )
        if not certificate_form_certificate:
            flash('Certificate not found', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='certificates'))
    document_form_mode = request.args.get('document_form') if section_key == 'upload_documents' else None
    document_form_document = None
    resume_document_form = request.args.get('resume_document_form') if section_key == 'resume' else None
    if document_form_mode == 'edit':
        document_id = request.args.get('document_id', type=int)
        document_form_document = DocumentModel.get_by_id(user_id, document_id)
        if not document_form_document or document_form_document.get('document_type') == 'certificate':
            flash('Document not found', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='upload_documents'))
    return render_template(
        'profile/section_detail.html',
        section=section,
        certificate_form_mode=certificate_form_mode,
        certificate_form_certificate=certificate_form_certificate,
        document_form_mode=document_form_mode,
        document_form_document=document_form_document,
        resume_document_form=resume_document_form,
        **data,
    )


@user_bp.route('/student/profile/basic-information', methods=['POST'])
@login_required
@card_permission_required('basic_information')
def update_student_basic_information():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))

    photo_path = None
    if 'photo' in request.files:
        photo_file = request.files['photo']
        if photo_file and photo_file.filename:
            allowed_ext = {'jpg', 'jpeg', 'png', 'webp'}
            filename = secure_filename(photo_file.filename)
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if ext not in allowed_ext:
                flash('Only JPG, PNG, and WEBP images are allowed', 'warning')
                return redirect(url_for('user.student_section_detail', section_key='basic_information'))
            if photo_file.content_length and photo_file.content_length > 2 * 1024 * 1024:
                flash('Image size must be 2 MB or less', 'warning')
                return redirect(url_for('user.student_section_detail', section_key='basic_information'))
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            filename = f"user_{user_id}_{os.path.splitext(filename)[0]}_{os.urandom(4).hex()}.{ext}"
            save_path = os.path.join(upload_dir, filename)
            photo_file.save(save_path)
            photo_path = os.path.join('static', 'uploads', 'profiles', filename).replace('\\', '/')

    existing_user = StudentProfileModel._get_user(user_id)

    StudentProfileModel.update_basic_information(
        user_id,
        {
            'name': request.form.get('name'),
            'mobile': request.form.get('mobile'),
            'email': request.form.get('email'),
            'gender': request.form.get('gender'),
            'blood_group': request.form.get('blood_group'),
            'address': request.form.get('address'),
            'photo': photo_path or (existing_user.get('photo') if existing_user else None),
        },
    )
    session['user_name'] = request.form.get('name')
    flash('Basic Information saved successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='basic_information'))


@user_bp.route('/student/profile/emergency-contact', methods=['POST'])
@login_required
@card_permission_required('emergency_contact')
def update_student_emergency_contact():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    StudentProfileModel.update_emergency_contact(
        user_id,
        {
            'emergency_primary_contact_name': request.form.get('emergency_primary_contact_name'),
            'emergency_primary_contact_relation': request.form.get('emergency_primary_contact_relation'),
            'emergency_primary_contact_mobile': request.form.get('emergency_primary_contact_mobile'),
            'emergency_primary_contact_whatsapp': request.form.get('emergency_primary_contact_whatsapp'),
            'emergency_secondary_contact_name': request.form.get('emergency_secondary_contact_name'),
            'emergency_secondary_contact_relation': request.form.get('emergency_secondary_contact_relation'),
            'emergency_secondary_contact_mobile': request.form.get('emergency_secondary_contact_mobile'),
            'emergency_doctor_name': request.form.get('emergency_doctor_name'),
            'emergency_doctor_phone': request.form.get('emergency_doctor_phone'),
            'emergency_address': request.form.get('emergency_address'),
            'emergency_note': request.form.get('emergency_note'),
        },
    )
    flash('Emergency Contact saved successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='emergency_contact'))


@user_bp.route('/student/profile/medical-report', methods=['POST'])
@login_required
@card_permission_required('medical_report')
def update_student_medical_report():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    medicines = []
    for name, dosage, frequency, purpose in zip(
        request.form.getlist('medicine_name[]'),
        request.form.getlist('dosage[]'),
        request.form.getlist('frequency[]'),
        request.form.getlist('purpose[]'),
    ):
        medicines.append({
            'medicine_name': (name or '').strip(),
            'dosage': (dosage or '').strip(),
            'frequency': (frequency or '').strip(),
            'purpose': (purpose or '').strip(),
        })
    vaccinations = []
    for name, dose, vaccination_date, next_due_date in zip(
        request.form.getlist('vaccine_name[]'),
        request.form.getlist('dose[]'),
        request.form.getlist('vaccination_date[]'),
        request.form.getlist('next_due_date[]'),
    ):
        vaccinations.append({
            'vaccine_name': (name or '').strip(),
            'dose': (dose or '').strip(),
            'vaccination_date': vaccination_date,
            'next_due_date': next_due_date,
        })

    medical_document_types = {
        'blood_test_report',
        'x_ray',
        'ecg',
        'prescription',
        'medical_certificate',
        'other_medical_report',
    }
    documents = []
    files = request.files.getlist('medical_file[]')
    names = request.form.getlist('document_name[]')
    types = request.form.getlist('document_type[]')
    dates = request.form.getlist('document_date[]')
    descriptions = request.form.getlist('description[]')
    allowed_ext = {'.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx'}
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'medical_documents')
    os.makedirs(upload_dir, exist_ok=True)
    for index, document_file in enumerate(files):
        if not document_file or not document_file.filename:
            continue
        document_type = types[index] if index < len(types) else ''
        if document_type not in medical_document_types:
            flash('Select a valid medical document type', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='medical_report'))
        original_name = document_file.filename or ''
        extension = os.path.splitext(original_name)[1].lower()
        if extension not in allowed_ext:
            flash('Medical documents must be PDF, image, DOC, or DOCX files', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='medical_report'))
        safe_stem = secure_filename(os.path.splitext(original_name)[0]) or document_type
        filename = f"user_{user_id}_{document_type}_{safe_stem}_{os.urandom(4).hex()}{extension}"
        save_path = os.path.join(upload_dir, filename)
        document_file.save(save_path)
        documents.append({
            'document_name': (names[index] if index < len(names) else '') or safe_stem,
            'document_type': document_type,
            'document_date': dates[index] if index < len(dates) else None,
            'description': descriptions[index] if index < len(descriptions) else None,
            'file_path': os.path.join('static', 'uploads', 'medical_documents', filename).replace('\\', '/'),
        })

    StudentProfileModel.update_medical_report(
        user_id,
        {
            'blood_group': request.form.get('blood_group'),
            'height': request.form.get('height'),
            'weight': request.form.get('weight'),
            'blood_pressure': request.form.get('blood_pressure'),
            'pulse_rate': request.form.get('pulse_rate'),
            'spo2': request.form.get('spo2'),
            'body_temperature': request.form.get('body_temperature'),
            'last_health_checkup_date': request.form.get('last_health_checkup_date'),
            'has_allergies': request.form.get('has_allergies'),
            'drug_allergies': request.form.get('drug_allergies'),
            'food_allergies': request.form.get('food_allergies'),
            'other_allergies': request.form.get('other_allergies'),
            'allergy_details': request.form.get('allergy_details'),
            'diabetes': request.form.get('diabetes'),
            'hypertension': request.form.get('hypertension'),
            'heart_disease': request.form.get('heart_disease'),
            'asthma': request.form.get('asthma'),
            'epilepsy': request.form.get('epilepsy'),
            'kidney_disease': request.form.get('kidney_disease'),
            'other_medical_condition': request.form.get('other_medical_condition'),
            'previous_surgery': request.form.get('previous_surgery'),
            'surgery_details': request.form.get('surgery_details'),
            'currently_taking_medicines': request.form.get('currently_taking_medicines'),
            'vaccination_status': request.form.get('vaccination_status'),
            'medicines': medicines,
            'vaccinations': vaccinations,
            'documents': documents,
        },
    )
    flash('Medical Report saved successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='medical_report'))


@user_bp.route('/student/profile/medical-report/document/<int:document_id>/delete', methods=['POST'])
@login_required
@card_permission_required('medical_report')
def delete_student_medical_document(document_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = StudentProfileModel.delete_medical_document(user_id, document_id)
    flash('Medical document deleted successfully' if deleted else 'Medical document not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='medical_report'))


@user_bp.route('/student/profile/visibility/<section_key>', methods=['POST'])
@login_required
def update_student_section_visibility(section_key):
    user_id = session.get('user_id')
    profile_model = StudentProfileModel
    profile_type = 'student'
    if EmployeeProfileModel.has_employee_profile(user_id):
        profile_model = EmployeeProfileModel
        profile_type = 'employee'
    elif not StudentProfileModel.has_student_profile(user_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Profile is not available for this account'}), 403
        flash('Profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    is_visible = (request.form.getlist('is_visible') or ['0'])[-1] == '1'
    if not profile_model.set_section_visibility(user_id, section_key, is_visible, profile_type=profile_type):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid profile section'}), 400
        flash('Invalid profile section', 'warning')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'is_visible': is_visible})
    return redirect(url_for('employee.employee_dashboard') if profile_type == 'employee' else url_for('user.student_dashboard'))


@user_bp.route('/student/profile/academic-information', methods=['POST'])
@login_required
@card_permission_required('academic_information')
def update_student_academic_information():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    success, message = StudentProfileModel.update_academic_information(
        user_id,
        {
            'college': request.form.get('college'),
            'branch': request.form.get('branch'),
            'year': request.form.get('year'),
            'roll_number': request.form.get('roll_number'),
            'bio': request.form.get('bio'),
        },
    )
    if success:
        flash('Academic Information saved successfully', 'success')
    else:
        flash(message, 'warning')
    return redirect(url_for('user.student_section_detail', section_key='academic_information'))


def _qualification_payload():
    return {
        'qualification': request.form.get('qualification', '').strip(),
        'specialization': request.form.get('specialization', '').strip(),
        'institution': request.form.get('institution', '').strip(),
        'board_university': request.form.get('board_university', '').strip(),
        'passing_year': request.form.get('passing_year', '').strip(),
        'percentage_cgpa': request.form.get('percentage_cgpa', '').strip(),
        'grade_class': request.form.get('grade_class', '').strip(),
        'qualification_type': request.form.get('qualification_type', '').strip(),
    }


@user_bp.route('/student/profile/qualifications', methods=['POST'])
@login_required
@card_permission_required('academic_information')
def add_student_qualification():
    user_id = session.get('user_id')
    payload = _qualification_payload()
    if not payload['qualification'] or not payload['institution']:
        flash('Qualification and institution are required', 'warning')
    elif QualificationModel.add_previous_qualification(user_id, payload):
        flash('Qualification added successfully', 'success')
    else:
        flash('Student profile is not available for this account', 'warning')
    return redirect(url_for('user.student_section_detail', section_key='academic_information'))


@user_bp.route('/student/profile/qualifications/<int:qualification_id>', methods=['POST'])
@login_required
@card_permission_required('academic_information')
def update_student_qualification(qualification_id):
    user_id = session.get('user_id')
    payload = _qualification_payload()
    if not payload['qualification'] or not payload['institution']:
        flash('Qualification and institution are required', 'warning')
    elif QualificationModel.update_previous_qualification(user_id, qualification_id, payload):
        flash('Qualification updated successfully', 'success')
    else:
        flash('Qualification not found', 'warning')
    return redirect(url_for('user.student_section_detail', section_key='academic_information'))


@user_bp.route('/student/profile/qualifications/<int:qualification_id>/delete', methods=['POST'])
@login_required
@card_permission_required('academic_information')
def delete_student_qualification(qualification_id):
    user_id = session.get('user_id')
    if QualificationModel.delete_previous_qualification(user_id, qualification_id):
        flash('Qualification deleted successfully', 'success')
    else:
        flash('Qualification not found', 'warning')
    return redirect(url_for('user.student_section_detail', section_key='academic_information'))


@user_bp.route('/student/profile/academic-information/delete', methods=['POST'])
@login_required
@card_permission_required('academic_information')
def delete_student_academic_information():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    StudentProfileModel.clear_academic_information(user_id)
    flash('Academic Information deleted successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='academic_information'))


@user_bp.route('/student/profile/skills', methods=['POST'])
@login_required
@card_permission_required('skills')
def update_student_skills():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    categories = {
        'Technical Skill', 'Professional Skill', 'Soft Skill', 'Communication', 'Language',
        'Leadership', 'Management', 'Creative Skill', 'Design', 'Business & Entrepreneurship',
        'Analytical Skill', 'Research', 'Teaching & Training', 'Healthcare & Medical',
        'Laboratory & Science', 'Agriculture', 'Legal', 'Finance & Accounting',
        'Marketing & Sales', 'Hospitality & Tourism', 'Sports & Fitness',
        'Skilled Trade / Vocational', 'Computer & IT', 'Other',
    }
    legacy_it_categories = {
        'Programming Language', 'Framework', 'Database', 'Web Technology', 'Mobile Development',
        'Cloud', 'DevOps', 'Cyber Security', 'Data Science / AI', 'Testing',
    }
    proficiency_levels = {'Beginner', 'Intermediate', 'Advanced', 'Expert'}
    language_levels = {'Basic', 'Good', 'Excellent', ''}

    def clean_years(value):
        value = (value or '').strip()
        if not value:
            return ''
        try:
            number = float(value)
        except ValueError:
            return None
        return value if number >= 0 else None

    technical_skills = []
    seen_technical = set()
    for name, category, proficiency, years in zip(
        request.form.getlist('technical_skill_name[]'),
        request.form.getlist('technical_skill_category[]'),
        request.form.getlist('technical_proficiency_level[]'),
        request.form.getlist('technical_years_experience[]'),
    ):
        name = (name or '').strip()
        category = (category or '').strip()
        if category in legacy_it_categories:
            category = 'Computer & IT'
        proficiency = (proficiency or '').strip()
        years = clean_years(years)
        if not any([name, category, proficiency, years]):
            continue
        if not name:
            flash('Technical skill name cannot be empty', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        if category not in categories:
            flash('Select a valid technical skill category', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        if proficiency not in proficiency_levels:
            flash('Select a valid technical skill proficiency level', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        if years is None:
            flash('Years of experience cannot be negative', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        key = (name.lower(), category.lower())
        if key in seen_technical:
            flash('Duplicate technical skills are not allowed', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        seen_technical.add(key)
        technical_skills.append({'skill_name': name, 'skill_category': category, 'proficiency_level': proficiency, 'years_experience': years})

    soft_skills = []
    seen_soft = set()
    for value in request.form.getlist('soft_skills[]') + request.form.getlist('custom_soft_skills[]'):
        name = (value or '').strip()
        if not name:
            continue
        key = name.lower()
        if key in seen_soft:
            continue
        seen_soft.add(key)
        soft_skills.append({'skill_name': name})

    skill_tools = []
    seen_tools = set()
    for name, proficiency, years in zip(
        request.form.getlist('tool_name[]'),
        request.form.getlist('tool_proficiency_level[]'),
        request.form.getlist('tool_years_experience[]'),
    ):
        name = (name or '').strip()
        proficiency = (proficiency or '').strip()
        years = clean_years(years)
        if not any([name, proficiency, years]):
            continue
        if not name:
            flash('Tool/Software name cannot be empty', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        if proficiency and proficiency not in proficiency_levels:
            flash('Select a valid tool proficiency level', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        if years is None:
            flash('Years of experience cannot be negative', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        key = name.lower()
        if key in seen_tools:
            flash('Duplicate tools are not allowed', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        seen_tools.add(key)
        skill_tools.append({'tool_name': name, 'proficiency_level': proficiency, 'years_experience': years})

    languages = []
    seen_languages = set()
    for name, reading, writing, speaking in zip(
        request.form.getlist('language_name[]'),
        request.form.getlist('reading_level[]'),
        request.form.getlist('writing_level[]'),
        request.form.getlist('speaking_level[]'),
    ):
        name = (name or '').strip()
        reading = (reading or '').strip()
        writing = (writing or '').strip()
        speaking = (speaking or '').strip()
        if not any([name, reading, writing, speaking]):
            continue
        if not name:
            flash('Language name cannot be empty', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        if reading not in language_levels or writing not in language_levels or speaking not in language_levels:
            flash('Select valid language levels', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        key = name.lower()
        if key in seen_languages:
            flash('Duplicate languages are not allowed', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='skills'))
        seen_languages.add(key)
        languages.append({'language_name': name, 'reading_level': reading, 'writing_level': writing, 'speaking_level': speaking})

    success, message = StudentProfileModel.update_skills(
        user_id,
        {
            'technical_skills': technical_skills,
            'soft_skills': soft_skills,
            'skill_tools': skill_tools,
            'languages': languages,
        },
    )
    flash('Skills saved successfully' if success else f'Could not save skills: {message}', 'success' if success else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='skills'))


@user_bp.route('/student/profile/skills/delete', methods=['POST'])
@login_required
@card_permission_required('skills')
def delete_student_skills():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    StudentProfileModel.clear_skills(user_id)
    flash('Skills deleted successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='skills'))


@user_bp.route('/student/profile/certificates', methods=['POST'])
@login_required
@card_permission_required('certificates')
def update_student_certificates():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    payload, error = _certificate_payload_from_request()
    if error:
        flash(error, 'warning')
        return redirect(url_for('user.student_section_detail', section_key='certificates'))
    document_file = request.files.get('document_file')
    extension, error = _certificate_file_info(document_file) if document_file and document_file.filename else (None, None)
    if error:
        flash(error, 'warning')
        return redirect(url_for('user.student_section_detail', section_key='certificates', certificate_form='add'))
    document_id = None
    saved_path = None
    if document_file and document_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificate_documents')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f'user_{user_id}_{os.urandom(16).hex()}{extension}'
        saved_path = os.path.join(upload_dir, filename)
        document_file.save(saved_path)
        document_id = DocumentModel.upsert(
            user_id=user_id,
            document_type='certificate',
            title=payload['title'],
            file_path=os.path.join('static', 'uploads', 'certificate_documents', filename).replace('\\', '/'),
            notes=payload['description'],
        )
        payload['document_id'] = document_id
    try:
        CertificateModel.create(user_id, payload)
    except Exception:
        if document_id:
            DocumentModel.delete(user_id, document_id)
        if saved_path and os.path.isfile(saved_path):
            os.remove(saved_path)
        raise
    flash('Certificate added successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='certificates'))


@user_bp.route('/student/profile/certificates/<int:certificate_id>', methods=['POST'])
@login_required
@card_permission_required('certificates')
def edit_student_certificate(certificate_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    payload, error = _certificate_payload_from_request()
    if error:
        flash(error, 'warning')
        return redirect(url_for('user.student_section_detail', section_key='certificates'))
    existing = next(
        (item for item in StudentProfileModel.get_student_dashboard_data(user_id).get('certificates', []) if item.get('id') == certificate_id),
        None,
    )
    if not existing:
        flash('Certificate not found', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='certificates'))
    payload['credential_id'] = existing.get('credential_id')
    payload['credential_url'] = existing.get('credential_url')
    document_file = request.files.get('document_file')
    extension, error = _certificate_file_info(document_file) if document_file and document_file.filename else (None, None)
    if error:
        flash(error, 'warning')
        return redirect(url_for('user.student_section_detail', section_key='certificates', certificate_form='edit', certificate_id=certificate_id))
    old_document_path = existing.get('document_path')
    old_document_id = existing.get('document_id')
    saved_path = None
    if document_file and document_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificate_documents')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f'user_{user_id}_{os.urandom(16).hex()}{extension}'
        saved_path = os.path.join(upload_dir, filename)
        document_file.save(saved_path)
        payload['document_id'] = DocumentModel.upsert(
            user_id=user_id,
            document_type='certificate',
            title=payload['title'],
            file_path=os.path.join('static', 'uploads', 'certificate_documents', filename).replace('\\', '/'),
            notes=payload['description'],
        )
    elif request.form.get('remove_document') == '1':
        payload['remove_document'] = True
    try:
        updated = CertificateModel.update(user_id, certificate_id, payload)
    except Exception:
        if payload.get('document_id'):
            DocumentModel.delete(user_id, payload['document_id'])
        if saved_path and os.path.isfile(saved_path):
            os.remove(saved_path)
        raise
    if not updated and saved_path and os.path.isfile(saved_path):
        os.remove(saved_path)
    if updated and (payload.get('document_id') or payload.get('remove_document')):
        _remove_certificate_file(old_document_path)
    flash('Certificate updated successfully' if updated else 'Certificate not found', 'success' if updated else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='certificates'))


@user_bp.route('/student/profile/certificates/<int:certificate_id>/delete', methods=['POST'])
@login_required
@card_permission_required('certificates')
def delete_student_certificate(certificate_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    existing = next(
        (item for item in StudentProfileModel.get_student_dashboard_data(user_id).get('certificates', []) if item.get('id') == certificate_id),
        None,
    )
    deleted = CertificateModel.delete(user_id, certificate_id)
    if deleted and existing:
        _remove_certificate_file(existing.get('document_path'))
    flash('Certificate deleted successfully' if deleted else 'Certificate not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='certificates'))


@user_bp.route('/student/profile/certificates/<int:certificate_id>/document')
@login_required
@card_permission_required('certificates')
def view_student_certificate_document(certificate_id):
    user_id = session.get('user_id')
    data = StudentProfileModel.get_student_dashboard_data(user_id)
    certificate = next((item for item in data.get('certificates', []) if item.get('id') == certificate_id), None)
    if not certificate or not certificate.get('document_path'):
        return 'Certificate document not found', 404
    upload_root = os.path.realpath(current_app.config['UPLOAD_FOLDER'])
    file_path = str(certificate['document_path']).replace('static/uploads/', '').replace('\\', '/')
    full_path = os.path.realpath(os.path.join(upload_root, file_path))
    if os.path.commonpath([upload_root, full_path]) != upload_root or not os.path.isfile(full_path):
        return 'Certificate document not found', 404
    return send_file(full_path, as_attachment=False, download_name=os.path.basename(full_path))


@user_bp.route('/student/profile/upload-documents', methods=['POST'])
@login_required
@card_permission_required('upload_documents')
def upload_student_document():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))

    document_types = {
        'caste_certificate': 'Caste Certificate',
        'domicile': 'Domicile Certificate',
        'nationality': 'Nationality Certificate',
        'mark_sheet': 'Mark Sheet',
        'aadhaar_card': 'Aadhaar Card',
        'degree_certificate': 'Degree Certificate',
    }
    document_type = (request.form.get('document_type') or '').strip()
    title = (request.form.get('title') or document_types.get(document_type, '')).strip()
    document_file = request.files.get('document_file')

    if document_type not in document_types:
        flash('Select a valid document type', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='upload_documents'))
    if not title:
        flash('Document title is required', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='upload_documents', document_form='add'))
    if not document_file or not document_file.filename:
        flash('Please choose a PDF document', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='upload_documents'))

    original_name = document_file.filename or ''
    extension = os.path.splitext(original_name)[1].lower()
    if extension != '.pdf' or document_file.mimetype not in ('application/pdf', 'application/x-pdf'):
        flash('Only PDF documents are allowed', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='upload_documents'))

    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents')
    os.makedirs(upload_dir, exist_ok=True)
    safe_stem = secure_filename(os.path.splitext(original_name)[0]) or document_type
    filename = f"user_{user_id}_{document_type}_{safe_stem}_{os.urandom(4).hex()}.pdf"
    save_path = os.path.join(upload_dir, filename)
    document_file.save(save_path)
    file_path = os.path.join('static', 'uploads', 'documents', filename).replace('\\', '/')

    try:
        DocumentModel.create(
            user_id=user_id,
            document_type=document_type,
            title=title or document_types[document_type],
            file_path=file_path,
            notes=request.form.get('notes'),
        )
    except Exception:
        if os.path.isfile(save_path):
            os.remove(save_path)
        raise
    flash('Document uploaded successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='upload_documents'))


@user_bp.route('/student/profile/upload-documents/<int:document_id>', methods=['POST'])
@login_required
@card_permission_required('upload_documents')
def edit_student_document(document_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    existing = DocumentModel.get_by_id(user_id, document_id)
    if not existing or existing.get('document_type') == 'certificate':
        flash('Document not found', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='upload_documents'))
    document_types = {
        'caste_certificate': 'Caste Certificate', 'domicile': 'Domicile',
        'nationality': 'Nationality Certificate', 'mark_sheet': 'Mark Sheet',
        'aadhaar_card': 'Aadhaar Card', 'degree_certificate': 'Degree Certificate',
    }
    document_type = (request.form.get('document_type') or '').strip()
    title = (request.form.get('title') or '').strip()
    if document_type not in document_types or not title:
        flash('Document type and title are required', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='upload_documents', document_form='edit', document_id=document_id))
    document_file = request.files.get('document_file')
    new_path = None
    new_save_path = None
    if document_file and document_file.filename:
        extension = os.path.splitext(document_file.filename)[1].lower()
        if extension != '.pdf' or document_file.mimetype not in ('application/pdf', 'application/x-pdf'):
            flash('Only PDF documents are allowed', 'warning')
            return redirect(url_for('user.student_section_detail', section_key='upload_documents', document_form='edit', document_id=document_id))
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f'user_{user_id}_{document_type}_{os.urandom(16).hex()}.pdf'
        new_save_path = os.path.join(upload_dir, filename)
        document_file.save(new_save_path)
        new_path = os.path.join('static', 'uploads', 'documents', filename).replace('\\', '/')
    try:
        updated = DocumentModel.update(user_id, document_id, document_type, title, request.form.get('notes'), new_path)
    except Exception:
        if new_save_path and os.path.isfile(new_save_path):
            os.remove(new_save_path)
        raise
    if updated and new_path:
        _remove_certificate_file(existing.get('file_path'))
    flash('Document updated successfully' if updated else 'Document not found', 'success' if updated else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='upload_documents'))


@user_bp.route('/student/profile/upload-documents/<int:document_id>/delete', methods=['POST'])
@login_required
@card_permission_required('upload_documents')
def delete_student_document(document_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    existing = DocumentModel.get_by_id(user_id, document_id)
    if existing and existing.get('document_type') == 'certificate':
        existing = None
    deleted = DocumentModel.delete(user_id, document_id) if existing else False
    if deleted:
        _remove_certificate_file(existing.get('file_path'))
    flash('Document deleted successfully' if deleted else 'Document not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='upload_documents'))


@user_bp.route('/student/profile/resume', methods=['POST'])
@login_required
@card_permission_required('resume')
def update_student_resume():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    ResumeProfileModel.save(
        user_id,
        {
            'headline': request.form.get('headline'),
            'summary': request.form.get('summary'),
            'current_city': request.form.get('current_city'),
            'preferred_role': request.form.get('preferred_role'),
            'linkedin_url': request.form.get('linkedin_url'),
            'github_url': request.form.get('github_url'),
            'document_url': request.form.get('document_url'),
        },
    )
    flash('Resume saved successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='resume'))


@user_bp.route('/student/profile/resume/document', methods=['POST'])
@login_required
@card_permission_required('resume')
def upload_student_resume_document():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    resume_file = request.files.get('resume_file')
    if not resume_file or not resume_file.filename:
        flash('Please choose a PDF resume', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='resume', resume_document_form='upload'))
    extension = os.path.splitext(resume_file.filename)[1].lower()
    if extension != '.pdf' or resume_file.mimetype not in ('application/pdf', 'application/x-pdf'):
        flash('Only PDF resumes are allowed', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='resume', resume_document_form='upload'))
    resume_file.stream.seek(0, os.SEEK_END)
    file_size = resume_file.stream.tell()
    resume_file.stream.seek(0)
    if file_size > 5 * 1024 * 1024:
        flash('Resume file size exceeds the allowed limit of 5 MB', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='resume', resume_document_form='upload'))
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'resume_documents')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f'user_{user_id}_{os.urandom(16).hex()}.pdf'
    save_path = os.path.join(upload_dir, filename)
    resume_file.save(save_path)
    file_path = os.path.join('static', 'uploads', 'resume_documents', filename).replace('\\', '/')
    try:
        old_document = ResumeProfileModel.attach_document(user_id, file_path)
    except Exception:
        if os.path.isfile(save_path):
            os.remove(save_path)
        raise
    if old_document:
        _remove_certificate_file(old_document.get('file_path'))
    flash('Resume uploaded successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='resume'))


@user_bp.route('/student/profile/resume/document')
@login_required
@card_permission_required('resume')
def view_student_resume_document():
    user_id = session.get('user_id')
    resume = StudentProfileModel._get_resume_profile(user_id)
    if not resume or not resume.get('document_path'):
        return 'Resume document not found', 404
    upload_root = os.path.realpath(current_app.config['UPLOAD_FOLDER'])
    relative_path = str(resume['document_path']).replace('static/uploads/', '').replace('\\', '/')
    file_path = os.path.realpath(os.path.join(upload_root, relative_path))
    if os.path.commonpath([upload_root, file_path]) != upload_root or not os.path.isfile(file_path):
        return 'Resume document not found', 404
    return send_file(file_path, as_attachment=False, download_name=os.path.basename(file_path))


@user_bp.route('/student/profile/resume/document/delete', methods=['POST'])
@login_required
@card_permission_required('resume')
def delete_student_resume_document():
    user_id = session.get('user_id')
    document = ResumeProfileModel.detach_document(user_id)
    if document:
        _remove_certificate_file(document.get('file_path'))
        flash('Resume document deleted successfully', 'success')
    else:
        flash('Resume document not found', 'warning')
    return redirect(url_for('user.student_section_detail', section_key='resume'))


@user_bp.route('/student/profile/resume/download')
@login_required
@card_permission_required('resume')
def download_student_resume():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    data = StudentProfileModel.get_student_dashboard_data(user_id)
    if not data:
        flash('Student profile not found', 'warning')
        return redirect(url_for('user.student_dashboard'))
    buf = BytesIO(_resume_pdf(data))
    buf.seek(0)
    filename = f"{(data.get('user') or {}).get('name') or 'resume'}_resume.pdf".replace(' ', '_')
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)


@user_bp.route('/student/profile/resume/public-download/<token>')
def public_download_student_resume(token):
    row = UserModel.find_by_qr_token(token)
    if not row or row[1] != 'student':
        return 'Resume not found', 404
    data = StudentProfileModel.get_student_dashboard_data(row[0])
    if not data or 'resume' not in data.get('visible_section_keys', set()):
        return 'Resume not available', 404
    buf = BytesIO(_resume_pdf(data))
    buf.seek(0)
    filename = f"{(data.get('user') or {}).get('name') or 'resume'}_resume.pdf".replace(' ', '_')
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)


@user_bp.route('/student/profile/resume/delete', methods=['POST'])
@login_required
@card_permission_required('resume')
def delete_student_resume():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    document = ResumeProfileModel.detach_document(user_id)
    if document:
        _remove_certificate_file(document.get('file_path'))
        flash('Resume document deleted successfully', 'success')
    else:
        flash('Resume document not found', 'warning')
    return redirect(url_for('user.student_section_detail', section_key='resume'))


@user_bp.route('/student/profile/projects', methods=['POST'])
@login_required
@card_permission_required('projects')
def create_student_project():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Project title is required', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='projects'))
    ProjectModel.create(
        user_id,
        {
            'title': title,
            'role_name': request.form.get('role_name'),
            'technologies': request.form.get('technologies'),
            'project_url': request.form.get('project_url'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'description': request.form.get('description'),
        },
    )
    flash('Project created successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='projects'))


@user_bp.route('/student/profile/projects/<int:project_id>', methods=['POST'])
@login_required
@card_permission_required('projects')
def edit_student_project(project_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Project title is required', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='projects'))
    updated = ProjectModel.update(
        user_id,
        project_id,
        {
            'title': title,
            'role_name': request.form.get('role_name'),
            'technologies': request.form.get('technologies'),
            'project_url': request.form.get('project_url'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'description': request.form.get('description'),
        },
    )
    flash('Project updated successfully' if updated else 'Project not found', 'success' if updated else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='projects'))


@user_bp.route('/student/profile/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@card_permission_required('projects')
def delete_student_project(project_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = ProjectModel.delete(user_id, project_id)
    flash('Project deleted successfully' if deleted else 'Project not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='projects'))


@user_bp.route('/student/profile/social-links', methods=['POST'])
@login_required
@card_permission_required('social_links')
def create_student_social_link():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    platform = (request.form.get('platform') or '').strip()
    profile_url = (request.form.get('profile_url') or '').strip()
    if not platform or not profile_url:
        flash('Platform and profile URL are required', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='social_links'))
    SocialLinkModel.create(
        user_id,
        {
            'platform': platform,
            'username': request.form.get('username'),
            'profile_url': profile_url,
        },
    )
    flash('Social link created successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='social_links'))


@user_bp.route('/student/profile/social-links/<int:social_link_id>', methods=['POST'])
@login_required
@card_permission_required('social_links')
def edit_student_social_link(social_link_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    platform = (request.form.get('platform') or '').strip()
    profile_url = (request.form.get('profile_url') or '').strip()
    if not platform or not profile_url:
        flash('Platform and profile URL are required', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='social_links'))
    updated = SocialLinkModel.update(
        user_id,
        social_link_id,
        {
            'platform': platform,
            'username': request.form.get('username'),
            'profile_url': profile_url,
        },
    )
    flash('Social link updated successfully' if updated else 'Social link not found', 'success' if updated else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='social_links'))


@user_bp.route('/student/profile/social-links/<int:social_link_id>/delete', methods=['POST'])
@login_required
@card_permission_required('social_links')
def delete_student_social_link(social_link_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = SocialLinkModel.delete(user_id, social_link_id)
    flash('Social link deleted successfully' if deleted else 'Social link not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='social_links'))
