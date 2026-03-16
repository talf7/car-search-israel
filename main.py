# -*- coding: utf-8 -*-
# VERSION 10 - sug_degem from REG (M=מסחרי, P=פרטי), fix commercial detection, Hebrew labels
import customtkinter as ctk
import requests
import threading
import json
import tempfile

API_BASE     = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_REG  = "053cea08-09bc-40ec-8f7a-156f0677aff3"
RESOURCE_WLTP = "142afde2-6228-49f9-8a29-9b6c3a0cbe40"

_session = requests.Session()


# ── Text helpers ──────────────────────────────────────────────────────────────
# Windows bidi always reverses Hebrew word order in tkinter labels.
# Fix: store strings in reverse word order → bidi re-reverses → correct display.

def rev(text):
    """Reverse word order so bidi shows it correctly."""
    return " ".join(reversed(text.split()))

# Pure Hebrew static strings (stored reversed)
T_TITLE           = "קנייה לפני בדיקה מחיר"        # → מחיר בדיקה לפני קנייה
T_PLACEHOLDER     = "רישוי מספר"                    # → מספר רישוי
T_SEARCHING       = "מחפש..."
T_NOT_FOUND       = "במאגר נמצא לא הרכב"            # → הרכב לא נמצא במאגר
T_NO_DATA         = "זמינים אינם הרכב נתוני — מחיר לחשב ניתן לא"
T_COMMERCIAL      = "המדויק המחיר את לברר יש — מסחרי רכב"
T_UNKNOWN_COST    = "מזוהה לא רכב סוג — עלות לחשב ניתן לא"
T_NET_ERROR       = "לאינטרנט חיבור בדוק — תקשורת שגיאת"
T_INVALID         = "ספרות 8 עד 5 — תקין לא רישוי מספר"
T_ENTER           = "רישוי מספר להכניס נא"
T_GRP_UNKNOWN     = "ידועה לא :אגרה קבוצת"          # → קבוצת אגרה: לא ידועה
T_DRV_UNKNOWN     = "ידוע לא :הנעה סוג"             # → סוג הנעה: לא ידוע
# Warning strings (stored reversed for bidi)
T_COMMERCIAL_WARN = "מדוייק מחיר לברר צריך לכן מסחרי הינו הרכב"
# → הרכב הינו מסחרי לכן צריך לברר מחיר מדוייק
T_PRICE_CHECK     = "מדוייק מחיר לברר יש"
# → יש לברר מחיר מדוייק


# Mixed Hebrew + number/value format strings
def fmt_price(price):
    return f"₪ {price:,}   :בדיקה עלות"          # → עלות בדיקה:   600 ₪

def fmt_group(val):
    return f"{val}   :אגרה קבוצת"                # → קבוצת אגרה:   3

def fmt_drive(val):
    return f"{val}   :הנעה סוג"                   # → סוג הנעה:   4X2

def fmt_battery(label_rev, price):
    return f"₪ {price:,}   :{label_rev}"          # → בדיקת סוללה לרכב חשמלי:   450 ₪

# sug_degem translation: REG uses "P"=פרטי (private), "M"=מסחרי (commercial)
_DEGEM_LABEL = {"P": "פרטי", "M": "מסחרי", "L": "אופנוע", "T": "טרקטור", "O": "נגרר"}

def fmt_rechev(val):
    label = _DEGEM_LABEL.get(str(val or "").strip().upper(), str(val or ""))
    rev_label = " ".join(reversed(label.split()))
    return f"{rev_label}   :רכב סוג"              # → סוג רכב:   פרטי / מסחרי

def fmt_merkav(val):
    # Replace ASCII apostrophe with Hebrew geresh (׳ U+05F3) to prevent bidi run splitting.
    # ASCII ' is "neutral" in bidi, causing Hebrew words like הצ'בק to be split into
    # two RTL runs that get reordered incorrectly. Hebrew geresh is RTL and stays in the run.
    clean = str(val or "").replace("'", "׳").replace("\u2019", "׳")
    rev_val = " ".join(reversed(clean.split()))
    return f"{rev_val}   :מרכב"                   # → מרכב:   הצ׳בק

def fmt_moshavim(val):
    # Show seats excluding driver (subtract 1)
    try:
        seats = int(val) - 1
        return f"{seats}   :נהג למעט ישיבה מקומות"  # → מקומות ישיבה למעט נהג:   4
    except (ValueError, TypeError):
        return f"{val}   :מושבים מספר"             # fallback


# ── Icon ──────────────────────────────────────────────────────────────────────
def _create_car_icon():
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([4, 26, 60, 50], radius=7, fill="#3b82f6")
        d.polygon([(15,26),(20,12),(44,12),(49,26)], fill="#1d4ed8")
        d.polygon([(42,25),(47,25),(43,13),(35,13)], fill="#93c5fd")
        d.polygon([(17,25),(22,25),(26,13),(18,13)], fill="#93c5fd")
        d.ellipse([ 8, 44, 28, 60], fill="#1e293b")
        d.ellipse([36, 44, 56, 60], fill="#1e293b")
        d.ellipse([14, 49, 22, 56], fill="#94a3b8")
        d.ellipse([42, 49, 50, 56], fill="#94a3b8")
        d.ellipse([52, 32, 61, 40], fill="#fde68a")
        d.ellipse([ 3, 32, 11, 40], fill="#ef4444")
        tmp = tempfile.mktemp(suffix=".ico")
        img.save(tmp, format="ICO", sizes=[(64,64),(32,32),(16,16)])
        return tmp
    except Exception:
        return None


# ── API ───────────────────────────────────────────────────────────────────────
def fetch_vehicle_data(plate_number):
    r1 = _session.get(API_BASE, params={
        "resource_id": RESOURCE_REG,
        "filters": json.dumps({"mispar_rechev": plate_number}),
        "limit": 1,
    }, timeout=10)
    r1.raise_for_status()
    reg_records = r1.json().get("result", {}).get("records", [])
    if not reg_records:
        return None, "not_found"
    reg = reg_records[0]

    sug_delek     = reg.get("sug_delek_nm", "") or ""
    sug_degem_reg = reg.get("sug_degem",    "") or ""  # "P"=פרטי, "M"=מסחרי (authoritative)

    tozeret_cd = reg.get("tozeret_cd")
    degem_nm   = reg.get("degem_nm")
    if tozeret_cd and degem_nm:
        try:
            r2 = _session.get(API_BASE, params={
                "resource_id": RESOURCE_WLTP,
                "filters": json.dumps({"tozeret_cd": tozeret_cd, "degem_nm": degem_nm}),
                "limit": 1,
            }, timeout=10)
            r2.raise_for_status()
            recs = r2.json().get("result", {}).get("records", [])
            if recs:
                result = dict(recs[0])          # includes mispar_moshavim, merkav, hanaa_nm…
                result["sug_delek_nm"] = sug_delek
                result["sug_degem"]    = sug_degem_reg  # override with REG (authoritative)
                return result, "ok"
        except Exception:
            pass

    return {"sug_delek_nm": sug_delek, "sug_degem": sug_degem_reg}, "no_wltp"


# ── Price / warning logic ─────────────────────────────────────────────────────
def is_commercial_vehicle(merkav, sug_degem):
    """True if vehicle is commercial → suppress price, show warning.
    REG sug_degem: "M"=מסחרי (177K vehicles), "P"=פרטי (3.9M vehicles).
    Also check merkav for "מסחרי" keyword."""
    if "מסחרי" in str(merkav or ""):
        return True
    if str(sug_degem or "").strip().upper() == "M":
        return True
    return False


def is_price_check_warning(merkav, mispar_moshavim):
    """True if MPV/אחוד body, or 6+ passenger seats (excl. driver)."""
    if "MPV" in str(merkav or "").upper() or "אחוד" in str(merkav or ""):
        return True
    try:
        if int(mispar_moshavim or 0) - 1 >= 6:
            return True
    except (ValueError, TypeError):
        pass
    return False


def get_inspection_price(kvuzat_agra_cd, hanaa_nm, merkav):
    if not kvuzat_agra_cd:
        return None
    try:
        group = int(kvuzat_agra_cd)
    except (ValueError, TypeError):
        return None
    if not group:
        return None
    is_4x4  = hanaa_nm == "4X4"
    is_mini = merkav and "מיני" in str(merkav)
    if is_4x4:
        if group <= 3: return 860
        if group <= 5: return 1000
        if group == 6: return 1300
        return 1500
    if is_mini:
        return 860 if group <= 5 else 1250
    if group <= 3: return 600
    if group <= 5: return 690
    if group == 6: return 860
    return 1250


def get_battery_check(sug_delek_nm):
    fuel = str(sug_delek_nm or "")
    if "חשמל" in fuel:
        return "חשמלי לרכב סוללה בדיקת", 450
    if "היברידי" in fuel or "היבריד" in fuel:
        return "היברידי לרכב סוללה בדיקת", 300
    return None


# ── App ───────────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(T_TITLE + " 🚗")
        self.geometry("560x620")
        self.minsize(500, 540)
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        icon = _create_car_icon()
        if icon:
            self.after(100, lambda: self.iconbitmap(icon))
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text=T_TITLE,
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack(pady=(30, 24))

        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(anchor="center")

        self.search_btn = ctk.CTkButton(
            search_frame, text="חפש", width=90, command=self._on_search
        )
        self.search_btn.pack(side="right", padx=(8, 0))

        self.entry = ctk.CTkEntry(
            search_frame, placeholder_text=T_PLACEHOLDER,
            font=ctk.CTkFont(size=16), justify="right", width=200
        )
        self.entry.pack(side="right")
        self.entry.bind("<Return>", lambda e: self._on_search())

        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=14), text_color="gray"
        )
        self.status_label.pack(pady=(10, 0))

        # Warning frame — shown conditionally
        self.warning_frame = ctk.CTkFrame(
            self, fg_color="#2a1a00", border_color="#f59e0b", border_width=1
        )
        self.warning_label = ctk.CTkLabel(
            self.warning_frame, text="",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#f59e0b",
            wraplength=420
        )
        self.warning_label.pack(pady=12, padx=20)

        # Results frame
        self.results_frame = ctk.CTkFrame(self)

        self.price_label = ctk.CTkLabel(
            self.results_frame, text="",
            font=ctk.CTkFont(size=22, weight="bold"), text_color="#4CAF50"
        )
        self.price_label.pack(pady=(22, 8), padx=30)

        self.group_label = ctk.CTkLabel(
            self.results_frame, text="", font=ctk.CTkFont(size=16)
        )
        self.group_label.pack(pady=6, padx=30)

        self.drive_label = ctk.CTkLabel(
            self.results_frame, text="", font=ctk.CTkFont(size=16)
        )
        self.drive_label.pack(pady=6, padx=30)

        self.rechev_label = ctk.CTkLabel(
            self.results_frame, text="", font=ctk.CTkFont(size=16)
        )
        self.rechev_label.pack(pady=4, padx=30)

        self.merkav_label = ctk.CTkLabel(
            self.results_frame, text="", font=ctk.CTkFont(size=16)
        )
        self.merkav_label.pack(pady=4, padx=30)

        self.moshavim_label = ctk.CTkLabel(
            self.results_frame, text="", font=ctk.CTkFont(size=16)
        )
        self.moshavim_label.pack(pady=(4, 22), padx=30)

        # Battery frame
        self.battery_frame = ctk.CTkFrame(
            self, fg_color="#1e2a1e", border_color="#2d5a2d", border_width=1
        )
        self.battery_label = ctk.CTkLabel(
            self.battery_frame, text="",
            font=ctk.CTkFont(size=16), text_color="#6fcf6f"
        )
        self.battery_label.pack(pady=14, padx=20)

    def _on_search(self):
        plate = self.entry.get().strip()
        if not plate:
            self._set_status(T_ENTER, "orange")
            return
        if not plate.isdigit() or not (5 <= len(plate) <= 8):
            self._set_status(T_INVALID, "orange")
            return
        self.search_btn.configure(state="disabled", text=T_SEARCHING)
        self._set_status(T_SEARCHING, "gray")
        self.results_frame.pack_forget()
        self.battery_frame.pack_forget()
        self.warning_frame.pack_forget()
        threading.Thread(target=self._fetch_and_update, args=(plate,), daemon=True).start()

    def _fetch_and_update(self, plate):
        try:
            data, status = fetch_vehicle_data(plate)
            self.after(0, self._update_ui, data, status)
        except Exception:
            self.after(0, self._show_error, T_NET_ERROR)

    def _update_ui(self, data, status):
        self.search_btn.configure(state="normal", text="חפש")

        if status == "not_found":
            self._set_status(T_NOT_FOUND, "orange")
            self.results_frame.pack_forget()
            self.battery_frame.pack_forget()
            self.warning_frame.pack_forget()
            return

        if status == "no_wltp" or data is None:
            self._set_status(T_NO_DATA, "orange")
            self._show_battery((data or {}).get("sug_delek_nm", ""))
            self.results_frame.pack_forget()
            self.warning_frame.pack_forget()
            return

        kvuzat_agra_cd  = data.get("kvuzat_agra_cd")
        hanaa_nm        = data.get("hanaa_nm",        "") or ""
        merkav          = data.get("merkav",          "") or ""
        sug_delek       = data.get("sug_delek_nm",    "") or ""
        sug_degem       = data.get("sug_degem",       "") or ""  # WLTP: "M"=passenger, "N"=commercial
        mispar_moshavim = data.get("mispar_moshavim", "") or ""  # WLTP: seat count

        # Populate detail rows
        self.rechev_label.configure(text=fmt_rechev(sug_degem) if sug_degem else "")
        self.merkav_label.configure(text=fmt_merkav(merkav) if merkav else "")
        self.moshavim_label.configure(text=fmt_moshavim(mispar_moshavim) if mispar_moshavim else "")

        if is_commercial_vehicle(merkav, sug_degem):
            self.price_label.configure(text=T_COMMERCIAL, text_color="orange")
            self.group_label.configure(
                text=fmt_group(kvuzat_agra_cd) if kvuzat_agra_cd else T_GRP_UNKNOWN
            )
            self.drive_label.configure(
                text=fmt_drive(hanaa_nm) if hanaa_nm else T_DRV_UNKNOWN
            )
            self._set_status("", "gray")
            self.warning_label.configure(text=T_COMMERCIAL_WARN)
            self.warning_frame.pack(pady=(0, 8), padx=40, fill="x")
            self.results_frame.pack(pady=14, padx=40, fill="x")
            self._show_battery(sug_delek)
            return

        price = get_inspection_price(kvuzat_agra_cd, hanaa_nm, merkav)
        self.price_label.configure(
            text=fmt_price(price) if price else T_UNKNOWN_COST,
            text_color="#4CAF50" if price else "orange"
        )
        self.group_label.configure(
            text=fmt_group(kvuzat_agra_cd) if kvuzat_agra_cd else T_GRP_UNKNOWN
        )
        self.drive_label.configure(
            text=fmt_drive(hanaa_nm) if hanaa_nm else T_DRV_UNKNOWN
        )
        self._set_status("", "gray")
        self._show_warning(merkav, mispar_moshavim)
        self.results_frame.pack(pady=14, padx=40, fill="x")
        self._show_battery(sug_delek)

    def _show_warning(self, merkav, mispar_moshavim):
        if is_price_check_warning(merkav, mispar_moshavim):
            self.warning_label.configure(text=T_PRICE_CHECK)
            self.warning_frame.pack(pady=(0, 8), padx=40, fill="x")
        else:
            self.warning_frame.pack_forget()

    def _show_battery(self, sug_delek_nm):
        result = get_battery_check(sug_delek_nm)
        if result:
            label_rev, price = result
            self.battery_label.configure(text=fmt_battery(label_rev, price))
            self.battery_frame.pack(pady=(0, 14), padx=40, fill="x")
        else:
            self.battery_frame.pack_forget()

    def _show_error(self, msg):
        self.search_btn.configure(state="normal", text="חפש")
        self._set_status(msg, "red")
        self.results_frame.pack_forget()
        self.battery_frame.pack_forget()
        self.warning_frame.pack_forget()

    def _set_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)


if __name__ == "__main__":
    App().mainloop()
