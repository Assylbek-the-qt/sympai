"""
PDF Medical Report generator.
Produces a single-file PDF with patient info, BP trend chart, stats summary,
and a full readings table. Designed to be handed to a doctor at a clinic visit.
"""
import io
from datetime import date

import matplotlib
matplotlib.use("Agg")  # non-interactive backend, safe in Docker
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ── Constants ─────────────────────────────────────────────────────────────────

RISK_LABELS = {
    "low":      "Норма",
    "medium":   "Повышенный",
    "high":     "Высокий",
    "critical": "Критический",
}

RISK_COLORS = {
    "low":      colors.HexColor("#27ae60"),
    "medium":   colors.HexColor("#f39c12"),
    "high":     colors.HexColor("#e67e22"),
    "critical": colors.HexColor("#c0392b"),
}

DIAG_LABELS = {
    "hypertension": "Гипертония",
    "diabetes":     "Диабет",
    "both":         "Гипертония + Диабет",
}

# ── Chart ─────────────────────────────────────────────────────────────────────

def _bp_chart(readings: list) -> io.BytesIO | None:
    if not readings:
        return None

    ordered = sorted(readings, key=lambda r: r.reading_date)
    dates = [r.reading_date for r in ordered]
    sbps  = [r.sbp for r in ordered]
    dbps  = [r.dbp for r in ordered]

    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(dates, sbps, "o-", color="#e74c3c", label="СБД (верхнее)", linewidth=2, markersize=5)
    ax.plot(dates, dbps, "s-", color="#3498db", label="ДБД (нижнее)",  linewidth=2, markersize=5)

    # Reference lines
    ax.axhline(y=180, color="#c0392b", linestyle=":",  alpha=0.7, linewidth=1, label="Критично 180")
    ax.axhline(y=140, color="#e67e22", linestyle="--", alpha=0.6, linewidth=1, label="Норма 140")
    ax.axhline(y=90,  color="#3498db", linestyle="--", alpha=0.4, linewidth=1)

    ax.set_ylabel("мм рт.ст.", fontsize=9)
    ax.set_title("Динамика артериального давления", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(bottom=max(0, min(dbps) - 20))

    interval = max(1, len(dates) // 7)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
    plt.xticks(rotation=25, fontsize=8)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ── Standalone chart PNG ──────────────────────────────────────────────────────

def build_chart_png(readings: list) -> bytes | None:
    """Return raw PNG bytes for the BP trend chart, or None if no readings."""
    buf = _bp_chart(readings)
    if buf is None:
        return None
    return buf.read()


# ── PDF builder ───────────────────────────────────────────────────────────────

def build_pdf(patient, readings: list) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm,   bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    h1  = ParagraphStyle("h1",  parent=styles["Heading1"], fontSize=16, alignment=TA_CENTER, spaceAfter=4)
    h2  = ParagraphStyle("h2",  parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"],   fontSize=9,  textColor=colors.grey, alignment=TA_CENTER)
    ftr = ParagraphStyle("ftr", parent=styles["Normal"],   fontSize=7,  textColor=colors.grey, alignment=TA_RIGHT)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Медицинский отчёт / Медициналық есеп", h1))
    story.append(Paragraph(
        f"SympAI · Мониторинг АД · {date.today().strftime('%d.%m.%Y')}",
        sub,
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ── Patient info ──────────────────────────────────────────────────────────
    story.append(Paragraph("Информация о пациенте", h2))

    diag_raw = str(patient.diagnosis).split(".")[-1]  # strips enum prefix
    diag_label = DIAG_LABELS.get(diag_raw, diag_raw)

    info_rows = [
        ["ФИО / Аты-жөні",         patient.full_name],
        ["Возраст / Жас",           str(patient.age)],
        ["Диагноз",                 diag_label],
        ["Лекарства / Дәрі",        patient.current_medication or "—"],
        ["Сопутствующие болезни",   patient.comorbidities or "—"],
    ]
    info_tbl = Table(info_rows, colWidths=[5.5 * cm, 11 * cm])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
        ("BOX",         (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID",   (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # ── BP chart ──────────────────────────────────────────────────────────────
    chart_buf = _bp_chart(readings)
    if chart_buf:
        story.append(Paragraph("Динамика давления / Қысым динамикасы", h2))
        story.append(Image(chart_buf, width=16 * cm, height=6.4 * cm))
        story.append(Spacer(1, 0.3 * cm))

    # ── Summary stats ─────────────────────────────────────────────────────────
    if readings:
        sbps       = [r.sbp for r in readings]
        dbps       = [r.dbp for r in readings]
        med_count  = sum(1 for r in readings if r.medication_taken)
        compliance = round((med_count / len(readings)) * 100)
        critical_n = sum(1 for r in readings if _risk_str(r) == "critical")
        high_n     = sum(1 for r in readings if _risk_str(r) == "high")

        story.append(Paragraph("Сводная статистика", h2))
        stats_rows = [
            ["Период",                f"Последние {len(readings)} показаний"],
            ["Среднее давление",      f"{round(sum(sbps)/len(sbps))}/{round(sum(dbps)/len(dbps))} мм рт.ст."],
            ["Приём лекарств",        f"{compliance}%  ({med_count} из {len(readings)} дней)"],
            ["Критических показаний", str(critical_n)],
            ["Высоких показаний",     str(high_n)],
        ]
        stats_tbl = Table(stats_rows, colWidths=[5.5 * cm, 11 * cm])
        stats_tbl.setStyle(TableStyle([
            ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
            ("BOX",         (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID",   (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            # Red text for critical count if > 0
            *([("TEXTCOLOR", (1, 3), (1, 3), colors.HexColor("#c0392b"))] if critical_n > 0 else []),
        ]))
        story.append(stats_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # ── Readings table ────────────────────────────────────────────────────────
    story.append(Paragraph("Журнал показаний / Деректер журналы", h2))

    headers = ["Дата", "АД", "Пульс", "Глюкоза", "Дәрі", "Риск"]
    rows = [headers]
    row_risk_levels = []

    for r in sorted(readings, key=lambda x: x.reading_date, reverse=True):
        risk_raw = _risk_str(r)
        rows.append([
            r.reading_date.strftime("%d.%m.%Y"),
            f"{r.sbp}/{r.dbp}",
            str(r.pulse) if r.pulse else "—",
            f"{r.glucose}" if r.glucose else "—",
            "✓" if r.medication_taken else "✗",
            RISK_LABELS.get(risk_raw, "—"),
        ])
        row_risk_levels.append(risk_raw)

    col_w = [2.5 * cm, 3 * cm, 2 * cm, 2.5 * cm, 1.5 * cm, 5 * cm]
    tbl = Table(rows, colWidths=col_w)

    tbl_style = [
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("BOX",         (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID",   (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Colour the risk cell per level
    for i, rl in enumerate(row_risk_levels):
        c = RISK_COLORS.get(rl)
        if c:
            tbl_style.append(("TEXTCOLOR", (5, i + 1), (5, i + 1), c))
            tbl_style.append(("FONTNAME",  (5, i + 1), (5, i + 1), "Helvetica-Bold"))

    tbl.setStyle(TableStyle(tbl_style))
    story.append(tbl)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Сгенерировано SympAI · {date.today().strftime('%d.%m.%Y')} · "
        "Документ предназначен для передачи лечащему врачу.",
        ftr,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _risk_str(reading) -> str:
    """Return a plain string risk level from either an ORM object or a string."""
    rl = reading.risk_level
    if rl is None:
        return ""
    return str(rl).split(".")[-1]  # strips 'RiskLevel.' prefix if present
