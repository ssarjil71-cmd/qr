from flask import Flask, render_template
from services.db import mysql_init
import config

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # init extensions
    mysql_init(app)

    # register blueprints
    from routes.auth_routes import auth_bp
    from routes.admin_routes import admin_bp
    from routes.qr_routes import qr_bp
    from routes.user_routes import user_bp
    from routes.employee_routes import employee_bp
    from routes.superadmin_routes import superadmin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(superadmin_bp, url_prefix='/superadmin')
    app.register_blueprint(qr_bp, url_prefix='/qr')
    app.register_blueprint(user_bp)
    app.register_blueprint(employee_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
