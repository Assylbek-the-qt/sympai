import os
import logging
from datetime import datetime, time as dtime, timezone, timedelta
from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler,
    filters, ContextTypes, CallbackContext,
)
from texts import TEXTS
import api_client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".dev.env"))
TOKEN = os.getenv("TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# States
LANG           = "lang"
NAME           = "name"
AGE            = "age"
DOCTOR         = "doctor"
DIAGNOSIS      = "diagnosis"
INIT_BP1       = "init_bp1"
INIT_BP2       = "init_bp2"
INIT_BP3       = "init_bp3"
INIT_MED       = "init_med"
INIT_COMORBID  = "init_comorbid"
DAILY_SBP      = "daily_sbp"
DAILY_DBP      = "daily_dbp"
DAILY_PULSE    = "daily_pulse"
DAILY_GLUCOSE  = "daily_glucose"
DAILY_MED      = "daily_med"
DAILY_SYMPTOMS = "daily_symptoms"
EVENING_CHECK  = "evening_check"
EVENING_SKIP   = "evening_skip"

users: dict[int, dict] = {}
TZ_ALMATY = timezone(timedelta(hours=5))

DIAGNOSIS_MAP = {
    "гипертония": "hypertension",
    "диабет":     "diabetes",
    "екеуі де":   "both",
    "оба":        "both",
}

def t(chat_id: int, key: str) -> str:
    lang = users.get(chat_id, {}).get("lang", "ru")
    return TEXTS.get(lang, TEXTS["ru"]).get(key, key)

def mkb(*rows) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(btn) for btn in row] for row in rows],
        resize_keyboard=True, one_time_keyboard=True,
    )

def ikb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=label, callback_data=data) for label, data in row]
         for row in rows]
    )

def parse_bp(text: str) -> tuple[int, int]:
    parts = text.strip().replace(" ", "").split("/")
    if len(parts) != 2:
        raise ValueError
    sbp, dbp = int(parts[0]), int(parts[1])
    if not (50 <= sbp <= 300 and 30 <= dbp <= 200):
        raise ValueError
    return sbp, dbp

def is_yes(text: str) -> bool:
    return any(w in text.lower() for w in ["иә", "да", "yes"])

# Inline keyboard builders
def _sbp_kb(cid):
    o = t(cid, "other")
    return ikb(
        [("110","sbp:110"),("120","sbp:120"),("130","sbp:130"),("140","sbp:140")],
        [("150","sbp:150"),("160","sbp:160"),("170","sbp:170"),("180","sbp:180")],
        [("190+","sbp:190"),(o,"sbp:other")],
    )

def _dbp_kb(cid):
    o = t(cid, "other")
    return ikb(
        [("70","dbp:70"),("80","dbp:80"),("90","dbp:90"),("100","dbp:100")],
        [("110","dbp:110"),("120","dbp:120"),(o,"dbp:other")],
    )

def _pulse_kb(cid):
    o = t(cid, "other")
    return ikb(
        [("55","pulse:55"),("60","pulse:60"),("65","pulse:65"),("70","pulse:70")],
        [("75","pulse:75"),("80","pulse:80"),("85","pulse:85"),("90","pulse:90")],
        [("95","pulse:95"),("100","pulse:100"),(o,"pulse:other")],
    )

def _med_kb(cid):
    return ikb([(t(cid,"yes"),"med:yes"),(t(cid,"no"),"med:no")])

def _sym_kb(cid):
    return ikb(
        [(t(cid,"symptom_headache"),"sym:headache"),(t(cid,"symptom_dizziness"),"sym:dizziness")],
        [(t(cid,"symptom_chest_pain"),"sym:chest_pain"),(t(cid,"symptom_none"),"sym:none")],
    )

def _eve_med_kb(cid):
    return ikb([(t(cid,"yes"),"evening_med:yes"),(t(cid,"no"),"evening_med:no")])

def _skip_kb(cid):
    return ikb(
        [(t(cid,"skip_forgot"),"skip_reason:forgot")],
        [(t(cid,"skip_ran_out"),"skip_reason:ran_out")],
        [(t(cid,"skip_side_effects"),"skip_reason:side_effects")],
        [(t(cid,"skip_other"),"skip_reason:other")],
    )

# /start
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"START | chat_id={chat_id}")
    try:
        patient = await api_client.get_patient(chat_id)
    except Exception as e:
        logger.warning(f"START | API unreachable: {e}")
        patient = None

    if patient:
        users[chat_id] = {
            "state": None, "lang": patient.get("language","ru"),
            "patient_id": patient["id"], "diagnosis_type": patient["diagnosis"],
            "temp": {}, "daily_logs": [],
        }
        await update.message.reply_text(t(chat_id,"idle_hint"), reply_markup=ReplyKeyboardRemove())
        return

    users[chat_id] = {"state": LANG, "temp": {}}
    await update.message.reply_text(
        TEXTS["kz"]["choose_lang"],
        reply_markup=mkb(["🇰🇿 Қазақша","🇷🇺 Русский"]),
    )

# /check
async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in users:
        await update.message.reply_text("Для начала введите /start")
        return
    user = users[chat_id]
    if user.get("state") not in (None, EVENING_CHECK, EVENING_SKIP):
        await update.message.reply_text(t(chat_id,"already_in_flow"))
        return
    user["state"] = None
    await _start_daily_check_for(context.bot, chat_id, user)

# /chart
async def cmd_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in users or not users[chat_id].get("patient_id"):
        await update.message.reply_text("Для начала введите /start")
        return
    patient_id = users[chat_id]["patient_id"]
    try:
        png_bytes = await api_client.get_chart(patient_id, limit=7)
        await update.message.reply_photo(
            photo=png_bytes,
            caption=t(chat_id, "chart_caption"),
        )
    except Exception as e:
        logger.error(f"CHART | {e}")
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status == 404:
            await update.message.reply_text(t(chat_id, "chart_no_data"))
        else:
            await update.message.reply_text(t(chat_id, "chart_error"))


# /report
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in users or not users[chat_id].get("patient_id"):
        await update.message.reply_text("Для начала введите /start")
        return
    patient_id = users[chat_id]["patient_id"]
    msg = await update.message.reply_text(t(chat_id,"report_generating"))
    try:
        pdf_bytes = await api_client.get_report(patient_id)
        await update.message.reply_document(
            document=pdf_bytes,
            filename="sympai_report.pdf",
            caption=t(chat_id,"report_ready"),
        )
        await msg.delete()
    except Exception as e:
        logger.error(f"REPORT | {e}")
        await msg.edit_text(t(chat_id,"report_error"))

# Registration
async def _lang(update, user, text):
    chat_id = update.effective_chat.id
    user["lang"] = "kz" if "Қазақша" in text else "ru"
    user["state"] = NAME
    await update.message.reply_text(t(chat_id,"ask_name"), reply_markup=ReplyKeyboardRemove())

async def _name(update, user, text):
    chat_id = update.effective_chat.id
    user["name"] = text
    user["state"] = AGE
    await update.message.reply_text(t(chat_id,"ask_age"))

async def _age(update, user, text):
    chat_id = update.effective_chat.id
    if not text.isdigit():
        await update.message.reply_text(t(chat_id,"invalid_number"))
        return
    user["age"] = int(text)
    user["state"] = DOCTOR
    try:
        doctors = await api_client.list_doctors()
    except Exception as e:
        logger.error(f"AGE | {e}")
        await update.message.reply_text(t(chat_id,"doctor_load_error"))
        user["state"] = AGE
        return
    if not doctors:
        await update.message.reply_text(t(chat_id,"doctor_load_error"))
        user["state"] = AGE
        return
    user["temp"]["doctors_map"] = {d["full_name"]: d["id"] for d in doctors}
    rows = [[name] for name in user["temp"]["doctors_map"]]
    await update.message.reply_text(t(chat_id,"ask_doctor"), reply_markup=mkb(*rows))

async def _doctor(update, user, text):
    chat_id = update.effective_chat.id
    doctors_map = user["temp"].get("doctors_map", {})
    doctor_id = doctors_map.get(text)
    if not doctor_id:
        rows = [[name] for name in doctors_map.keys()]
        await update.message.reply_text(t(chat_id,"ask_doctor"), reply_markup=mkb(*rows))
        return
    user["doctor_id"] = doctor_id
    user["state"] = DIAGNOSIS
    await update.message.reply_text(t(chat_id,"ask_diagnosis"), reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("👇", reply_markup=ikb(
        [(t(chat_id,"diagnosis_hypertension"),"diag:hypertension")],
        [(t(chat_id,"diagnosis_diabetes"),"diag:diabetes")],
        [(t(chat_id,"diagnosis_both"),"diag:both")],
    ))

async def _diagnosis(update, user, text):
    chat_id = update.effective_chat.id
    diagnosis_type = DIAGNOSIS_MAP.get(text.lower())
    if not diagnosis_type:
        return
    await _set_diagnosis(chat_id, user, diagnosis_type, update.message.reply_text)

async def _set_diagnosis(chat_id, user, diagnosis_type, reply_fn):
    user["diagnosis_type"] = diagnosis_type
    user["state"] = INIT_BP1
    user["temp"]["bp_history"] = []
    await reply_fn(t(chat_id,"ask_bp_1"))

async def _init_bp(update, user, text, next_state, next_key):
    chat_id = update.effective_chat.id
    try:
        sbp, dbp = parse_bp(text)
    except (ValueError, IndexError):
        await update.message.reply_text(t(chat_id,"invalid_bp"))
        return
    user["temp"]["bp_history"].append({"sbp": sbp, "dbp": dbp})
    user["state"] = next_state
    await update.message.reply_text(t(chat_id, next_key))

async def _init_bp1(update, user, text): await _init_bp(update, user, text, INIT_BP2, "ask_bp_2")
async def _init_bp2(update, user, text): await _init_bp(update, user, text, INIT_BP3, "ask_bp_3")
async def _init_bp3(update, user, text): await _init_bp(update, user, text, INIT_MED,  "ask_medicines")

async def _init_med(update, user, text):
    chat_id = update.effective_chat.id
    user["medicines"] = text
    user["state"] = INIT_COMORBID
    await update.message.reply_text(t(chat_id,"ask_comorbidities"))

async def _init_comorbid(update, user, text):
    chat_id = update.effective_chat.id
    payload = {
        "full_name":          user["name"],
        "age":                user["age"],
        "telegram_id":        chat_id,
        "doctor_id":          user["doctor_id"],
        "diagnosis":          user["diagnosis_type"],
        "current_medication": user.get("medicines"),
        "language":           user["lang"],
        "comorbidities":      text if text.lower() not in ["жоқ","нет","no"] else None,
    }
    try:
        patient = await api_client.create_patient(payload)
        user["patient_id"] = patient["id"]
        user["temp"].pop("bp_history", None)
        user["state"] = None
        await api_client.set_patient_state(patient["id"], "idle")
        await update.message.reply_text(t(chat_id,"registration_complete"))
    except Exception as e:
        logger.error(f"COMORBID | {e}")
        await update.message.reply_text(t(chat_id,"registration_error"))
        user["state"] = None

# Daily check
async def _start_daily_check_for(bot, chat_id, user):
    if not user.get("patient_id"):
        return
    user["state"] = DAILY_SBP
    user["temp"] = {"date": datetime.now(TZ_ALMATY).strftime("%Y-%m-%d")}
    try:
        await api_client.set_patient_state(user["patient_id"], "in_check")
    except Exception as e:
        logger.warning(f"DAILY_START | {e}")
    await bot.send_message(chat_id, t(chat_id,"daily_intro"))
    await bot.send_message(chat_id, t(chat_id,"ask_sbp"), reply_markup=_sbp_kb(chat_id))

async def _daily_sbp(update, user, text):
    chat_id = update.effective_chat.id
    if not text.isdigit() or not (50 <= int(text) <= 300):
        await update.message.reply_text(t(chat_id,"invalid_number"))
        return
    user["temp"]["sbp"] = int(text)
    user["state"] = DAILY_DBP
    await update.message.reply_text(t(chat_id,"ask_dbp"), reply_markup=_dbp_kb(chat_id))

async def _daily_dbp(update, user, text):
    chat_id = update.effective_chat.id
    if not text.isdigit() or not (30 <= int(text) <= 200):
        await update.message.reply_text(t(chat_id,"invalid_number"))
        return
    user["temp"]["dbp"] = int(text)
    user["state"] = DAILY_PULSE
    await update.message.reply_text(t(chat_id,"ask_pulse"), reply_markup=_pulse_kb(chat_id))

async def _daily_pulse(update, user, text):
    chat_id = update.effective_chat.id
    if not text.isdigit() or not (30 <= int(text) <= 250):
        await update.message.reply_text(t(chat_id,"invalid_number"))
        return
    user["temp"]["pulse"] = int(text)
    await _after_pulse(chat_id, user, update.message.reply_text)

async def _after_pulse(chat_id, user, reply_fn):
    if user.get("diagnosis_type") in ("diabetes","both"):
        user["state"] = DAILY_GLUCOSE
        await reply_fn(t(chat_id,"ask_glucose"))
    else:
        user["state"] = DAILY_MED
        await reply_fn(t(chat_id,"ask_med_taken"), reply_markup=_med_kb(chat_id))

async def _daily_glucose(update, user, text):
    chat_id = update.effective_chat.id
    try:
        glucose = float(text.replace(",","."))
        if not (1.0 <= glucose <= 30.0):
            raise ValueError
    except ValueError:
        await update.message.reply_text(t(chat_id,"invalid_number"))
        return
    user["temp"]["glucose"] = glucose
    user["state"] = DAILY_MED
    await update.message.reply_text(t(chat_id,"ask_med_taken"), reply_markup=_med_kb(chat_id))

async def _daily_med(update, user, text):
    chat_id = update.effective_chat.id
    user["temp"]["med_taken"] = is_yes(text)
    user["state"] = DAILY_SYMPTOMS
    await update.message.reply_text(t(chat_id,"ask_symptoms"), reply_markup=_sym_kb(chat_id))

SYMPTOM_KEYS = {
    "бас ауру":       "headache",
    "головная боль":  "headache",
    "көз қарауыту":   "dizziness",
    "головокружение": "dizziness",
    "кеуде ауру":     "chest_pain",
    "боль в груди":   "chest_pain",
}

async def _daily_symptoms(update, user, text):
    chat_id = update.effective_chat.id
    tl = text.lower()
    symptoms = [eng for phrase, eng in SYMPTOM_KEYS.items() if phrase in tl]
    await _do_submit(chat_id, user, symptoms, update.message.reply_text, update.get_bot())

async def _do_submit(chat_id, user, symptoms, reply_fn, bot=None):
    if not user.get("patient_id"):
        user["state"] = None
        await reply_fn(t(chat_id,"registration_error"), reply_markup=ReplyKeyboardRemove())
        return
    payload = {
        "patient_id":       user["patient_id"],
        "reading_date":     datetime.now(TZ_ALMATY).strftime("%Y-%m-%d"),
        "sbp":              user["temp"]["sbp"],
        "dbp":              user["temp"]["dbp"],
        "pulse":            user["temp"]["pulse"],
        "glucose":          user["temp"].get("glucose"),
        "medication_taken": user["temp"]["med_taken"],
        "symptoms":         symptoms if symptoms else None,
    }
    send_chart = False
    try:
        reading = await api_client.submit_reading(payload)
        risk = reading.get("risk_level","low")
        user["last_reading_id"] = reading.get("id")
        await api_client.set_patient_state(user["patient_id"], "idle")
        user["readings_count"] = user.get("readings_count", 0) + 1
        if user["readings_count"] % 7 == 0:
            send_chart = True
        logger.info(f"DAILY_DONE | chat_id={chat_id} | risk={risk.upper()} | count={user['readings_count']}")
    except Exception as e:
        logger.error(f"DAILY_SUBMIT | {e}")
        risk = "low"
    user["state"] = None
    await reply_fn(t(chat_id, f"risk_{risk}"), reply_markup=ReplyKeyboardRemove())
    if send_chart and bot:
        try:
            png_bytes = await api_client.get_chart(user["patient_id"], limit=7)
            await bot.send_photo(chat_id, photo=png_bytes, caption=t(chat_id, "chart_caption"))
        except Exception as e:
            logger.warning(f"AUTO_CHART | {e}")

# Callback handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data
    if chat_id not in users:
        return
    user  = users[chat_id]
    state = user.get("state")
    key, _, value = data.partition(":")

    async def edit(text, **kw):
        try:
            await query.edit_message_text(text, **kw)
        except Exception:
            pass

    async def send(text, **kw):
        await context.bot.send_message(chat_id, text, **kw)

    if key == "diag" and state == DIAGNOSIS:
        labels = {"hypertension": t(chat_id,"diagnosis_hypertension"),
                  "diabetes":     t(chat_id,"diagnosis_diabetes"),
                  "both":         t(chat_id,"diagnosis_both")}
        await edit(f"✓ {labels.get(value, value)}")
        await _set_diagnosis(chat_id, user, value, send)

    elif key == "sbp" and state == DAILY_SBP:
        if value == "other":
            await edit(t(chat_id,"ask_sbp_other"))
        else:
            n = int(value)
            user["temp"]["sbp"] = n
            user["state"] = DAILY_DBP
            await edit(f"✓ СБД: {n} мм рт.ст.")
            await send(t(chat_id,"ask_dbp"), reply_markup=_dbp_kb(chat_id))

    elif key == "dbp" and state == DAILY_DBP:
        if value == "other":
            await edit(t(chat_id,"ask_dbp_other"))
        else:
            n = int(value)
            user["temp"]["dbp"] = n
            user["state"] = DAILY_PULSE
            await edit(f"✓ ДБД: {n} мм рт.ст.")
            await send(t(chat_id,"ask_pulse"), reply_markup=_pulse_kb(chat_id))

    elif key == "pulse" and state == DAILY_PULSE:
        if value == "other":
            await edit(t(chat_id,"ask_pulse_other"))
        else:
            n = int(value)
            user["temp"]["pulse"] = n
            await edit(f"✓ Пульс: {n} уд/мин")
            await _after_pulse(chat_id, user, send)

    elif key == "med" and state == DAILY_MED:
        taken = (value == "yes")
        user["temp"]["med_taken"] = taken
        user["state"] = DAILY_SYMPTOMS
        await edit(f"✓ {t(chat_id,'yes') if taken else t(chat_id,'no')}")
        await send(t(chat_id,"ask_symptoms"), reply_markup=_sym_kb(chat_id))

    elif key == "sym" and state == DAILY_SYMPTOMS:
        symptoms = [] if value == "none" else [value]
        sym_labels = {"headache": t(chat_id,"symptom_headache"),
                      "dizziness": t(chat_id,"symptom_dizziness"),
                      "chest_pain": t(chat_id,"symptom_chest_pain"),
                      "none": t(chat_id,"symptom_none")}
        await edit(f"✓ {sym_labels.get(value, value)}")
        await _do_submit(chat_id, user, symptoms, send, context.bot)

    elif key == "evening_med" and state == EVENING_CHECK:
        if value == "yes":
            user["state"] = None
            await edit(t(chat_id,"evening_med_confirmed"))
        else:
            user["state"] = EVENING_SKIP
            await edit(t(chat_id,"ask_skip_reason"), reply_markup=_skip_kb(chat_id))

    elif key == "skip_reason" and state == EVENING_SKIP:
        user["state"] = None
        await edit(t(chat_id,"skip_reason_saved"))
        reading_id = user.get("last_reading_id")
        if reading_id:
            try:
                await api_client.set_skip_reason(reading_id, value)
            except Exception as e:
                logger.warning(f"SKIP_REASON | {e}")

# Cron jobs
async def daily_check_job(context: CallbackContext):
    logger.info("CRON 08:00 | Daily check")
    try:
        idle_patients = await api_client.get_idle_patients()
    except Exception as e:
        logger.error(f"CRON | {e}")
        idle_patients = [{"telegram_id": cid} for cid, u in users.items()
                         if u.get("state") is None and u.get("patient_id")]
    for patient in idle_patients:
        tg_id = patient.get("telegram_id")
        if tg_id and tg_id in users and users[tg_id].get("state") is None:
            await _start_daily_check_for(context.bot, tg_id, users[tg_id])

async def med_reminder_job(context: CallbackContext):
    logger.info("CRON 09:00 | Medication reminder")
    count = 0
    for chat_id, user in users.items():
        if not user.get("patient_id"):
            continue
        try:
            await context.bot.send_message(chat_id, t(chat_id,"med_reminder"))
            count += 1
        except Exception as e:
            logger.warning(f"MED_REMINDER | {chat_id}: {e}")
    logger.info(f"CRON 09:00 | Reminded {count} patient(s)")

async def evening_check_job(context: CallbackContext):
    logger.info("CRON 20:00 | Evening compliance check")
    today = datetime.now(TZ_ALMATY).strftime("%Y-%m-%d")
    count = 0
    for chat_id, user in users.items():
        if user.get("state") is not None or not user.get("patient_id"):
            continue
        if user.get("evening_checked_date") == today:
            continue
        user["state"] = EVENING_CHECK
        user["evening_checked_date"] = today
        try:
            await context.bot.send_message(
                chat_id, t(chat_id,"evening_ask_med"),
                reply_markup=_eve_med_kb(chat_id),
            )
            count += 1
        except Exception as e:
            user["state"] = None
            logger.warning(f"EVENING | {chat_id}: {e}")
    logger.info(f"CRON 20:00 | Checked {count} patient(s)")

# Message router
ROUTES = {
    LANG: _lang, NAME: _name, AGE: _age, DOCTOR: _doctor,
    DIAGNOSIS: _diagnosis,
    INIT_BP1: _init_bp1, INIT_BP2: _init_bp2, INIT_BP3: _init_bp3,
    INIT_MED: _init_med, INIT_COMORBID: _init_comorbid,
    DAILY_SBP: _daily_sbp, DAILY_DBP: _daily_dbp, DAILY_PULSE: _daily_pulse,
    DAILY_GLUCOSE: _daily_glucose, DAILY_MED: _daily_med,
    DAILY_SYMPTOMS: _daily_symptoms,
}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text    = update.message.text.strip()
    print(f"[{datetime.now(TZ_ALMATY).strftime('%H:%M:%S')}] {chat_id}: {text!r}")

    if chat_id not in users:
        await update.message.reply_text(
            "Botты бастау үшін /start деп жазыңыз\nДля начала введите /start"
        )
        return

    user  = users[chat_id]
    state = user.get("state")

    if state is None:
        await update.message.reply_text(t(chat_id,"idle_hint"))
        return

    if state in (EVENING_CHECK, EVENING_SKIP):
        return  # inline-only states

    handler = ROUTES.get(state)
    if handler:
        await handler(update, user, text)

# Startup
async def on_startup(app) -> None:
    try:
        patients = await api_client.get_all_patients()
    except Exception as e:
        logger.warning(f"STARTUP | {e}")
        return
    for p in patients:
        tg_id = p.get("telegram_id")
        if not tg_id:
            continue
        users[tg_id] = {
            "state": None, "patient_id": p["id"],
            "lang": p.get("language","ru"),
            "diagnosis_type": p.get("diagnosis"), "temp": {},
        }
    logger.info(f"STARTUP | Loaded {len([p for p in patients if p.get('telegram_id')])} patient(s)")

def main():
    logger.info("SympAI Bot starting...")
    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("check",  cmd_check))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("chart",  cmd_chart))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_daily(daily_check_job,  time=dtime(hour=8,  minute=0, tzinfo=TZ_ALMATY), name="daily_check")
    app.job_queue.run_daily(med_reminder_job, time=dtime(hour=9,  minute=0, tzinfo=TZ_ALMATY), name="med_reminder")
    app.job_queue.run_daily(evening_check_job,time=dtime(hour=20, minute=0, tzinfo=TZ_ALMATY), name="evening_check")
    logger.info("Crons: 08:00 daily · 09:00 med reminder · 20:00 evening check")
    app.run_polling()

if __name__ == "__main__":
    main()
