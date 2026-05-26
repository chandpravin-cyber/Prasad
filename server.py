#!/usr/bin/env python3
"""
Prasad Planner – local server
- Serves static files (HTML, CSV, PDF)
- POST /save-pdf  →  generates PDF with reportlab, saves to PDF/, returns shareable URL
Run:  python3 server.py
"""

import http.server, socketserver, json, os, socket, urllib.parse
from pathlib import Path

# ── reportlab imports ──────────────────────────────────────────────────────────
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, KeepTogether
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units    import mm
from reportlab.lib.styles   import getSampleStyleSheet, ParagraphStyle
from reportlab.lib           import colors
from reportlab.lib.enums    import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Config ────────────────────────────────────────────────────────────────────
PORT    = 8080
BASE    = Path(__file__).parent
PDF_DIR = BASE / "PDF"
PDF_DIR.mkdir(exist_ok=True)

# ── Brand colours ─────────────────────────────────────────────────────────────
C_PRIMARY  = colors.HexColor("#8B1A1A")
C_DARK     = colors.HexColor("#2C3E50")
C_ACCENT   = colors.HexColor("#E8820C")
C_TEAL     = colors.HexColor("#1A7A6E")
C_ROW_ALT  = colors.HexColor("#FBF7F2")
C_BORDER   = colors.HexColor("#E0D8D0")
C_WHITE    = colors.white
C_MUTED    = colors.HexColor("#6B6B6B")

CAT_COLORS = {
    "Rice & Khichdi":        colors.HexColor("#7B5E2A"),
    "Dal":                   colors.HexColor("#8B3A0F"),
    "Sabji & Curries":       colors.HexColor("#1A6B3A"),
    "Raita Salad & Chutney": colors.HexColor("#1A5A8B"),
    "Sweets (Khiri & Halwa)":colors.HexColor("#7B2A6B"),
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def fmt_num(n):
    if n >= 100: return str(round(n))
    if n >= 10:  return f"{n:.1f}".rstrip('0').rstrip('.')
    if n >= 1:   return f"{n:.2f}".rstrip('0').rstrip('.')
    return f"{n:.3f}".rstrip('0').rstrip('.')

def to_metric(qty, unit):
    if unit == "lb":
        kg = qty * 0.453592
        return (f"{kg:.3f}".rstrip('0').rstrip('.'), "kg") if kg >= 1 \
               else (str(round(kg * 1000)), "g")
    if unit == "gallons":
        L = qty * 3.78541
        return (f"{L:.3f}".rstrip('0').rstrip('.'), "L") if L >= 1 \
               else (str(round(L * 1000)), "mL")
    return (fmt_num(qty), unit)

def sanitise(name):
    return "".join(c for c in name if c.isalnum() or c in " _-").strip() or "shopping_list"

# ── PDF builder ───────────────────────────────────────────────────────────────
def build_pdf(path: Path, payload: dict):
    people    = payload.get("people", 250)
    unit_mode = payload.get("unitMode", "both")   # 'both' | 'imperial' | 'metric'
    dishes    = payload.get("dishes", [])
    show_comb = payload.get("showCombined", True)
    show_dish = payload.get("showPerDish",  True)
    categories= payload.get("categories", [])

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=12*mm,  bottomMargin=12*mm,
    )

    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    s_white  = ps("W",   fontSize=9,  textColor=C_WHITE,  leading=11)
    s_ing    = ps("I",   fontSize=9,  textColor=colors.black, leading=11)
    s_muted  = ps("M",   fontSize=8,  textColor=C_MUTED,  leading=10)
    s_imp    = ps("Imp", fontSize=9,  textColor=C_ACCENT, leading=11, alignment=TA_RIGHT)
    s_met    = ps("Met", fontSize=9,  textColor=C_TEAL,   leading=11, alignment=TA_RIGHT)
    s_right  = ps("R",   fontSize=9,  textColor=colors.black, leading=11, alignment=TA_RIGHT)

    story = []
    W = doc.width

    # column widths
    if unit_mode == "both":
        col_w = [8*mm, W-8*mm-22*mm-14*mm-22*mm-14*mm-28*mm, 22*mm, 14*mm, 22*mm, 14*mm, 28*mm]
    else:
        col_w = [8*mm, W-8*mm-28*mm-16*mm-32*mm, 28*mm, 16*mm, 32*mm]

    # ── Title banner ──────────────────────────────────────────────────────────
    unit_label = {"both": "Imperial & Metric", "imperial": "Imperial (lb)", "metric": "Metric (kg/g)"}[unit_mode]
    banner = Table([
        [Paragraph(f"<b>Prasad Menu – Ingredient Planner</b>",
                   ps("T", fontSize=15, textColor=C_WHITE, leading=18))],
        [Paragraph(f"{len(dishes)} dishes  ·  {people} people  ·  {unit_label}",
                   ps("S", fontSize=9, textColor=colors.HexColor("#FFCCCC"), leading=12))],
    ], colWidths=[W])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_PRIMARY),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("TOPPADDING",    (0,0), (0,0),   8),
        ("BOTTOMPADDING", (0,1), (0,1),   8),
        ("TOPPADDING",    (0,1), (0,1),   1),
        ("BOTTOMPADDING", (0,0), (0,0),   1),
    ]))
    story += [banner, Spacer(1, 5*mm)]

    def th(text, align=TA_LEFT):
        return Paragraph(f"<b>{text}</b>", ps("TH", fontSize=8, textColor=C_WHITE, leading=10, alignment=align))

    def header_row(with_used=False):
        if unit_mode == "both":
            row = [th("#", TA_RIGHT), th("Ingredient"), th("Qty (lb)", TA_RIGHT), th("Unit"),
                   th("Metric", TA_RIGHT), th("Unit")]
        elif unit_mode == "imperial":
            row = [th("#", TA_RIGHT), th("Ingredient"), th("Quantity", TA_RIGHT), th("Unit")]
        else:
            row = [th("#", TA_RIGHT), th("Ingredient"), th("Quantity", TA_RIGHT), th("Unit")]
        if with_used:
            row.append(th("Used in"))
        return [row]

    def ing_row(idx, name, qty250, unit, used=""):
        qty     = qty250 * people / 250
        imp_str = fmt_num(qty)
        mq, mu  = to_metric(qty, unit)
        conv    = unit in ("lb", "gallons")
        disp_q  = mq  if conv else imp_str
        disp_u  = mu  if conv else unit

        if unit_mode == "both":
            row = [Paragraph(str(idx), s_muted),
                   Paragraph(name, s_ing),
                   Paragraph(imp_str, s_imp),
                   Paragraph(unit, s_muted),
                   Paragraph(str(disp_q), s_met),
                   Paragraph(disp_u, s_muted)]
        elif unit_mode == "imperial":
            row = [Paragraph(str(idx), s_muted),
                   Paragraph(name, s_ing),
                   Paragraph(imp_str, s_imp),
                   Paragraph(unit, s_muted)]
        else:
            row = [Paragraph(str(idx), s_muted),
                   Paragraph(name, s_ing),
                   Paragraph(str(disp_q), s_met),
                   Paragraph(disp_u, s_muted)]
        if used is not None:
            row.append(Paragraph(used, s_muted))
        return row

    def tbl_style(n_rows, hdr_bg=C_DARK):
        cmds = [
            ("BACKGROUND",    (0,0), (-1,0),   hdr_bg),
            ("LEFTPADDING",   (0,0), (-1,-1),  4),
            ("RIGHTPADDING",  (0,0), (-1,-1),  4),
            ("TOPPADDING",    (0,0), (-1,-1),  3),
            ("BOTTOMPADDING", (0,0), (-1,-1),  3),
            ("GRID",          (0,0), (-1,-1),  0.3, C_BORDER),
            ("VALIGN",        (0,0), (-1,-1),  "MIDDLE"),
        ]
        for i in range(2, n_rows+1, 2):
            cmds.append(("BACKGROUND", (0,i), (-1,i), C_ROW_ALT))
        return TableStyle(cmds)

    def section_header(text, subtext, bg):
        t = Table([[
            Paragraph(f"<b>{text}</b>  <font size='8' color='#cccccc'>{subtext}</font>",
                      ps("SH", fontSize=10, textColor=C_WHITE, leading=14))
        ]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), bg),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        return t

    # ── Combined list ─────────────────────────────────────────────────────────
    if show_comb and dishes:
        combined = {}
        for dish in dishes:
            for ing in dish.get("ingredients", []):
                key = ing["name"].lower()
                if key not in combined:
                    combined[key] = {"name": ing["name"], "qty250": 0,
                                     "unit": ing["unit"], "dishes": []}
                combined[key]["qty250"] += ing["qty250"]
                combined[key]["dishes"].append(dish["name"])

        rows = sorted(combined.values(), key=lambda x: x["name"])
        hdr  = section_header("Combined Shopping List",
                              f"{len(rows)} unique ingredients · {people} people", C_DARK)
        data = header_row(with_used=True)
        for i, r in enumerate(rows):
            used = ", ".join(dict.fromkeys(r["dishes"]))
            data.append(ing_row(i+1, r["name"], r["qty250"], r["unit"], used))

        tbl = Table(data, colWidths=col_w, repeatRows=1)
        tbl.setStyle(tbl_style(len(rows)))
        story += [KeepTogether([hdr, tbl]), Spacer(1, 5*mm)]

    # ── Per-dish ──────────────────────────────────────────────────────────────
    if show_dish and dishes:
        cat_map = {}
        for dish in dishes:
            cat = dish.get("category", "Other")
            cat_map.setdefault(cat, []).append(dish)

        for cat in (categories or list(cat_map.keys())):
            for dish in cat_map.get(cat, []):
                bg   = CAT_COLORS.get(cat, C_PRIMARY)
                ings = dish.get("ingredients", [])
                hdr  = section_header(dish["name"],
                                      f"{len(ings)} ingredients · {people} people", bg)
                data = header_row(with_used=False)
                for i, ing in enumerate(ings):
                    data.append(ing_row(i+1, ing["name"], ing["qty250"], ing["unit"], None))
                tbl = Table(data, colWidths=col_w, repeatRows=1)
                tbl.setStyle(tbl_style(len(ings), hdr_bg=bg))
                story += [KeepTogether([hdr, tbl]), Spacer(1, 4*mm)]

    doc.build(story)


# ── HTTP Handler ──────────────────────────────────────────────────────────────
class Handler(http.server.SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path == "/save-pdf":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                payload  = json.loads(body)
                filename = sanitise(payload.get("filename", "shopping_list"))
                if not filename.endswith(".pdf"):
                    filename += ".pdf"

                dest = PDF_DIR / filename
                build_pdf(dest, payload)

                local_ip  = get_local_ip()
                enc       = urllib.parse.quote(filename)
                url_local = f"http://localhost:{PORT}/PDF/{enc}"
                url_wifi  = f"http://{local_ip}:{PORT}/PDF/{enc}"

                self._respond(200, {"ok": True, "filename": filename,
                                    "url_local": url_local, "url_wifi": url_wifi})
                print(f"  ✅  Saved: PDF/{filename}")
            except Exception as e:
                import traceback; traceback.print_exc()
                self._respond(500, {"ok": False, "error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 55)
    print("  🍛  Prasad Planner – Local Server")
    print("=" * 55)
    print(f"  Local :  http://localhost:{PORT}/prasad_planner.html")
    print(f"  Wi-Fi :  http://{local_ip}:{PORT}/prasad_planner.html")
    print(f"  PDFs  :  {PDF_DIR}")
    print("  Press Ctrl+C to stop")
    print("=" * 55)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
