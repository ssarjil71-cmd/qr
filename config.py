import os
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

basedir = os.path.abspath(os.path.dirname(__file__))
if load_dotenv:
    load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-secret')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'qr_card')
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    QR_FOLDER = os.path.join(basedir, 'static', 'qr')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    SUREPASS_API_BASE = os.environ.get('SUREPASS_API_BASE', 'https://kyc-api.surepass.io')
    SUREPASS_API_KEY = os.environ.get('SUREPASS_API_KEY', '')
    MSG91_AUTH_KEY = os.environ.get('MSG91_AUTH_KEY', '')
    MSG91_OTP_TEMPLATE_ID = os.environ.get('MSG91_OTP_TEMPLATE_ID', '')
    MSG91_SENDER_ID = os.environ.get('MSG91_SENDER_ID', '')
    MSG91_OTP_BASE = os.environ.get('MSG91_OTP_BASE', 'https://control.msg91.com/api/v5/otp')
    REGISTRATION_TEST_OTP = os.environ.get('REGISTRATION_TEST_OTP', '1111')
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
