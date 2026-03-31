"""
Co-Chan GUI — Interface graphique pour Co-Chan Downloader
Place ce fichier dans le meme dossier que Co-chan.py
Lancement : python Co-Chan-GUI.py
"""

import os
import sys
import queue
import shutil
import threading
import subprocess
import platform
import time
import importlib.util
from tkinter import *
from tkinter import ttk, filedialog, messagebox

# ══════════════════════════════════════════════════════════════════════════════
#  IMPORT CO-CHAN
# ══════════════════════════════════════════════════════════════════════════════

COCHAN_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Co-chan.py")

def import_cochan():
    if not os.path.exists(COCHAN_SCRIPT):
        messagebox.showerror(
            "Fichier manquant",
            "Co-chan.py introuvable dans :\n" + os.path.dirname(COCHAN_SCRIPT) + "\n\n"
            "Place Co-Chan-GUI.py dans le meme dossier que Co-chan.py"
        )
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("cochan", COCHAN_SCRIPT)
    mod  = importlib.util.module_from_spec(spec)
    mod.__name__ = "cochan"
    spec.loader.exec_module(mod)
    return mod

# ══════════════════════════════════════════════════════════════════════════════
#  THEME — sobre, sombre, minimaliste
# ══════════════════════════════════════════════════════════════════════════════

BG_DEEP  = "#111111"
BG_CARD  = "#1c1c1c"
BG_PANEL = "#242424"
ACCENT   = "#5b9cf6"
ACCENT_D = "#3d7de0"
TEXT_W   = "#e4e4e4"
TEXT_DIM = "#5a5a5a"
TEXT_MID = "#999999"
GREEN_C  = "#52a873"
RED_C    = "#d95f5f"
YELLOW_C = "#c9944a"
BORDER   = "#2e2e2e"
BORDER_L = "#3a3a3a"

FNT_TITLE = ("Segoe UI", 16, "bold")
FNT_HEAD  = ("Segoe UI", 10, "bold")
FNT_BODY  = ("Segoe UI", 10)
FNT_SMALL = ("Segoe UI", 9)
FNT_MONO  = ("Consolas", 9)

# ══════════════════════════════════════════════════════════════════════════════
#  STYLE ttk
# ══════════════════════════════════════════════════════════════════════════════

def apply_ttk_style():
    s = ttk.Style()
    s.theme_use("clam")
    for name, h in [("Main", 6), ("Thin", 4)]:
        s.configure(name + ".Horizontal.TProgressbar",
                    troughcolor=BG_PANEL, background=ACCENT,
                    bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT_D,
                    thickness=h)

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def mk_btn(parent, text, cmd, bg=ACCENT, fg=BG_DEEP,
           abg=ACCENT_D, font=FNT_HEAD, padx=16, pady=6, **kw):
    b = Button(parent, text=text, command=cmd,
               bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
               font=font, relief="flat", cursor="hand2",
               padx=padx, pady=pady, bd=0, **kw)
    b.bind("<Enter>", lambda e: b.configure(bg=abg))
    b.bind("<Leave>", lambda e: b.configure(bg=bg))
    return b

def mk_ghost_btn(parent, text, cmd, padx=12, pady=6, **kw):
    return mk_btn(parent, text, cmd,
                  bg=BG_PANEL, fg=TEXT_MID, abg=BORDER_L,
                  font=FNT_SMALL, padx=padx, pady=pady, **kw)

def mk_sep(parent, pady=10):
    Frame(parent, bg=BORDER, height=1).pack(fill=X, pady=pady)

def mk_label_row(parent, key, value):
    r = Frame(parent, bg=BG_DEEP)
    r.pack(fill=X, pady=3)
    Label(r, text=key, font=FNT_SMALL, bg=BG_DEEP,
          fg=TEXT_DIM, width=12, anchor="w").pack(side=LEFT)
    Label(r, text=value, font=FNT_SMALL, bg=BG_DEEP,
          fg=TEXT_MID).pack(side=LEFT)

def styled_entry(parent, textvariable, width=None, **kw):
    fr = Frame(parent, bg=BORDER, padx=1, pady=1)
    opts = dict(textvariable=textvariable, font=("Segoe UI", 11),
                bg=BG_PANEL, fg=TEXT_W, insertbackground=ACCENT,
                relief="flat", highlightthickness=0)
    if width:
        opts["width"] = width
    e = Entry(fr, **opts, **kw)
    e.pack(fill=X, ipady=6, ipadx=8)
    e.bind("<FocusIn>",  lambda ev: fr.configure(bg=ACCENT))
    e.bind("<FocusOut>", lambda ev: fr.configure(bg=BORDER))
    return fr, e

def mk_topbar(parent, title, subtitle="", back_cmd=None, right_widget=None):
    bar = Frame(parent, bg=BG_CARD, padx=22, pady=14)
    bar.pack(fill=X)
    Frame(parent, bg=BORDER, height=1).pack(fill=X)
    if back_cmd:
        mk_ghost_btn(bar, "←", back_cmd, padx=8).pack(side=LEFT, padx=(0, 14))
    col = Frame(bar, bg=BG_CARD)
    col.pack(side=LEFT, fill=X, expand=True)
    Label(col, text=title, font=FNT_TITLE, bg=BG_CARD, fg=TEXT_W).pack(anchor="w")
    if subtitle:
        Label(col, text=subtitle, font=FNT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w")
    if right_widget:
        right_widget(bar)

# ══════════════════════════════════════════════════════════════════════════════
#  APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class App(Tk):
    def __init__(self):
        super().__init__()
        self.title("Co-Chan")
        self.configure(bg=BG_DEEP)
        self.resizable(False, False)
        W, H = 780, 600
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d+%d+%d" % (W, H, (sw-W)//2, (sh-H)//2))
        apply_ttk_style()

        self.cc         = None
        self.base_url   = None
        self.anime_cap  = None
        self.fmt_url    = None
        self.language   = None
        self.seasons    = None
        self.stop_event = threading.Event()
        self.dl_queue   = queue.Queue()
        self._dl_params = (0, 1, False, False)

        c = Frame(self, bg=BG_DEEP)
        c.pack(fill=BOTH, expand=True)

        self.frames = {}
        for Cls in (SplashScreen, MainScreen, LangScreen,
                    SeasonScreen, DownloadScreen, SettingsScreen):
            f = Cls(c, self)
            self.frames[Cls.__name__] = f

        self.show("SplashScreen")

    def show(self, name):
        for f in self.frames.values():
            f.pack_forget()
        f = self.frames[name]
        f.pack(fill=BOTH, expand=True)
        if hasattr(f, "on_show"):
            f.on_show()

    def get_dl_dir(self):
        return self.cc.get_download_path() if self.cc else os.path.expanduser("~")

    def poll(self):
        try:
            while True:
                self.frames["DownloadScreen"].handle(self.dl_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(80, self.poll)

# ══════════════════════════════════════════════════════════════════════════════
#  ECRAN 1 — SPLASH
# ══════════════════════════════════════════════════════════════════════════════

class SplashScreen(Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DEEP)
        self.app = app

        ctr = Frame(self, bg=BG_DEEP)
        ctr.place(relx=0.5, rely=0.38, anchor="center")
        Label(ctr, text="Co-Chan", font=("Segoe UI", 36, "bold"),
              bg=BG_DEEP, fg=TEXT_W).pack()
        Label(ctr, text="Downloader", font=("Segoe UI", 11),
              bg=BG_DEEP, fg=TEXT_DIM).pack()

        bar_frame = Frame(self, bg=BG_DEEP)
        bar_frame.place(relx=0.5, rely=0.60, anchor="center")
        self.pb = ttk.Progressbar(bar_frame, style="Main.Horizontal.TProgressbar",
                                  length=280, mode="determinate")
        self.pb.pack()

        self.sv = StringVar(value="Initialisation...")
        Label(self, textvariable=self.sv, font=FNT_SMALL,
              bg=BG_DEEP, fg=TEXT_DIM).place(relx=0.5, rely=0.67, anchor="center")

        self._pct = 0
        self._tick()

    def _tick(self):
        if self._pct < 25:
            self._pct += 1
            self.pb["value"] = self._pct
            self.after(30, self._tick)

    def on_show(self):
        def worker():
            try:
                cc  = import_cochan()
                cc.set_process_priority()
                url = cc.check_domain_availability()
                self.app.cc       = cc
                self.app.base_url = url
                self.after(0, self._ok)
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._err(err))
        threading.Thread(target=worker, daemon=True).start()

    def _ok(self):
        self.sv.set("Connecte.")
        self.pb["value"] = 100
        self.after(400, lambda: self.app.show("MainScreen"))

    def _err(self, e):
        self.sv.set("Erreur : " + e)
        messagebox.showerror("Connexion impossible", e)

# ══════════════════════════════════════════════════════════════════════════════
#  ECRAN 2 — RECHERCHE
# ══════════════════════════════════════════════════════════════════════════════

class MainScreen(Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DEEP)
        self.app = app
        self._searching = False
        self._build()

    def _build(self):
        def right(bar):
            mk_ghost_btn(bar, "Parametres",
                         lambda: self.app.show("SettingsScreen")).pack(side=RIGHT)
        mk_topbar(self, "Co-Chan", "Telechargeur anime-sama", right_widget=right)

        body = Frame(self, bg=BG_DEEP, padx=28, pady=24)
        body.pack(fill=BOTH, expand=True)

        Label(body, text="Nom de l'anime", font=FNT_SMALL,
              bg=BG_DEEP, fg=TEXT_DIM).pack(anchor="w", pady=(0, 4))

        row = Frame(body, bg=BG_DEEP)
        row.pack(fill=X)
        self.sv = StringVar()
        ew, self.entry = styled_entry(row, self.sv)
        ew.pack(side=LEFT, fill=X, expand=True)
        self.entry.bind("<Return>", lambda e: self._search())
        self.btn_s = mk_btn(row, "Rechercher", self._search, padx=14, pady=7)
        self.btn_s.pack(side=LEFT, padx=(8, 0))

        self.status_v = StringVar(value="")
        self.status_l = Label(body, textvariable=self.status_v,
                              font=FNT_SMALL, bg=BG_DEEP, fg=TEXT_DIM)
        self.status_l.pack(anchor="w", pady=(8, 0))
        self.pb = ttk.Progressbar(body, style="Thin.Horizontal.TProgressbar",
                                  length=710, mode="indeterminate")

        mk_sep(body, pady=20)

        Label(body, text="Utilisation", font=FNT_HEAD,
              bg=BG_DEEP, fg=TEXT_MID).pack(anchor="w", pady=(0, 10))
        for txt in [
            "Tapez le nom de l'anime puis Entree",
            "Selectionnez la langue disponible",
            "Choisissez les saisons et le mode de telechargement",
            "La progression s'affiche en temps reel",
        ]:
            r = Frame(body, bg=BG_DEEP)
            r.pack(fill=X, pady=3)
            Label(r, text="—", font=FNT_SMALL, bg=BG_DEEP,
                  fg=ACCENT, width=3).pack(side=LEFT)
            Label(r, text=txt, font=FNT_SMALL, bg=BG_DEEP,
                  fg=TEXT_DIM).pack(side=LEFT)

        Label(self, text="Sibnet · Vidmoly · Sendvid   ·   yt-dlp",
              font=FNT_SMALL, bg=BG_DEEP, fg=TEXT_DIM).pack(side=BOTTOM, pady=8)

    def _search(self):
        q = self.sv.get().strip()
        if not q or self._searching:
            return
        self._searching = True
        self.btn_s.configure(text="...", state="disabled")
        self.entry.configure(state="disabled")
        self.status_v.set("Connexion...")
        self.status_l.configure(fg=TEXT_DIM)
        self.pb.pack(anchor="w", pady=(4, 0))
        self.pb.start(12)

        def worker():
            try:
                cc  = self.app.cc
                nm  = cc.normalize_anime_name(q)
                cap = nm.title()
                fmt = cc.format_url_name(nm)
                ok  = cc.check_anime_exists(self.app.base_url, fmt)
                if ok:
                    self.app.anime_cap = cap
                    self.app.fmt_url   = fmt
                    self.after(0, self._found)
                else:
                    self.after(0, lambda: self._not_found(cap))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._error(err))
        threading.Thread(target=worker, daemon=True).start()

    def _stop_anim(self):
        self.pb.stop(); self.pb.pack_forget()
        self._searching = False
        self.btn_s.configure(text="Rechercher", state="normal")
        self.entry.configure(state="normal")

    def _found(self):
        self._stop_anim()
        self.status_v.set(self.app.anime_cap + " — trouve")
        self.status_l.configure(fg=GREEN_C)
        self.after(500, lambda: self.app.show("LangScreen"))

    def _not_found(self, cap):
        self._stop_anim()
        self.status_v.set(cap + " — introuvable, verifiez l'orthographe")
        self.status_l.configure(fg=RED_C)

    def _error(self, e):
        self._stop_anim()
        self.status_v.set("Erreur : " + e)
        self.status_l.configure(fg=RED_C)

    def on_show(self):
        self.status_v.set("")
        self._searching = False
        self.btn_s.configure(text="Rechercher", state="normal")
        self.entry.configure(state="normal")
        self.pb.stop(); self.pb.pack_forget()
        self.entry.focus_set()

# ══════════════════════════════════════════════════════════════════════════════
#  ECRAN 3 — LANGUE
# ══════════════════════════════════════════════════════════════════════════════

class LangScreen(Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DEEP)
        self.app = app
        self._build()

    def _build(self):
        mk_topbar(self, "Langue", "Versions disponibles",
                  back_cmd=lambda: self.app.show("MainScreen"))
        self.body = Frame(self, bg=BG_DEEP, padx=28, pady=20)
        self.body.pack(fill=BOTH, expand=True)
        self.anime_l = Label(self.body, text="", font=("Segoe UI", 13, "bold"),
                             bg=BG_DEEP, fg=TEXT_W)
        self.anime_l.pack(anchor="w", pady=(0, 4))
        self.status_v = StringVar(value="")
        self.status_l = Label(self.body, textvariable=self.status_v,
                              font=FNT_SMALL, bg=BG_DEEP, fg=TEXT_DIM)
        self.status_l.pack(anchor="w")
        self.pb = ttk.Progressbar(self.body, style="Thin.Horizontal.TProgressbar",
                                  length=710, mode="indeterminate")
        self.pb.pack(anchor="w", pady=(4, 12))
        self.list_frame = Frame(self.body, bg=BG_DEEP)
        self.list_frame.pack(fill=BOTH, expand=True)

    def on_show(self):
        self.anime_l.configure(text=self.app.anime_cap)
        self.status_v.set("Recherche des versions...")
        self.pb.start(12)
        for w in self.list_frame.winfo_children():
            w.destroy()

        def worker():
            try:
                vf = self.app.cc.check_available_languages(
                    self.app.base_url, self.app.fmt_url)
                self.after(0, lambda: self._show(vf))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._err(err))
        threading.Thread(target=worker, daemon=True).start()

    def _err(self, e):
        self.pb.stop(); self.pb.pack_forget()
        self.status_v.set("Erreur : " + e)
        self.status_l.configure(fg=RED_C)

    def _show(self, vf_list):
        self.pb.stop(); self.pb.pack_forget()
        langs = list(vf_list)
        if "vostfr" not in langs:
            langs.append("vostfr")
        self.status_v.set(str(len(langs)) + " version(s) disponible(s)")

        LABELS = {
            "vf":    "Version Francaise",
            "vostfr":"Sous-titres francais",
            "va":    "Version Anglaise",
            "vkr":   "Version Coreenne",
            "vcn":   "Version Chinoise",
            "vqc":   "Version Quebecoise",
        }

        for lang in langs:
            label = LABELS.get(lang, lang.upper())
            card = Frame(self.list_frame, bg=BG_CARD, cursor="hand2",
                         padx=18, pady=12)
            card.pack(fill=X, pady=1)
            col = Frame(card, bg=BG_CARD)
            col.pack(side=LEFT, fill=X, expand=True)
            Label(col, text=lang.upper(), font=FNT_HEAD,
                  bg=BG_CARD, fg=TEXT_W).pack(anchor="w")
            Label(col, text=label, font=FNT_SMALL,
                  bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w")
            Label(card, text="›", font=("Segoe UI", 14),
                  bg=BG_CARD, fg=TEXT_DIM).pack(side=RIGHT)

            def pick(l=lang): self.app.language = l; self.app.show("SeasonScreen")

            def hover(e, c=card, col=col):
                c.configure(bg=BG_PANEL)
                for w in list(c.winfo_children()) + list(col.winfo_children()):
                    try: w.configure(bg=BG_PANEL)
                    except: pass

            def leave(e, c=card, col=col):
                c.configure(bg=BG_CARD)
                for w in list(c.winfo_children()) + list(col.winfo_children()):
                    try: w.configure(bg=BG_CARD)
                    except: pass

            for w in [card, col] + list(col.winfo_children()):
                try:
                    w.bind("<Button-1>", lambda e, f=pick: f())
                    w.bind("<Enter>", hover)
                    w.bind("<Leave>", leave)
                except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  ECRAN 4 — SAISONS
# ══════════════════════════════════════════════════════════════════════════════

class SeasonScreen(Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DEEP)
        self.app = app
        self._build()

    def _build(self):
        mk_topbar(self, "Saisons", "Selectionnez et configurez le telechargement",
                  back_cmd=lambda: self.app.show("LangScreen"))

        body = Frame(self, bg=BG_DEEP, padx=28, pady=18)
        body.pack(fill=BOTH, expand=True)

        self.info_l = Label(body, text="", font=("Segoe UI", 12, "bold"),
                            bg=BG_DEEP, fg=TEXT_W)
        self.info_l.pack(anchor="w", pady=(0, 4))
        self.status_v = StringVar(value="")
        self.status_l = Label(body, textvariable=self.status_v,
                              font=FNT_SMALL, bg=BG_DEEP, fg=TEXT_DIM)
        self.status_l.pack(anchor="w")
        self.pb = ttk.Progressbar(body, style="Thin.Horizontal.TProgressbar",
                                  length=710, mode="indeterminate")

        lb_frame = Frame(body, bg=BG_PANEL)
        lb_frame.pack(fill=BOTH, expand=True, pady=12)
        sc = Scrollbar(lb_frame, orient=VERTICAL, bg=BG_PANEL,
                       troughcolor=BG_PANEL, bd=0, relief="flat")
        sc.pack(side=RIGHT, fill=Y)
        self.lb = Listbox(lb_frame, yscrollcommand=sc.set,
                          font=FNT_MONO, bg=BG_PANEL, fg=TEXT_W,
                          selectbackground=ACCENT, selectforeground=BG_DEEP,
                          relief="flat", highlightthickness=0,
                          activestyle="none", selectmode=EXTENDED, height=6, bd=0)
        self.lb.pack(fill=BOTH, expand=True, padx=1, pady=1)
        sc.configure(command=self.lb.yview)

        opts_row = Frame(body, bg=BG_DEEP)
        opts_row.pack(fill=X)

        mc = Frame(opts_row, bg=BG_CARD, padx=16, pady=12)
        mc.pack(side=LEFT, fill=Y, padx=(0, 12))
        Label(mc, text="Mode", font=FNT_HEAD, bg=BG_CARD, fg=TEXT_W).pack(anchor="w", pady=(0,6))
        self.mode_v = StringVar(value="all")
        for val, txt in [
            ("all",    "Tout telecharger"),
            ("season", "Saison selectionnee"),
            ("from",   "Depuis un episode"),
            ("single", "Episode unique"),
        ]:
            Radiobutton(mc, text=txt, variable=self.mode_v, value=val,
                        font=FNT_SMALL, bg=BG_CARD, fg=TEXT_MID,
                        selectcolor=BG_PANEL, activebackground=BG_CARD,
                        activeforeground=ACCENT,
                        command=self._update_mode).pack(anchor="w", pady=2)

        ec = Frame(opts_row, bg=BG_CARD, padx=16, pady=12)
        ec.pack(side=LEFT, fill=Y)
        Label(ec, text="Episode de depart", font=FNT_HEAD,
              bg=BG_CARD, fg=TEXT_W).pack(anchor="w", pady=(0,6))
        self.ep_v = StringVar(value="1")
        ep_wrap, self.ep_entry = styled_entry(ec, self.ep_v, width=8)
        ep_wrap.pack(anchor="w")
        self.ep_entry.configure(state="disabled")
        Label(ec, text="(modes Depuis et Unique)",
              font=FNT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w", pady=(6,0))

        nav = Frame(self, bg=BG_DEEP, padx=28, pady=12)
        nav.pack(side=BOTTOM, fill=X)
        mk_btn(nav, "Telecharger", self._launch, padx=20, pady=8).pack(side=RIGHT)

    def on_show(self):
        self.info_l.configure(
            text=self.app.anime_cap + "  ·  " + self.app.language.upper())
        self.status_v.set("Chargement des saisons...")
        self.lb.delete(0, END)
        self.pb.pack(anchor="w", pady=(4, 0))
        self.pb.start(12)

        def worker():
            try:
                raw  = self.app.cc.check_seasons(
                    self.app.base_url, self.app.fmt_url, self.app.language)
                seas = self.app.cc.resolve_season_choices(raw)
                self.app.seasons = seas
                self.after(0, lambda: self._show(seas))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._err(err))
        threading.Thread(target=worker, daemon=True).start()

    def _show(self, seasons):
        self.pb.stop(); self.pb.pack_forget()
        if not seasons:
            self.status_v.set("Aucune saison trouvee.")
            self.status_l.configure(fg=RED_C)
            return
        self.status_v.set(str(len(seasons)) + " saison(s)  —  Ctrl+clic pour multi-selection")
        for d, _ in seasons:
            s = str(d)
            if s.lower() == "film":  tag = "FILM"
            elif s.lower() == "oav": tag = "OAV "
            elif "hs" in s.lower():  tag = "HS  "
            else:                    tag = "S   "
            self.lb.insert(END, "  %s  %s" % (tag, s.upper()))
        self.lb.selection_set(0)

    def _err(self, e):
        self.pb.stop(); self.pb.pack_forget()
        self.status_v.set("Erreur : " + e)
        self.status_l.configure(fg=RED_C)

    def _update_mode(self):
        m = self.mode_v.get()
        self.ep_entry.configure(
            state="normal" if m in ("from", "single") else "disabled")

    def _launch(self):
        if not self.app.seasons:
            return
        mode = self.mode_v.get()
        sel  = list(self.lb.curselection())
        start_s, start_ep, only_s, only_ep = 0, 1, False, False

        if mode == "all":
            pass
        elif mode == "season":
            if not sel:
                messagebox.showwarning("Selection", "Choisissez au moins une saison.")
                return
            start_s = self.app.seasons[sel[0]][0]
            only_s  = True
        elif mode in ("from", "single"):
            if not sel:
                messagebox.showwarning("Selection", "Choisissez une saison.")
                return
            try:
                start_ep = int(self.ep_v.get())
            except ValueError:
                messagebox.showwarning("Episode", "Numero d'episode invalide.")
                return
            start_s = self.app.seasons[sel[0]][0]
            only_ep = (mode == "single")

        self.app._dl_params = (start_s, start_ep, only_s, only_ep)
        self.app.show("DownloadScreen")

# ══════════════════════════════════════════════════════════════════════════════
#  ECRAN 5 — TELECHARGEMENT
# ══════════════════════════════════════════════════════════════════════════════

class DownloadScreen(Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DEEP)
        self.app = app
        self._done = self._fail = self._total = 0
        self._build()

    def _build(self):
        mk_topbar(self, "Telechargement", "Progression en temps reel")

        body = Frame(self, bg=BG_DEEP, padx=28, pady=16)
        body.pack(fill=BOTH, expand=True)

        info = Frame(body, bg=BG_CARD, padx=16, pady=12)
        info.pack(fill=X, pady=(0, 14))
        self.anime_l   = Label(info, text="", font=FNT_HEAD, bg=BG_CARD, fg=TEXT_W)
        self.anime_l.pack(anchor="w")
        self.episode_l = Label(info, text="", font=FNT_SMALL, bg=BG_CARD, fg=TEXT_DIM)
        self.episode_l.pack(anchor="w", pady=(3, 0))

        Label(body, text="Episode", font=FNT_SMALL,
              bg=BG_DEEP, fg=TEXT_DIM).pack(anchor="w")
        self.pb_ep = ttk.Progressbar(body, style="Main.Horizontal.TProgressbar",
                                     length=710, mode="determinate")
        self.pb_ep.pack(anchor="w", pady=(2, 10))

        Label(body, text="Global", font=FNT_SMALL,
              bg=BG_DEEP, fg=TEXT_DIM).pack(anchor="w")
        self.pb_tot = ttk.Progressbar(body, style="Thin.Horizontal.TProgressbar",
                                      length=710, mode="determinate")
        self.pb_tot.pack(anchor="w", pady=(2, 4))
        self.tot_l = Label(body, text="", font=FNT_SMALL, bg=BG_DEEP, fg=TEXT_DIM)
        self.tot_l.pack(anchor="w", pady=(0, 10))

        log_wrap = Frame(body, bg=BG_PANEL)
        log_wrap.pack(fill=BOTH, expand=True)
        Label(log_wrap, text=" Journal", font=FNT_SMALL,
              bg=BG_PANEL, fg=TEXT_DIM, pady=4).pack(anchor="w")
        Frame(log_wrap, bg=BORDER, height=1).pack(fill=X)
        sc = Scrollbar(log_wrap, orient=VERTICAL)
        sc.pack(side=RIGHT, fill=Y)
        self.log = Text(log_wrap, yscrollcommand=sc.set,
                        font=FNT_MONO, bg=BG_PANEL, fg=TEXT_MID,
                        relief="flat", highlightthickness=0,
                        state="disabled", height=9, padx=8, pady=4)
        self.log.pack(fill=BOTH, expand=True)
        sc.configure(command=self.log.yview)
        for tag, col in [("info", ACCENT), ("ok", GREEN_C),
                         ("warn", YELLOW_C), ("err", RED_C), ("dim", TEXT_DIM)]:
            self.log.tag_configure(tag, foreground=col)

        nav = Frame(self, bg=BG_DEEP, padx=28, pady=10)
        nav.pack(side=BOTTOM, fill=X)
        self.btn_stop = mk_btn(nav, "Arreter", self._stop,
                               bg=BG_PANEL, fg=RED_C, abg=BORDER_L,
                               padx=14, pady=7)
        self.btn_stop.pack(side=LEFT)
        mk_ghost_btn(nav, "Ouvrir dossier", self._open).pack(side=LEFT, padx=(8,0))
        mk_btn(nav, "Nouvel anime", self._new, padx=16, pady=7).pack(side=RIGHT)

    def on_show(self):
        self.anime_l.configure(
            text=self.app.anime_cap + "  ·  " + self.app.language.upper())
        self.episode_l.configure(text="Demarrage...")
        self.pb_ep["value"] = self.pb_tot["value"] = 0
        self.tot_l.configure(text="")
        self._done = self._fail = self._total = 0
        self._clear_log()
        self._log("Demarrage", "info")
        self.btn_stop.configure(text="Arreter", state="normal",
                                bg=BG_PANEL, fg=RED_C)
        self.app.stop_event.clear()
        t = threading.Thread(target=self._worker,
                             args=(self.app._dl_params,), daemon=True)
        t.start()
        self.app.poll()

    def _log(self, text, tag="dim"):
        self.log.configure(state="normal")
        ts = time.strftime("%H:%M")
        self.log.insert(END, ts + "  " + text + "\n", tag)
        self.log.see(END)
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", END)
        self.log.configure(state="disabled")

    def handle(self, msg):
        t = msg.get("type")
        if t == "ep_start":
            s, e, tot = msg["s"], msg["e"], msg["tot"]
            self._total = tot
            self.episode_l.configure(
                text="S%s  E%d / %d" % (str(s).upper(), e, tot))
            self.pb_ep["value"] = 0
            self._log("S%s E%d/%d" % (str(s).upper(), e, tot), "info")
        elif t == "ep_pct":
            self.pb_ep["value"] = msg["pct"] * 100
        elif t == "ep_ok":
            self._done += 1
            self.pb_ep["value"] = 100
            self._log("OK  S%s E%d/%d" % (str(msg["s"]).upper(), msg["e"], msg["tot"]), "ok")
            self._upd_total()
        elif t == "ep_fail":
            self._fail += 1
            self._log("ECHEC  S%s E%d" % (str(msg["s"]).upper(), msg["e"]), "warn")
            self._upd_total()
        elif t == "log":
            self._log(msg["txt"], msg.get("tag", "dim"))
        elif t == "done":
            self.episode_l.configure(text="Termine")
            self.pb_ep["value"] = self.pb_tot["value"] = 100
            self._log("Telechargement termine.", "ok")
            self.btn_stop.configure(text="Termine", state="disabled")
        elif t == "stopped":
            self.episode_l.configure(text="Arrete")
            self._log("Arrete par l'utilisateur.", "warn")

    def _upd_total(self):
        tot = max(self._total, 1)
        self.pb_tot["value"] = (self._done + self._fail) / tot * 100
        self.tot_l.configure(
            text="%d ok  ·  %d echec  ·  %d total" % (
                self._done, self._fail, self._total))

    def _stop(self):
        self.app.stop_event.set()
        self._log("Arret en cours...", "warn")

    def _open(self):
        p = self.app.get_dl_dir()
        try:
            if os.name == "nt":       os.startfile(p)
            elif platform.system() == "Darwin": subprocess.run(["open", p])
            else:                     subprocess.run(["xdg-open", p])
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _new(self):
        self.app.stop_event.set()
        self.app.show("MainScreen")

    def _worker(self, params):
        from yt_dlp import YoutubeDL
        import tempfile

        q  = self.app.dl_queue
        cc = self.app.cc
        start_s, start_ep, only_s, only_ep = params

        def send(m): q.put(m)
        def slog(txt, tag="dim"): send({"type": "log", "txt": txt, "tag": tag})

        try:
            seasons     = self.app.seasons
            anime_cap   = self.app.anime_cap
            language    = self.app.language
            folder_name = cc.format_folder_name(anime_cap, language)
            dl_base     = cc.get_download_path()
            fmt_url     = self.app.fmt_url

            slog(dl_base + "/" + folder_name)

            for disp_s, url_list in seasons:
                if self.app.stop_event.is_set(): break
                if only_s  and start_s != 0 and disp_s != start_s: continue
                if only_ep and disp_s != start_s: continue

                all_arrs = []
                for url in url_list:
                    eps = cc.extract_video_links(url)
                    if eps: all_arrs.extend(eps)

                if not all_arrs:
                    slog("S%s : aucun lien" % str(disp_s).upper(), "warn")
                    continue

                cur_idx  = 0
                all_lnks = all_arrs[0]
                total    = max(len(a) for a in all_arrs)
                if total == 0: continue

                ep_ctr = 1
                if start_s != 0:
                    keys = [s for s, _ in seasons]
                    try:
                        si = keys.index(start_s)
                        ci = keys.index(disp_s)
                        if ci < si: continue
                        if ci == si and start_ep > 1: ep_ctr = start_ep
                    except ValueError: pass

                slog("S%s — %d episode(s)" % (str(disp_s).upper(), total), "info")

                while ep_ctr <= total:
                    if self.app.stop_event.is_set(): break

                    ep_idx = ep_ctr - 1
                    send({"type": "ep_start", "s": disp_s, "e": ep_ctr, "tot": total})

                    lt = lv = None
                    primary_ok = False

                    if ep_idx < len(all_lnks):
                        lt, lv = all_lnks[ep_idx]
                        if lt == "sibnet" and cc.check_http_403(lv):
                            ep_ctr += 1
                            if only_ep: break
                            continue
                        primary_ok = True

                    dl_dir = os.path.join(dl_base, folder_name)
                    os.makedirs(dl_dir, exist_ok=True)

                    if ep_ctr == 1 and disp_s == seasons[0][0]:
                        try: cc.get_anime_image(anime_cap, dl_dir, fmt_url)
                        except: pass

                    filename = os.path.join(
                        dl_dir, "s" + str(disp_s) + "_e" + str(ep_ctr) + ".mp4")

                    def make_hook(s=disp_s, e=ep_ctr, tot=total):
                        def h(d):
                            if d["status"] == "downloading":
                                dl_b = d.get("downloaded_bytes") or 0
                                tot_ = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                                if tot_ > 0:
                                    pct = dl_b / tot_
                                else:
                                    ps = d.get("_percent_str","0").strip().replace("%","").strip()
                                    try:    pct = float(ps) / 100
                                    except: pct = 0.0
                                send({"type": "ep_pct", "pct": min(pct, 1.0)})
                            elif d["status"] == "finished":
                                send({"type": "ep_pct", "pct": 1.0})
                        return h

                    def do_dl(ltype, lval, silent=False):
                        if not cc.check_disk_space(): return False
                        if ltype == "vidmoly":
                            fu = cc.get_vidmoly_m3u8(lval)
                            if not fu: return False
                            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
                        else:
                            fu  = lval
                            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"
                        tmp = os.path.join(tempfile.gettempdir(), "anime-dl", folder_name)
                        os.makedirs(tmp, exist_ok=True)
                        aria2c = shutil.which("aria2c")
                        opts = {
                            "outtmpl":                       filename,
                            "quiet":                         True,
                            "ignoreerrors":                  True,
                            "no_warnings":                   True,
                            "noprogress":                    True,
                            "progress_hooks":                [] if silent else [make_hook()],
                            "format":                        fmt,
                            "merge_output_format":           "mp4",
                            "logger":                        cc._SilentLogger(),
                            "socket_timeout":                30,
                            "retries":                       15,
                            "fragment_retries":              15,
                            "concurrent_fragment_downloads": 8,
                            "buffersize":                    1024 * 1024,
                            "http_chunk_size":               10 * 1024 * 1024,
                            "paths":                         {"temp": tmp},
                        }
                        if aria2c:
                            opts["external_downloader"] = "aria2c"
                            opts["external_downloader_args"] = {
                                "aria2c": ["-x","16","-s","16","-k","5M","--quiet"]
                            }
                        try:
                            with YoutubeDL(opts) as ydl:
                                ret = ydl.download([fu])
                            mp4 = filename if filename.endswith(".mp4") else filename + ".mp4"
                            return ret == 0 and os.path.isfile(mp4) and os.path.getsize(mp4) > 0
                        except Exception:
                            return False

                    success = do_dl(lt, lv) if primary_ok else False

                    if not success:
                        for fi, fb in enumerate(all_arrs):
                            if fi == cur_idx: continue
                            if len(fb) >= ep_ctr:
                                ft, fv = fb[ep_ctr - 1]
                                if do_dl(ft, fv, silent=True):
                                    cur_idx = fi; all_lnks = fb; success = True; break
                                if os.path.exists(filename) and os.path.getsize(filename) == 0:
                                    os.remove(filename)

                    if success:
                        send({"type": "ep_ok",  "s": disp_s, "e": ep_ctr, "tot": total})
                    else:
                        send({"type": "ep_fail", "s": disp_s, "e": ep_ctr})

                    ep_ctr += 1
                    if only_ep: break
                if only_ep: break

            send({"type": "stopped" if self.app.stop_event.is_set() else "done"})

        except Exception as e:
            send({"type": "log", "txt": "Erreur : " + str(e), "tag": "err"})
            send({"type": "done"})

# ══════════════════════════════════════════════════════════════════════════════
#  ECRAN 6 — PARAMETRES
# ══════════════════════════════════════════════════════════════════════════════

class SettingsScreen(Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG_DEEP)
        self.app = app
        self._build()

    def _build(self):
        mk_topbar(self, "Parametres", "Configuration",
                  back_cmd=lambda: self.app.show("MainScreen"))

        body = Frame(self, bg=BG_DEEP, padx=28, pady=24)
        body.pack(fill=BOTH, expand=True)

        Label(body, text="Dossier de telechargement", font=FNT_HEAD,
              bg=BG_DEEP, fg=TEXT_W).pack(anchor="w", pady=(0, 8))
        row = Frame(body, bg=BG_DEEP)
        row.pack(fill=X)
        self.dir_v = StringVar()
        dir_wrap, self.dir_e = styled_entry(row, self.dir_v)
        self.dir_e.configure(state="readonly")
        dir_wrap.pack(side=LEFT, fill=X, expand=True)
        mk_ghost_btn(row, "Parcourir", self._browse).pack(side=LEFT, padx=(8, 4))
        mk_ghost_btn(row, "Ouvrir",    self._open_d).pack(side=LEFT)

        self.save_l = Label(body, text="", font=FNT_SMALL, bg=BG_DEEP, fg=GREEN_C)
        self.save_l.pack(anchor="w", pady=(6, 0))
        mk_btn(body, "Sauvegarder", self._save, padx=14, pady=7).pack(
            anchor="w", pady=(10, 0))

        mk_sep(body, pady=20)

        Label(body, text="Informations", font=FNT_HEAD,
              bg=BG_DEEP, fg=TEXT_W).pack(anchor="w", pady=(0, 8))
        info = Frame(body, bg=BG_DEEP)
        info.pack(anchor="w")
        for k, v in [
            ("Version",   "Co-Chan"),
            ("Sources",   "Sibnet · Vidmoly · Sendvid"),
            ("Moteur",    "yt-dlp"),
            ("Catalogue", "Anime-Sama"),
        ]:
            mk_label_row(info, k, v)

    def on_show(self):
        if self.app.cc:
            self.dir_v.set(self.app.cc.get_download_path())
        self.save_l.configure(text="")

    def _browse(self):
        p = filedialog.askdirectory(initialdir=self.dir_v.get() or os.path.expanduser("~"))
        if p:
            self.dir_e.configure(state="normal")
            self.dir_v.set(p)
            self.dir_e.configure(state="readonly")

    def _save(self):
        p = self.dir_v.get().strip()
        if not p: return
        try:
            os.makedirs(p, exist_ok=True)
            if self.app.cc:
                self.app.cc._save_config({"download_dir": p})
            self.save_l.configure(text="Sauvegarde.", fg=GREEN_C)
        except Exception as e:
            self.save_l.configure(text="Erreur : " + str(e), fg=RED_C)

    def _open_d(self):
        p = self.dir_v.get()
        if not os.path.isdir(p): return
        try:
            if os.name == "nt":       os.startfile(p)
            elif platform.system() == "Darwin": subprocess.run(["open", p])
            else:                     subprocess.run(["xdg-open", p])
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  LANCEMENT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
