import os
import qrcode
from PIL import Image
import secrets

from flask import current_app

def generate_token():
    return secrets.token_urlsafe(32)

def generate_qr_for_user(user_id, payload_url):
    token = generate_token()
    payload_url = payload_url.replace('__TOKEN__', token)
    qr_img = qrcode.make(payload_url)
    qr_folder = current_app.config['QR_FOLDER']
    os.makedirs(qr_folder, exist_ok=True)
    filename = f'qr_{user_id}_{token}.png'
    path = os.path.join(qr_folder, filename)
    qr_img.save(path)
    # Return path with forward slashes for web URLs (qr/qr_1_token.png)
    relative_path = os.path.relpath(path, start=os.path.join(current_app.root_path, 'static')).replace('\\', '/')
    return token, relative_path
