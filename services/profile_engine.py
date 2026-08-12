import copy


class ProfileEngine:
    PROFILE_CONFIGS = {
        'student': {
            'label': 'Student',
            'dashboard_title': 'Student Profile Dashboard',
            'description': 'Manage your profile section by section.',
            'sections': [
                {'key': 'basic_information', 'title': 'Basic Information', 'form_template': 'profile/forms/basic_information.html'},
                {'key': 'academic_information', 'title': 'Academic Information', 'form_template': 'profile/forms/student_academic_information.html'},
                {'key': 'emergency_contact', 'title': 'Emergency Contact', 'form_template': 'profile/forms/emergency_contact.html'},
                {'key': 'medical_report', 'title': 'Medical Report', 'form_template': 'profile/forms/medical_report.html'},
                {'key': 'skills', 'title': 'Skills', 'form_template': 'profile/forms/skills.html'},
                {'key': 'projects', 'title': 'Projects', 'form_template': 'profile/forms/projects.html'},
                {'key': 'certificates', 'title': 'Certificates', 'form_template': 'profile/forms/certificates.html'},
                {'key': 'upload_documents', 'title': 'Upload Documents', 'form_template': 'profile/forms/upload_documents.html'},
                {'key': 'resume', 'title': 'Resume', 'form_template': 'profile/forms/resume.html'},
                {'key': 'social_links', 'title': 'Social Links', 'form_template': 'profile/forms/social_links.html'},
            ],
        },
        'employee': {
            'label': 'Employee',
            'dashboard_title': 'Employee Profile Dashboard',
            'description': 'Manage your profile section by section.',
            'sections': [
                {'key': 'basic_information', 'title': 'Basic Information', 'form_template': 'profile/forms/basic_information.html'},
                {'key': 'company_information', 'title': 'Company Information', 'form_template': 'profile/forms/employee_company_information.html'},
                {'key': 'work_experience', 'title': 'Work Experience', 'form_template': 'profile/forms/employee_work_experience.html'},
                {'key': 'skills', 'title': 'Skills', 'form_template': 'profile/forms/skills.html'},
                {'key': 'projects', 'title': 'Projects', 'form_template': 'profile/forms/projects.html'},
                {'key': 'certificates', 'title': 'Certificates', 'form_template': 'profile/forms/certificates.html'},
                {'key': 'resume', 'title': 'Resume', 'form_template': 'profile/forms/resume.html'},
                {'key': 'social_links', 'title': 'Social Links', 'form_template': 'profile/forms/social_links.html'},
            ],
        },
        'emergency': {
            'label': 'Emergency',
            'dashboard_title': 'Emergency Profile Dashboard',
            'description': 'Manage your profile section by section.',
            'sections': [],
        },
        'intern': {
            'label': 'Intern',
            'dashboard_title': 'Intern Profile Dashboard',
            'description': 'Manage your profile section by section.',
            'sections': [],
        },
        'freelancer': {
            'label': 'Freelancer',
            'dashboard_title': 'Freelancer Profile Dashboard',
            'description': 'Manage your profile section by section.',
            'sections': [],
        },
        'business_owner': {
            'label': 'Business Owner',
            'dashboard_title': 'Business Owner Profile Dashboard',
            'description': 'Manage your profile section by section.',
            'sections': [],
        },
        'visitor': {
            'label': 'Visitor',
            'dashboard_title': 'Visitor Profile Dashboard',
            'description': 'Manage your profile section by section.',
            'sections': [],
        },
        'citizen': {
            'label': 'Citizen',
            'dashboard_title': 'Citizen Profile Dashboard',
            'description': 'Manage your profile section by section.',
            'sections': [],
        },
    }

    @classmethod
    def get_profile_config(cls, profile_type):
        config = cls.PROFILE_CONFIGS.get(profile_type, {})
        return copy.deepcopy(config)

    @classmethod
    def build_dashboard_context(cls, profile_type, data):
        config = cls.get_profile_config(profile_type)
        config_sections = config.get('sections', [])
        config_map = {section['key']: section for section in config_sections}
        sections = []
        source_sections = data.get('sections') or config_sections
        for section in source_sections:
            merged = dict(config_map.get(section.get('key'), {}))
            merged.update(section)
            sections.append(merged)
        return {
            **data,
            'profile_type': profile_type,
            'profile_label': config.get('label', profile_type.title()),
            'profile_dashboard_title': config.get('dashboard_title', 'Profile Dashboard'),
            'profile_dashboard_description': config.get('description', ''),
            'profile_sections': sections,
        }
