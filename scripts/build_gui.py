"""Noctis Auth — lanceur de compilation (interface Tk + sortie non bloquante).

Usage développeur : double-cliquer sur BUILD.bat à la racine du dépôt.
"""

import ctypes
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
from app_config import APP_VERSION  # noqa: E402

if sys.platform == 'win32':
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'Noctis.Auth.Builder.2.9')
    except Exception:
        pass

GOLD = '#F4C542'
BG = '#08090C'
PANEL = '#111217'
WHITE = '#F5F5F7'
MUTED = '#9B9DA7'


class BuildWindow:
    def __init__(self, root):
        self.root = root
        root.title('Noctis Auth — Compilation')
        root.geometry('720x520')
        root.resizable(False, False)
        root.configure(bg=BG)
        try:
            root.iconbitmap(str(ROOT / 'noctis.ico'))
        except Exception:
            pass
        self.events = queue.Queue()
        self.percent = 0
        self._ui()
        root.after(80, self._poll)
        threading.Thread(target=self._work, daemon=True).start()

    def _round(self, canvas, x1, y1, x2, y2, r, fill, outline=''):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return canvas.create_polygon(pts, smooth=True, splinesteps=24, fill=fill,
                                     outline=outline, width=1)

    def _ui(self):
        canvas = tk.Canvas(self.root, width=720, height=520, bg=BG,
                           highlightthickness=0)
        canvas.pack(fill='both', expand=True)
        canvas.create_oval(450, -250, 870, 180, outline='#332817', width=3)
        canvas.create_oval(475, -230, 845, 155, outline='#211B13', width=2)
        canvas.create_oval(-250, 380, 180, 800, outline='#2A2112', width=3)
        self._round(canvas, 24, 20, 696, 498, 24, PANEL, '#514126')
        canvas.create_rectangle(48, 21, 672, 23, fill=GOLD, outline='')

        logo_path = ROOT / 'assets' / 'noctis_logo.png'
        try:
            self.logo = tk.PhotoImage(file=str(logo_path))
            factor = max(1, self.logo.width() // 68)
            if factor > 1:
                self.logo = self.logo.subsample(factor, factor)
            canvas.create_image(78, 73, image=self.logo, anchor='center')
        except Exception:
            canvas.create_text(78, 73, text='N', fill=GOLD,
                               font=('Segoe UI', 25, 'bold'))
        canvas.create_text(125, 57, text='NOCTIS AUTH', anchor='w', fill=WHITE,
                           font=('Segoe UI', 19, 'bold'))
        canvas.create_text(126, 82, text='COMPILATION • WINDOWS', anchor='w',
                           fill=MUTED, font=('Segoe UI', 8, 'bold'))

        self._round(canvas, 48, 125, 672, 415, 18, '#0D0E12', '#2D2A25')
        canvas.create_text(76, 158, text='Compilation de ton application',
                           anchor='w', fill=WHITE, font=('Segoe UI', 18, 'bold'))
        canvas.create_text(76, 188,
                           text='Application + installateur autonome NoctisAuth_Setup.exe.',
                           anchor='w', fill=MUTED, font=('Segoe UI', 10))
        self.status_id = canvas.create_text(76, 242, text='Initialisation…',
                                            anchor='w', fill=WHITE,
                                            font=('Segoe UI', 10))
        self.pct_id = canvas.create_text(640, 242, text='0 %', anchor='e',
                                         fill=GOLD, font=('Segoe UI', 13, 'bold'))
        self._round(canvas, 76, 263, 644, 278, 8, '#292A30')
        self.progress = canvas.create_rectangle(78, 265, 80, 276, fill=GOLD,
                                                outline='')
        canvas.create_text(76, 316, text='ÉTAPES', anchor='w', fill='#777A84',
                           font=('Segoe UI', 8, 'bold'))
        self.step_ids = []
        steps = [(344, 'Vérification des composants'),
                 (370, 'Compilation de l’application'),
                 (396, 'Création de NoctisAuth_Setup.exe')]
        for y, label in steps:
            dot = canvas.create_oval(77, y - 5, 87, y + 5, fill='#37383F',
                                     outline='')
            text = canvas.create_text(101, y, text=label, anchor='w',
                                      fill=MUTED, font=('Segoe UI', 9))
            self.step_ids.append((dot, text))
        canvas.create_text(76, 459, text='NOCTIS  •  SOBRE, RAPIDE ET SÉCURISÉ',
                           anchor='w', fill='#686B74',
                           font=('Segoe UI', 8, 'bold'))
        canvas.create_text(644, 459, text=APP_VERSION, anchor='e',
                           fill='#777A84', font=('Segoe UI', 9))
        self.canvas = canvas

    def _emit(self, percent, message):
        self.events.put(('progress', percent, message))

    def _run(self, args, label, start, end, cwd=ROOT):
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        proc = subprocess.Popen(args, cwd=str(cwd), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding='utf-8', errors='replace', bufsize=1,
                                creationflags=flags)
        output = []

        def reader():
            try:
                for line in proc.stdout:
                    output.append(line.rstrip())
            except Exception:
                pass

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        progress = start
        self._emit(progress, label)
        started = time.monotonic()
        while proc.poll() is None:
            elapsed = time.monotonic() - started
            target = min(end - 1, start + int(elapsed / 2.4))
            if target > progress:
                progress = target
                self._emit(progress, label)
            time.sleep(.25)
        thread.join(timeout=2)
        if proc.returncode:
            tail = '\n'.join(output[-45:])
            raise RuntimeError((tail or f'{label} — code {proc.returncode}')[-5000:])
        self._emit(end, label)

    def _work(self):
        try:
            self._emit(3, 'Vérification de Python…')
            python = os.getenv('NOCTIS_PYTHON', 'py')
            self._run([python, '-m', 'pip', 'install', '-r',
                       'requirements-build.txt', '--disable-pip-version-check'],
                      'Installation des composants nécessaires…', 4, 22)
            self._emit(23, 'Vérification de la version…')
            self._run([python, 'scripts/check_version.py'],
                      'Vérification de la version…', 23, 26)
            self._run([python, '-m', 'PyInstaller', '--noconfirm', '--clean',
                       '--distpath', 'dist', '--workpath', 'build/app',
                       'packaging/NoctisAuth.spec'],
                      'Compilation de Noctis Auth…', 27, 68)
            self._run([python, '-m', 'PyInstaller', '--noconfirm', '--clean',
                       '--distpath', 'dist', '--workpath', 'build/setup',
                       'packaging/NoctisAuth_Setup.spec'],
                      'Création de NoctisAuth_Setup.exe…', 69, 96)
            self._run([python, 'scripts/make_checksum.py'],
                      'Calcul des empreintes SHA-256…', 96, 99)
            setup = ROOT / 'dist' / 'NoctisAuth_Setup.exe'
            if not setup.exists():
                raise RuntimeError('Le fichier NoctisAuth_Setup.exe est introuvable.')
            self._emit(100, 'Compilation terminée — ouverture de l’installateur…')
            time.sleep(.5)
            subprocess.Popen([str(setup)], cwd=str(setup.parent),
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.events.put(('done',))
        except Exception as exc:
            self.events.put(('error', str(exc)))

    def _poll(self):
        try:
            while True:
                item = self.events.get_nowait()
                if item[0] == 'done':
                    self.root.destroy()
                    return
                if item[0] == 'error':
                    from tkinter import messagebox
                    messagebox.showerror(
                        'Noctis Auth — Compilation impossible',
                        item[1] + '\n\nVérifie Python et ta connexion Internet, '
                                  'puis relance BUILD.bat.')
                    self.root.destroy()
                    return
                _, percent, message = item
                self.percent = percent
                self.canvas.itemconfigure(self.status_id, text=message)
                self.canvas.itemconfigure(self.pct_id, text=f'{percent} %')
                self.canvas.coords(self.progress, 78, 265,
                                   78 + 564 * percent / 100, 276)
                active = 0 if percent < 26 else (1 if percent < 69 else 2)
                for index, (dot, text) in enumerate(self.step_ids):
                    color = GOLD if index <= active else '#37383F'
                    self.canvas.itemconfigure(dot, fill=color)
                    self.canvas.itemconfigure(
                        text, fill=WHITE if index == active else MUTED)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(80, self._poll)


if __name__ == '__main__':
    root = tk.Tk()
    BuildWindow(root)
    root.mainloop()
