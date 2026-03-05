import os
import logging
from datetime import datetime, time as dtime, timezone, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
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

# ── States ────────────────────────────────────────────────────────────────────
LANG          = "lang"
NAME          = "name"
AGE           = "age"
DOCTOR        = "doctor"
DIAGNOSIS     = "diagnosis"
INIT_BP1      = "init_bp1"
INIT_BP2      = "init_bp2"
INIT_BP3      = "init_bp3"
INIT_MED      = "init_med"
INIT_COMORBID = "init_comorbid"
DAILY_SBP     = "daily_sbp"
DAILY_DBP     = "daily_dbp"
DAILY_PULSE   = "daily_pulse"
DAILY_GLUCOSE = "daily_glucose"
DAILY_MED     = "daily_med"
DAILY_SYMPTOMS = "daily_symptoms"

# ── In-memory storage ─────────────────────────────────────────────────────────
users: dict[int, dict] = {}  # chat_id -> user data

# ── Helpers ───────────────────────────────────────────────────────────────────
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
        resize_keyboard=True,
        one_time_keyboard=True,
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

# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"START | chat_id={chat_id}")

    # Check if already registered
    try:
        patient = await api_client.get_patient(chat_id)
    except Exception as e:
        logger.warning(f"START | API unreachable: {e}")
        patient = None

    if patient:
        users[chat_id] = {
            "state": None,
            "lang": patient.get("language", "ru"),
            "patient_id": patient["id"],
            "diagnosis_type": patient["diagnosis"],
            "temp": {},
            "daily_logs": [],
        }
        logger.info(f"START | Already registered patient_id={patient['id']}")
        await update.message.reply_text(
            t(chat_id, "idle_hint"), reply_markup=ReplyKeyboardRemove()
        )
        return

    users[chat_id] = {"state": LANG, "temp": {}}
    await update.message.reply_text(
        TEXTS["kz"]["choose_lang"],
        reply_markup=mkb(["🇰🇿 Қазақша", "🇷🇺 Русский"]),
    )

# ── /check (manual daily trigger for testing) ─────────────────────────────────
async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in users:
        await update.message.reply_text("Для начала введите /start")
        return
    user = users[chat_id]
    if user.get("state") is not None:
        await update.message.reply_text(t(chat_id, "already_in_flow"))
        return
    await _start_daily_check_for(context.bot, chat_id, user)

# ── Registration handlers ─────────────────────────────────────────────────────
async def _lang(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    user["lang"] = "kz" if "Қазақша" in text else "ru"
    user["state"] = NAME
    logger.info(f"LANG | chat_id={chat_id} | lang={user['lang']}")
    await update.message.reply_text(t(chat_id, "ask_name"), reply_markup=ReplyKeyboardRemove())

async def _name(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    user["name"] = text
    user["state"] = AGE
    logger.info(f"NAME | chat_id={chat_id} | name={text!r}")
    await update.message.reply_text(t(chat_id, "ask_age"))

async def _age(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    if not text.isdigit():
        await update.message.reply_text(t(chat_id, "invalid_number"))
        return
    user["age"] = int(text)
    user["state"] = DOCTOR

    # Load doctors from API and show as keyboard
    try:
        doctors = await api_client.list_doctors()
    except Exception as e:
        logger.error(f"AGE | Failed to load doctors: {e}")
        await update.message.reply_text(t(chat_id, "doctor_load_error"))
        user["state"] = AGE  # stay, let user retry
        return

    if not doctors:
        logger.error("AGE | No doctors in DB")
        await update.message.reply_text(t(chat_id, "doctor_load_error"))
        user["state"] = AGE
        return

    # Store name→id map for lookup in _doctor()
    user["temp"]["doctors_map"] = {d["full_name"]: d["id"] for d in doctors}
    names = [d["full_name"] for d in doctors]

    # Build keyboard rows of 1
    rows = [[name] for name in names]
    logger.info(f"AGE | chat_id={chat_id} | age={text} | {len(doctors)} doctors loaded")
    await update.message.reply_text(t(chat_id, "ask_doctor"), reply_markup=mkb(*rows))

async def _doctor(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    doctors_map: dict = user["temp"].get("doctors_map", {})
    doctor_id = doctors_map.get(text)

    if not doctor_id:
        # Show keyboard again if invalid selection
        rows = [[name] for name in doctors_map.keys()]
        await update.message.reply_text(
            t(chat_id, "ask_doctor"), reply_markup=mkb(*rows)
        )
        return

    user["doctor_id"] = doctor_id
    user["state"] = DIAGNOSIS
    logger.info(f"DOCTOR | chat_id={chat_id} | doctor_id={doctor_id}")
    await update.message.reply_text(
        t(chat_id, "ask_diagnosis"),
        reply_markup=mkb([
            t(chat_id, "diagnosis_hypertension"),
            t(chat_id, "diagnosis_diabetes"),
            t(chat_id, "diagnosis_both"),
        ]),
    )

async def _diagnosis(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    diagnosis_type = DIAGNOSIS_MAP.get(text.lower())
    if not diagnosis_type:
        await update.message.reply_text(
            t(chat_id, "ask_diagnosis"),
            reply_markup=mkb([
                t(chat_id, "diagnosis_hypertension"),
                t(chat_id, "diagnosis_diabetes"),
                t(chat_id, "diagnosis_both"),
            ]),
        )
        return

    user["diagnosis_type"] = diagnosis_type
    user["state"] = INIT_BP1
    user["temp"]["bp_history"] = []
    logger.info(f"DIAGNOSIS | chat_id={chat_id} | type={diagnosis_type}")
    await update.message.reply_text(t(chat_id, "ask_bp_1"), reply_markup=ReplyKeyboardRemove())

async def _init_bp(update: Update, user: dict, text: str, next_state: str, next_key: str):
    chat_id = update.effective_chat.id
    try:
        sbp, dbp = parse_bp(text)
    except (ValueError, IndexError):
        await update.message.reply_text(t(chat_id, "invalid_bp"))
        return
    user["temp"]["bp_history"].append({"sbp": sbp, "dbp": dbp})
    user["state"] = next_state
    logger.info(f"INIT_BP | chat_id={chat_id} | bp={sbp}/{dbp} | next={next_state}")
    await update.message.reply_text(t(chat_id, next_key))

async def _init_bp1(update: Update, user: dict, text: str):
    await _init_bp(update, user, text, INIT_BP2, "ask_bp_2")

async def _init_bp2(update: Update, user: dict, text: str):
    await _init_bp(update, user, text, INIT_BP3, "ask_bp_3")

async def _init_bp3(update: Update, user: dict, text: str):
    await _init_bp(update, user, text, INIT_MED, "ask_medicines")

async def _init_med(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    user["medicines"] = text
    user["state"] = INIT_COMORBID
    logger.info(f"MEDICINES | chat_id={chat_id} | {text!r}")
    await update.message.reply_text(t(chat_id, "ask_comorbidities"))

async def _init_comorbid(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    user["comorbidities"] = text

    payload = {
        "full_name":          user["name"],
        "age":                user["age"],
        "telegram_id":        chat_id,
        "doctor_id":          user["doctor_id"],
        "diagnosis":          user["diagnosis_type"],
        "current_medication": user.get("medicines"),
        "language":           user["lang"],
        "comorbidities":      text if text.lower() not in ["жоқ", "нет", "no"] else None,
    }

    try:
        patient = await api_client.create_patient(payload)
        user["patient_id"] = patient["id"]
        user["temp"].pop("bp_history", None)
        user["state"] = None
        # Sync idle state to API so cron can find this patient
        await api_client.set_patient_state(patient["id"], "idle")
        logger.info(f"REGISTERED | chat_id={chat_id} | patient_id={patient['id']}")
        await update.message.reply_text(t(chat_id, "registration_complete"))
    except Exception as e:
        logger.error(f"COMORBID | create_patient failed: {e}")
        await update.message.reply_text(t(chat_id, "registration_error"))
        user["state"] = None  # reset so user can /start again

# ── Daily check cron ──────────────────────────────────────────────────────────
async def _start_daily_check_for(bot, chat_id: int, user: dict):
    if not user.get("patient_id"):
        logger.warning(f"DAILY_START | Skipping chat_id={chat_id} — no patient_id (registration incomplete)")
        return
    user["state"] = DAILY_SBP
    user["temp"] = {"date": datetime.now(TZ_ALMATY).strftime("%Y-%m-%d")}
    # Mark in_check so cron doesn't trigger this patient again today
    try:
        await api_client.set_patient_state(user["patient_id"], "in_check")
    except Exception as e:
        logger.warning(f"DAILY_START | Could not set state in_check for {user['patient_id']}: {e}")
    logger.info(f"DAILY_START | chat_id={chat_id} | patient_id={user['patient_id']}")
    await bot.send_message(chat_id, t(chat_id, "daily_intro"))
    await bot.send_message(chat_id, t(chat_id, "ask_sbp"))

async def daily_check_job(context: CallbackContext):
    logger.info("CRON | Daily check triggered")
    try:
        idle_patients = await api_client.get_idle_patients()
    except Exception as e:
        logger.error(f"CRON | Failed to fetch idle patients: {e}")
        # Fall back to in-memory
        idle_patients = []
        for cid, u in users.items():
            if u.get("state") is None and u.get("patient_id"):
                idle_patients.append({"telegram_id": cid})

    logger.info(f"CRON | {len(idle_patients)} idle patient(s) to notify")
    for patient in idle_patients:
        tg_id = patient.get("telegram_id")
        if not tg_id or tg_id not in users:
            continue
        user = users[tg_id]
        if user.get("state") is None:
            await _start_daily_check_for(context.bot, tg_id, user)

# ── Daily check handlers ──────────────────────────────────────────────────────
async def _daily_sbp(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    if not text.isdigit() or not (50 <= int(text) <= 300):
        await update.message.reply_text(t(chat_id, "invalid_number"))
        return
    user["temp"]["sbp"] = int(text)
    user["state"] = DAILY_DBP
    logger.info(f"DAILY_SBP | chat_id={chat_id} | sbp={text}")
    await update.message.reply_text(t(chat_id, "ask_dbp"))

async def _daily_dbp(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    if not text.isdigit() or not (30 <= int(text) <= 200):
        await update.message.reply_text(t(chat_id, "invalid_number"))
        return
    user["temp"]["dbp"] = int(text)
    user["state"] = DAILY_PULSE
    logger.info(f"DAILY_DBP | chat_id={chat_id} | dbp={text}")
    await update.message.reply_text(t(chat_id, "ask_pulse"))

async def _daily_pulse(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    if not text.isdigit() or not (30 <= int(text) <= 250):
        await update.message.reply_text(t(chat_id, "invalid_number"))
        return
    user["temp"]["pulse"] = int(text)

    # Ask glucose for diabetes/both patients
    if user.get("diagnosis_type") in ("diabetes", "both"):
        user["state"] = DAILY_GLUCOSE
        logger.info(f"DAILY_PULSE | chat_id={chat_id} | pulse={text} | next=glucose")
        await update.message.reply_text(t(chat_id, "ask_glucose"))
    else:
        user["state"] = DAILY_MED
        logger.info(f"DAILY_PULSE | chat_id={chat_id} | pulse={text} | next=med")
        await update.message.reply_text(
            t(chat_id, "ask_med_taken"),
            reply_markup=mkb([t(chat_id, "yes"), t(chat_id, "no")]),
        )

async def _daily_glucose(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    try:
        glucose = float(text.replace(",", "."))
        if not (1.0 <= glucose <= 30.0):
            raise ValueError
    except ValueError:
        await update.message.reply_text(t(chat_id, "invalid_number"))
        return
    user["temp"]["glucose"] = glucose
    user["state"] = DAILY_MED
    logger.info(f"DAILY_GLUCOSE | chat_id={chat_id} | glucose={glucose}")
    await update.message.reply_text(
        t(chat_id, "ask_med_taken"),
        reply_markup=mkb([t(chat_id, "yes"), t(chat_id, "no")]),
    )

async def _daily_med(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    user["temp"]["med_taken"] = is_yes(text)
    user["state"] = DAILY_SYMPTOMS
    logger.info(f"DAILY_MED | chat_id={chat_id} | taken={user['temp']['med_taken']}")
    await update.message.reply_text(
        t(chat_id, "ask_symptoms"),
        reply_markup=mkb(
            [t(chat_id, "symptom_headache"), t(chat_id, "symptom_dizziness")],
            [t(chat_id, "symptom_chest_pain"), t(chat_id, "symptom_none")],
        ),
    )

SYMPTOM_KEYS = {
    "бас ауру":      "headache",
    "головная боль": "headache",
    "көз қарауыту":  "dizziness",
    "головокружение":"dizziness",
    "кеуде ауру":    "chest_pain",
    "боль в груди":  "chest_pain",
}

async def _daily_symptoms(update: Update, user: dict, text: str):
    chat_id = update.effective_chat.id
    tl = text.lower()
    symptoms = [eng for phrase, eng in SYMPTOM_KEYS.items() if phrase in tl]

    if not user.get("patient_id"):
        logger.error(f"DAILY_SYMPTOMS | No patient_id for chat_id={chat_id} — skipping submit")
        user["state"] = None
        await update.message.reply_text(t(chat_id, "registration_error"), reply_markup=ReplyKeyboardRemove())
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

    try:
        reading = await api_client.submit_reading(payload)
        risk = reading.get("risk_level", "low")
        logger.info(f"DAILY_DONE | chat_id={chat_id} | symptoms={symptoms} | risk={risk.upper()}")
        # Reset to idle so cron picks this patient up tomorrow
        await api_client.set_patient_state(user["patient_id"], "idle")
    except Exception as e:
        logger.error(f"DAILY_SYMPTOMS | submit_reading failed: {e}")
        risk = "low"  # show neutral response on API failure

    user["state"] = None

    await update.message.reply_text(
        t(chat_id, f"risk_{risk}"),
        reply_markup=ReplyKeyboardRemove(),
    )

# ── Main message router ───────────────────────────────────────────────────────
ROUTES = {
    LANG:          _lang,
    NAME:          _name,
    AGE:           _age,
    DOCTOR:        _doctor,
    DIAGNOSIS:     _diagnosis,
    INIT_BP1:      _init_bp1,
    INIT_BP2:      _init_bp2,
    INIT_BP3:      _init_bp3,
    INIT_MED:      _init_med,
    INIT_COMORBID: _init_comorbid,
    DAILY_SBP:     _daily_sbp,
    DAILY_DBP:     _daily_dbp,
    DAILY_PULSE:   _daily_pulse,
    DAILY_GLUCOSE: _daily_glucose,
    DAILY_MED:     _daily_med,
    DAILY_SYMPTOMS:_daily_symptoms,
}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    print(f"[{datetime.now(TZ_ALMATY).strftime('%H:%M:%S')}] {chat_id}: {text!r}")

    if chat_id not in users:
        await update.message.reply_text(
            "Botты бастау үшін /start деп жазыңыз\nДля начала введите /start"
        )
        return

    user = users[chat_id]
    state = user.get("state")

    if state is None:
        await update.message.reply_text(t(chat_id, "idle_hint"))
        return

    handler = ROUTES.get(state)
    if handler:
        await handler(update, user, text)

# ── Startup: reload patients from API ────────────────────────────────────────
async def on_startup(app) -> None:
    """Populate in-memory users dict from API on bot start."""
    try:
        patients = await api_client.get_all_patients()
    except Exception as e:
        logger.warning(f"STARTUP | Could not load patients from API: {e}")
        return

    for p in patients:
        tg_id = p.get("telegram_id")
        if not tg_id:
            continue
        users[tg_id] = {
            "state":          None,
            "patient_id":     p["id"],
            "lang":           p.get("language", "ru"),
            "diagnosis_type": p.get("diagnosis"),
            "temp":           {},
        }

    logger.info(f"STARTUP | Loaded {len([p for p in patients if p.get('telegram_id')])} patient(s) into memory")

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  SympAI Hypertension Bot starting...")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Daily cron at 08:00 Almaty time
    app.job_queue.run_daily(
        daily_check_job,
        time=dtime(hour=8, minute=0, tzinfo=TZ_ALMATY),
        name="daily_check",
    )

    logger.info("Daily check scheduled at 08:00 Almaty (UTC+5)")
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
