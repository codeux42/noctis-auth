"""Noctis Auth - coffre-fort local de codes A2F.

Version 2.9 : distribution Windows professionnelle. L'interface, le coffre
AES-256-GCM et les 119 services de la version 2.8 sont conservés à l'identique.
Les ajouts concernent la vérification des mises à jour GitHub Releases, la
vérification SHA-256 de l'installateur et l'intégration avec NoctisAuth_Setup.exe.
"""

import base64
import ctypes
import hashlib
import hmac
import json
import math
import os
import struct
import sys
import threading
import time
import tkinter as tk
import unicodedata
import webbrowser
from pathlib import Path
import io
import urllib.request

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import noctis_update
from app_config import APP_ID, APP_NAME, APP_VERSION, github_configured

APP_USER_MODEL_ID = APP_ID
PERIOD = 30

if sys.platform == 'win32':
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def resource_path(name):
    """Localise une ressource en source comme dans l'exécutable PyInstaller."""
    relative = Path(name)
    candidates = []
    if getattr(sys, '_MEIPASS', None):
        candidates.append(Path(sys._MEIPASS) / relative)
    here = Path(__file__).resolve().parent
    candidates.extend((
        here / relative,
        here.parent / relative,
        here.parent / 'assets' / relative.name,
        here / 'assets' / relative.name,
    ))
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0]) if candidates else str(relative)


APP_DIR = Path(os.getenv('APPDATA', str(Path.home()))) / 'NoctisAuth'
VAULT = APP_DIR / 'vault.json'
SETTINGS_FILE = APP_DIR / 'settings.json'


def load_preferences():
    """Préférences non sensibles (aucun secret, aucun code A2F)."""
    defaults = {'check_updates_on_start': True}
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return defaults
    if isinstance(data, dict) and isinstance(data.get('check_updates_on_start'), bool):
        defaults['check_updates_on_start'] = data['check_updates_on_start']
    return defaults


def save_preferences(preferences):
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        temporary = SETTINGS_FILE.with_suffix('.tmp')
        temporary.write_text(json.dumps(preferences, ensure_ascii=False), encoding='utf-8')
        temporary.replace(SETTINGS_FILE)
    except OSError:
        pass

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
BG = '#07080B'
BG_SOFT = '#090B0F'
SIDEBAR = '#08090C'
SURFACE = '#0F1117'
SURFACE_2 = '#14161D'
SURFACE_3 = '#1A1D25'
INPUT_BG = '#0C0E13'
CARD = '#101218'
CARD_LINE = '#252A35'
LINE = '#232833'
LINE_BRIGHT = '#343B49'
GOLD = '#F4C542'
GOLD_LIGHT = '#FFE08A'
GOLD_DIM = '#B9922F'
WHITE = '#F6F7F9'
MUTED = '#9CA1AD'
SUBTLE = '#626775'
GREEN = '#4AD295'
RED = '#F07878'
MODAL_BG = '#0C0E13'

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('dark-blue')

# Fonts used by the PIL renderer.
FONT_REG = 'C:/Windows/Fonts/segoeui.ttf'
FONT_SEMI = 'C:/Windows/Fonts/segoeuisl.ttf'
FONT_BOLD = 'C:/Windows/Fonts/segoeuib.ttf'
FONT_MONO = 'C:/Windows/Fonts/consolab.ttf'
FONT_UI = 'Segoe UI'

# ---------------------------------------------------------------------------
# Services (> 110) : nom, couleur, monogramme, catégorie
# ---------------------------------------------------------------------------
SERVICE_ROWS = [
    # Services proposant une authentification par application TOTP
    ('Discord', '#5865F2', 'D', 'Gaming'),
    ('Epic Games', '#2A2A2E', 'EG', 'Gaming'),
    ('PlayStation', '#003791', 'PS', 'Gaming'),
    ('Ubisoft Connect', '#0070FF', 'UB', 'Gaming'),
    ('Roblox', '#DA3737', 'RB', 'Gaming'),
    ('Twitch', '#9146FF', 'TW', 'Gaming'),
    ('Google', '#4285F4', 'G', 'Internet'),
    ('Microsoft', '#4EA0F1', 'MS', 'Internet'),
    ('GitHub', '#8B949E', 'GH', 'Développeur'),
    ('GitLab', '#FC6D26', 'GL', 'Développeur'),
    ('Bitbucket', '#2684FF', 'BB', 'Développeur'),
    ('Amazon AWS', '#FF9900', 'AWS', 'Cloud'),
    ('Cloudflare', '#F38020', 'CF', 'Cloud'),
    ('DigitalOcean', '#0080FF', 'DO', 'Cloud'),
    ('Vercel', '#E8E8E8', 'VC', 'Développeur'),
    ('Netlify', '#00C7B7', 'NL', 'Développeur'),
    ('Docker', '#2496ED', 'DK', 'Développeur'),
    ('OpenAI', '#74AA9C', 'AI', 'Intelligence artificielle'),
    ('Notion', '#D8D8D8', 'NO', 'Productivité'),
    ('Slack', '#4A154B', 'SL', 'Productivité'),
    ('Zoom', '#2D8CFF', 'ZM', 'Productivité'),
    ('Dropbox', '#0061FF', 'DB', 'Stockage'),
    ('Proton', '#6D4AFF', 'PR', 'Sécurité'),
    ('Bitwarden', '#175DDC', 'BW', 'Sécurité'),
    ('Facebook', '#1877F2', 'FB', 'Social'),
    ('Instagram', '#E4405F', 'IG', 'Social'),
    ('X', '#E8E8E8', 'X', 'Social'),
    ('TikTok', '#FE2C55', 'TT', 'Social'),
    ('Reddit', '#FF4500', 'RD', 'Social'),
    ('LinkedIn', '#0A66C2', 'LI', 'Social'),
    ('PayPal', '#00457C', 'PP', 'Finance'),
    ('Stripe', '#635BFF', 'SR', 'Finance'),
    ('Amazon', '#FF9900', 'AZ', 'E-commerce'),
    ('Autre', '#7C828E', '?', 'Personnalisé'),
]

SERVICES = [
    {'name': name, 'color': color, 'abbr': abbr, 'tag': tag}
    for name, color, abbr, tag in SERVICE_ROWS
]

POPULAR = [
    'Discord', 'Google', 'Microsoft', 'GitHub', 'Instagram', 'Twitch',
    'Epic Games', 'PlayStation', 'Roblox', 'PayPal', 'Proton', 'Bitwarden',
    'OpenAI', 'Amazon', 'Autre',
]


def normalize(value):
    value = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(ch for ch in value if not unicodedata.combining(ch)).casefold()


SERVICE_BY_KEY = {normalize(s['name']): s for s in SERVICES}
SERVICE_BY_KEY['twitter'] = SERVICE_BY_KEY['x']
SERVICE_BY_KEY['amazon web services'] = SERVICE_BY_KEY['amazon aws']
SERVICE_BY_KEY['google authenticator'] = SERVICE_BY_KEY['google']


def service_for(name):
    key = normalize(name)
    if key in SERVICE_BY_KEY:
        return SERVICE_BY_KEY[key]
    return {'name': name or 'Compte', 'color': GOLD, 'abbr': (name or '?')[:2].upper(), 'tag': 'Personnalisé'}


# ---------------------------------------------------------------------------
# Small drawing helpers
# ---------------------------------------------------------------------------
_ICON_CACHE = {}
_FONT_CACHE = {}
_TILE_CACHE = {}
_BUTTON_CACHE = {}
_RING_CACHE = {}
_RING_CTK_CACHE = {}
_TITLE_CACHE = {}
_GLOW_CACHE = {}
_GLASS_TILE_CACHE = {}

# Logos de marque (favicons) : téléchargés une fois puis mis en cache localement.
SERVICE_DOMAINS = {
    'Discord': 'discord.com', 'Epic Games': 'epicgames.com',
    'PlayStation': 'playstation.com', 'Ubisoft Connect': 'ubisoft.com',
    'Roblox': 'roblox.com', 'Twitch': 'twitch.tv',
    'Google': 'google.com', 'Microsoft': 'microsoft.com',
    'GitHub': 'github.com', 'GitLab': 'gitlab.com', 'Bitbucket': 'bitbucket.org',
    'Amazon AWS': 'aws.amazon.com', 'Cloudflare': 'cloudflare.com',
    'DigitalOcean': 'digitalocean.com', 'Vercel': 'vercel.com',
    'Netlify': 'netlify.com', 'Docker': 'docker.com', 'OpenAI': 'openai.com',
    'Notion': 'notion.so', 'Slack': 'slack.com', 'Zoom': 'zoom.us',
    'Dropbox': 'dropbox.com', 'Proton': 'proton.me', 'Bitwarden': 'bitwarden.com',
    'Facebook': 'facebook.com', 'Instagram': 'instagram.com', 'X': 'x.com',
    'TikTok': 'tiktok.com', 'Reddit': 'reddit.com', 'LinkedIn': 'linkedin.com',
    'PayPal': 'paypal.com', 'Stripe': 'stripe.com', 'Amazon': 'amazon.com',
}
_SERVICE_LOGO_CACHE = {}


def service_logo_image(service, target):
    """Récupère le favicon du service et le conserve dans le cache local."""
    name = service.get('name', '')
    if name in _SERVICE_LOGO_CACHE:
        cached = _SERVICE_LOGO_CACHE[name]
        return cached.copy() if cached is not None else None
    domain = SERVICE_DOMAINS.get(name)
    if not domain:
        _SERVICE_LOGO_CACHE[name] = None
        return None
    cache_dir = APP_DIR / 'logos'
    cache_file = cache_dir / (normalize(name).replace(' ', '-') + '.png')
    try:
        if cache_file.exists():
            logo = Image.open(cache_file).convert('RGBA')
        else:
            url = 'https://www.google.com/s2/favicons?domain=' + domain + '&sz=128'
            request = urllib.request.Request(url, headers={'User-Agent': 'NoctisAuth/2.10'})
            with urllib.request.urlopen(request, timeout=0.45) as response:
                data = response.read(256 * 1024)
            logo = Image.open(io.BytesIO(data)).convert('RGBA')
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(data)
        logo.thumbnail((target, target), Image.Resampling.LANCZOS)
        _SERVICE_LOGO_CACHE[name] = logo.copy()
        return logo
    except Exception:
        _SERVICE_LOGO_CACHE[name] = None
        return None


def draw_generic_service_mark(image):
    """Pictogramme neutre de secours, sans monogramme."""
    draw = ImageDraw.Draw(image)
    w, h = image.size
    cx, cy = w // 2, h // 2
    r = int(w * 0.19)
    width = max(3, w // 22)
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline='#FFFFFF', width=width)
    draw.arc((cx-int(w*.29), cy-int(w*.29), cx+int(w*.29), cy+int(w*.29)),
             start=205, end=335, fill='#FFFFFF', width=width)
    draw.ellipse((cx-int(w*.035), cy-int(w*.035), cx+int(w*.035), cy+int(w*.035)),
                 fill='#FFFFFF')



def hex_rgb(color):
    if isinstance(color, (tuple, list)):
        return tuple(int(c) for c in color[:3])
    color = color.lstrip('#')
    if len(color) == 3:
        color = ''.join(c * 2 for c in color)
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def mix(color_a, color_b, t):
    a, b = hex_rgb(color_a), hex_rgb(color_b)
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(color, amount):
    rgb = hex_rgb(color)
    if amount >= 0:
        return tuple(round(c + (255 - c) * amount) for c in rgb)
    return tuple(round(c * (1 + amount)) for c in rgb)


def pil_font(path, size):
    key = (path, size)
    font = _FONT_CACHE.get(key)
    if font is None:
        try:
            font = ImageFont.truetype(path, size)
        except Exception:
            font = ImageFont.load_default()
        _FONT_CACHE[key] = font
    return font


def rounded_mask(size, radius):
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1),
                                          radius=radius, fill=255)
    return mask


def vertical_gradient(size, top, bottom):
    w, h = size
    image = Image.new('RGB', (1, max(1, h)))
    draw = ImageDraw.Draw(image)
    a, b = hex_rgb(top), hex_rgb(bottom)
    for y in range(max(1, h)):
        t = y / max(1, h - 1)
        draw.point((0, y), fill=tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    return image.resize((max(1, w), max(1, h)), Image.Resampling.BILINEAR).convert('RGBA')


def ctk_icon(name, size, color=WHITE, stroke=1.9):
    key = ('ctk', name, size, color, stroke)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    source = icon_pil(name, max(8, round(size * 3)), color, stroke * 3, ss=2)
    image = ctk.CTkImage(light_image=source, dark_image=source, size=(size, size))
    _ICON_CACHE[key] = image
    return image


def icon_pil(name, px, color=WHITE, stroke=2.0, ss=3):
    key = (name, px, color, stroke, ss)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    px = max(6, int(px))
    canvas = px * ss
    unit = canvas / 24.0
    stroke_px = max(1, int(round(stroke * ss)))
    image = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def p(x, y):
        return (x * unit, y * unit)

    def line(points, fill=color, width=stroke_px):
        pts = [p(x, y) for x, y in points]
        draw.line(pts, fill=fill, width=width, joint='curve')
        for point in (pts[0], pts[-1]):
            r = width / 2.0
            draw.ellipse((point[0] - r, point[1] - r, point[0] + r, point[1] + r), fill=fill)

    def poly(points, fill=color, width=stroke_px):
        line(points + [points[0]], fill=fill, width=width)

    def circle(cx, cy, r, fill=None, width=stroke_px):
        draw.ellipse((p(cx - r, cy - r), p(cx + r, cy + r)), outline=fill, width=width)

    def disc(cx, cy, r, fill=color):
        draw.ellipse((p(cx - r, cy - r), p(cx + r, cy + r)), fill=fill)

    def rrect(x0, y0, x1, y1, radius, fill=color, width=stroke_px):
        draw.rounded_rectangle((p(x0, y0), p(x1, y1)), radius=radius * unit,
                               outline=fill, width=width)

    if name == 'plus':
        line([(12, 5), (12, 19)]); line([(5, 12), (19, 12)])
    elif name == 'minus':
        line([(5, 12), (19, 12)])
    elif name == 'search':
        circle(9.6, 9.6, 5.7)
        line([(14, 14), (19.5, 19.5)])
    elif name == 'copy':
        rrect(8.5, 8.5, 19.5, 19.5, 2.4)
        rrect(4.5, 4.5, 15.5, 15.5, 2.4)
    elif name == 'edit':
        poly([(4, 20), (5.2, 15), (15.6, 4.6), (19.4, 8.4), (9, 18.8)])
        line([(14.6, 5.6), (18.4, 9.4)])
        line([(5.2, 15), (9, 18.8)])
    elif name == 'trash':
        line([(4, 7), (20, 7)])
        draw.arc((p(9, 3.5), p(15, 10.5)), 180, 360, fill=color, width=stroke_px)
        line([(6.5, 7), (7.6, 20), (16.4, 20), (17.5, 7)])
        line([(10.4, 11), (10.4, 16.5)])
        line([(13.6, 11), (13.6, 16.5)])
    elif name == 'sliders':
        for y in (7, 12, 17):
            line([(4, y), (20, y)])
        disc(9, 7, 2.4); disc(15, 12, 2.4); disc(8, 17, 2.4)
    elif name == 'info':
        circle(12, 12, 8.6)
        disc(12, 7.6, 1.15)
        line([(12, 11), (12, 17)])
    elif name == 'grid':
        rrect(4, 4, 10.6, 10.6, 1.6)
        rrect(13.4, 4, 20, 10.6, 1.6)
        rrect(4, 13.4, 10.6, 20, 1.6)
        rrect(13.4, 13.4, 20, 20, 1.6)
    elif name == 'lock':
        rrect(5, 10.4, 19, 21, 3)
        draw.arc((p(8, 3), p(16, 11)), 180, 360, fill=color, width=stroke_px)
        line([(8, 7), (8, 10.4)])
        line([(16, 7), (16, 10.4)])
    elif name == 'unlock':
        rrect(5, 10.4, 19, 21, 3)
        draw.arc((p(9, 3), p(17, 11)), 180, 320, fill=color, width=stroke_px)
        line([(17, 7), (17, 10.4)])
    elif name == 'shield':
        poly([(12, 3), (20, 6.4), (20, 12), (12, 21), (4, 12), (4, 6.4)])
        line([(8.5, 12), (11, 14.5), (15.5, 9.5)])
    elif name == 'key':
        circle(8.5, 8.5, 4.8)
        line([(11.8, 11.8), (20, 20)])
        line([(16.6, 16.6), (13.9, 19.3)])
        line([(18.4, 18.4), (15.7, 21.1)])
    elif name == 'arrow-left':
        line([(19.5, 12), (4.8, 12)])
        line([(10.6, 5.9), (4.6, 12), (10.6, 18.1)])
    elif name == 'arrow-right':
        line([(4.5, 12), (19.2, 12)])
        line([(13.4, 5.9), (19.4, 12), (13.4, 18.1)])
    elif name == 'x':
        line([(6, 6), (18, 18)])
        line([(18, 6), (6, 18)])
    elif name == 'check':
        line([(4.6, 12.6), (9.6, 17.6), (19.5, 7.1)])
    elif name == 'check-circle':
        circle(12, 12, 8.6)
        line([(7.8, 12.2), (10.8, 15.2), (16.4, 8.7)])
    elif name == 'refresh':
        draw.arc((p(4.2, 4.2), p(19.8, 19.8)), 35, 320, fill=color, width=stroke_px)
        end = math.radians(35)
        ex, ey = 12 + 7.8 * math.cos(end), 12 + 7.8 * math.sin(end)
        line([(ex - 3.3, ey - 1.0), (ex, ey), (ex + 0.4, ey - 3.6)])
    elif name == 'download':
        line([(12, 3.6), (12, 15.4)])
        line([(7.1, 10.6), (12, 15.6), (16.9, 10.6)])
        line([(4.2, 16.6), (4.2, 20.2), (19.8, 20.2), (19.8, 16.6)])
    elif name == 'folder':
        poly([(3.6, 8.0), (9.1, 8.0), (11.2, 10.6), (20.4, 10.6),
              (20.4, 19.2), (3.6, 19.2)])
        line([(3.6, 8.0), (3.6, 19.2)])
    elif name == 'sparkle':
        draw.polygon([p(12, 2.8), p(14, 10), p(21.2, 12), p(14, 14), p(12, 21.2),
                      p(10, 14), p(2.8, 12), p(10, 10)], fill=color)
    elif name == 'clock':
        circle(12, 12, 8.5)
        line([(12, 7.4), (12, 12), (16, 13.7)])
    elif name == 'user':
        circle(12, 8.3, 4.0)
        draw.arc((p(4.2, 14), p(19.8, 26.5)), 180, 360, fill=color, width=stroke_px)
    elif name == 'chevron-down':
        line([(6, 9), (12, 15), (18, 9)])
    elif name == 'chevron-right':
        line([(9, 6), (15, 12), (9, 18)])
    elif name == 'eye':
        draw.ellipse((p(2.8, 6.5), p(21.2, 17.5)), outline=color, width=stroke_px)
        disc(12, 12, 2.5)
    elif name == 'eye-off':
        draw.ellipse((p(2.8, 6.5), p(21.2, 17.5)), outline=color, width=stroke_px)
        disc(12, 12, 2.5)
        line([(4, 4), (20, 20)])
    elif name == 'alert':
        poly([(12, 3.5), (21, 20), (3, 20)])
        line([(12, 9.2), (12, 14.2)])
        disc(12, 17, 1.15)
    elif name == 'logout':
        line([(10, 4.2), (4.6, 4.2), (4.6, 19.8), (10, 19.8)])
        line([(13, 12), (21, 12)])
        line([(17.4, 8.2), (21.2, 12), (17.4, 15.8)])
    elif name == 'wand':
        line([(5, 19), (15.5, 8.5)])
        draw.polygon([p(16.5, 3.2), p(18.1, 6.4), p(21.2, 7.5), p(18.5, 9.4),
                      p(18.1, 12.8), p(16.2, 10.1), p(12.8, 9.6), p(15.3, 7.3)], fill=color)
        line([(4, 8), (4, 12)]); line([(2, 10), (6, 10)])
    elif name == 'dot':
        disc(12, 12, 4.2)
    else:
        disc(12, 12, 6)

    if ss > 1:
        image = image.resize((px, px), Image.Resampling.LANCZOS)
    _ICON_CACHE[key] = image
    return image
# ---------------------------------------------------------------------------
# Liquid-glass renderers
# ---------------------------------------------------------------------------
TONE_RGB = {
    'gold': (244, 197, 66),
    'danger': (240, 120, 120),
    'green': (74, 210, 149),
    'neutral': (205, 210, 220),
}


def service_tile_image(service, size=58):
    key = ('service', service['name'], service['color'], service['abbr'], size)
    cached = _TILE_CACHE.get(key)
    if cached is not None:
        return cached
    ss = 3
    sz = size * ss
    color = service['color']
    img = Image.new('RGBA', (sz, sz), (0, 0, 0, 0))
    radius = int(sz * 0.30)
    mask = rounded_mask((sz, sz), radius)
    fill = vertical_gradient((sz, sz), '#%02X%02X%02X' % shade(color, 0.22),
                             '#%02X%02X%02X' % shade(color, -0.30))
    tile = Image.composite(fill, Image.new('RGBA', (sz, sz), (0, 0, 0, 0)), mask)

    effects = Image.new('RGBA', (sz, sz), (0, 0, 0, 0))
    ed = ImageDraw.Draw(effects)
    ed.ellipse((int(-sz * 0.28), int(-sz * 0.55), int(sz * 0.95), int(sz * 0.52)),
               fill=(255, 255, 255, 26))
    ed.rounded_rectangle((1, 1, sz - 2, sz - 2), radius=radius,
                         outline=(255, 255, 255, 54), width=max(2, ss))
    ed.line([(radius * 0.8, 2.5 * ss), (sz - radius * 0.8, 2.5 * ss)],
            fill=(255, 255, 255, 125), width=max(2, ss))
    ed.rounded_rectangle((4 * ss, sz - 6 * ss, sz - 4 * ss, sz - 2 * ss),
                         radius=radius, fill=(0, 0, 0, 55))
    effects = Image.composite(effects, Image.new('RGBA', (sz, sz), (0, 0, 0, 0)), mask)
    img = Image.alpha_composite(tile, effects)

    target = int(sz * 0.58)
    logo = service_logo_image(service, target)
    if logo is not None:
        logo.thumbnail((target, target), Image.Resampling.LANCZOS)
        img.alpha_composite(logo, (int((sz - logo.width) / 2), int((sz - logo.height) / 2)))
    else:
        draw_generic_service_mark(img)

    image = img.resize((size, size), Image.Resampling.LANCZOS)
    _TILE_CACHE[key] = image
    return image


def tile_ctk(service, size=58):
    key = ('ctk', 'service', service['name'], service['color'], service['abbr'], size)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    source = service_tile_image(service, size)
    image = ctk.CTkImage(light_image=source, dark_image=source, size=(size, size))
    _ICON_CACHE[key] = image
    return image


def icon_tile_image(name, size=46, tone='gold'):
    key = ('icontile', name, size, tone)
    cached = _GLASS_TILE_CACHE.get(key)
    if cached is not None:
        return cached
    ss = 3
    sz = size * ss
    radius = int(sz * 0.30)
    tone_rgb = TONE_RGB.get(tone, TONE_RGB['gold'])
    mask = rounded_mask((sz, sz), radius)
    base = mix(BG, '#%02X%02X%02X' % tone_rgb, 0.10)
    fill = vertical_gradient((sz, sz), '#%02X%02X%02X' % shade(base, 0.16),
                             '#%02X%02X%02X' % shade(base, -0.18))
    img = Image.composite(fill, Image.new('RGBA', (sz, sz), (0, 0, 0, 0)), mask)
    effects = Image.new('RGBA', (sz, sz), (0, 0, 0, 0))
    ed = ImageDraw.Draw(effects)
    ed.rounded_rectangle((1, 1, sz - 2, sz - 2), radius=radius,
                         outline=(*tone_rgb, 120), width=max(2, ss))
    ed.line([(radius, 2.5 * ss), (sz - radius, 2.5 * ss)],
            fill=(255, 255, 255, 120), width=max(2, ss))
    effects = Image.composite(effects, Image.new('RGBA', (sz, sz), (0, 0, 0, 0)), mask)
    img = Image.alpha_composite(img, effects)
    glyph = icon_pil(name, int(sz * 0.48), '#%02X%02X%02X' % tone_rgb,
                     stroke=max(2.0, ss * 1.8), ss=2)
    img.alpha_composite(glyph, (int((sz - glyph.width) / 2), int((sz - glyph.height) / 2)))
    image = img.resize((size, size), Image.Resampling.LANCZOS)
    _GLASS_TILE_CACHE[key] = image
    return image


def icon_tile_ctk(name, size=46, tone='gold'):
    key = ('ctk', 'icontile', name, size, tone)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    source = icon_tile_image(name, size, tone)
    image = ctk.CTkImage(light_image=source, dark_image=source, size=(size, size))
    _ICON_CACHE[key] = image
    return image


def render_button_image(w, h, radius, text, icon, icon_size, style, tone, align,
                        font_size, bold, state, base, selected, padx, gap):
    key = (w, h, radius, text, icon, icon_size, style, tone, align, font_size,
           bold, state, base, selected, padx, gap)
    cached = _BUTTON_CACHE.get(key)
    if cached is not None:
        return cached

    ss = 3
    W, H, R = w * ss, h * ss, radius * ss
    transparent = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    mask = rounded_mask((W, H), R)
    tone_rgb = TONE_RGB.get(tone, TONE_RGB['neutral'])

    if style == 'gold':
        top, bottom = {
            'normal': ('#FFE49B', '#D6A42A'),
            'hover': ('#FFF0C6', '#E8BB44'),
            'pressed': ('#F4D079', '#C2901C'),
        }[state]
        fill = vertical_gradient((W, H), top, bottom)
    elif style == 'danger':
        top, bottom = {
            'normal': ('#F59494', '#C64C4C'),
            'hover': ('#FFAAAA', '#DA5E5E'),
            'pressed': ('#E27D7D', '#AE3D3D'),
        }[state]
        fill = vertical_gradient((W, H), top, bottom)
    elif style == 'danger-soft':
        fill = Image.new('RGBA', (W, H), (50, 30, 33, 255))
    else:
        fill = Image.new('RGBA', (W, H), (*hex_rgb(base), 255))

    surface = Image.composite(fill, transparent, mask)
    effects = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ed = ImageDraw.Draw(effects)

    if style == 'gold' or style == 'danger':
        ed.rounded_rectangle((1, 1, W - 2, H - 2), radius=R,
                             outline=(255, 255, 255, 150), width=ss)
        ed.line([(R * 0.8, 2.6 * ss), (W - R * 0.8, 2.6 * ss)],
                fill=(255, 255, 255, 200), width=ss + 1)
        ed.rounded_rectangle((5 * ss, 5 * ss, W - 5 * ss, H - 5 * ss), radius=max(2, R - 4 * ss),
                             outline=(255, 255, 255, 55), width=ss)
        ed.rounded_rectangle((3 * ss, H - 7 * ss, W - 3 * ss, H - 3 * ss),
                             radius=R, fill=(0, 0, 0, 40))
    else:
        if style == 'ghost':
            alpha_top = {'normal': 5, 'hover': 14, 'pressed': 18}[state]
            alpha_bottom = {'normal': 0, 'hover': 3, 'pressed': 4}[state]
            rim = {'normal': 0, 'hover': 36, 'pressed': 60}[state]
        else:
            alpha_top = {'normal': 24, 'hover': 38, 'pressed': 16}[state]
            alpha_bottom = {'normal': 4, 'hover': 9, 'pressed': 10}[state]
            rim = {'normal': 46, 'hover': 82, 'pressed': 105}[state]
        if selected:
            alpha_top, alpha_bottom, rim = 44, 14, 145
        for y in range(H):
            t = y / max(1, H - 1)
            alpha = int(alpha_top * (1 - t) ** 1.4 + alpha_bottom)
            if alpha > 0:
                ed.line([(0, y), (W, y)], fill=(*tone_rgb, alpha))
        ed.rounded_rectangle((4 * ss, H - 8 * ss, W - 4 * ss, H - 3 * ss),
                             radius=R, fill=(0, 0, 0, 66))
        if rim:
            ed.rounded_rectangle((1, 1, W - 2, H - 2), radius=R,
                                 outline=(255, 255, 255, rim), width=max(2, ss - 1))
        accent = {'normal': 52, 'hover': 96, 'pressed': 118}[state]
        ed.line([(R, H - 3.2 * ss), (W - R, H - 3.2 * ss)],
                fill=(*tone_rgb, accent), width=max(2, ss - 1))
        ed.line([(R * 0.9, 2.4 * ss), (W - R * 0.9, 2.4 * ss)],
                fill=(255, 255, 255, 74 if state == 'normal' else 130), width=max(2, ss - 1))

    if selected:
        ed.rounded_rectangle((7 * ss, H * 0.24, 10 * ss, H * 0.76),
                             radius=3 * ss, fill=(*tone_rgb, 255))

    effects = Image.composite(effects, transparent, mask)
    img = Image.alpha_composite(surface, effects)

    if style == 'gold':
        text_color = '#191204' if state != 'pressed' else '#2A1F08'
        icon_color = text_color
    elif style == 'danger':
        text_color = '#FFF6F6'
        icon_color = '#FFF6F6'
    elif style == 'danger-soft':
        text_color = '#F6C4C4'
        icon_color = RED
    elif selected:
        text_color = WHITE
        icon_color = GOLD_LIGHT
    elif tone == 'danger':
        text_color = '#F6B9B9'
        icon_color = RED
    elif tone == 'green':
        text_color = WHITE
        icon_color = GREEN
    elif tone == 'gold':
        text_color = '#FFF6DA' if state != 'normal' else WHITE
        icon_color = GOLD_LIGHT if state != 'normal' else GOLD
    elif style == 'ghost':
        text_color = MUTED
        icon_color = SUBTLE
    else:
        text_color = WHITE
        icon_color = '#CBD0D9'

    # Auto-shrink the label if it would overflow the button.
    size_px = max(8, int(round(font_size * ss)))
    font = pil_font(FONT_BOLD if bold else FONT_REG, size_px)
    text_len = font.getlength(text) if text else 0
    icon_px = int(round(icon_size * ss)) if icon else 0
    gap_px = int(round(gap * ss)) if (icon and text) else 0
    max_width = W - int(padx * ss) * 2
    while text and (text_len + icon_px + gap_px) > max_width and size_px > 8 * ss:
        size_px -= 1
        font = pil_font(FONT_BOLD if bold else FONT_REG, size_px)
        text_len = font.getlength(text)

    group_w = icon_px + gap_px + text_len
    if align == 'w':
        start_x = padx * ss
    elif align == 'e':
        start_x = W - padx * ss - group_w
    else:
        start_x = (W - group_w) / 2

    if icon:
        glyph = icon_pil(icon, icon_px, icon_color, stroke=1.85 * ss, ss=2)
        img.alpha_composite(glyph, (int(start_x), int((H - icon_px) / 2)))
    if text:
        draw = ImageDraw.Draw(img)
        draw.text((start_x + icon_px + gap_px, H / 2 + ss * 0.4), text,
                  font=font, fill=text_color, anchor='lm')

    out = img.resize((w, h), Image.Resampling.LANCZOS)
    _BUTTON_CACHE[key] = out
    return out


class GlassButton(ctk.CTkLabel):
    """Bouton 100 % dessiné (verre liquide + icône vectorielle)."""

    def __init__(self, master, text='', icon=None, command=None, width=180, height=46,
                 radius=15, style='glass', tone='neutral', align='center', font_size=13,
                 bold=True, base=BG, selected=False, icon_size=18, padx=18, gap=9):
        self._command = command
        self._params = dict(width=width, height=height, radius=radius, text=text,
                            icon=icon, icon_size=icon_size, style=style, tone=tone,
                            align=align, font_size=font_size, bold=bold, base=base,
                            selected=selected, padx=padx, gap=gap)
        self._images = self._render_images()
        super().__init__(master, text='', image=self._images['normal'], width=width,
                         height=height, fg_color=base, bg_color=base, corner_radius=0)
        for widget in (self, getattr(self, '_label', None)):
            if widget is None:
                continue
            widget.bind('<Enter>', self._on_enter)
            widget.bind('<Leave>', self._on_leave)
            widget.bind('<ButtonPress-1>', self._on_press)
            widget.bind('<ButtonRelease-1>', self._on_release)
            try:
                if command is not None:
                    widget.configure(cursor='hand2')
            except Exception:
                pass

    def _render_images(self):
        p = self._params
        result = {}
        for state in ('normal', 'hover', 'pressed'):
            source = render_button_image(
                p['width'], p['height'], p['radius'], p['text'], p['icon'],
                p['icon_size'], p['style'], p['tone'], p['align'], p['font_size'],
                p['bold'], state, p['base'], p['selected'], p['padx'], p['gap'])
            result[state] = ctk.CTkImage(light_image=source, dark_image=source,
                                         size=(p['width'], p['height']))
        return result

    def _on_enter(self, _event=None):
        if self._command is not None:
            self.configure(image=self._images['hover'])

    def _on_leave(self, _event=None):
        self.configure(image=self._images['normal'])

    def _on_press(self, _event=None):
        if self._command is not None:
            self.configure(image=self._images['pressed'])

    def _on_release(self, _event=None):
        if self._command is None:
            return
        try:
            self.configure(image=self._images['hover'])
        except Exception:
            return
        self._command()

    def set_selected(self, selected):
        if self._params['selected'] == selected:
            return
        self._params['selected'] = selected
        self._images = self._render_images()
        self.configure(image=self._images['normal'])

    def set_icon(self, icon, tone=None, style=None):
        self._params['icon'] = icon
        if tone is not None:
            self._params['tone'] = tone
        if style is not None:
            self._params['style'] = style
        self._images = self._render_images()
        self.configure(image=self._images['normal'])

    def set_text(self, text):
        if self._params['text'] == text:
            return
        self._params['text'] = text
        self._images = self._render_images()
        try:
            self.configure(image=self._images['normal'])
        except Exception:
            pass

    def set_command(self, command):
        self._command = command
        try:
            self.configure(cursor='hand2' if command is not None else 'arrow')
        except Exception:
            pass

    def flash_success(self):
        if self._params['icon'] == 'check':
            return
        old = dict(self._params)
        self._params['icon'] = 'check'
        self._params['tone'] = 'green'
        self._params['style'] = 'glass'
        self._images = self._render_images()
        try:
            self.configure(image=self._images['normal'])
        except Exception:
            return
        self.after(1400, lambda: self._restore(old))

    def _restore(self, old):
        try:
            if not self.winfo_exists():
                return
            self._params = old
            self._images = self._render_images()
            self.configure(image=self._images['normal'])
        except Exception:
            pass


class GlassSearch(ctk.CTkFrame):
    """Champ de recherche en verre avec icône, focus doré et bouton effacer."""

    def __init__(self, master, placeholder, height=48, bg=INPUT_BG, icon='search',
                 font_size=13, on_change=None):
        super().__init__(master, fg_color=bg, corner_radius=15, border_width=1,
                         border_color=LINE, height=height)
        self.var = tk.StringVar()
        self._on_change = on_change
        self._height = height
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._icon = ctk.CTkLabel(self, text='', image=ctk_icon(icon, 18, SUBTLE),
                                  fg_color='transparent', width=18, height=18)
        self._icon.grid(row=0, column=0, padx=(16, 10))
        self.entry = ctk.CTkEntry(
            self, textvariable=self.var, placeholder_text=placeholder,
            fg_color='transparent', border_width=0, height=max(28, height - 12),
            text_color=WHITE, placeholder_text_color=SUBTLE,
            font=ctk.CTkFont(family=FONT_UI, size=font_size))
        self.entry.grid(row=0, column=1, sticky='ew', pady=6)
        self._clear = ctk.CTkLabel(self, text='', image=ctk_icon('x', 12, SUBTLE),
                                   fg_color='transparent', width=20, height=20, cursor='hand2')
        self._clear.grid(row=0, column=2, padx=(6, 14))
        self._clear.grid_remove()
        self._clear.bind('<Button-1>', self._clear_text)
        self.entry.bind('<FocusIn>', lambda _e: self.configure(border_color=GOLD_DIM))
        self.entry.bind('<FocusOut>', lambda _e: self.configure(border_color=LINE))
        self.var.trace_add('write', self._changed)

    def _changed(self, *_args):
        if self.var.get():
            self._clear.grid()
        else:
            self._clear.grid_remove()
        if self._on_change is not None:
            self._on_change()

    def _clear_text(self, _event=None):
        self.var.set('')
        self.entry.focus_set()

    def get(self):
        return self.var.get()

    def set(self, value):
        self.var.set(value)


def gradient_title(parts, size=40, font_path=FONT_BOLD):
    """Rend un titre en dégradé (parties : (texte, (couleur haut, couleur bas)))."""
    key = (tuple(parts), size, font_path)
    cached = _TITLE_CACHE.get(key)
    if cached is not None:
        return cached
    ss = 3
    font = pil_font(font_path, size * ss)
    ascent, descent = font.getmetrics()
    height = ascent + descent + 6
    widths = [font.getlength(part[0]) for part in parts]
    width = int(sum(widths)) + 4
    image = Image.new('RGBA', (max(2, width), height), (0, 0, 0, 0))
    x = 1.0
    for (text, (top, bottom)), part_width in zip(parts, widths):
        mask = Image.new('L', image.size, 0)
        ImageDraw.Draw(mask).text((x, ascent + 3), text, font=font, fill=255, anchor='ls')
        gradient = vertical_gradient(image.size, top, bottom)
        image.alpha_composite(Image.composite(
            gradient, Image.new('RGBA', image.size, (0, 0, 0, 0)), mask))
        x += part_width
    ctk_image = ctk.CTkImage(light_image=image, dark_image=image,
                             size=(max(1, int(width / ss)), max(1, int(height / ss))))
    _TITLE_CACHE[key] = ctk_image
    return ctk_image


def ring_image(remaining, size=66):
    key = ('ring', remaining, size)
    cached = _RING_CACHE.get(key)
    if cached is not None:
        return cached
    ss = 3
    sz = size * ss
    img = Image.new('RGBA', (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, int(2.4 * ss))
    d.ellipse((pad - ss, pad - ss, sz - pad + ss, sz - pad + ss), fill=(22, 25, 32, 255))
    d.ellipse((pad, pad, sz - pad, sz - pad), outline=(47, 53, 65, 255), width=max(2, ss))
    frac = max(0.0, min(1.0, remaining / PERIOD))
    if frac > 0.66:
        color = '#4AD295'
    elif frac > 0.22:
        color = '#F4C542'
    else:
        color = '#F07878'
    box = (pad, pad, sz - pad, sz - pad)
    d.arc(box, -90, -90 + frac * 360, fill=(*hex_rgb(color), 55), width=max(4, 3 * ss))
    d.arc(box, -90, -90 + frac * 360, fill=color, width=max(3, 2 * ss))
    radius = (sz - 2 * pad) / 2.0
    for angle in (-90, -90 + frac * 360):
        rad = math.radians(angle)
        cx = sz / 2 + radius * math.cos(rad)
        cy = sz / 2 + radius * math.sin(rad)
        d.ellipse((cx - ss, cy - ss, cx + ss, cy + ss), fill=color)
    out = img.resize((size, size), Image.Resampling.LANCZOS)
    _RING_CACHE[key] = out
    return out


def ring_ctk(remaining, size=66):
    key = (remaining, size)
    cached = _RING_CTK_CACHE.get(key)
    if cached is not None:
        return cached
    source = ring_image(remaining, size)
    image = ctk.CTkImage(light_image=source, dark_image=source, size=(size, size))
    _RING_CTK_CACHE[key] = image
    return image


def glow_image(width, height, color=GOLD, strength=80):
    key = (width, height, color, strength)
    cached = _GLOW_CACHE.get(key)
    if cached is not None:
        return cached
    small = Image.new('RGBA', (180, 180), (0, 0, 0, 0))
    d = ImageDraw.Draw(small)
    rgb = hex_rgb(color)
    for radius in range(90, 0, -2):
        alpha = int(strength * (1 - radius / 90.0) ** 2.1)
        if alpha <= 0:
            continue
        d.ellipse((90 - radius, 90 - radius, 90 + radius, 90 + radius),
                  fill=(*rgb, alpha))
    small = small.filter(ImageFilter.GaussianBlur(14))
    big = small.resize((max(2, width), max(2, height)), Image.Resampling.BILINEAR)
    ctk_image = ctk.CTkImage(light_image=big, dark_image=big, size=(width, height))
    _GLOW_CACHE[key] = ctk_image
    return ctk_image


_VIGNETTE_BASE = None


def vignette_overlay(width, height, strength=128):
    global _VIGNETTE_BASE
    if _VIGNETTE_BASE is None:
        base = Image.new('RGBA', (180, 180), (0, 0, 0, 0))
        pixels = base.load()
        for y in range(180):
            for x in range(180):
                dx = (x - 90) / 90.0
                dy = (y - 90) / 90.0
                distance = min(1.25, math.sqrt(dx * dx + dy * dy) / 1.12)
                alpha = int(strength * max(0.0, (distance - 0.42) / 0.58) ** 1.8)
                pixels[x, y] = (0, 0, 0, alpha)
        _VIGNETTE_BASE = base.filter(ImageFilter.GaussianBlur(9))
    return _VIGNETTE_BASE.resize((max(2, width), max(2, height)),
                                 Image.Resampling.BILINEAR)


# ---------------------------------------------------------------------------
# Coffre chiffré
# ---------------------------------------------------------------------------
def b32decode(secret):
    value = ''.join(secret.strip().replace(' ', '').replace('-', '').upper().split())
    return base64.b32decode(value + '=' * ((8 - len(value) % 8) % 8), casefold=True)


def totp(secret, timestamp=None):
    counter = int((time.time() if timestamp is None else timestamp) // PERIOD)
    digest = hmac.new(b32decode(secret), struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    number = (struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000
    return f'{number:06d}'


def derive(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000, 32)


def load_vault(password):
    raw = json.loads(VAULT.read_text(encoding='utf-8'))
    salt = base64.b64decode(raw['salt'])
    nonce = base64.b64decode(raw['nonce'])
    plain = AESGCM(derive(password, salt)).decrypt(nonce, base64.b64decode(raw['data']),
                                                   b'NoctisAuth-v1')
    return json.loads(plain.decode()), salt


def save_vault(password, accounts, salt=None):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    salt = salt or os.urandom(16)
    nonce = os.urandom(12)
    encrypted = AESGCM(derive(password, salt)).encrypt(
        nonce, json.dumps(accounts, ensure_ascii=False).encode(), b'NoctisAuth-v1')
    tmp = VAULT.with_suffix('.tmp')
    tmp.write_text(json.dumps({
        'version': 1,
        'salt': base64.b64encode(salt).decode(),
        'nonce': base64.b64encode(nonce).decode(),
        'data': base64.b64encode(encrypted).decode(),
    }), encoding='utf-8')
    tmp.replace(VAULT)
    return salt


# ---------------------------------------------------------------------------
# Fenêtres modales en verre
# ---------------------------------------------------------------------------
class Modal(ctk.CTkToplevel):
    def __init__(self, app, title, subtitle='', width=540, height=410,
                 icon='lock', tone='gold'):
        super().__init__(app)
        self.app = app
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=MODAL_BG)
        try:
            self.iconbitmap(resource_path('noctis.ico'))
        except Exception:
            pass
        self.transient(app)
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.bind('<Escape>', lambda _event: self._close())
        self._closed = False
        self._first_focus = None

        accent = ctk.CTkFrame(self, height=3, fg_color=GOLD, corner_radius=0)
        accent.pack(fill='x')
        head = ctk.CTkFrame(self, fg_color='transparent')
        head.pack(fill='x', padx=28, pady=(22, 16))
        ctk.CTkLabel(head, text='', image=icon_tile_ctk(icon, 48, tone),
                     fg_color='transparent').pack(side='left', padx=(0, 15))
        box = ctk.CTkFrame(head, fg_color='transparent')
        box.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(box, text=title, text_color=WHITE, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=20, weight='bold')).pack(
                         anchor='w', pady=(3, 0))
        if subtitle:
            ctk.CTkLabel(box, text=subtitle, text_color=MUTED, anchor='w', justify='left',
                         wraplength=width - 130,
                         font=ctk.CTkFont(family=FONT_UI, size=12)).pack(
                             anchor='w', pady=(3, 0))
        ctk.CTkFrame(self, height=1, fg_color=LINE).pack(fill='x', padx=26)

        self.footer = ctk.CTkFrame(self, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=26, pady=(8, 20))
        self.body = ctk.CTkFrame(self, fg_color='transparent')
        self.body.pack(fill='both', expand=True, padx=26, pady=(16, 4))

        try:
            sw = app.winfo_width()
            sh = app.winfo_height()
            if sw < 200 or sh < 200:
                sw, sh = 1480, 920
            x = app.winfo_rootx() + (sw - width) // 2
            y = app.winfo_rooty() + (sh - height) // 2
        except Exception:
            x = y = 180
        self.geometry(f'{width}x{height}+{max(0, x)}+{max(0, y)}')
        self.deiconify()
        self.update_idletasks()
        self.lift()
        self.after(30, self._grab)
        self.after(80, self._focus)

    def _grab(self):
        try:
            if self.winfo_exists():
                self.grab_set()
                self.focus_force()
        except Exception:
            pass

    def _focus(self):
        try:
            if self._first_focus is not None:
                self._first_focus.focus_set()
        except Exception:
            pass

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def label(self, text, color=MUTED, size=12, pady=(0, 10), wrap=None, bold=False):
        label = ctk.CTkLabel(self.body, text=text, text_color=color, anchor='w',
                             justify='left', wraplength=wrap or 430,
                             font=ctk.CTkFont(family=FONT_UI, size=size,
                                              weight='bold' if bold else 'normal'))
        label.pack(anchor='w', pady=pady)
        return label

    def field(self, placeholder, value='', masked=False, reveal=False, icon=None,
              label=None, return_command=None):
        if label:
            ctk.CTkLabel(self.body, text=label, text_color=GOLD_DIM, anchor='w',
                         font=ctk.CTkFont(family=FONT_UI, size=10, weight='bold')).pack(
                             anchor='w', pady=(6, 6))
        shell = ctk.CTkFrame(self.body, fg_color=INPUT_BG, corner_radius=14,
                             border_width=1, border_color=LINE, height=50)
        shell.pack(fill='x', pady=(0, 12))
        shell.pack_propagate(False)
        left_pad = 12
        if icon:
            ctk.CTkLabel(shell, text='', image=ctk_icon(icon, 17, SUBTLE),
                         fg_color='transparent', width=17, height=17).pack(
                             side='left', padx=(14, 9))
            left_pad = 4
        entry = ctk.CTkEntry(shell, placeholder_text=placeholder, height=40,
                             corner_radius=10, border_width=0, fg_color='transparent',
                             text_color=WHITE, placeholder_text_color=SUBTLE,
                             show='•' if masked else '',
                             font=ctk.CTkFont(family=FONT_UI, size=13))
        entry.pack(side='left', fill='x', expand=True, padx=(left_pad, 10), pady=5)
        if reveal:
            eye = GlassButton(shell, icon='eye', width=32, height=32, radius=10,
                              style='ghost', tone='neutral', base=INPUT_BG,
                              icon_size=15, padx=0,
                              command=lambda: self._toggle_reveal(entry, eye))
            eye.pack(side='right', padx=(0, 7))

        def focus_in(_event):
            shell.configure(border_color=GOLD_DIM)

        def focus_out(_event):
            shell.configure(border_color=LINE)

        entry.bind('<FocusIn>', focus_in)
        entry.bind('<FocusOut>', focus_out)
        if return_command:
            entry.bind('<Return>', lambda _e: return_command())
        if value:
            entry.insert(0, value)
        if self._first_focus is None:
            self._first_focus = entry
        return entry

    @staticmethod
    def _toggle_reveal(entry, button):
        hidden = entry.cget('show') == '•'
        entry.configure(show='' if hidden else '•')
        button.set_icon('eye-off' if hidden else 'eye')

    def action(self, text, command, style='glass', tone='neutral', icon=None, width=170):
        button = GlassButton(self.footer, text=text, command=command, width=width,
                             height=44, radius=14, style=style, tone=tone,
                             base=MODAL_BG, icon=icon, icon_size=16, font_size=13)
        button.pack(side='right', padx=(8, 0))
        return button


def readable(color, amount=0.45):
    rgb = hex_rgb(color)
    lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0
    if lum < 0.45:
        return '#%02X%02X%02X' % mix(color, WHITE, amount)
    if isinstance(color, str):
        return color
    return '#%02X%02X%02X' % hex_rgb(color)


def format_code(value):
    return f'{value[:3]} {value[3:]}'


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class AuthApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.configure(fg_color=BG)
        self.minsize(1100, 740)
        try:
            icon_file = resource_path('noctis.ico')
            self.iconbitmap(default=icon_file)
            self.iconbitmap(icon_file)
        except Exception:
            pass

        self.password = None
        self.accounts = []
        self.salt = None
        self.cards = []
        self.card_by_index = {}
        self.current_page = 'accounts'
        self.selected_service = None
        self._service_results = []
        self._service_tiles = {}
        self._acct_search_job = None
        self._svc_search_job = None
        self._error_job = None
        self._auto_name = True
        self._animation_phase = 0.0
        self._animation_job = None
        self._resize_job = None
        self._bg_small = None
        self._bg_small_key = None
        self.preferences = load_preferences()
        self._update_busy = False
        self._available_release = None
        self._update_badge_visible = False

        self._load_assets()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.bg_label = ctk.CTkLabel(self, text='', image=self.bg_image)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.sidebar = ctk.CTkFrame(self, width=272, corner_radius=0, fg_color=SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky='nsew')
        self.sidebar.grid_propagate(False)
        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main.grid(row=0, column=1, sticky='nsew', padx=(30, 32), pady=(20, 18))
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self._build_sidebar()
        self._build_header()
        self._build_pages()
        self._build_status()

        self.bind('<Configure>', self._on_resize)
        self.update_idletasks()
        width, height = 1480, 920
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(width, max(1100, screen_w - 80))
        height = min(height, max(740, screen_h - 100))
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - 20)
        self.geometry(f'{width}x{height}+{x}+{y}')
        self._switch_page('accounts')
        self.after(260, self._animate_background)
        self.after(320, self.unlock)
        self.after(800, self.refresh)
        if self.preferences.get('check_updates_on_start', True):
            self.after(7000, lambda: self.check_updates(manual=False))

    # ------------------------------------------------------------------ setup
    def _load_assets(self):
        bg_path = resource_path(os.path.join('assets', 'noctis_background.png'))
        logo_path = resource_path(os.path.join('assets', 'noctis_logo.png'))
        try:
            bg = Image.open(bg_path).convert('RGB')
        except Exception:
            bg = vertical_gradient((1536, 1024), '#16110A', '#07080B').convert('RGB')
        self.bg_original = bg
        self.bg_image = ctk.CTkImage(light_image=bg, dark_image=bg, size=(1480, 920))
        try:
            logo = Image.open(logo_path).convert('RGBA')
            box = logo.getbbox()
            if box:
                logo = logo.crop(box)
            side = max(logo.width, logo.height)
            pad = int(side * 0.16)
            square = Image.new('RGBA', (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
            square.alpha_composite(logo, ((square.width - logo.width) // 2,
                                          (square.height - logo.height) // 2))
        except Exception:
            square = vertical_gradient((128, 128), '#FFE08A', '#C99A28')
        self.logo_image = ctk.CTkImage(light_image=square, dark_image=square, size=(58, 58))
        self.logo_big_image = ctk.CTkImage(light_image=square, dark_image=square, size=(92, 92))

    def _build_sidebar(self):
        edge = ctk.CTkFrame(self.sidebar, width=1, fg_color='#1B1F28', corner_radius=0)
        edge.place(relx=1.0, x=-1, relheight=1)

        brand = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        brand.pack(fill='x', pady=(32, 0))
        banner = ctk.CTkFrame(brand, fg_color='transparent', width=126, height=104)
        banner.pack(anchor='center')
        banner.pack_propagate(False)
        glow = ctk.CTkLabel(banner, text='', image=glow_image(126, 104, GOLD, 74),
                            fg_color='transparent')
        glow.place(relx=0.5, rely=0.5, anchor='center')
        ctk.CTkLabel(banner, text='', image=self.logo_image,
                     fg_color='transparent').place(relx=0.5, rely=0.5, anchor='center')
        name_row = ctk.CTkFrame(brand, fg_color='transparent')
        name_row.pack(anchor='center', pady=(2, 2))
        ctk.CTkLabel(name_row, text='NOCTIS', text_color=WHITE,
                     font=ctk.CTkFont(family=FONT_UI, size=20, weight='bold')).pack(side='left')
        ctk.CTkLabel(name_row, text=' AUTH', text_color=GOLD,
                     font=ctk.CTkFont(family=FONT_UI, size=20, weight='bold')).pack(side='left')
        ctk.CTkLabel(brand, text='Authentificateur local', text_color=SUBTLE,
                     font=ctk.CTkFont(family=FONT_UI, size=11)).pack(anchor='center')

        ctk.CTkLabel(self.sidebar, text='NAVIGATION', text_color='#4E5361', anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).pack(
                         anchor='w', padx=30, pady=(32, 8))

        self.nav = {}
        self.nav['accounts'] = self._nav_button('grid', 'Mes comptes', self.show_accounts)

        def add_from_nav():
            self.add_account()

        self.nav['add'] = self._nav_button('plus', 'Nouveau compte', add_from_nav)
        self.nav['settings'] = self._nav_button('sliders', 'Paramètres', self.show_settings)
        self.nav['about'] = self._nav_button('info', 'À propos', self.show_about)
        for key in ('accounts', 'add', 'settings', 'about'):
            self.nav[key].pack(anchor='w', padx=24, pady=3)

        ctk.CTkFrame(self.sidebar, fg_color='transparent', width=1, height=1).pack(
            expand=True, fill='both')

        summary = ctk.CTkFrame(self.sidebar, fg_color=SURFACE, corner_radius=18,
                               border_width=1, border_color=LINE)
        summary.pack(fill='x', padx=20, pady=(0, 10))
        ctk.CTkLabel(summary, text='', image=icon_tile_ctk('key', 34, 'gold'),
                     fg_color='transparent').pack(side='left', padx=(12, 10), pady=12)
        summary_text = ctk.CTkFrame(summary, fg_color='transparent')
        summary_text.pack(side='left', pady=10)
        self.sidebar_count = ctk.CTkLabel(summary_text, text='0 compte', text_color=WHITE,
                                          anchor='w',
                                          font=ctk.CTkFont(family=FONT_UI, size=12, weight='bold'))
        self.sidebar_count.pack(anchor='w')
        ctk.CTkLabel(summary_text, text='protégé localement', text_color=SUBTLE, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=10)).pack(anchor='w')

        secure = ctk.CTkFrame(self.sidebar, fg_color=SURFACE, corner_radius=18,
                              border_width=1, border_color=LINE)
        secure.pack(fill='x', padx=20, pady=(0, 18))
        ctk.CTkLabel(secure, text='', image=icon_tile_ctk('shield', 34, 'green'),
                     fg_color='transparent').pack(side='left', padx=(12, 10), pady=12)
        secure_text = ctk.CTkFrame(secure, fg_color='transparent')
        secure_text.pack(side='left', pady=10)
        ctk.CTkLabel(secure_text, text='Chiffré localement', text_color=WHITE, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=12, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(secure_text, text='AES-256-GCM  ·  hors ligne', text_color=SUBTLE,
                     anchor='w', font=ctk.CTkFont(family=FONT_UI, size=10)).pack(anchor='w')
        ctk.CTkLabel(secure, text='●', text_color=GREEN, font=ctk.CTkFont(size=10)).pack(
            side='right', padx=(4, 14))

        self.update_btn = GlassButton(self.sidebar, text='Mise à jour disponible',
                                      icon='download', command=self._open_available_update,
                                      width=224, height=44, radius=14, style='glass',
                                      tone='gold', align='w', font_size=11, bold=True,
                                      base=SIDEBAR, icon_size=15, padx=15, gap=9)
        self.version_label = ctk.CTkLabel(self.sidebar, text=f'v{APP_VERSION}  ·  Noctis',
                                          text_color='#414653',
                                          font=ctk.CTkFont(family=FONT_UI, size=9))
        self.version_label.pack(pady=(0, 18))

    def _nav_button(self, icon, text, command):
        return GlassButton(self.sidebar, text=text, icon=icon, command=command,
                           width=224, height=50, radius=15, style='glass', tone='gold',
                           align='w', font_size=13, bold=True, base=SIDEBAR,
                           icon_size=17, padx=17, gap=10)

    def _build_header(self):
        header = ctk.CTkFrame(self.main, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', pady=(4, 14))
        header.grid_columnconfigure(0, weight=1)
        self.header = header

        ctk.CTkLabel(header, text='', image=glow_image(470, 270, GOLD, 46),
                     fg_color='transparent').place(x=-130, y=-128)

        left = ctk.CTkFrame(header, fg_color='transparent')
        left.grid(row=0, column=0, sticky='w')
        eyebrow = ctk.CTkFrame(left, fg_color='transparent')
        eyebrow.pack(anchor='w', pady=(0, 6))
        ctk.CTkFrame(eyebrow, width=18, height=2, fg_color=GOLD,
                     corner_radius=1).pack(side='left', padx=(0, 9))
        self.eyebrow = ctk.CTkLabel(eyebrow, text='COFFRE PERSONNEL  ·  CHIFFRÉ LOCALEMENT',
                                    text_color=GOLD_DIM,
                                    font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold'))
        self.eyebrow.pack(side='left')
        self.title_label = ctk.CTkLabel(left, text='', fg_color='transparent')
        self.title_label.pack(anchor='w', pady=(0, 2))
        self.subtitle_label = ctk.CTkLabel(left, text='', text_color=MUTED, anchor='w',
                                           font=ctk.CTkFont(family=FONT_UI, size=13))
        self.subtitle_label.pack(anchor='w')

        actions = ctk.CTkFrame(header, fg_color='transparent')
        actions.grid(row=0, column=1, sticky='e')
        self.add_btn = GlassButton(actions, text='Nouveau compte', icon='plus',
                                   command=self.add_account, width=204, height=52,
                                   radius=17, style='gold', align='center', font_size=13,
                                   base=BG, icon_size=17, padx=18, gap=9)
        self.add_btn.grid(row=0, column=0)
        self.back_btn = GlassButton(actions, text='Retour aux comptes', icon='arrow-left',
                                    command=self.show_accounts, width=194, height=48,
                                    radius=16, style='glass', tone='neutral',
                                    align='center', font_size=12, base=BG,
                                    icon_size=16, padx=16, gap=8)
        self.back_btn.grid(row=0, column=0)
        self.back_btn.grid_remove()

    def _build_pages(self):
        holder = ctk.CTkFrame(self.main, fg_color='transparent')
        holder.grid(row=1, column=0, sticky='nsew')
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)
        self.holder = holder

        self.accounts_page = ctk.CTkFrame(holder, fg_color='transparent')
        self.accounts_page.grid(row=0, column=0, sticky='nsew')
        self.accounts_page.grid_columnconfigure(0, weight=1)
        self.accounts_page.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self.accounts_page, fg_color='transparent')
        toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 14))
        toolbar.grid_columnconfigure(0, weight=1)
        self.search_box = GlassSearch(toolbar, 'Rechercher un compte, un service, une catégorie...',
                                      height=48, on_change=self._on_account_search)
        self.search_box.grid(row=0, column=0, sticky='ew')
        self.search_var = self.search_box.var
        self.count_label = ctk.CTkLabel(toolbar, text='00 COMPTE', text_color=GOLD,
                                        fg_color=SURFACE_2, corner_radius=12, height=34,
                                        width=116, font=ctk.CTkFont(family=FONT_UI, size=10,
                                                                    weight='bold'))
        self.count_label.grid(row=0, column=1, padx=(14, 0))

        # Le scroll est entièrement géré par CTkScrollableFrame (routage par widget).
        self.list = ctk.CTkScrollableFrame(
            self.accounts_page, fg_color='transparent', corner_radius=0,
            scrollbar_fg_color='#0B0D11', scrollbar_button_color='#2B303B',
            scrollbar_button_hover_color='#4A4130')
        self.list.grid(row=1, column=0, sticky='nsew')
        self.list.grid_columnconfigure(0, weight=1)

        self.add_page = ctk.CTkFrame(holder, fg_color='transparent')
        self.add_page.grid(row=0, column=0, sticky='nsew')
        self.add_page.grid_columnconfigure(0, weight=1)
        self.add_page.grid_rowconfigure(0, weight=1)
        self._build_add_page()

    def _build_add_page(self):
        card = ctk.CTkFrame(self.add_page, fg_color=SURFACE, corner_radius=26,
                            border_width=1, border_color=LINE)
        card.grid(row=0, column=0, sticky='nsew')
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)
        self.add_card = card

        top = ctk.CTkFrame(card, fg_color='transparent')
        top.grid(row=0, column=0, sticky='ew', padx=28, pady=(22, 0))
        top.grid_columnconfigure(0, weight=1)
        top_text = ctk.CTkFrame(top, fg_color='transparent')
        top_text.grid(row=0, column=0, sticky='w')
        ctk.CTkLabel(top_text, text='Choisir un service', text_color=WHITE, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=18, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(top_text, text=f'{len(SERVICES)} services disponibles  ·  tape pour filtrer',
                     text_color=MUTED, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=11)).pack(anchor='w', pady=(2, 0))
        self.service_count = ctk.CTkLabel(top, text='Populaires', text_color=GOLD,
                                          fg_color=SURFACE_2, corner_radius=10, height=28,
                                          width=112, font=ctk.CTkFont(family=FONT_UI, size=10,
                                                                      weight='bold'))
        self.service_count.grid(row=0, column=1, sticky='e')

        self.service_search = GlassSearch(
            card, 'Rechercher un service : Discord, Steam, banque, gaming...',
            height=48, on_change=self._on_service_search)
        self.service_search.grid(row=1, column=0, sticky='ew', padx=28, pady=(14, 10))
        self.service_search.entry.bind('<Return>', lambda _e: self._pick_first_service())

        self.services_frame = ctk.CTkScrollableFrame(
            card, fg_color='transparent', corner_radius=0,
            scrollbar_fg_color='#0F1117', scrollbar_button_color='#2B303B',
            scrollbar_button_hover_color='#4A4130')
        self.services_frame.grid(row=2, column=0, sticky='nsew', padx=(24, 20))
        for column in range(4):
            self.services_frame.grid_columnconfigure(column, weight=1, uniform='service')

        selected_bar = ctk.CTkFrame(card, fg_color=SURFACE_2, corner_radius=14,
                                    border_width=1, border_color=LINE)
        selected_bar.grid(row=3, column=0, sticky='ew', padx=28, pady=(10, 12))
        self.selected_icon = ctk.CTkLabel(selected_bar, text='',
                                          image=tile_ctk(service_for('Autre'), 34),
                                          fg_color='transparent')
        self.selected_icon.pack(side='left', padx=(10, 10), pady=6)
        self.selected_label = ctk.CTkLabel(selected_bar, text='Aucun service sélectionné',
                                           text_color=MUTED, anchor='w',
                                           font=ctk.CTkFont(family=FONT_UI, size=12,
                                                            weight='bold'))
        self.selected_label.pack(side='left')
        self.selected_tag = ctk.CTkLabel(selected_bar, text='', text_color=SUBTLE,
                                         anchor='e',
                                         font=ctk.CTkFont(family=FONT_UI, size=10))
        self.selected_tag.pack(side='right', padx=(8, 14))

        ctk.CTkFrame(card, height=1, fg_color=LINE).grid(row=4, column=0, sticky='ew',
                                                         padx=28)

        fields = ctk.CTkFrame(card, fg_color='transparent')
        fields.grid(row=5, column=0, sticky='ew', padx=28, pady=(14, 0))
        fields.grid_columnconfigure(0, weight=1, uniform='field')
        fields.grid_columnconfigure(1, weight=1, uniform='field')

        ctk.CTkLabel(fields, text='NOM DU COMPTE', text_color=GOLD_DIM, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).grid(
                         row=0, column=0, sticky='w', padx=(0, 10), pady=(0, 6))
        ctk.CTkLabel(fields, text='CLÉ SECRÈTE A2F (BASE32)', text_color=GOLD_DIM, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).grid(
                         row=0, column=1, sticky='w', padx=(10, 0), pady=(0, 6))

        self.name_entry = ctk.CTkEntry(
            fields, placeholder_text='Ex. Mon compte personnel', height=44,
            corner_radius=13, border_width=1, border_color=LINE, fg_color=INPUT_BG,
            text_color=WHITE, placeholder_text_color=SUBTLE,
            font=ctk.CTkFont(family=FONT_UI, size=12))
        self.name_entry.grid(row=1, column=0, sticky='ew', padx=(0, 10))
        self.name_entry.bind('<FocusIn>', lambda _e: self.name_entry.configure(border_color=GOLD_DIM))
        self.name_entry.bind('<FocusOut>', lambda _e: self.name_entry.configure(border_color=LINE))
        self.name_entry.bind('<KeyRelease>', lambda _e: setattr(self, '_auto_name', False))

        secret_shell = ctk.CTkFrame(fields, fg_color=INPUT_BG, corner_radius=13,
                                    border_width=1, border_color=LINE, height=44)
        secret_shell.grid(row=1, column=1, sticky='ew', padx=(10, 0))
        secret_shell.pack_propagate(False)
        self.secret_shell = secret_shell
        self.secret_entry = ctk.CTkEntry(
            secret_shell, placeholder_text='Colle la vraie clé fournie par le service',
            height=36, corner_radius=10, border_width=0, fg_color='transparent',
            text_color=WHITE, placeholder_text_color=SUBTLE,
            font=ctk.CTkFont(family=FONT_UI, size=12))
        self.secret_entry.pack(side='left', fill='x', expand=True, padx=(12, 4), pady=4)
        self.secret_eye = GlassButton(
            secret_shell, icon='eye', command=self._toggle_secret, width=30, height=30,
            radius=9, style='ghost', tone='neutral', base=INPUT_BG, icon_size=14, padx=0)
        self.secret_eye.pack(side='right', padx=(0, 5))
        self.secret_entry.bind('<FocusIn>', lambda _e: secret_shell.configure(border_color=GOLD_DIM))
        self.secret_entry.bind('<FocusOut>', lambda _e: secret_shell.configure(border_color=LINE))

        info_row = ctk.CTkFrame(card, fg_color='transparent')
        info_row.grid(row=6, column=0, sticky='ew', padx=28, pady=(8, 0))
        info_row.grid_columnconfigure(0, weight=1)
        self.form_error = ctk.CTkLabel(info_row, text='', text_color=RED, anchor='w',
                                       font=ctk.CTkFont(family=FONT_UI, size=11))
        self.form_error.grid(row=0, column=0, sticky='w')
        ctk.CTkLabel(info_row,
                     text='La clé est vérifiée avant enregistrement  ·  rien ne quitte cet appareil',
                     text_color='#5A5F6C', anchor='e',
                     font=ctk.CTkFont(family=FONT_UI, size=9)).grid(row=0, column=1, sticky='e')

        actions = ctk.CTkFrame(card, fg_color='transparent')
        actions.grid(row=7, column=0, sticky='e', padx=28, pady=(12, 22))
        GlassButton(actions, text='Annuler', icon='x', command=self.show_accounts,
                    width=128, height=46, radius=15, style='glass', tone='neutral',
                    font_size=12, base=SURFACE, icon_size=15, padx=15, gap=7).grid(
                        row=0, column=0, padx=(0, 10))
        self.save_btn = GlassButton(actions, text='Ajouter le compte', icon='plus',
                                    command=self.save_account, width=198, height=48,
                                    radius=15, style='gold', font_size=12, base=SURFACE,
                                    icon_size=16, padx=16, gap=8)
        self.save_btn.grid(row=0, column=1)

    def _build_status(self):
        status_row = ctk.CTkFrame(self.main, fg_color='transparent')
        status_row.grid(row=2, column=0, sticky='ew', pady=(12, 0))
        status_row.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(status_row, text='●  Coffre verrouillé', text_color=SUBTLE,
                                   anchor='w', font=ctk.CTkFont(family=FONT_UI, size=10))
        self.status.grid(row=0, column=0, sticky='w')
        ctk.CTkLabel(status_row, text='AES-256-GCM  ·  HORS LIGNE', text_color='#3F4450',
                     anchor='e', font=ctk.CTkFont(family=FONT_UI, size=9)).grid(
                         row=0, column=1, sticky='e')

    # ------------------------------------------------------------------ window
    def _on_resize(self, event):
        if event.widget is not self:
            return
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(150, self._resize_background)

    def _resize_background(self):
        try:
            width = max(900, self.winfo_width())
            height = max(650, self.winfo_height())
            self.bg_image.configure(size=(width, height))
            self._bg_small_key = None
        except Exception:
            pass

    def _build_bg_small(self, width, height):
        key = (width, height)
        if self._bg_small_key == key and self._bg_small is not None:
            return self._bg_small
        sw = max(460, int(width * 0.5))
        sh = max(320, int(height * 0.5))
        base = self.bg_original.resize((sw, sh), Image.Resampling.LANCZOS).convert('RGBA')
        base = Image.alpha_composite(base, Image.new('RGBA', (sw, sh), (6, 7, 10, 172)))
        try:
            base = Image.alpha_composite(base, vignette_overlay(sw, sh))
        except Exception:
            pass
        self._bg_small = base
        self._bg_small_key = key
        return base

    def _animate_background(self):
        try:
            if self.winfo_viewable() and self.state() != 'iconic':
                width = max(760, self.winfo_width())
                height = max(520, self.winfo_height())
                base = self._build_bg_small(width, height)
                sw, sh = base.size
                phase = self._animation_phase
                glow = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
                draw = ImageDraw.Draw(glow)
                for band in range(6):
                    speed = 0.020 + band * 0.0035
                    y_base = int(sh * ((band * 0.172 + 0.04) % 0.94))
                    pts = []
                    for step in range(41):
                        t = step / 40.0
                        x = int(-sw * 0.10 + t * sw * 1.2)
                        wave = math.sin(t * math.pi * 2 + phase * (1.6 + band * 0.18) + band * 1.7)
                        wave2 = math.sin(t * math.pi * 4 - phase * 1.05 + band * 0.8)
                        y = int(y_base + wave * sh * 0.052 + wave2 * sh * 0.016)
                        pts.append((x, y))
                    pulse = 0.5 + 0.5 * math.sin(phase * 2.1 + band * 0.9)
                    draw.line(pts, fill=(255, 186, 70, int(22 + 38 * pulse)),
                              width=2 + (band % 2), joint='curve')
                for i in range(3):
                    x = int(((phase * (0.06 + i * 0.014) + i * 0.33) % 1.0) * sw)
                    y = int(sh * (0.2 + i * 0.24 + math.sin(phase * 1.7 + i) * 0.035))
                    draw.line((x - 90, y + 34, x + 90, y - 34),
                              fill=(255, 215, 130, 80), width=2)
                glow = glow.filter(ImageFilter.GaussianBlur(6))
                frame = Image.alpha_composite(base, glow)
                self._animated_bg_image = ctk.CTkImage(
                    light_image=frame, dark_image=frame, size=(width, height))
                self.bg_label.configure(image=self._animated_bg_image)
                self._animation_phase = (phase + 0.10) % 1000
        except Exception:
            pass
        try:
            if self.winfo_exists():
                self._animation_job = self.after(150, self._animate_background)
        except Exception:
            pass

    # ------------------------------------------------------------- navigation
    def _switch_page(self, name):
        self.current_page = name
        if name == 'add':
            self.add_page.tkraise()
            self.add_btn.grid_remove()
            self.back_btn.grid()
            self.title_label.configure(image=gradient_title(
                [('Nouveau ', ('#FFFFFF', '#B9BEC9')), ('compte', ('#FFE9A8', '#F4C542'))]))
            self.subtitle_label.configure(
                text='Sélectionne un service puis colle la vraie clé A2F fournie par ses paramètres.')
        else:
            self.accounts_page.tkraise()
            self.back_btn.grid_remove()
            self.add_btn.grid()
            self.title_label.configure(image=gradient_title(
                [('Mes ', ('#FFFFFF', '#B9BEC9')), ('comptes', ('#FFE9A8', '#F4C542'))]))
            self.subtitle_label.configure(text='Retrouve, copie et gère tes codes de sécurité.')
        self.nav['accounts'].set_selected(name == 'accounts')
        self.nav['add'].set_selected(name == 'add')

    def _on_account_search(self):
        if self._acct_search_job:
            try:
                self.after_cancel(self._acct_search_job)
            except Exception:
                pass
        self._acct_search_job = self.after(140, self.render_accounts)

    def _on_service_search(self):
        if self._svc_search_job:
            try:
                self.after_cancel(self._svc_search_job)
            except Exception:
                pass
        self.service_count.configure(text='Recherche…')
        self._svc_search_job = self.after(120, self._render_services)

    # ---------------------------------------------------------------- services
    def _render_services(self):
        if not hasattr(self, 'services_frame') or not self.services_frame.winfo_exists():
            return
        if self._svc_search_job:
            try:
                self.after_cancel(self._svc_search_job)
            except Exception:
                pass
            self._svc_search_job = None
        for widget in self.services_frame.winfo_children():
            widget.destroy()
        self._service_tiles = {}
        query = self.service_search.get().strip()
        needle = normalize(query)
        if needle:
            matches = [s for s in SERVICES
                       if needle in normalize(s['name']) or needle in normalize(s['tag'])
                       or needle in normalize(s['abbr'])]
            if not matches and len(query) >= 2:
                matches.insert(0, {'name': query.title(), 'color': '#8A8F98',
                                   'abbr': '+', 'tag': 'Personnalisé'})
        else:
            matches = [service_for(name) for name in POPULAR]
        if not matches and needle:
            self._service_results = []
            self.service_count.configure(text='0 trouvé')
            hint = ctk.CTkLabel(
                self.services_frame,
                text='Aucun service ne correspond à cette recherche.\nContinue à taper pour créer une tuile personnalisée.',
                text_color=SUBTLE, justify='center',
                font=ctk.CTkFont(family=FONT_UI, size=11))
            hint.grid(row=0, column=0, columnspan=4, pady=40)
            self.after_idle(self._scroll_services_top)
            return
        if not matches:
            matches = [service_for('Autre')]
        self._service_results = matches[:64]

        for index, service in enumerate(self._service_results):
            chosen = (self.selected_service is not None and
                      normalize(self.selected_service['name']) == normalize(service['name']))
            button = ctk.CTkButton(
                self.services_frame,
                text='   ' + service['name'],
                image=tile_ctk(service, 28),
                compound='left', anchor='w',
                height=54, corner_radius=14, border_width=1,
                border_color=GOLD if chosen else '#242A36',
                fg_color='#282213' if chosen else SURFACE_2,
                hover_color='#332B18' if chosen else '#1B1F28',
                text_color=GOLD_LIGHT if chosen else '#D8DBE2',
                font=ctk.CTkFont(family=FONT_UI, size=11,
                                 weight='bold' if chosen else 'normal'),
                command=lambda s=service: self._select_service(s))
            button.grid(row=index // 4, column=index % 4, sticky='ew', padx=4, pady=4)
            self._service_tiles[normalize(service['name'])] = (button, service)

        total = len(matches)
        if needle:
            suffix = f'{len(self._service_results)} / {total}' if total > 64 else f'{total} trouvé' + ('s' if total > 1 else '')
            self.service_count.configure(text=suffix)
        else:
            self.service_count.configure(text='Populaires')
        self.after_idle(self._scroll_services_top)

    def _scroll_services_top(self):
        try:
            self.services_frame._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _pick_first_service(self):
        if self._service_results:
            self._select_service(self._service_results[0])

    def _select_service(self, service):
        self.selected_service = service
        chosen_key = normalize(service['name'])
        for key, (button, _service) in self._service_tiles.items():
            if key == chosen_key:
                button.configure(fg_color='#282213', hover_color='#332B18',
                                 border_color=GOLD, text_color=GOLD_LIGHT,
                                 font=ctk.CTkFont(family=FONT_UI, size=11, weight='bold'))
            else:
                button.configure(fg_color=SURFACE_2, hover_color='#1B1F28',
                                 border_color='#242A36', text_color='#D8DBE2',
                                 font=ctk.CTkFont(family=FONT_UI, size=11))
        self.selected_icon.configure(image=tile_ctk(service, 34))
        self.selected_label.configure(text=service['name'], text_color=WHITE)
        self.selected_tag.configure(
            text=f'{service["tag"]}  ·  prêt à ajouter', text_color=readable(service['color']))
        if service['name'] != 'Autre' and (self._auto_name or not self.name_entry.get().strip()):
            self.name_entry.delete(0, 'end')
            self.name_entry.insert(0, service['name'])
            self._auto_name = True
        self.form_error.configure(text='')
        self.after(40, self.secret_entry.focus_set)

    def _toggle_secret(self):
        hidden = self.secret_entry.cget('show') == '•'
        self.secret_entry.configure(show='' if hidden else '•')
        self.secret_eye.set_icon('eye-off' if hidden else 'eye')

    # ------------------------------------------------------------------- add
    def add_account(self):
        if self.password is None:
            return
        self._switch_page('add')
        self.selected_service = None
        self._auto_name = True
        self.name_entry.delete(0, 'end')
        self.secret_entry.delete(0, 'end')
        self.secret_entry.configure(show='•')
        self.secret_eye.set_icon('eye')
        self.form_error.configure(text='')
        self.service_search.set('')
        self._render_services()
        self.after(120, self.service_search.entry.focus_set)

    def _show_error(self, text):
        self.form_error.configure(text=text)
        if self._error_job:
            try:
                self.after_cancel(self._error_job)
            except Exception:
                pass
        self._error_job = self.after(7000, lambda: self.form_error.configure(text=''))

    def save_account(self):
        service = self.selected_service
        if service is None:
            self._show_error('Choisis d’abord un service dans la liste ci-dessus.')
            self.service_search.entry.focus_set()
            return
        name = self.name_entry.get().strip()
        if not name:
            self._show_error('Donne un nom à ce compte.')
            self.name_entry.focus_set()
            return
        raw = self.secret_entry.get().strip().replace(' ', '').replace('-', '').upper()
        if not raw:
            self._show_error('La vraie clé A2F est obligatoire, aucun code ne sera inventé.')
            self.secret_entry.focus_set()
            return
        try:
            decoded = b32decode(raw)
            if len(decoded) < 10 or not all(ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=' for ch in raw):
                raise ValueError('Clé Base32 invalide')
            totp(raw)
        except Exception:
            self._show_error('Clé invalide : récupère la vraie clé Base32 dans les paramètres A2F du service.')
            self.secret_entry.focus_set()
            return
        self.accounts.append({'name': name, 'issuer': service['name'], 'secret': raw})
        try:
            self.persist()
        except Exception as exc:
            self.accounts.pop()
            self.alert('Enregistrement impossible', f'Le coffre n’a pas pu être écrit.\n{exc}')
            return
        self.show_accounts()
        self._set_status(f'●  {service["name"]} ajouté  ·  clé A2F vérifiée', GREEN)

    # ---------------------------------------------------------------- accounts
    def _update_counts(self):
        count = len(self.accounts)
        self.count_label.configure(text=f'{count:02d} COMPTE' + ('S' if count > 1 else ''))
        self.sidebar_count.configure(text=f'{count} compte' + ('s' if count > 1 else ''))

    def render_accounts(self):
        if not hasattr(self, 'list') or not self.list.winfo_exists():
            return
        if self._acct_search_job:
            try:
                self.after_cancel(self._acct_search_job)
            except Exception:
                pass
            self._acct_search_job = None
        for widget in self.list.winfo_children():
            widget.destroy()
        self.cards = []
        self.card_by_index = {}
        self._update_counts()
        if self.password is None:
            return
        needle = normalize(self.search_box.get())
        matches = []
        for index, account in enumerate(self.accounts):
            service = service_for(account.get('issuer', ''))
            haystack = ' '.join((normalize(account.get('name', '')),
                                 normalize(account.get('issuer', '')),
                                 normalize(service.get('tag', ''))))
            if not needle or needle in haystack:
                matches.append((index, account, service))
        if not matches:
            self._render_empty(bool(self.accounts), self.search_box.get().strip())
            return
        for row, (index, account, service) in enumerate(matches):
            self._render_card(row, index, account, service)
        self.after_idle(self._scroll_accounts_top)

    def _scroll_accounts_top(self):
        try:
            self.list._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _render_empty(self, has_accounts, query):
        panel = ctk.CTkFrame(self.list, fg_color=CARD, corner_radius=24,
                             border_width=1, border_color=CARD_LINE)
        panel.grid(row=0, column=0, sticky='ew', padx=4, pady=34)
        inner = ctk.CTkFrame(panel, fg_color='transparent')
        inner.pack(expand=True, pady=34)
        if has_accounts:
            icon, title = 'search', 'Aucun résultat'
            hint = f'Aucun compte ne correspond à « {query} ».'
            action_text, action_icon, command = 'Effacer la recherche', 'refresh', lambda: self.search_box.set('')
        else:
            icon, title = 'sparkle', 'Ton coffre est vide'
            hint = 'Ajoute ton premier compte : le code s’affichera ici, prêt à être copié.'
            action_text, action_icon, command = 'Ajouter mon premier compte', 'plus', self.add_account
        ctk.CTkLabel(inner, text='', image=icon_tile_ctk(icon, 58, 'gold'),
                     fg_color='transparent').pack(pady=(0, 14))
        ctk.CTkLabel(inner, text=title, text_color=WHITE,
                     font=ctk.CTkFont(family=FONT_UI, size=20, weight='bold')).pack()
        ctk.CTkLabel(inner, text=hint, text_color=MUTED, wraplength=460,
                     font=ctk.CTkFont(family=FONT_UI, size=12)).pack(pady=(5, 18))
        GlassButton(inner, text=action_text, icon=action_icon, command=command,
                    width=248, height=48, radius=15, style='gold', font_size=12,
                    base=CARD, icon_size=16, padx=16, gap=8).pack()

    def _render_card(self, row, index, account, service):
        card = ctk.CTkFrame(self.list, fg_color=CARD, corner_radius=22,
                            border_width=1, border_color=CARD_LINE, height=112)
        card.grid(row=row, column=0, sticky='ew', pady=6, padx=2)
        card.grid_propagate(False)
        card.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(card, text='', image=tile_ctk(service, 58),
                     fg_color='transparent').grid(row=0, column=0, padx=(18, 14))
        ctk.CTkFrame(card, width=4, height=54, fg_color=service['color'],
                     corner_radius=2).grid(row=0, column=1, padx=(0, 16), sticky='ns')

        info = ctk.CTkFrame(card, fg_color='transparent')
        info.grid(row=0, column=2, sticky='w')
        name = account.get('name', 'Compte')
        display_name = name if len(name) <= 32 else name[:31] + '…'
        ctk.CTkLabel(info, text=display_name, text_color=WHITE, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=16, weight='bold')).pack(anchor='w')
        meta = ctk.CTkFrame(info, fg_color='transparent')
        meta.pack(anchor='w', pady=(5, 0))
        chip_color = readable(service['color'], 0.55)
        ctk.CTkLabel(meta, text=f' {service["name"]} ', text_color=chip_color,
                     fg_color=SURFACE_2, corner_radius=8, height=20,
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).pack(side='left')
        ctk.CTkLabel(meta, text=f'   {service["tag"]}', text_color=SUBTLE, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=10)).pack(side='left')

        code_box = ctk.CTkFrame(card, fg_color='transparent')
        code_box.grid(row=0, column=3, padx=(12, 6))
        ctk.CTkLabel(code_box, text='CODE A2F', text_color='#5B606D', anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=8, weight='bold')).pack(anchor='w')
        try:
            value = totp(account['secret'])
        except Exception:
            value = None
        code_label = ctk.CTkLabel(code_box, text=format_code(value) if value else '--- ---',
                                  text_color=WHITE, cursor='hand2',
                                  font=ctk.CTkFont(family='Consolas', size=26, weight='bold'))
        code_label.pack(anchor='w')
        code_label.bind('<Button-1>', lambda _e, i=index: self.copy_code(i))

        remaining = PERIOD - int(time.time()) % PERIOD
        timer = ctk.CTkLabel(card, text=str(remaining), image=ring_ctk(remaining, 66),
                             compound='center', fg_color='transparent', width=66, height=66,
                             text_color=RED if remaining <= 5 else WHITE,
                             font=ctk.CTkFont(family=FONT_UI, size=13, weight='bold'))
        timer.grid(row=0, column=4, padx=(6, 4))

        actions = ctk.CTkFrame(card, fg_color='transparent')
        actions.grid(row=0, column=5, padx=(2, 16))
        copy_btn = GlassButton(actions, icon='copy', command=lambda i=index: self.copy_code(i),
                               width=42, height=42, radius=13, style='glass', tone='gold',
                               base=CARD, icon_size=17, padx=0)
        copy_btn.pack(side='left', padx=(0, 6))
        stacked = ctk.CTkFrame(actions, fg_color='transparent')
        stacked.pack(side='left')
        GlassButton(stacked, icon='edit', command=lambda i=index: self.rename_account(i),
                    width=32, height=32, radius=10, style='glass', tone='neutral',
                    base=CARD, icon_size=14, padx=0).pack(pady=(0, 4))
        GlassButton(stacked, icon='trash', command=lambda i=index: self.delete_account(i),
                    width=32, height=32, radius=10, style='glass', tone='danger',
                    base=CARD, icon_size=14, padx=0).pack()

        record = {'secret': account['secret'], 'code': code_label, 'timer': timer,
                  'remaining': remaining, 'counter': int(time.time() // PERIOD),
                  'copy': copy_btn}
        self.cards.append(record)
        self.card_by_index[index] = record

    def copy_code(self, index):
        if index not in self.card_by_index:
            return
        try:
            code = totp(self.accounts[index]['secret'])
        except Exception:
            self.alert('Code impossible', 'La clé de ce compte est illisible.')
            return
        self.clipboard_clear()
        self.clipboard_append(code)
        self.update()
        record = self.card_by_index.get(index)
        if record:
            record['copy'].flash_success()
        remaining = PERIOD - int(time.time()) % PERIOD
        self._set_status(f'●  Code copié  ·  expire dans {remaining}s', GOLD)

    def rename_account(self, index):
        if index >= len(self.accounts):
            return
        account = self.accounts[index]
        dialog = Modal(self, 'Modifier le compte', 'Le nom et le service sont modifiables, la clé A2F reste intacte.',
                       width=560, height=500, icon='edit', tone='gold')
        name = dialog.field('Nom du compte', account.get('name', ''), icon='user',
                            label='NOM DU COMPTE')
        issuer = dialog.field('Service / description', account.get('issuer', ''), icon='grid',
                              label='SERVICE / DESCRIPTION')

        def save():
            value = name.get().strip()
            if not value:
                self.alert('Nom requis', 'Le nom du compte ne peut pas être vide.')
                name.focus_set()
                return
            old = (account.get('name', ''), account.get('issuer', ''))
            account['name'] = value
            account['issuer'] = issuer.get().strip() or old[1] or 'Autre'
            try:
                self.persist()
            except Exception as exc:
                account['name'], account['issuer'] = old
                self.alert('Enregistrement impossible', f'Le coffre n’a pas pu être écrit.\n{exc}')
                return
            dialog._close()
            self.render_accounts()
            self._set_status('●  Compte modifié', GOLD)

        dialog.action('Enregistrer', save, style='gold', icon='check', width=168)
        dialog.action('Annuler', dialog._close, style='glass', width=118)

    def delete_account(self, index):
        if index >= len(self.accounts):
            return
        name = self.accounts[index].get('name', 'ce compte')
        if not self.confirm('Supprimer le compte',
                            f'Supprimer définitivement « {name} » ?\nCette action ne peut pas être annulée.',
                            'Supprimer'):
            return
        removed = self.accounts.pop(index)
        try:
            self.persist()
        except Exception as exc:
            self.accounts.insert(index, removed)
            self.alert('Suppression impossible', f'Le coffre n’a pas pu être écrit.\n{exc}')
            return
        self.render_accounts()
        self._set_status(f'●  {name} supprimé', MUTED)

    def persist(self):
        self.salt = save_vault(self.password, self.accounts, self.salt)

    # ------------------------------------------------------------------ security
    def _password_dialog(self, title, subtitle):
        dialog = Modal(self, title, subtitle, width=540, height=390, icon='lock', tone='gold')
        entry = dialog.field('Mot de passe principal', masked=True, reveal=True, icon='lock')
        result = {'value': None}

        def confirm():
            result['value'] = entry.get()
            dialog._close()

        dialog.action('Continuer', confirm, style='gold', icon='arrow-right', width=176)
        entry.bind('<Return>', lambda _e: confirm())
        self.wait_window(dialog)
        return result['value']

    def unlock(self):
        if VAULT.exists():
            password = self._password_dialog('Déverrouiller le coffre',
                                             'Entre ton mot de passe principal pour accéder à tes codes.')
            if password is None:
                self.destroy()
                return
            try:
                self.accounts, self.salt = load_vault(password)
                self.password = password
            except Exception:
                self.alert('Accès refusé', 'Mot de passe incorrect ou coffre illisible. Réessaie.')
                self.after(120, self.unlock)
                return
        else:
            password = self._password_dialog('Créer ton coffre',
                                             'Choisis un mot de passe principal solide. Il ne peut pas être récupéré.')
            if not password:
                self.destroy()
                return
            confirm = self._password_dialog('Confirmer le mot de passe',
                                            'Saisis-le une seconde fois pour sécuriser le coffre.')
            if password != confirm:
                self.alert('Mots de passe différents', 'Les deux saisies ne correspondent pas. Recommence.')
                self.after(120, self.unlock)
                return
            self.password = password
            self.accounts = []
            try:
                self.salt = save_vault(password, self.accounts)
            except Exception as exc:
                self.alert('Création impossible', f'Le coffre n’a pas pu être créé.\n{exc}')
                self.destroy()
                return
        self._switch_page('accounts')
        self._set_status('●  Coffre déverrouillé  ·  chiffrement AES-256-GCM actif', GREEN)
        self.render_accounts()

    def alert(self, title, message, kind='error'):
        tone = 'danger' if kind == 'error' else 'gold'
        icon = 'alert' if kind == 'error' else 'info'
        dialog = Modal(self, title, '', width=500, height=330, icon=icon, tone=tone)
        dialog.label(message, color='#F3C6C6' if kind == 'error' else MUTED, size=13,
                     pady=(4, 10), wrap=420)
        dialog.action('Compris', dialog._close, style='gold', icon='check', width=140)
        self.wait_window(dialog)

    def confirm(self, title, message, confirm_text='Confirmer'):
        dialog = Modal(self, title, '', width=520, height=350, icon='trash', tone='danger')
        dialog.label(message, color='#F3C6C6', size=13, pady=(4, 10), wrap=430)
        result = {'ok': False}

        def accept():
            result['ok'] = True
            dialog._close()

        dialog.action(confirm_text, accept, style='danger', icon='trash', width=150)
        dialog.action('Annuler', dialog._close, style='glass', width=116)
        self.wait_window(dialog)
        return result['ok']

    # ------------------------------------------------------------------ updates
    def _toggle_update_checks(self):
        self.preferences['check_updates_on_start'] = bool(self.update_switch.get())
        save_preferences(self.preferences)
        state = 'activée' if self.preferences['check_updates_on_start'] else 'désactivée'
        self._set_status(f'●  Recherche de mises à jour {state}', MUTED)

    def _open_available_update(self):
        if self._available_release is not None:
            self._show_update_dialog(self._available_release)

    def check_updates(self, manual=False):
        """Vérifie GitHub Releases sans jamais transmettre de donnée du coffre."""
        if not github_configured():
            if manual:
                self.alert(
                    'Mises à jour',
                    'Le dépôt GitHub de Noctis Auth n’est pas encore configuré.\n'
                    'L’application reste entièrement fonctionnelle hors ligne.',
                    kind='info')
            return
        if self._update_busy:
            if manual:
                self._set_status('●  Vérification des mises à jour déjà en cours…', GOLD_DIM)
            return
        self._update_busy = True
        if manual:
            self._set_status('●  Recherche de mises à jour…', GOLD_DIM)

        def worker():
            try:
                release = noctis_update.fetch_latest_release()
                result = ('ok', release)
            except Exception as exc:
                result = ('error', str(exc))
            try:
                self.after(0, lambda: self._on_update_result(result, manual))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True, name='noctis-update-check').start()

    def _on_update_result(self, result, manual):
        self._update_busy = False
        kind, payload = result
        if kind == 'error':
            self._set_status('●  Vérification des mises à jour impossible', MUTED)
            if manual:
                self.alert('Mises à jour', payload, kind='error')
            return
        release = payload
        if release is None:
            self._set_status('●  Dépôt de mises à jour non configuré', MUTED)
            return
        if noctis_update.is_newer(release.version):
            self._available_release = release
            self._show_update_badge(release.version)
            self._set_status(f'●  Mise à jour {release.version} disponible', GOLD)
            if manual:
                self._show_update_dialog(release)
        else:
            self._set_status(f'●  Noctis Auth {APP_VERSION} est à jour', GREEN)
            if manual:
                self.alert('Mises à jour',
                           f'Noctis Auth {APP_VERSION} est la dernière version disponible.',
                           kind='info')

    def _show_update_badge(self, version):
        try:
            self.update_btn.set_text(f'Mise à jour {version}')
            if not self._update_badge_visible:
                self.update_btn.pack(fill='x', padx=20, pady=(0, 8),
                                     before=self.version_label)
                self._update_badge_visible = True
        except Exception:
            pass

    def _show_update_dialog(self, release):
        notes = (release.notes or '').strip()
        if len(notes) > 2400:
            notes = notes[:2400] + '…'
        if not notes:
            notes = 'Aucune note de version fournie.'
        dialog = Modal(self, 'Mise à jour disponible',
                       f'Noctis Auth {release.version} est prête à être installée.',
                       width=620, height=600, icon='download', tone='gold')
        info = ctk.CTkFrame(dialog.body, fg_color=SURFACE, corner_radius=14,
                            border_width=1, border_color=LINE)
        info.pack(fill='x', pady=(0, 12))
        box = ctk.CTkFrame(info, fg_color='transparent')
        box.pack(fill='x', padx=16, pady=12)
        ctk.CTkLabel(box, text=f'Version installée : {APP_VERSION}',
                     text_color=MUTED, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=11)).pack(anchor='w')
        ctk.CTkLabel(box, text=f'Nouvelle version : {release.version}',
                     text_color=GOLD, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=12, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(dialog.body, text='NOUVEAUTÉS', text_color=GOLD_DIM, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).pack(
                         anchor='w', pady=(0, 6))
        notes_box = ctk.CTkTextbox(dialog.body, fg_color=INPUT_BG, border_width=1,
                                   border_color=LINE, corner_radius=12, text_color=MUTED,
                                   font=ctk.CTkFont(family=FONT_UI, size=11),
                                   wrap='word', height=220)
        notes_box.pack(fill='both', expand=True)
        notes_box.insert('1.0', notes)
        notes_box.configure(state='disabled')
        ctk.CTkLabel(dialog.body,
                     text='L’installateur sera vérifié par empreinte SHA-256 avant exécution. '
                          'Ton coffre et tes comptes ne sont jamais modifiés.',
                     text_color=SUBTLE, anchor='w', justify='left', wraplength=540,
                     font=ctk.CTkFont(family=FONT_UI, size=10)).pack(anchor='w', pady=(10, 0))
        dialog.action('Plus tard', dialog._close, style='glass', width=104)
        dialog.action('Voir sur GitHub',
                      lambda: webbrowser.open(release.page_url),
                      style='glass', icon='arrow-right', width=168)
        dialog.action('Télécharger et installer',
                      lambda: self._download_update(release, dialog),
                      style='gold', icon='download', width=246)

    def _download_update(self, release, parent_dialog=None):
        if parent_dialog is not None:
            parent_dialog._close()
        dialog = Modal(self, 'Mise à jour',
                       f'Téléchargement de Noctis Auth {release.version}…',
                       width=580, height=440, icon='download', tone='gold')
        status = dialog.label(
            'L’installateur est téléchargé puis vérifié par empreinte SHA-256 '
            'avant toute exécution.', color=MUTED, size=11, pady=(0, 14), wrap=490)
        bar = ctk.CTkProgressBar(dialog.body, height=12, corner_radius=8,
                                 progress_color=GOLD, fg_color='#2A2B31')
        bar.pack(fill='x', pady=(0, 8))
        bar.set(0)
        pct = ctk.CTkLabel(dialog.body, text='0 %', text_color=GOLD,
                           font=ctk.CTkFont(family=FONT_UI, size=13, weight='bold'))
        pct.pack(anchor='e')
        state = {'last': -1}

        def on_progress(done, total):
            if total <= 0:
                return
            value = int(done * 100 / total)
            if value == state['last']:
                return
            state['last'] = value
            ratio = min(1.0, done / total)

            def apply():
                try:
                    if dialog.winfo_exists():
                        bar.set(ratio)
                        pct.configure(text=f'{value} %')
                except Exception:
                    pass

            try:
                self.after(0, apply)
            except Exception:
                pass

        def finish(result):
            try:
                if not dialog.winfo_exists():
                    return
            except Exception:
                return
            kind, payload = result
            if kind == 'error':
                status.configure(text=payload, text_color=RED)
                dialog.action('Réessayer', lambda: (dialog._close(),
                                                    self._download_update(release)),
                              style='gold', icon='refresh', width=150)
                dialog.action('Fermer', dialog._close, style='glass', width=110)
                return
            path = payload
            bar.set(1)
            pct.configure(text='100 %')
            status.configure(text='Installateur vérifié · empreinte SHA-256 valide.',
                             text_color=GREEN)

            def install():
                try:
                    install_dir = (Path(sys.executable).resolve().parent
                                   if getattr(sys, 'frozen', False) else None)
                    noctis_update.cleanup_download_cache(keep=path)
                    noctis_update.launch_installer(path, silent=True,
                                                   install_dir=install_dir)
                except Exception as exc:
                    self.alert('Mise à jour',
                               f'Impossible de lancer l’installateur.\n{exc}')
                    return
                dialog._close()
                self._set_status('●  Installation de la mise à jour…', GOLD)
                self.after(600, self._quit_for_update)

            dialog.action('Plus tard', dialog._close, style='glass', width=110)
            dialog.action('Installer maintenant', install, style='gold',
                          icon='download', width=210)

        def worker():
            try:
                path = noctis_update.download_and_verify(release, progress=on_progress)
                result = ('ok', path)
            except Exception as exc:
                result = ('error', str(exc))
            try:
                self.after(0, lambda: finish(result))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True, name='noctis-update-download').start()

    def _quit_for_update(self):
        try:
            self.quit()
        finally:
            try:
                self.destroy()
            except Exception:
                pass

    def show_settings(self):
        dialog = Modal(self, 'Paramètres', 'Sécurité et confidentialité de Noctis Auth.',
                       width=600, height=600, icon='sliders', tone='gold')
        dialog.label('Ton coffre est chiffré localement avec AES-256-GCM. Les clés A2F ne sont '
                     'envoyées à aucun serveur et restent dans %APPDATA%\\NoctisAuth.',
                     color=MUTED, size=12, pady=(2, 16), wrap=510)
        rows = [
            ('shield', 'Chiffrement local', 'AES-256-GCM · PBKDF2-SHA256 · 600 000 itérations'),
            ('key', 'Ton mot de passe', 'Il n’est jamais stocké : sans lui, le coffre reste fermé.'),
            ('dot', 'Coffre hors ligne', 'Les codes restent locaux ; seule la mise à jour contacte GitHub.'),
        ]
        for icon, title, text in rows:
            row = ctk.CTkFrame(dialog.body, fg_color='transparent')
            row.pack(fill='x', pady=5)
            ctk.CTkLabel(row, text='', image=icon_tile_ctk(icon, 34, 'gold'),
                         fg_color='transparent').pack(side='left', padx=(0, 12))
            box = ctk.CTkFrame(row, fg_color='transparent')
            box.pack(side='left', fill='x', expand=True)
            ctk.CTkLabel(box, text=title, text_color=WHITE, anchor='w',
                         font=ctk.CTkFont(family=FONT_UI, size=12, weight='bold')).pack(anchor='w')
            ctk.CTkLabel(box, text=text, text_color=SUBTLE, anchor='w',
                         font=ctk.CTkFont(family=FONT_UI, size=10)).pack(anchor='w')

        update_card = ctk.CTkFrame(dialog.body, fg_color=SURFACE, corner_radius=14,
                                   border_width=1, border_color=LINE)
        update_card.pack(fill='x', pady=(14, 0))
        ctk.CTkLabel(update_card, text='', image=icon_tile_ctk('download', 34, 'gold'),
                     fg_color='transparent').pack(side='left', padx=(12, 10), pady=12)
        update_text = ctk.CTkFrame(update_card, fg_color='transparent')
        update_text.pack(side='left', fill='x', expand=True, pady=10)
        ctk.CTkLabel(update_text, text='Mises à jour GitHub', text_color=WHITE, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=12, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(update_text,
                     text=f'Version {APP_VERSION} · vérification SHA-256 de l’installateur',
                     text_color=SUBTLE, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=10)).pack(anchor='w')
        self.update_switch = ctk.CTkSwitch(
            update_card, text='', width=46, height=24, switch_width=46, switch_height=24,
            fg_color='#2A2B31', progress_color=GOLD, button_color='#EDEDF0',
            button_hover_color=WHITE, command=self._toggle_update_checks)
        if self.preferences.get('check_updates_on_start', True):
            self.update_switch.select()
        self.update_switch.pack(side='right', padx=(8, 14))

        dialog.action('Verrouiller le coffre', lambda: (dialog._close(), self.lock()),
                      style='gold', icon='lock', width=190)
        dialog.action('Vérifier les mises à jour',
                      lambda: (dialog._close(), self.check_updates(manual=True)),
                      style='glass', icon='refresh', width=210)
        dialog.action('Fermer', dialog._close, style='glass', width=100)

    def show_about(self):
        dialog = Modal(self, 'À propos', '', width=580, height=600, icon='sparkle', tone='gold')
        ctk.CTkLabel(dialog.body, text='', image=self.logo_big_image,
                     fg_color='transparent').pack(pady=(0, 2))
        ctk.CTkLabel(dialog.body, text='NOCTIS AUTH', text_color=WHITE,
                     font=ctk.CTkFont(family=FONT_UI, size=22, weight='bold')).pack()
        ctk.CTkLabel(dialog.body, text=f'version {APP_VERSION}  ·  authentificateur local',
                     text_color=GOLD, font=ctk.CTkFont(family=FONT_UI, size=10,
                                                       weight='bold')).pack(pady=(2, 16))
        for line in ('Plus de 110 services disponibles avec recherche instantanée.',
                     'Codes TOTP calculés hors ligne, copie en un clic.',
                     'Coffre AES-256-GCM chiffré sur cet appareil uniquement.',
                     'Mises à jour GitHub vérifiées par empreinte SHA-256.'):
            row = ctk.CTkFrame(dialog.body, fg_color='transparent')
            row.pack(fill='x', pady=3)
            ctk.CTkLabel(row, text='', image=ctk_icon('check-circle', 18, GREEN),
                         fg_color='transparent', width=18, height=18).pack(side='left', padx=(4, 10))
            ctk.CTkLabel(row, text=line, text_color=MUTED, anchor='w',
                         font=ctk.CTkFont(family=FONT_UI, size=11)).pack(side='left')
        dialog.action('Fermer', dialog._close, style='gold', icon='check', width=120)
        dialog.action('Vérifier les mises à jour',
                      lambda: (dialog._close(), self.check_updates(manual=True)),
                      style='glass', icon='refresh', width=210)

    def lock(self):
        self.password = None
        self.accounts = []
        self.cards = []
        self.card_by_index = {}
        self.selected_service = None
        self._switch_page('accounts')
        self.search_box.set('')
        self.render_accounts()
        self._set_status('●  Coffre verrouillé', MUTED)
        self.after(160, self.unlock)

    def _set_status(self, text, color=SUBTLE):
        try:
            self.status.configure(text=text, text_color=color)
        except Exception:
            pass

    # ------------------------------------------------------------------ refresh
    def refresh(self):
        if self.password is not None:
            now = time.time()
            remaining = PERIOD - int(now) % PERIOD
            counter = int(now // PERIOD)
            for record in list(self.cards):
                try:
                    if record['remaining'] != remaining:
                        record['remaining'] = remaining
                        record['timer'].configure(
                            text=str(remaining), image=ring_ctk(remaining, 66),
                            text_color=RED if remaining <= 5 else WHITE)
                    if record['counter'] != counter:
                        record['counter'] = counter
                        value = totp(record['secret'])
                        record['code'].configure(text=format_code(value))
                except Exception:
                    try:
                        record['code'].configure(text='--- ---')
                    except Exception:
                        pass
        try:
            if self.winfo_exists():
                self.after(400, self.refresh)
        except Exception:
            pass

    # ------------------------------------------------------------------ pages
    def show_accounts(self):
        if self.password is None:
            return
        if self.search_box.get():
            self.search_box.set('')
        self._switch_page('accounts')
        self.render_accounts()


if __name__ == '__main__':
    AuthApp().mainloop()


