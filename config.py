import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-secret')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'qr_card')
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    QR_FOLDER = os.path.join(basedir, 'static', 'qr')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
