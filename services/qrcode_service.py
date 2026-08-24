import os
import secrets

import qrcode
from PIL import Image, ImageDraw, ImageFont
from flask import current_app


def generate_token():
    return secrets.token_urlsafe(32)


def _hex_to_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _linear_gradient(size, start_color, end_color):
    width, height = size
    start = _hex_to_rgb(start_color)
    end = _hex_to_rgb(end_color)
    image = Image.new('RGB', size)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    return image


def _font(size, bold=False):
    candidates = (
        'arialbd.ttf',
        'arial.ttf',
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _centered_text(draw, box, text, fill, font):
    left, top, right, bottom = box
    text_box = draw.textbbox((0, 0), text, font=font)
    width = text_box[2] - text_box[0]
    height = text_box[3] - text_box[1]
    draw.text(
        (left + (right - left - width) / 2, top + (bottom - top - height) / 2),
        text,
        fill=fill,
        font=font,
    )


def _apply_brand_module_color(qr_img, qr_type='profile'):
    qr_rgb = qr_img.convert('RGB')
    white = Image.new('RGB', qr_rgb.size, 'white')
    gradient = _linear_gradient(qr_rgb.size, '#1d4ed8', '#7c3aed')
    if qr_type == 'emergency':
        gradient = _linear_gradient(qr_rgb.size, '#123c9c', '#be185d')
    mask = qr_rgb.convert('L').point(lambda pixel: 255 if pixel < 128 else 0)
    white.paste(gradient, (0, 0), mask)
    return white


def _add_center_logo(qr_img):
    qr_img = qr_img.convert('RGBA')
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'qr-nexid-hero-art.png')
    if not os.path.exists(logo_path):
        return qr_img.convert('RGB')

    logo = Image.open(logo_path).convert('RGBA')
    qr_width, qr_height = qr_img.size
    max_logo_width = int(qr_width * 0.18)
    max_logo_height = int(qr_height * 0.18)
    logo.thumbnail((max_logo_width, max_logo_height), Image.LANCZOS)

    padding = max(8, int(qr_width * 0.025))
    bg_width = logo.width + padding * 2
    bg_height = logo.height + padding * 2
    bg = Image.new('RGBA', (bg_width, bg_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(bg)
    draw.rounded_rectangle(
        (0, 0, bg_width - 1, bg_height - 1),
        radius=max(10, int(bg_width * 0.16)),
        fill=(255, 255, 255, 255),
    )
    bg.alpha_composite(logo, (padding, padding))

    x = (qr_width - bg_width) // 2
    y = (qr_height - bg_height) // 2
    qr_img.alpha_composite(bg, (x, y))
    return qr_img.convert('RGB')


def create_qr_image(payload_url, qr_type='profile'):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(payload_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='black', back_color='white')
    qr_img = _apply_brand_module_color(qr_img, qr_type)
    return _add_center_logo(qr_img)


def render_qr_to_path(payload_url, path, qr_type='profile'):
    create_qr_image(payload_url, qr_type).save(path)


def render_premium_card(qr_path, user_name, qr_type='profile'):
    is_emergency = qr_type == 'emergency'
    accent = '#be185d' if is_emergency else '#2563eb'
    title = 'EMERGENCY ACCESS' if is_emergency else 'VERIFIED DIGITAL IDENTITY'

    card = Image.new('RGB', (900, 1260), '#f8fbff')
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((48, 48, 852, 1212), radius=44, fill='white', outline='#c7d8ff', width=3)
    draw.rounded_rectangle((66, 66, 834, 1194), radius=34, outline='#7c3aed', width=2)
    draw.line((112, 166, 788, 166), fill='#2563eb', width=4)
    draw.line((112, 173, 788, 173), fill='#7c3aed', width=2)

    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'qr-nexid-logo.png')
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert('RGBA')
        logo.thumbnail((310, 88), Image.LANCZOS)
        card.paste(logo.convert('RGB'), ((900 - logo.width) // 2, 94), logo)
    else:
        draw.text((350, 108), 'QR-NexID', fill='#1d4ed8')

    title_font = _font(34, bold=True)
    name_font = _font(38, bold=True)
    label_font = _font(24, bold=True)
    small_font = _font(19, bold=True)

    _centered_text(draw, (110, 212, 790, 258), str(user_name or 'QR-NexID User'), '#0f172a', name_font)
    _centered_text(draw, (110, 258, 790, 292), title, accent, label_font)

    shell = (148, 314, 752, 918)
    qr_box = (190, 356, 710, 876)
    draw.rounded_rectangle(shell, radius=42, fill='#eef4ff')
    draw.rounded_rectangle((162, 328, 738, 904), radius=34, fill='white', outline='#7c3aed', width=4)
    qr_image = Image.open(qr_path).convert('RGB').resize((520, 520), Image.LANCZOS)
    card.paste(qr_image, (qr_box[0], qr_box[1]))

    corner_len = 72
    for x1, y1, sx, sy in [(138, 304, 1, 1), (762, 304, -1, 1), (138, 928, 1, -1), (762, 928, -1, -1)]:
        draw.line((x1, y1, x1 + corner_len * sx, y1), fill=accent, width=7)
        draw.line((x1, y1, x1, y1 + corner_len * sy), fill=accent, width=7)
    draw.line((226, 330, 674, 330), fill='#60a5fa', width=2)
    draw.line((226, 902, 674, 902), fill='#a78bfa', width=2)

    draw.line((210, 958, 690, 958), fill='#7c3aed', width=2)
    _centered_text(draw, (110, 976, 790, 1022), 'SCAN ME • KNOW ME', '#1d4ed8', title_font)
    _centered_text(draw, (110, 1032, 790, 1066), 'SECURE DIGITAL IDENTITY • VERIFIED', '#64748b', small_font)
    _centered_text(draw, (110, 1082, 790, 1124), title, accent, label_font)
    return card


def generate_qr_for_user(user_id, payload_url, prefix='qr', qr_type='profile'):
    token = generate_token()
    payload_url = payload_url.replace('__TOKEN__', token)
    qr_folder = current_app.config['QR_FOLDER']
    os.makedirs(qr_folder, exist_ok=True)
    filename = f'{prefix}_{user_id}_{token}.png'
    path = os.path.join(qr_folder, filename)
    render_qr_to_path(payload_url, path, qr_type)
    relative_path = os.path.relpath(path, start=os.path.join(current_app.root_path, 'static')).replace('\\', '/')
    return token, relative_path
