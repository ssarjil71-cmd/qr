from app import create_app
from flask import session

app = create_app()
with app.test_request_context('/student/dashboard'):
    session['user_id'] = 1
    session['user_type'] = 'student'
    session['user_name'] = 'Test User'
    html = app.jinja_env.get_template('profile/dashboard.html').render(
        hide_navbar=True,
        user={'name': 'Test User', 'email': 'test@example.com', 'mobile': '1234567890', 'photo': None, 'qr_token': ''},
        overall_completion=80,
        profile_dashboard_title='Student Dashboard',
        profile_dashboard_description='Profile sections',
        profile_type='student',
        profile_sections=[],
        student_profile={},
        employee_profile={},
        projects=[],
        certificates=[],
        uploaded_documents=[],
        resume_profile={},
        social_links=[],
        experiences=[],
        medical_report={},
        medicines=[],
        vaccinations=[],
        medical_documents=[],
        technical_skills=[],
        soft_skills=[],
        skill_tools=[],
        languages=[]
    )
    print('rendered_ok', '<profile-dashboard-shell>' in html, 'Welcome back' not in html, 'profile-fab' not in html, 'Profile Sections' in html)
