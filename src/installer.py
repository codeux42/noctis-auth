"""Noctis Auth — installateur Windows autonome.

Caractéristiques :
  * installation par utilisateur (aucun droit administrateur, aucun Python requis) ;
  * copie réelle avec pourcentage calculé sur les octets écrits ;
  * interface liquid glass assortie à l'application et logo officiel ;
  * raccourcis Bureau / menu Démarrer et entrée « Applications et fonctionnalités » ;
  * désinstallation propre, qui conserve le coffre sauf demande explicite ;
  * modes silencieux (/S) et mise à jour (/DIR=...) pour le système de mises à jour.

Le coffre utilisateur (%APPDATA%\\NoctisAuth) n'est jamais lu ni modifié par
l'installateur, sauf lors d'une désinstallation avec /PURGE explicite.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import threading
import time
import winreg
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app_config import (APP_EXE, APP_NAME, APP_VERSION, SETUP_EXE, SETUP_ID,
                        github_configured, releases_page_url)

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
LOCAL = Path(os.getenv('LOCALAPPDATA', str(Path.home())))
ROAMING = Path(os.getenv('APPDATA', str(Path.home())))
DEFAULT_DIR = LOCAL / 'Programs' / 'Noctis Auth'
DATA_DIR = ROAMING / 'NoctisAuth'
UPDATE_DIR = LOCAL / 'NoctisAuth' / 'Updates'
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\NoctisAuth'
APP_PATHS_KEY = r'Software\Microsoft\Windows\CurrentVersion\App Paths\NoctisAuth.exe'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
DETACHED = (getattr(subprocess, 'DETACHED_PROCESS', 0)
            | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))


def resource_path(name: str) -> str:
    relative = Path(name)
    candidates = []
    if getattr(sys, '_MEIPASS', None):
        candidates.append(Path(sys._MEIPASS) / relative)
    here = Path(__file__).resolve().parent
    candidates.extend((here / relative, here.parent / relative,
                       here.parent / 'assets' / relative.name,
                       here / 'assets' / relative.name))
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0]) if candidates else str(relative)


# ---------------------------------------------------------------------------
# Palette (identique à l'application)
# ---------------------------------------------------------------------------
BG = '#07080B'
SHELL = '#0C0E13'
CARD = '#101218'
CARD_2 = '#161920'
LINE = '#252A35'
LINE_BRIGHT = '#39404E'
GOLD = '#F4C542'
GOLD_LIGHT = '#FFE08A'
GOLD_DIM = '#B9922F'
WHITE = '#F6F7F9'
MUTED = '#9CA1AD'
SUBTLE = '#626775'
GREEN = '#4AD295'
RED = '#F07878'
FONT_UI = 'Segoe UI'
FONT_REG = 'C:/Windows/Fonts/segoeui.ttf'
FONT_BOLD = 'C:/Windows/Fonts/segoeuib.ttf'


def hex_rgb(color):
    color = str(color).lstrip('#')
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def vertical_gradient(size, top, bottom):
    width, height = size
    top_rgb, bottom_rgb = hex_rgb(top), hex_rgb(bottom)
    image = Image.new('RGB', (1, height))
    pixels = image.load()
    for y in range(height):
        t = y / max(1, height - 1)
        pixels[0, y] = tuple(int(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * t)
                             for i in range(3))
    return image.resize((width, height), Image.Resampling.BILINEAR).convert('RGBA')


def rounded_mask(size, radius):
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1),
                                           radius=radius, fill=255)
    return mask


def pil_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def radial_glow(size, color, alpha):
    mask = Image.new('L', (72, 72), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 71, 71), fill=alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(18))
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    layer = Image.new('RGBA', (size, size), (*hex_rgb(color), 255))
    layer.putalpha(mask)
    return layer


_BACKGROUND_CACHE = {}


def build_background(width, height):
    key = (width, height)
    if key in _BACKGROUND_CACHE:
        return _BACKGROUND_CACHE[key]
    image = vertical_gradient((width, height), '#0B0D12', '#050609')
    image.alpha_composite(radial_glow(620, GOLD, 52), (width - 420, -260))
    image.alpha_composite(radial_glow(520, GOLD, 30), (-280, height - 340))
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((width - 340, -270, width + 250, 320), outline=(244, 197, 66, 26),
                 width=2)
    draw.ellipse((width - 310, -240, width + 220, 290), outline=(244, 197, 66, 14),
                 width=1)
    draw.ellipse((-260, height - 380, 230, height + 160), outline=(244, 197, 66, 18),
                 width=2)
    image = Image.alpha_composite(image, overlay)
    result = image.convert('RGB')
    _BACKGROUND_CACHE[key] = result
    return result


# ---------------------------------------------------------------------------
# Icônes vectorielles
# ---------------------------------------------------------------------------
_ICON_CACHE = {}
_CTK_ICONS = {}


def icon_pil(name, px, color=WHITE, stroke=1.9, ss=3):
    key = (name, px, color, stroke)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    px = max(6, int(px))
    canvas = px * ss
    unit = canvas / 24.0
    width = max(1, int(round(stroke * ss)))
    image = Image.new('RGBA', (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def p(x, y):
        return (x * unit, y * unit)

    def line(points, fill=color, w=width):
        pts = [p(x, y) for x, y in points]
        draw.line(pts, fill=fill, width=w, joint='curve')
        for point in (pts[0], pts[-1]):
            r = w / 2.0
            draw.ellipse((point[0] - r, point[1] - r, point[0] + r, point[1] + r),
                         fill=fill)

    def poly(points, fill=color, w=width):
        line(points + [points[0]], fill=fill, w=w)

    def circle(cx, cy, r, fill=None, w=width):
        draw.ellipse((p(cx - r, cy - r), p(cx + r, cy + r)), outline=fill, width=w)

    def disc(cx, cy, r, fill=color):
        draw.ellipse((p(cx - r, cy - r), p(cx + r, cy + r)), fill=fill)

    def rrect(x0, y0, x1, y1, radius, fill=color, w=width):
        draw.rounded_rectangle((p(x0, y0), p(x1, y1)), radius=radius * unit,
                               outline=fill, width=w)

    if name == 'download':
        line([(12, 3.6), (12, 15.4)])
        line([(7.1, 10.6), (12, 15.6), (16.9, 10.6)])
        line([(4.2, 16.6), (4.2, 20.2), (19.8, 20.2), (19.8, 16.6)])
    elif name == 'folder':
        poly([(3.6, 8.0), (9.1, 8.0), (11.2, 10.6), (20.4, 10.6),
              (20.4, 19.2), (3.6, 19.2)])
        line([(3.6, 8.0), (3.6, 19.2)])
    elif name == 'check':
        line([(4.6, 12.6), (9.6, 17.6), (19.5, 7.1)])
    elif name == 'check-circle':
        circle(12, 12, 8.6)
        line([(7.8, 12.2), (10.8, 15.2), (16.4, 8.7)])
    elif name == 'arrow-right':
        line([(4.5, 12), (19.2, 12)])
        line([(13.4, 5.9), (19.4, 12), (13.4, 18.1)])
    elif name == 'arrow-left':
        line([(19.5, 12), (4.8, 12)])
        line([(10.6, 5.9), (4.6, 12), (10.6, 18.1)])
    elif name == 'chevron-right':
        line([(9, 6), (15, 12), (9, 18)])
    elif name == 'trash':
        line([(4, 7), (20, 7)])
        draw.arc((p(9, 3.5), p(15, 10.5)), 180, 360, fill=color, width=width)
        line([(6.5, 7), (7.6, 20), (16.4, 20), (17.5, 7)])
        line([(10.4, 11), (10.4, 16.5)])
        line([(13.6, 11), (13.6, 16.5)])
    elif name == 'alert':
        poly([(12, 3.5), (21, 20), (3, 20)])
        line([(12, 9.2), (12, 14.2)])
        disc(12, 17, 1.15)
    elif name == 'info':
        circle(12, 12, 8.6)
        disc(12, 7.6, 1.15)
        line([(12, 11), (12, 17)])
    elif name == 'shield':
        poly([(12, 3), (20, 6.4), (20, 12), (12, 21), (4, 12), (4, 6.4)])
        line([(8.5, 12), (11, 14.5), (15.5, 9.5)])
    elif name == 'key':
        circle(8.5, 8.5, 4.8)
        line([(11.8, 11.8), (20, 20)])
        line([(16.6, 16.6), (13.9, 19.3)])
        line([(18.4, 18.4), (15.7, 21.1)])
    elif name == 'refresh':
        draw.arc((p(4.2, 4.2), p(19.8, 19.8)), 35, 320, fill=color, width=width)
        import math
        end = math.radians(35)
        ex, ey = 12 + 7.8 * math.cos(end), 12 + 7.8 * math.sin(end)
        line([(ex - 3.3, ey - 1.0), (ex, ey), (ex + 0.4, ey - 3.6)])
    elif name == 'x':
        line([(6, 6), (18, 18)])
        line([(18, 6), (6, 18)])
    elif name == 'sparkle':
        draw.polygon([p(12, 2.8), p(14, 10), p(21.2, 12), p(14, 14), p(12, 21.2),
                      p(10, 14), p(2.8, 12), p(10, 10)], fill=color)
    elif name == 'lock':
        rrect(5, 10.4, 19, 21, 3)
        draw.arc((p(8, 3), p(16, 11)), 180, 360, fill=color, width=width)
        line([(8, 7), (8, 10.4)])
        line([(16, 7), (16, 10.4)])
    elif name == 'sliders':
        for y in (7, 12, 17):
            line([(4, y), (20, y)])
        disc(9, 7, 2.4)
        disc(15, 12, 2.4)
        disc(8, 17, 2.4)
    elif name == 'grid':
        rrect(4, 4, 10.6, 10.6, 1.6)
        rrect(13.4, 4, 20, 10.6, 1.6)
        rrect(4, 13.4, 10.6, 20, 1.6)
        rrect(13.4, 13.4, 20, 20, 1.6)
    elif name == 'user':
        circle(12, 8.3, 4.0)
        draw.arc((p(4.2, 14), p(19.8, 26.5)), 180, 360, fill=color, width=width)
    elif name == 'clock':
        circle(12, 12, 8.5)
        line([(12, 7.4), (12, 12), (16, 13.7)])
    elif name == 'dot':
        disc(12, 12, 4.2)
    else:
        disc(12, 12, 6)

    if ss > 1:
        image = image.resize((px, px), Image.Resampling.LANCZOS)
    _ICON_CACHE[key] = image
    return image


def icon_ctk(name, size, color=WHITE):
    key = (name, size, color)
    cached = _CTK_ICONS.get(key)
    if cached is None:
        source = icon_pil(name, size, color)
        cached = ctk.CTkImage(light_image=source, dark_image=source, size=(size, size))
        _CTK_ICONS[key] = cached
    return cached


# ---------------------------------------------------------------------------
# Boutons liquid glass
# ---------------------------------------------------------------------------
_BUTTON_CACHE = {}


def render_glass(width, height, radius, text, icon, style, state, base,
                 align='center', font_size=13, padx=18, gap=9, icon_size=16):
    key = (width, height, radius, text, icon, style, state, base, align,
           font_size, padx, gap, icon_size)
    if key in _BUTTON_CACHE:
        return _BUTTON_CACHE[key]
    ss = 3
    W, H, R = width * ss, height * ss, radius * ss
    transparent = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    mask = rounded_mask((W, H), R)

    if style == 'gold':
        palette = {'normal': ('#FFE49B', '#D6A42A'),
                   'hover': ('#FFF0C6', '#E8BB44'),
                   'pressed': ('#F4D079', '#C2901C')}[state]
        fill = vertical_gradient((W, H), *palette)
        surface = Image.composite(fill, transparent, mask)
        effects = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(effects)
        draw.rounded_rectangle((1, 1, W - 2, H - 2), radius=R,
                               outline=(255, 255, 255, 155), width=ss)
        draw.line([(R * .8, 2.6 * ss), (W - R * .8, 2.6 * ss)],
                  fill=(255, 255, 255, 210), width=ss + 1)
        draw.rounded_rectangle((5 * ss, 5 * ss, W - 5 * ss, H - 5 * ss),
                               radius=max(2, R - 4 * ss),
                               outline=(255, 255, 255, 60), width=ss)
        draw.rounded_rectangle((3 * ss, H - 7 * ss, W - 3 * ss, H - 3 * ss),
                               radius=R, fill=(0, 0, 0, 45))
        effects = Image.composite(effects, transparent, mask)
        image = Image.alpha_composite(surface, effects)
        text_color = icon_color = '#191204' if state != 'pressed' else '#2A1F08'
    elif style == 'danger':
        palette = {'normal': ('#F59494', '#C64C4C'),
                   'hover': ('#FFAAAA', '#DA5E5E'),
                   'pressed': ('#E27D7D', '#AE3D3D')}[state]
        fill = vertical_gradient((W, H), *palette)
        surface = Image.composite(fill, transparent, mask)
        effects = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(effects)
        draw.rounded_rectangle((1, 1, W - 2, H - 2), radius=R,
                               outline=(255, 255, 255, 150), width=ss)
        draw.line([(R * .8, 2.6 * ss), (W - R * .8, 2.6 * ss)],
                  fill=(255, 255, 255, 195), width=ss + 1)
        effects = Image.composite(effects, transparent, mask)
        image = Image.alpha_composite(surface, effects)
        text_color = icon_color = '#FFF6F6'
    else:
        tone = (244, 197, 66)
        base_color = Image.new('RGBA', (W, H), (*hex_rgb(base), 255))
        surface = Image.composite(base_color, transparent, mask)
        effects = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(effects)
        alpha_top = {'normal': 24, 'hover': 40, 'pressed': 16}[state]
        alpha_bottom = {'normal': 4, 'hover': 10, 'pressed': 10}[state]
        rim = {'normal': 46, 'hover': 86, 'pressed': 105}[state]
        for y in range(H):
            t = y / max(1, H - 1)
            alpha = int(alpha_top * (1 - t) ** 1.4 + alpha_bottom)
            if alpha > 0:
                draw.line([(0, y), (W, y)], fill=(*tone, alpha))
        draw.rounded_rectangle((4 * ss, H - 8 * ss, W - 4 * ss, H - 3 * ss),
                               radius=R, fill=(0, 0, 0, 66))
        draw.rounded_rectangle((1, 1, W - 2, H - 2), radius=R,
                               outline=(255, 255, 255, rim), width=max(2, ss - 1))
        draw.line([(R, H - 3.2 * ss), (W - R, H - 3.2 * ss)],
                  fill=(*tone, {'normal': 52, 'hover': 96, 'pressed': 118}[state]),
                  width=max(2, ss - 1))
        draw.line([(R * .9, 2.4 * ss), (W - R * .9, 2.4 * ss)],
                  fill=(255, 255, 255, 74 if state == 'normal' else 130),
                  width=max(2, ss - 1))
        effects = Image.composite(effects, transparent, mask)
        image = Image.alpha_composite(surface, effects)
        text_color = WHITE
        icon_color = GOLD_LIGHT

    size_px = max(8, int(round(font_size * ss)))
    font = pil_font(FONT_BOLD, size_px)
    text_len = font.getlength(text) if text else 0
    icon_px = int(round(icon_size * ss)) if icon else 0
    gap_px = int(round(gap * ss)) if (icon and text) else 0
    max_width = W - int(padx * ss) * 2
    while text and (text_len + icon_px + gap_px) > max_width and size_px > 8 * ss:
        size_px -= 1
        font = pil_font(FONT_BOLD, size_px)
        text_len = font.getlength(text)

    group = icon_px + gap_px + text_len
    if align == 'w':
        start = padx * ss
    elif align == 'e':
        start = W - padx * ss - group
    else:
        start = (W - group) / 2
    if icon:
        glyph = icon_pil(icon, icon_px, icon_color, stroke=1.8 * ss)
        image.alpha_composite(glyph, (int(start), int((H - icon_px) / 2)))
    if text:
        draw = ImageDraw.Draw(image)
        draw.text((start + icon_px + gap_px, H / 2 + ss * .4), text,
                  font=font, fill=text_color, anchor='lm')

    result = image.resize((width, height), Image.Resampling.LANCZOS)
    _BUTTON_CACHE[key] = result
    return result


class GlassButton(ctk.CTkLabel):
    def __init__(self, master, text='', icon=None, command=None, width=180,
                 height=46, radius=15, style='glass', base=SHELL, align='center',
                 font_size=13, padx=18, gap=9, icon_size=16):
        self._command = command
        self._params = dict(width=width, height=height, radius=radius, text=text,
                            icon=icon, style=style, base=base, align=align,
                            font_size=font_size, padx=padx, gap=gap,
                            icon_size=icon_size)
        self._images = self._render()
        super().__init__(master, text='', image=self._images['normal'],
                         width=width, height=height, fg_color=base, bg_color=base,
                         corner_radius=0)
        for widget in (self, getattr(self, '_label', None)):
            if widget is None:
                continue
            widget.bind('<Enter>', self._enter)
            widget.bind('<Leave>', self._leave)
            widget.bind('<ButtonPress-1>', self._press)
            widget.bind('<ButtonRelease-1>', self._release)
            if command is not None:
                try:
                    widget.configure(cursor='hand2')
                except Exception:
                    pass

    def _render(self):
        p = self._params
        return {state: ctk.CTkImage(
            light_image=render_glass(p['width'], p['height'], p['radius'],
                                     p['text'], p['icon'], p['style'], state,
                                     p['base'], p['align'], p['font_size'],
                                     p['padx'], p['gap'], p['icon_size']),
            dark_image=render_glass(p['width'], p['height'], p['radius'],
                                    p['text'], p['icon'], p['style'], state,
                                    p['base'], p['align'], p['font_size'],
                                    p['padx'], p['gap'], p['icon_size']),
            size=(p['width'], p['height']))
            for state in ('normal', 'hover', 'pressed')}

    def _enter(self, _event=None):
        if self._command is not None:
            try:
                self.configure(image=self._images['hover'])
            except Exception:
                pass

    def _leave(self, _event=None):
        try:
            self.configure(image=self._images['normal'])
        except Exception:
            pass

    def _press(self, _event=None):
        if self._command is not None:
            try:
                self.configure(image=self._images['pressed'])
            except Exception:
                pass

    def _release(self, _event=None):
        if self._command is None:
            return
        try:
            self.configure(image=self._images['hover'])
        except Exception:
            return
        self._command()

    def set_text(self, text):
        if self._params['text'] == text:
            return
        self._params['text'] = text
        self._images = self._render()
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

    def set_style(self, style):
        if self._params['style'] == style:
            return
        self._params['style'] = style
        self._images = self._render()
        try:
            self.configure(image=self._images['normal'])
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Utilitaires Windows
# ---------------------------------------------------------------------------
def set_dpi_and_appid():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(SETUP_ID)
    except Exception:
        pass


def set_dark_titlebar(window):
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        for attribute, value in ((20, 1), (19, 1)):
            data = ctypes.c_int(value)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))
        color = ctypes.c_int(0x000C0908)  # COLORREF (BGR) de #08090C
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
    except Exception:
        pass


def known_folder(csidl):
    try:
        buffer = ctypes.create_unicode_buffer(260)
        result = ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
        if result == 0 and buffer.value:
            return Path(buffer.value)
    except Exception:
        pass
    return None


def desktop_folder():
    return known_folder(0x10) or (Path.home() / 'Desktop')


def programs_folder():
    return known_folder(0x02) or (ROAMING / 'Microsoft' / 'Windows' /
                                  'Start Menu' / 'Programs')


def _ps(value):
    return "'" + str(value).replace("'", "''") + "'"


def create_shortcuts(shortcuts):
    """shortcuts : liste de (lien, cible, arguments, dossier, icône)."""
    script = ['$ErrorActionPreference="Stop"',
              '$w=New-Object -ComObject WScript.Shell']
    for link, target, arguments, working, icon in shortcuts:
        Path(link).parent.mkdir(parents=True, exist_ok=True)
        script.extend([
            f'$s=$w.CreateShortcut({_ps(link)})',
            f'$s.TargetPath={_ps(target)}',
            f'$s.Arguments={_ps(arguments)}',
            f'$s.WorkingDirectory={_ps(working)}',
            f'$s.IconLocation={_ps(str(icon) + ",0")}',
            '$s.Description="Noctis Auth"',
            '$s.Save()',
        ])
    command = ';'.join(script)
    completed = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
         'Bypass', '-Command', command],
        creationflags=NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if completed.returncode != 0:
        raise RuntimeError('Création des raccourcis impossible.')


def remove_shortcuts():
    targets = [desktop_folder() / 'Noctis Auth.lnk',
               programs_folder() / 'Noctis Auth.lnk']
    for link in targets:
        try:
            link.unlink(missing_ok=True)
        except OSError:
            pass
    folder = programs_folder() / 'Noctis Auth'
    if folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)


def register_install(install_dir, setup_path):
    install_dir = Path(install_dir)
    total = 0
    for path in install_dir.rglob('*'):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            pass
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    try:
        values = [
            ('DisplayName', APP_NAME),
            ('DisplayVersion', APP_VERSION),
            ('Publisher', 'Noctis'),
            ('DisplayIcon', str(install_dir / APP_EXE)),
            ('InstallLocation', str(install_dir)),
            ('UninstallString', f'"{setup_path}" --uninstall'),
            ('QuietUninstallString', f'"{setup_path}" --uninstall /S'),
            ('InstallDate', time.strftime('%Y%m%d')),
        ]
        if github_configured():
            values.append(('URLInfoAbout', releases_page_url()))
        for name, value in values:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        for name, value in (('NoModify', 1), ('NoRepair', 1),
                            ('EstimatedSize', max(1, total // 1024))):
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
    finally:
        winreg.CloseKey(key)
    try:
        app_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, APP_PATHS_KEY)
        winreg.SetValueEx(app_key, '', 0, winreg.REG_SZ, str(install_dir / APP_EXE))
        winreg.SetValueEx(app_key, 'Path', 0, winreg.REG_SZ, str(install_dir))
        winreg.CloseKey(app_key)
    except OSError:
        pass


def remove_registry():
    for key_name in (UNINSTALL_KEY, APP_PATHS_KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_name)
        except OSError:
            pass


def read_install_dir():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        try:
            value = winreg.QueryValueEx(key, 'InstallLocation')[0]
        finally:
            winreg.CloseKey(key)
        path = Path(value)
        if path.is_dir():
            return path
    except OSError:
        pass
    candidate = Path(sys.executable).resolve().parent
    if (candidate / APP_EXE).is_file():
        return candidate
    return DEFAULT_DIR


def _copy_with_retry(source, destination, retry_seconds=45):
    """Copie atomique : le fichier final n'est remplacé qu'une fois complet."""
    destination = Path(destination)
    temporary = destination.with_name(destination.name + '.new')
    try:
        temporary.unlink(missing_ok=True)
    except OSError:
        pass
    shutil.copy2(source, temporary)
    deadline = time.monotonic() + retry_seconds
    while True:
        try:
            os.replace(temporary, destination)
            return
        except PermissionError:
            if time.monotonic() > deadline:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                raise RuntimeError(
                    'Noctis Auth est encore ouvert. Ferme l’application puis réessaie.')
            time.sleep(0.5)


def spawn_cleanup(install_dir, purge):
    args = [sys.executable, '--cleanup', f'/DIR={install_dir}']
    if purge:
        args.append('/PURGE')
    subprocess.Popen(args, close_fds=True, creationflags=DETACHED | NO_WINDOW)


def _schedule_self_delete(folder):
    exe = Path(sys.executable).resolve()
    folder = Path(folder).resolve()
    same_folder = exe.parent == folder
    parts = ['ping 127.0.0.1 -n 4 >nul']
    if same_folder:
        parts.append(f'del /f /q "{exe}"')
    parts.append(f'rmdir /s /q "{folder}"')
    command = ' & '.join(parts)
    try:
        subprocess.Popen(['cmd.exe', '/c', command], creationflags=NO_WINDOW,
                         close_fds=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception:
        pass


def cleanup_main(install_dir, purge):
    """Exécuté par le processus enfant : retire tout puis s'auto-supprime."""
    time.sleep(1.2)
    remove_shortcuts()
    remove_registry()
    if purge:
        shutil.rmtree(DATA_DIR, ignore_errors=True)
    shutil.rmtree(UPDATE_DIR, ignore_errors=True)
    folder = Path(install_dir) if install_dir else read_install_dir()
    if folder.is_dir():
        for _ in range(20):
            shutil.rmtree(folder, ignore_errors=True)
            if not folder.exists():
                break
            time.sleep(0.3)
        if folder.exists():
            _schedule_self_delete(folder)


def silent_install(target):
    target = Path(target).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    payload = Path(resource_path(APP_EXE))
    icon = Path(resource_path('noctis.ico'))
    if not payload.is_file():
        raise RuntimeError('NoctisAuth.exe est absent de l’installateur.')
    destination = target / APP_EXE
    setup_destination = target / SETUP_EXE
    _copy_with_retry(payload, destination)
    if icon.is_file():
        _copy_with_retry(icon, target / 'noctis.ico')
    if Path(sys.executable).resolve() != setup_destination.resolve():
        _copy_with_retry(sys.executable, setup_destination)
    shortcuts = [(desktop_folder() / 'Noctis Auth.lnk', destination, '',
                  target, destination)]
    programs = programs_folder() / 'Noctis Auth'
    shortcuts.append((programs / 'Noctis Auth.lnk', destination, '',
                      target, destination))
    shortcuts.append((programs / 'Désinstaller Noctis Auth.lnk',
                      setup_destination, '--uninstall', target, setup_destination))
    try:
        create_shortcuts(shortcuts)
    except Exception:
        pass
    register_install(target, setup_destination)


def parse_args(argv):
    options = {'silent': False, 'uninstall': False, 'cleanup': False,
               'purge': False, 'dir': None}
    index = 0
    while index < len(argv):
        arg = argv[index]
        lower = arg.lower()
        if lower in ('/s', '/silent', '--silent'):
            options['silent'] = True
        elif lower in ('/uninstall', '--uninstall'):
            options['uninstall'] = True
        elif lower == '--cleanup':
            options['cleanup'] = True
        elif lower in ('/purge', '--purge'):
            options['purge'] = True
        elif lower.startswith('/dir=') or lower.startswith('--dir='):
            value = arg.split('=', 1)[1].strip().strip('"')
            options['dir'] = Path(value)
        elif lower in ('/dir', '--dir') and index + 1 < len(argv):
            index += 1
            options['dir'] = Path(argv[index].strip('"'))
        index += 1
    return options


# ---------------------------------------------------------------------------
# Fenêtre d'installation
# ---------------------------------------------------------------------------
class SetupWindow:
    WIDTH, HEIGHT = 820, 650

    def __init__(self, root, initial_dir=None):
        self.root = root
        self._last_percent = -1
        self._installing = False
        root.title(f'{APP_NAME} — Installation')
        root.geometry(f'{self.WIDTH}x{self.HEIGHT}')
        root.resizable(False, False)
        root.configure(fg_color=BG)
        try:
            root.iconbitmap(resource_path('noctis.ico'))
        except Exception:
            pass
        set_dark_titlebar(root)
        self.folder = ctk.StringVar(value=str(initial_dir or DEFAULT_DIR))
        self.desktop_shortcut = ctk.BooleanVar(value=True)
        self.start_after = ctk.BooleanVar(value=True)
        self._ui()

    def _logo(self, size):
        try:
            image = Image.open(resource_path('assets/noctis_logo.png')).convert('RGBA')
            box = image.getbbox()
            if box:
                image = image.crop(box)
            side = max(image.width, image.height)
            pad = int(side * .14)
            square = Image.new('RGBA', (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
            square.alpha_composite(image, ((square.width - image.width) // 2,
                                           (square.height - image.height) // 2))
            return ctk.CTkImage(light_image=square, dark_image=square,
                                size=(size, size))
        except Exception:
            return None

    def _ui(self):
        background = ctk.CTkImage(light_image=build_background(self.WIDTH, self.HEIGHT),
                                  dark_image=build_background(self.WIDTH, self.HEIGHT),
                                  size=(self.WIDTH, self.HEIGHT))
        self._background = background
        ctk.CTkLabel(self.root, text='', image=background,
                     fg_color=BG).place(x=0, y=0, relwidth=1, relheight=1)

        shell = ctk.CTkFrame(self.root, fg_color=SHELL, corner_radius=26,
                             border_width=1, border_color='#514126')
        shell.pack(fill='both', expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(shell, fg_color='transparent')
        header.pack(fill='x', padx=30, pady=(22, 8))
        logo = self._logo(58)
        if logo is not None:
            self._logo_image = logo
            ctk.CTkLabel(header, text='', image=logo,
                         fg_color='transparent').pack(side='left', padx=(0, 15))
        titles = ctk.CTkFrame(header, fg_color='transparent')
        titles.pack(side='left', fill='y')
        ctk.CTkLabel(titles, text='NOCTIS AUTH', text_color=GOLD,
                     font=ctk.CTkFont(family=FONT_UI, size=24, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(titles, text='INSTALLATION WINDOWS  •  WINDOWS 10 / 11',
                     text_color=MUTED,
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).pack(anchor='w')
        badge = ctk.CTkFrame(header, fg_color='#191B22', corner_radius=12,
                             border_width=1, border_color='#3B3E49')
        badge.pack(side='right', pady=6)
        ctk.CTkLabel(badge, text=f'v{APP_VERSION}', text_color=WHITE,
                     font=ctk.CTkFont(family=FONT_UI, size=11, weight='bold')).pack(
                         padx=14, pady=4)

        footer = ctk.CTkFrame(shell, fg_color='transparent')
        footer.pack(side='bottom', fill='x', padx=30, pady=(0, 16))
        ctk.CTkLabel(footer, text='◇  NOCTIS  •  Tes codes restent chiffrés sur cet appareil.',
                     text_color='#777983',
                     font=ctk.CTkFont(family=FONT_UI, size=9)).pack(side='left')
        ctk.CTkLabel(footer, text='INSTALLATION SÉCURISÉE', text_color='#777983',
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).pack(side='right')

        body = ctk.CTkFrame(shell, fg_color=CARD, corner_radius=20, border_width=1,
                            border_color='#303139')
        body.pack(fill='both', expand=True, padx=26, pady=(0, 10))
        self.body = body

        ctk.CTkLabel(body, text='Installe ton espace de sécurité',
                     text_color=WHITE,
                     font=ctk.CTkFont(family=FONT_UI, size=21, weight='bold')).pack(
                         anchor='w', padx=26, pady=(20, 3))
        ctk.CTkLabel(body,
                     text='Installation simple, sans Python ni fenêtre de commande. '
                          'Ton coffre existant est conservé.',
                     text_color=MUTED,
                     font=ctk.CTkFont(family=FONT_UI, size=12)).pack(anchor='w', padx=26)

        chips = ctk.CTkFrame(body, fg_color='transparent')
        chips.pack(fill='x', padx=22, pady=(14, 4))
        for icon, text in (('shield', 'Chiffré localement'),
                           ('key', 'Aucun prérequis'),
                           ('download', 'Mises à jour intégrées')):
            chip = ctk.CTkFrame(chips, fg_color='#151821', corner_radius=10,
                                border_width=1, border_color='#262B36')
            chip.pack(side='left', padx=(0, 8))
            ctk.CTkLabel(chip, text='', image=icon_ctk(icon, 14, GOLD_DIM),
                         fg_color='transparent', width=14, height=14).pack(
                             side='left', padx=(10, 7), pady=7)
            ctk.CTkLabel(chip, text=text, text_color=MUTED,
                         font=ctk.CTkFont(family=FONT_UI, size=10)).pack(
                             side='left', padx=(0, 11))

        ctk.CTkLabel(body, text='EMPLACEMENT', text_color=GOLD_DIM, anchor='w',
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).pack(
                         anchor='w', padx=26, pady=(16, 7))
        row = ctk.CTkFrame(body, fg_color='transparent')
        row.pack(fill='x', padx=24)
        self.path_entry = ctk.CTkEntry(
            row, textvariable=self.folder, height=44, corner_radius=12,
            fg_color='#0C0E13', border_color='#3A3B43', text_color=WHITE,
            font=ctk.CTkFont(family=FONT_UI, size=11))
        self.path_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.browse_btn = GlassButton(row, text='Parcourir', icon='folder',
                                      command=self.browse, width=116, height=44,
                                      radius=12, style='glass', base=CARD,
                                      font_size=11, icon_size=16)
        self.browse_btn.pack(side='right')

        options = ctk.CTkFrame(body, fg_color='transparent')
        options.pack(fill='x', padx=26, pady=(14, 2))
        self.desktop_check = ctk.CTkCheckBox(
            options, text='Raccourci sur le Bureau', variable=self.desktop_shortcut,
            checkbox_width=20, checkbox_height=20, corner_radius=6, border_width=2,
            fg_color=GOLD, hover_color=GOLD_DIM, checkmark_color='#15130A',
            border_color='#4A4B55', text_color=MUTED,
            font=ctk.CTkFont(family=FONT_UI, size=11))
        self.desktop_check.pack(side='left')
        self.start_check = ctk.CTkCheckBox(
            options, text='Lancer après l’installation', variable=self.start_after,
            checkbox_width=20, checkbox_height=20, corner_radius=6, border_width=2,
            fg_color=GOLD, hover_color=GOLD_DIM, checkmark_color='#15130A',
            border_color='#4A4B55', text_color=MUTED,
            font=ctk.CTkFont(family=FONT_UI, size=11))
        self.start_check.pack(side='left', padx=(24, 0))

        self.install_btn = GlassButton(
            body, text='Installer Noctis Auth', icon='download',
            command=self.install, width=680, height=54, radius=17,
            style='gold', base=CARD, font_size=14)
        self.install_btn.pack(padx=24, pady=(16, 12))

        self.status = ctk.CTkLabel(body, text='Prêt à installer', text_color=MUTED,
                                   anchor='w', justify='left', wraplength=680,
                                   font=ctk.CTkFont(family=FONT_UI, size=11))
        self.status.pack(anchor='w', padx=27)
        progress_row = ctk.CTkFrame(body, fg_color='transparent')
        progress_row.pack(fill='x', padx=24, pady=(7, 0))
        self.bar = ctk.CTkProgressBar(progress_row, height=12, corner_radius=8,
                                      progress_color=GOLD, fg_color='#2A2B31')
        self.bar.pack(side='left', fill='x', expand=True, padx=(0, 12))
        self.bar.set(0)
        self.pct = ctk.CTkLabel(progress_row, text='0 %', text_color=GOLD,
                                font=ctk.CTkFont(family=FONT_UI, size=13,
                                                 weight='bold'))
        self.pct.pack(side='right')

        self.finish_row = ctk.CTkFrame(body, fg_color='transparent')
        self._center()

    def _center(self):
        self.root.update_idletasks()
        x = max(0, (self.root.winfo_screenwidth() - self.WIDTH) // 2)
        y = max(0, (self.root.winfo_screenheight() - self.HEIGHT) // 2 - 20)
        self.root.geometry(f'{self.WIDTH}x{self.HEIGHT}+{x}+{y}')

    def browse(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title='Choisir le dossier d’installation')
        if path:
            self.folder.set(str(Path(path) / 'Noctis Auth'))

    def _progress(self, value, text=None):
        value = max(0.0, min(100.0, float(value)))
        percent = int(value)
        if percent == self._last_percent and text is None:
            return
        self._last_percent = percent

        def apply():
            try:
                if not self.root.winfo_exists():
                    return
                self.bar.set(value / 100.0)
                self.pct.configure(text=f'{percent} %')
                if text is not None:
                    self.status.configure(text=text, text_color=MUTED)
            except Exception:
                pass

        try:
            self.root.after(0, apply)
        except Exception:
            pass

    def _set_busy(self, busy):
        self._installing = busy
        state = 'disabled' if busy else 'normal'
        self.path_entry.configure(state=state)
        for widget in (self.desktop_check, self.start_check):
            widget.configure(state=state)
        if busy:
            self.install_btn.set_command(None)
            self.install_btn.set_text('INSTALLATION EN COURS…')
            self.browse_btn.set_command(None)
        else:
            self.install_btn.set_command(self.install)
            self.browse_btn.set_command(self.browse)

    def install(self):
        if self._installing:
            return
        value = self.folder.get().strip().strip('"')
        if not value:
            self.status.configure(text='Choisis un dossier d’installation.',
                                  text_color=RED)
            return
        target = Path(value).expanduser()
        try:
            if target.resolve() == Path(target.resolve().anchor):
                raise ValueError
        except (OSError, ValueError):
            self.status.configure(text='Ce dossier ne peut pas être utilisé.', text_color=RED)
            return
        self._set_busy(True)
        self._progress(1, 'Préparation du dossier…')
        threading.Thread(target=self._install_worker, args=(target,), daemon=True,
                         name='noctis-setup').start()

    def _install_worker(self, target):
        try:
            payload = Path(resource_path(APP_EXE))
            icon = Path(resource_path('noctis.ico'))
            if not payload.is_file():
                raise RuntimeError('NoctisAuth.exe est absent de l’installateur.')
            target.mkdir(parents=True, exist_ok=True)
            destination = target / APP_EXE
            setup_destination = target / SETUP_EXE
            setup_source = Path(sys.executable).resolve()
            copy_setup = setup_source != setup_destination.resolve()

            total = payload.stat().st_size
            if icon.is_file():
                total += icon.stat().st_size
            if copy_setup:
                total += setup_source.stat().st_size
            copied = [0]

            def advance(count):
                copied[0] += count
                self._progress(4 + 90 * copied[0] / max(1, total))

            self._progress(3, 'Copie sécurisée de l’application…')
            self._copy(payload, destination, advance)
            if icon.is_file():
                self._copy(icon, target / 'noctis.ico', advance)
            if copy_setup:
                self._copy(setup_source, setup_destination, advance)

            warnings = []
            self._progress(95, 'Création des raccourcis…')
            try:
                self._create_links(target, destination, setup_destination)
            except Exception:
                warnings.append('Les raccourcis n’ont pas pu être créés.')
            self._progress(98, 'Enregistrement dans Windows…')
            try:
                register_install(target, setup_destination)
            except Exception:
                warnings.append('L’entrée de désinstallation n’a pas pu être enregistrée.')
            self._progress(100, 'Installation terminée.')
            self.root.after(0, lambda: self._finished(destination, warnings))
        except Exception as exc:
            message = str(exc)
            self.root.after(0, lambda: self._failed(message))

    def _copy(self, source, destination, advance):
        destination = Path(destination)
        temporary = destination.with_name(destination.name + '.new')
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        with open(source, 'rb') as reader, open(temporary, 'wb') as writer:
            while True:
                chunk = reader.read(1024 * 1024)
                if not chunk:
                    break
                writer.write(chunk)
                advance(len(chunk))
        deadline = time.monotonic() + 45
        while True:
            try:
                os.replace(temporary, destination)
                return
            except PermissionError:
                if time.monotonic() > deadline:
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        pass
                    raise RuntimeError(
                        'Noctis Auth est encore ouvert. Ferme l’application '
                        'puis clique sur Réessayer.')
                self._progress(self._last_percent,
                               'Fermeture de Noctis Auth en cours…')
                time.sleep(0.5)

    def _create_links(self, target, destination, setup_destination):
        shortcuts = []
        if self.desktop_shortcut.get():
            shortcuts.append((desktop_folder() / 'Noctis Auth.lnk', destination,
                              '', target, destination))
        programs = programs_folder() / 'Noctis Auth'
        shortcuts.append((programs / 'Noctis Auth.lnk', destination, '',
                          target, destination))
        shortcuts.append((programs / 'Désinstaller Noctis Auth.lnk',
                          setup_destination, '--uninstall', target,
                          setup_destination))
        create_shortcuts(shortcuts)

    def _finished(self, destination, warnings):
        self._set_busy(False)
        self.install_btn.set_command(None)
        self.install_btn.set_text('Noctis Auth est installé ✓')
        self._progress(100, 'Installation terminée avec succès.')
        if warnings:
            self._progress(100, 'Installation terminée. ' + ' '.join(warnings))
        if self.start_after.get():
            self.status.configure(text='Installation terminée. Lancement de Noctis Auth…',
                                  text_color=GREEN)
            self.root.after(700, lambda: self._launch(destination))
            return
        self.finish_row.pack(fill='x', padx=24, pady=(12, 16))
        GlassButton(self.finish_row, text='Lancer Noctis Auth', icon='arrow-right',
                    command=lambda: self._launch(destination), width=320, height=46,
                    radius=14, style='gold', base=CARD, font_size=12).pack(side='left')
        GlassButton(self.finish_row, text='Terminer', icon='check',
                    command=self.root.destroy, width=150, height=46, radius=14,
                    style='glass', base=CARD, font_size=12).pack(side='left', padx=(10, 0))

    def _launch(self, destination):
        try:
            subprocess.Popen([str(destination)], cwd=str(destination.parent),
                             close_fds=True)
        except Exception:
            pass
        self.root.after(500, self.root.destroy)

    def _failed(self, message):
        self._set_busy(False)
        self.install_btn.set_text('Réessayer l’installation')
        self.install_btn.set_command(self.install)
        self.status.configure(text=message, text_color=RED)
        self._progress(0)


# ---------------------------------------------------------------------------
# Fenêtre de désinstallation
# ---------------------------------------------------------------------------
class UninstallWindow:
    WIDTH, HEIGHT = 800, 620

    def __init__(self, root):
        self.root = root
        self.install_dir = read_install_dir()
        self._last_percent = -1
        root.title(f'{APP_NAME} — Désinstallation')
        root.geometry(f'{self.WIDTH}x{self.HEIGHT}')
        root.resizable(False, False)
        root.configure(fg_color=BG)
        try:
            root.iconbitmap(resource_path('noctis.ico'))
        except Exception:
            pass
        set_dark_titlebar(root)
        self.purge = ctk.BooleanVar(value=False)
        self._ui()

    def _ui(self):
        image = build_background(self.WIDTH, self.HEIGHT)
        self._background = ctk.CTkImage(light_image=image, dark_image=image,
                                        size=(self.WIDTH, self.HEIGHT))
        ctk.CTkLabel(self.root, text='', image=self._background,
                     fg_color=BG).place(x=0, y=0, relwidth=1, relheight=1)
        shell = ctk.CTkFrame(self.root, fg_color=SHELL, corner_radius=26,
                             border_width=1, border_color='#4A2A2C')
        shell.pack(fill='both', expand=True, padx=20, pady=20)
        header = ctk.CTkFrame(shell, fg_color='transparent')
        header.pack(fill='x', padx=30, pady=(22, 8))
        ctk.CTkLabel(header, text='', image=icon_ctk('trash', 30, RED),
                     fg_color='transparent', width=30, height=30).pack(side='left',
                                                                      padx=(0, 14))
        titles = ctk.CTkFrame(header, fg_color='transparent')
        titles.pack(side='left')
        ctk.CTkLabel(titles, text='NOCTIS AUTH', text_color=GOLD,
                     font=ctk.CTkFont(family=FONT_UI, size=23, weight='bold')).pack(anchor='w')
        ctk.CTkLabel(titles, text='DÉSINSTALLATION WINDOWS', text_color=MUTED,
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).pack(anchor='w')

        body = ctk.CTkFrame(shell, fg_color=CARD, corner_radius=20, border_width=1,
                            border_color='#303139')
        body.pack(fill='both', expand=True, padx=26, pady=(0, 16))
        ctk.CTkLabel(body, text='Désinstalle Noctis Auth',
                     text_color=WHITE,
                     font=ctk.CTkFont(family=FONT_UI, size=21, weight='bold')).pack(
                         anchor='w', padx=26, pady=(24, 4))
        ctk.CTkLabel(body,
                     text='L’application et ses raccourcis seront retirés de cet ordinateur. '
                          'Ton coffre chiffré et tes comptes A2F seront conservés par défaut.',
                     text_color=MUTED, justify='left', wraplength=660,
                     font=ctk.CTkFont(family=FONT_UI, size=12)).pack(anchor='w', padx=26)
        location = ctk.CTkFrame(body, fg_color='#151821', corner_radius=12,
                                border_width=1, border_color='#262B36')
        location.pack(fill='x', padx=24, pady=(20, 10))
        ctk.CTkLabel(location, text='DOSSIER D’INSTALLATION', text_color=GOLD_DIM,
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight='bold')).pack(
                         anchor='w', padx=14, pady=(10, 2))
        ctk.CTkLabel(location, text=str(self.install_dir), text_color=WHITE,
                     font=ctk.CTkFont(family=FONT_UI, size=11)).pack(
                         anchor='w', padx=14, pady=(0, 10))
        self.purge_check = ctk.CTkCheckBox(
            body, text='Supprimer aussi mon coffre et mes comptes (irréversible)',
            variable=self.purge, checkbox_width=20, checkbox_height=20,
            corner_radius=6, border_width=2, fg_color='#C64C4C',
            hover_color='#DA5E5E', checkmark_color='#FFFFFF', border_color='#6B3A3A',
            text_color='#F0B4B4',
            font=ctk.CTkFont(family=FONT_UI, size=11))
        self.purge_check.pack(anchor='w', padx=26, pady=(6, 4))
        ctk.CTkLabel(body,
                     text='Sans cette case, le fichier %APPDATA%\\NoctisAuth\\vault.json '
                          'reste intact et sera réutilisé à la prochaine installation.',
                     text_color=SUBTLE, justify='left', wraplength=660,
                     font=ctk.CTkFont(family=FONT_UI, size=10)).pack(anchor='w', padx=26)

        buttons = ctk.CTkFrame(body, fg_color='transparent')
        buttons.pack(fill='x', padx=24, pady=(22, 8))
        self.uninstall_btn = GlassButton(buttons, text='Désinstaller', icon='trash',
                                         command=self.uninstall, width=250, height=50,
                                         radius=15, style='danger', base=CARD,
                                         font_size=13)
        self.uninstall_btn.pack(side='left')
        GlassButton(buttons, text='Annuler', icon='x', command=self.root.destroy,
                    width=150, height=50, radius=15, style='glass', base=CARD,
                    font_size=12).pack(side='left', padx=(10, 0))

        self.status = ctk.CTkLabel(body, text='Prêt à désinstaller', text_color=MUTED,
                                   anchor='w', font=ctk.CTkFont(family=FONT_UI, size=11))
        self.status.pack(anchor='w', padx=27, pady=(6, 4))
        row = ctk.CTkFrame(body, fg_color='transparent')
        row.pack(fill='x', padx=24)
        self.bar = ctk.CTkProgressBar(row, height=12, corner_radius=8,
                                      progress_color=RED, fg_color='#2A2B31')
        self.bar.pack(side='left', fill='x', expand=True, padx=(0, 12))
        self.bar.set(0)
        self.pct = ctk.CTkLabel(row, text='0 %', text_color=RED,
                                font=ctk.CTkFont(family=FONT_UI, size=13, weight='bold'))
        self.pct.pack(side='right')
        self._center()

    def _center(self):
        self.root.update_idletasks()
        x = max(0, (self.root.winfo_screenwidth() - self.WIDTH) // 2)
        y = max(0, (self.root.winfo_screenheight() - self.HEIGHT) // 2 - 20)
        self.root.geometry(f'{self.WIDTH}x{self.HEIGHT}+{x}+{y}')

    def _progress(self, value, text):
        percent = int(max(0, min(100, value)))

        def apply():
            try:
                self.bar.set(percent / 100)
                self.pct.configure(text=f'{percent} %')
                self.status.configure(text=text)
            except Exception:
                pass

        self.root.after(0, apply)

    def uninstall(self):
        self.uninstall_btn.set_command(None)
        self.uninstall_btn.set_text('DÉSINSTALLATION EN COURS…')
        self.purge_check.configure(state='disabled')
        self._progress(20, 'Suppression des raccourcis et de l’enregistrement…')
        purge = bool(self.purge.get())
        try:
            spawn_cleanup(self.install_dir, purge)
        except Exception as exc:
            self.status.configure(text=f'Désinstallation impossible : {exc}',
                                  text_color=RED)
            self.uninstall_btn.set_command(self.uninstall)
            return
        self._progress(100, 'Désinstallation terminée. Fermeture…')
        if purge:
            self.status.configure(text='Désinstallation terminée. Le coffre a été supprimé.',
                                  text_color=RED)
        else:
            self.status.configure(text='Désinstallation terminée. Ton coffre est conservé.',
                                  text_color=GREEN)
        self.root.after(1400, self.root.destroy)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
def create_root():
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('dark-blue')
    return ctk.CTk()


def main():
    options = parse_args(sys.argv[1:])
    set_dpi_and_appid()

    if options['cleanup']:
        cleanup_main(options['dir'], options['purge'])
        return 0

    if options['uninstall']:
        if options['silent']:
            spawn_cleanup(options['dir'] or read_install_dir(), options['purge'])
            return 0
        root = create_root()
        UninstallWindow(root)
        root.mainloop()
        return 0

    if options['silent']:
        try:
            silent_install(options['dir'] or DEFAULT_DIR)
            return 0
        except Exception:
            return 1

    root = create_root()
    SetupWindow(root, options['dir'])
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
