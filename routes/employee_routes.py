from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models.employee_profile import EmployeeProfileModel, ExperienceModel
from models.student_profile import CertificateModel, ProjectModel, ResumeProfileModel, SocialLinkModel
from services.auth import login_required
from services.profile_engine import ProfileEngine


employee_bp = Blueprint('employee', __name__, template_folder='../templates')


@employee_bp.route('/employee/dashboard')
@login_required
def employee_dashboard():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    data = ProfileEngine.build_dashboard_context('employee', EmployeeProfileModel.get_employee_dashboard_data(user_id))
    if not data:
        flash('Employee profile not found', 'warning')
        return redirect(url_for('auth.dashboard'))
    return render_template('profile/dashboard.html', **data)


@employee_bp.route('/employee/dashboard/<section_key>')
@login_required
def employee_section_detail(section_key):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    data = ProfileEngine.build_dashboard_context('employee', EmployeeProfileModel.get_employee_dashboard_data(user_id))
    section = next((item for item in data.get('profile_sections', []) if item.get('key') == section_key), None)
    if not section:
        flash('Profile section not found', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
    return render_template('profile/section_detail.html', section=section, **data)


@employee_bp.route('/employee/profile/basic-information', methods=['POST'])
@login_required
def update_employee_basic_information():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    EmployeeProfileModel.update_basic_information(
        user_id,
        {
            'name': request.form.get('name'),
            'mobile': request.form.get('mobile'),
            'email': request.form.get('email'),
            'address': request.form.get('address'),
        },
    )
    session['user_name'] = request.form.get('name')
    flash('Basic Information saved successfully', 'success')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/company-information', methods=['POST'])
@login_required
def update_employee_company_information():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    EmployeeProfileModel.update_company_information(
        user_id,
        {
            'company_name': request.form.get('company_name'),
            'employee_code': request.form.get('employee_code'),
            'designation': request.form.get('designation'),
            'employment_type': request.form.get('employment_type'),
            'office_location': request.form.get('office_location'),
            'joining_date': request.form.get('joining_date'),
            'professional_summary': request.form.get('professional_summary'),
        },
    )
    flash('Company Information saved successfully', 'success')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/company-information/delete', methods=['POST'])
@login_required
def delete_employee_company_information():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    EmployeeProfileModel.clear_company_information(user_id)
    flash('Company Information deleted successfully', 'success')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/work-experience', methods=['POST'])
@login_required
def create_employee_experience():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    company_name = (request.form.get('company_name') or '').strip()
    job_title = (request.form.get('job_title') or '').strip()
    if not company_name or not job_title:
        flash('Company name and job title are required', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
    ExperienceModel.create(
        user_id,
        {
            'company_name': company_name,
            'job_title': job_title,
            'employment_type': request.form.get('employment_type'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'is_current': request.form.get('is_current'),
            'location': request.form.get('location'),
            'description': request.form.get('description'),
        },
    )
    flash('Work Experience created successfully', 'success')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/work-experience/<int:experience_id>', methods=['POST'])
@login_required
def edit_employee_experience(experience_id):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    company_name = (request.form.get('company_name') or '').strip()
    job_title = (request.form.get('job_title') or '').strip()
    if not company_name or not job_title:
        flash('Company name and job title are required', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
    updated = ExperienceModel.update(
        user_id,
        experience_id,
        {
            'company_name': company_name,
            'job_title': job_title,
            'employment_type': request.form.get('employment_type'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'is_current': request.form.get('is_current'),
            'location': request.form.get('location'),
            'description': request.form.get('description'),
        },
    )
    flash('Work Experience updated successfully' if updated else 'Work Experience not found', 'success' if updated else 'warning')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/work-experience/<int:experience_id>/delete', methods=['POST'])
@login_required
def delete_employee_experience(experience_id):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = ExperienceModel.delete(user_id, experience_id)
    flash('Work Experience deleted successfully' if deleted else 'Work Experience not found', 'success' if deleted else 'warning')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/skills', methods=['POST'])
@login_required
def update_employee_skills():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    EmployeeProfileModel.update_skills(user_id, {'skills': request.form.get('skills')})
    flash('Skills saved successfully', 'success')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/skills/delete', methods=['POST'])
@login_required
def delete_employee_skills():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    EmployeeProfileModel.clear_skills(user_id)
    flash('Skills deleted successfully', 'success')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/projects', methods=['POST'])
@login_required
def create_employee_project():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Project title is required', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
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
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/projects/<int:project_id>', methods=['POST'])
@login_required
def edit_employee_project(project_id):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Project title is required', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
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
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_employee_project(project_id):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = ProjectModel.delete(user_id, project_id)
    flash('Project deleted successfully' if deleted else 'Project not found', 'success' if deleted else 'warning')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/certificates', methods=['POST'])
@login_required
def create_employee_certificate():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Certificate title is required', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
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
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/certificates/<int:certificate_id>', methods=['POST'])
@login_required
def edit_employee_certificate(certificate_id):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    title = (request.form.get('title') or '').strip()
    if not title:
        flash('Certificate title is required', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
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
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/certificates/<int:certificate_id>/delete', methods=['POST'])
@login_required
def delete_employee_certificate(certificate_id):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = CertificateModel.delete(user_id, certificate_id)
    flash('Certificate deleted successfully' if deleted else 'Certificate not found', 'success' if deleted else 'warning')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/resume', methods=['POST'])
@login_required
def update_employee_resume():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
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
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/resume/delete', methods=['POST'])
@login_required
def delete_employee_resume():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    ResumeProfileModel.delete(user_id)
    flash('Resume deleted successfully', 'success')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/social-links', methods=['POST'])
@login_required
def create_employee_social_link():
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    platform = (request.form.get('platform') or '').strip()
    profile_url = (request.form.get('profile_url') or '').strip()
    if not platform or not profile_url:
        flash('Platform and profile URL are required', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
    SocialLinkModel.create(
        user_id,
        {
            'platform': platform,
            'username': request.form.get('username'),
            'profile_url': profile_url,
        },
    )
    flash('Social link created successfully', 'success')
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/social-links/<int:social_link_id>', methods=['POST'])
@login_required
def edit_employee_social_link(social_link_id):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    platform = (request.form.get('platform') or '').strip()
    profile_url = (request.form.get('profile_url') or '').strip()
    if not platform or not profile_url:
        flash('Platform and profile URL are required', 'warning')
        return redirect(url_for('employee.employee_dashboard'))
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
    return redirect(url_for('employee.employee_dashboard'))


@employee_bp.route('/employee/profile/social-links/<int:social_link_id>/delete', methods=['POST'])
@login_required
def delete_employee_social_link(social_link_id):
    user_id = session.get('user_id')
    if not EmployeeProfileModel.has_employee_profile(user_id):
        flash('Employee profile is not available for this account', 'warning')
        return redirect(url_for('auth.dashboard'))
    deleted = SocialLinkModel.delete(user_id, social_link_id)
    flash('Social link deleted successfully' if deleted else 'Social link not found', 'success' if deleted else 'warning')
    return redirect(url_for('employee.employee_dashboard'))
