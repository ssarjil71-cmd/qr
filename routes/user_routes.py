import os
import textwrap
from io import BytesIO

from flask import Blueprint, render_template, request, current_app, send_file, send_from_directory, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from services.auth import login_required
from models.user import UserModel
from models.student_profile import (
    CertificateModel,
    DocumentModel,
    ProjectModel,
    ResumeProfileModel,
    SocialLinkModel,
    StudentProfileModel,
)
from services.profile_engine import ProfileEngine

user_bp = Blueprint('user', __name__, template_folder='../templates')


def _clean_photo(value):
    if not value or str(value).startswith('scrypt:'):
        return None
    cleaned = str(value)
    if cleaned.startswith('static/uploads/'):
        cleaned = cleaned.replace('static/uploads/', '', 1)
    return cleaned


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
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


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
    return render_template('profile/dashboard.html', **data)


@user_bp.route('/student/dashboard/<section_key>')
@login_required
def student_section_detail(section_key):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    data = ProfileEngine.build_dashboard_context('student', StudentProfileModel.get_student_dashboard_data(user_id))
    section = next((item for item in data.get('profile_sections', []) if item.get('key') == section_key), None)
    if not section:
        flash('Profile section not found', 'warning')
        return redirect(url_for('user.student_dashboard'))
    return render_template('profile/section_detail.html', section=section, **data)


@user_bp.route('/student/profile/basic-information', methods=['POST'])
@login_required
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
            'dob': request.form.get('dob'),
            'gender': request.form.get('gender'),
            'blood_group': request.form.get('blood_group'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'pin_code': request.form.get('pin_code'),
            'nationality': request.form.get('nationality'),
            'photo': photo_path or (existing_user.get('photo') if existing_user else None),
        },
    )
    session['user_name'] = request.form.get('name')
    flash('Basic Information saved successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='basic_information'))


@user_bp.route('/student/profile/emergency-contact', methods=['POST'])
@login_required
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
def update_student_medical_report():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    StudentProfileModel.update_medical_report(
        user_id,
        {'medical_notes': request.form.get('medical_notes')},
    )
    flash('Medical Report saved successfully', 'success')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/visibility/<section_key>', methods=['POST'])
@login_required
def update_student_section_visibility(section_key):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Student profile is not available for this account'}), 403
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    is_visible = (request.form.getlist('is_visible') or ['0'])[-1] == '1'
    if not StudentProfileModel.set_section_visibility(user_id, section_key, is_visible):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid profile section'}), 400
        flash('Invalid profile section', 'warning')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'is_visible': is_visible})
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/academic-information', methods=['POST'])
@login_required
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
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/academic-information/delete', methods=['POST'])
@login_required
def delete_student_academic_information():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    StudentProfileModel.clear_academic_information(user_id)
    flash('Academic Information deleted successfully', 'success')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/skills', methods=['POST'])
@login_required
def update_student_skills():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    StudentProfileModel.update_skills(user_id, {'skills': request.form.get('skills')})
    flash('Skills saved successfully', 'success')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/skills/delete', methods=['POST'])
@login_required
def delete_student_skills():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    StudentProfileModel.clear_skills(user_id)
    flash('Skills deleted successfully', 'success')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/certificates', methods=['POST'])
@login_required
def update_student_certificates():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Certificate title is required', 'warning')
        return redirect(url_for('user.student_dashboard'))
    CertificateModel.create(
        user_id,
        {
            'title': title,
            'issuer': request.form.get('issuer'),
            'issue_date': request.form.get('issue_date'),
            'expiry_date': request.form.get('expiry_date'),
            'credential_id': request.form.get('credential_id'),
            'credential_url': request.form.get('credential_url'),
            'document_url': request.form.get('document_url'),
            'description': request.form.get('description'),
        },
    )
    flash('Certificate created successfully', 'success')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/certificates/<int:certificate_id>', methods=['POST'])
@login_required
def edit_student_certificate(certificate_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Certificate title is required', 'warning')
        return redirect(url_for('user.student_dashboard'))
    updated = CertificateModel.update(
        user_id,
        certificate_id,
        {
            'title': title,
            'issuer': request.form.get('issuer'),
            'issue_date': request.form.get('issue_date'),
            'expiry_date': request.form.get('expiry_date'),
            'credential_id': request.form.get('credential_id'),
            'credential_url': request.form.get('credential_url'),
            'document_url': request.form.get('document_url'),
            'description': request.form.get('description'),
        },
    )
    flash('Certificate updated successfully' if updated else 'Certificate not found', 'success' if updated else 'warning')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/certificates/<int:certificate_id>/delete', methods=['POST'])
@login_required
def delete_student_certificate(certificate_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = CertificateModel.delete(user_id, certificate_id)
    flash('Certificate deleted successfully' if deleted else 'Certificate not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/upload-documents', methods=['POST'])
@login_required
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
    }
    document_type = (request.form.get('document_type') or '').strip()
    title = (request.form.get('title') or document_types.get(document_type, '')).strip()
    document_file = request.files.get('document_file')

    if document_type not in document_types:
        flash('Select a valid document type', 'warning')
        return redirect(url_for('user.student_section_detail', section_key='upload_documents'))
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

    DocumentModel.upsert(
        user_id=user_id,
        document_type=document_type,
        title=title or document_types[document_type],
        file_path=file_path,
        notes=request.form.get('notes'),
    )
    flash('Document uploaded successfully', 'success')
    return redirect(url_for('user.student_section_detail', section_key='upload_documents'))


@user_bp.route('/student/profile/upload-documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_student_document(document_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = DocumentModel.delete(user_id, document_id)
    flash('Document deleted successfully' if deleted else 'Document not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_section_detail', section_key='upload_documents'))


@user_bp.route('/student/profile/resume', methods=['POST'])
@login_required
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


@user_bp.route('/student/profile/resume/download')
@login_required
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
def delete_student_resume():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    ResumeProfileModel.delete(user_id)
    flash('Resume deleted successfully', 'success')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/projects', methods=['POST'])
@login_required
def create_student_project():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Project title is required', 'warning')
        return redirect(url_for('user.student_dashboard'))
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
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/projects/<int:project_id>', methods=['POST'])
@login_required
def edit_student_project(project_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Project title is required', 'warning')
        return redirect(url_for('user.student_dashboard'))
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
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_student_project(project_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = ProjectModel.delete(user_id, project_id)
    flash('Project deleted successfully' if deleted else 'Project not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/social-links', methods=['POST'])
@login_required
def create_student_social_link():
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    platform = (request.form.get('platform') or '').strip()
    profile_url = (request.form.get('profile_url') or '').strip()
    if not platform or not profile_url:
        flash('Platform and profile URL are required', 'warning')
        return redirect(url_for('user.student_dashboard'))
    SocialLinkModel.create(
        user_id,
        {
            'platform': platform,
            'username': request.form.get('username'),
            'profile_url': profile_url,
        },
    )
    flash('Social link created successfully', 'success')
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/social-links/<int:social_link_id>', methods=['POST'])
@login_required
def edit_student_social_link(social_link_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    platform = (request.form.get('platform') or '').strip()
    profile_url = (request.form.get('profile_url') or '').strip()
    if not platform or not profile_url:
        flash('Platform and profile URL are required', 'warning')
        return redirect(url_for('user.student_dashboard'))
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
    return redirect(url_for('user.student_dashboard'))


@user_bp.route('/student/profile/social-links/<int:social_link_id>/delete', methods=['POST'])
@login_required
def delete_student_social_link(social_link_id):
    user_id = session.get('user_id')
    if not StudentProfileModel.has_student_profile(user_id):
        flash('Student profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = SocialLinkModel.delete(user_id, social_link_id)
    flash('Social link deleted successfully' if deleted else 'Social link not found', 'success' if deleted else 'warning')
    return redirect(url_for('user.student_dashboard'))
