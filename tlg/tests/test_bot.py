"""
Bot test suite — no Telegram server or API required.
All api_client calls and Telegram Update objects are mocked.

Run:
    cd tlg
    pip install pytest pytest-asyncio
    pytest tests/test_bot.py -v
"""
import sys
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

# Add tlg/ to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import bot
from bot import (
    parse_bp, is_yes, t,
    _lang, _name, _age, _doctor, _diagnosis,
    _init_bp1, _init_bp2, _init_bp3, _init_med, _init_comorbid,
    _daily_sbp, _daily_dbp, _daily_pulse, _daily_glucose, _daily_med, _daily_symptoms,
    _start_daily_check_for, daily_check_job, on_startup, handle_message, cmd_start,
    LANG, NAME, AGE, DOCTOR, DIAGNOSIS,
    INIT_BP1, INIT_BP2, INIT_BP3, INIT_MED, INIT_COMORBID,
    DAILY_SBP, DAILY_DBP, DAILY_PULSE, DAILY_GLUCOSE, DAILY_MED, DAILY_SYMPTOMS,
    users,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

CHAT_ID = 999

def make_update(text: str, chat_id: int = CHAT_ID):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update

def make_user(
    state=None,
    lang="ru",
    diagnosis="hypertension",
    patient_id="pat-1",
    doctor_id="doc-1",
    **extra,
):
    return {
        "state": state,
        "lang": lang,
        "diagnosis_type": diagnosis,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "temp": {},
        **extra,
    }

def setup_user(state=None, **kwargs):
    """Put a user into the global users dict and return it."""
    u = make_user(state=state, **kwargs)
    users[CHAT_ID] = u
    return u

def teardown_user():
    users.pop(CHAT_ID, None)


# ── 1. Helpers ────────────────────────────────────────────────────────────────

class TestParseBP:
    def test_valid(self):
        assert parse_bp("130/80") == (130, 80)

    def test_valid_with_spaces(self):
        assert parse_bp("130 / 80") == (130, 80)

    def test_sbp_lower_boundary(self):
        assert parse_bp("50/80") == (50, 80)

    def test_sbp_upper_boundary(self):
        assert parse_bp("300/80") == (300, 80)

    def test_sbp_too_low(self):
        with pytest.raises(ValueError):
            parse_bp("49/80")

    def test_sbp_too_high(self):
        with pytest.raises(ValueError):
            parse_bp("301/80")

    def test_dbp_lower_boundary(self):
        assert parse_bp("130/30") == (130, 30)

    def test_dbp_upper_boundary(self):
        assert parse_bp("130/200") == (130, 200)

    def test_dbp_too_low(self):
        with pytest.raises(ValueError):
            parse_bp("130/29")

    def test_dbp_too_high(self):
        with pytest.raises(ValueError):
            parse_bp("130/201")

    def test_wrong_separator(self):
        with pytest.raises((ValueError, IndexError)):
            parse_bp("130-80")

    def test_too_many_parts(self):
        with pytest.raises((ValueError, IndexError)):
            parse_bp("1/2/3")

    def test_single_value(self):
        with pytest.raises((ValueError, IndexError)):
            parse_bp("130")


class TestIsYes:
    def test_da(self):       assert is_yes("да") is True
    def test_iya(self):      assert is_yes("Иә") is True
    def test_yes(self):      assert is_yes("yes") is True
    def test_yes_upper(self):assert is_yes("YES") is True
    def test_net(self):      assert is_yes("нет") is False
    def test_no(self):       assert is_yes("no") is False
    def test_empty(self):    assert is_yes("") is False


class TestT:
    def setup_method(self):
        users[CHAT_ID] = {"lang": "ru"}

    def teardown_method(self):
        users.pop(CHAT_ID, None)

    def test_ru_key(self):
        assert t(CHAT_ID, "idle_hint") == "Для ежедневной проверки введите /check."

    def test_kz_key(self):
        users[CHAT_ID]["lang"] = "kz"
        assert t(CHAT_ID, "idle_hint") == "Күнделікті тексеруді бастау үшін /check деп жазыңыз."

    def test_missing_key_returns_key(self):
        result = t(CHAT_ID, "nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_unknown_chat_defaults_to_ru(self):
        result = t(99999, "idle_hint")
        assert "check" in result.lower()


# ── 2. /start ─────────────────────────────────────────────────────────────────

class TestCmdStart:
    def teardown_method(self):
        teardown_user()

    @pytest.mark.asyncio
    @patch("bot.api_client.get_patient", new_callable=AsyncMock)
    async def test_new_user_starts_registration(self, mock_get):
        mock_get.return_value = None
        update = make_update("/start")
        ctx = MagicMock()
        await cmd_start(update, ctx)
        assert users[CHAT_ID]["state"] == LANG
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.api_client.get_patient", new_callable=AsyncMock)
    async def test_registered_user_skips_registration(self, mock_get):
        mock_get.return_value = {
            "id": "pat-1", "language": "kz", "diagnosis": "hypertension"
        }
        update = make_update("/start")
        ctx = MagicMock()
        await cmd_start(update, ctx)
        assert users[CHAT_ID]["state"] is None
        assert users[CHAT_ID]["patient_id"] == "pat-1"
        assert users[CHAT_ID]["lang"] == "kz"

    @pytest.mark.asyncio
    @patch("bot.api_client.get_patient", new_callable=AsyncMock)
    async def test_api_unreachable_treats_as_new(self, mock_get):
        mock_get.side_effect = Exception("connection refused")
        update = make_update("/start")
        ctx = MagicMock()
        await cmd_start(update, ctx)  # should not raise
        assert users[CHAT_ID]["state"] == LANG


# ── 3. Registration flow ──────────────────────────────────────────────────────

class TestRegistration:
    def setup_method(self):
        setup_user(state=LANG)

    def teardown_method(self):
        teardown_user()

    @pytest.mark.asyncio
    async def test_lang_kz(self):
        u = users[CHAT_ID]
        await _lang(make_update("🇰🇿 Қазақша"), u, "🇰🇿 Қазақша")
        assert u["lang"] == "kz"
        assert u["state"] == NAME

    @pytest.mark.asyncio
    async def test_lang_ru(self):
        u = users[CHAT_ID]
        await _lang(make_update("🇷🇺 Русский"), u, "🇷🇺 Русский")
        assert u["lang"] == "ru"
        assert u["state"] == NAME

    @pytest.mark.asyncio
    async def test_name_stored(self):
        u = users[CHAT_ID]
        u["state"] = NAME
        await _name(make_update("Аскар Сейткали"), u, "Аскар Сейткали")
        assert u["name"] == "Аскар Сейткали"
        assert u["state"] == AGE

    @pytest.mark.asyncio
    async def test_age_non_digit_stays(self):
        u = users[CHAT_ID]
        u["state"] = AGE
        update = make_update("abc")
        with patch("bot.api_client.list_doctors", new_callable=AsyncMock):
            await _age(update, u, "abc")
        assert u["state"] == AGE
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.api_client.list_doctors", new_callable=AsyncMock)
    async def test_age_valid_loads_doctors(self, mock_list):
        mock_list.return_value = [{"full_name": "Dr. Asem", "id": "doc-1"}]
        u = users[CHAT_ID]
        u["state"] = AGE
        update = make_update("45")
        await _age(update, u, "45")
        assert u["age"] == 45
        assert u["state"] == DOCTOR
        assert u["temp"]["doctors_map"] == {"Dr. Asem": "doc-1"}

    @pytest.mark.asyncio
    @patch("bot.api_client.list_doctors", new_callable=AsyncMock)
    async def test_age_api_failure_stays(self, mock_list):
        mock_list.side_effect = Exception("API down")
        u = users[CHAT_ID]
        u["state"] = AGE
        update = make_update("45")
        await _age(update, u, "45")
        assert u["state"] == AGE

    @pytest.mark.asyncio
    async def test_doctor_invalid_reshows_keyboard(self):
        u = users[CHAT_ID]
        u["state"] = DOCTOR
        u["temp"]["doctors_map"] = {"Dr. Asem": "doc-1"}
        update = make_update("Unknown Doctor")
        await _doctor(update, u, "Unknown Doctor")
        assert u["state"] == DOCTOR
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_doctor_valid_stores_id(self):
        u = users[CHAT_ID]
        u["state"] = DOCTOR
        u["temp"]["doctors_map"] = {"Dr. Asem": "doc-1"}
        update = make_update("Dr. Asem")
        await _doctor(update, u, "Dr. Asem")
        assert u["doctor_id"] == "doc-1"
        assert u["state"] == DIAGNOSIS

    @pytest.mark.asyncio
    async def test_diagnosis_invalid_reshows(self):
        u = users[CHAT_ID]
        u["state"] = DIAGNOSIS
        update = make_update("RandomText")
        await _diagnosis(update, u, "RandomText")
        assert u["state"] == DIAGNOSIS

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text,expected", [
        ("Гипертония", "hypertension"),
        ("Диабет",     "diabetes"),
        ("Екеуі де",   "both"),
        ("Оба",        "both"),
    ])
    async def test_diagnosis_all_options(self, text, expected):
        u = users[CHAT_ID]
        u["state"] = DIAGNOSIS
        u["temp"]["bp_history"] = []
        await _diagnosis(make_update(text), u, text)
        assert u["diagnosis_type"] == expected
        assert u["state"] == INIT_BP1

    @pytest.mark.asyncio
    async def test_init_bp_valid(self):
        u = users[CHAT_ID]
        u["state"] = INIT_BP1
        u["temp"]["bp_history"] = []
        update = make_update("130/80")
        await _init_bp1(update, u, "130/80")
        assert u["temp"]["bp_history"] == [{"sbp": 130, "dbp": 80}]
        assert u["state"] == INIT_BP2

    @pytest.mark.asyncio
    async def test_init_bp_invalid_format(self):
        u = users[CHAT_ID]
        u["state"] = INIT_BP1
        u["temp"]["bp_history"] = []
        update = make_update("130-80")
        await _init_bp1(update, u, "130-80")
        assert u["state"] == INIT_BP1
        assert u["temp"]["bp_history"] == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bp,valid", [
        ("49/80",  False), ("50/80",  True), ("300/80", True), ("301/80", False),
        ("130/29", False), ("130/30", True), ("130/200",True), ("130/201",False),
    ])
    async def test_init_bp_boundaries(self, bp, valid):
        u = users[CHAT_ID]
        u["state"] = INIT_BP1
        u["temp"]["bp_history"] = []
        await _init_bp1(make_update(bp), u, bp)
        assert (len(u["temp"]["bp_history"]) == 1) == valid

    @pytest.mark.asyncio
    async def test_init_med_stores(self):
        u = users[CHAT_ID]
        u["state"] = INIT_MED
        await _init_med(make_update("Lisinopril 10mg"), u, "Lisinopril 10mg")
        assert u["medicines"] == "Lisinopril 10mg"
        assert u["state"] == INIT_COMORBID

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text,expected_none", [
        ("нет", True), ("жоқ", True), ("no", True), ("Диабет 2 тип", False),
    ])
    @patch("bot.api_client.create_patient", new_callable=AsyncMock)
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_init_comorbid_payload(self, mock_state, mock_create, text, expected_none):
        mock_create.return_value = {"id": "pat-new"}
        u = users[CHAT_ID]
        u.update({"state": INIT_COMORBID, "name": "Test", "age": 40,
                   "lang": "ru", "diagnosis_type": "hypertension",
                   "doctor_id": "doc-1", "medicines": "none"})
        u["temp"]["bp_history"] = []
        await _init_comorbid(make_update(text), u, text)
        payload = mock_create.call_args[0][0]
        if expected_none:
            assert payload["comorbidities"] is None
        else:
            assert payload["comorbidities"] == text

    @pytest.mark.asyncio
    @patch("bot.api_client.create_patient", new_callable=AsyncMock)
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_init_comorbid_success(self, mock_state, mock_create):
        mock_create.return_value = {"id": "pat-new"}
        u = users[CHAT_ID]
        u.update({"state": INIT_COMORBID, "name": "Test", "age": 40,
                   "lang": "ru", "diagnosis_type": "hypertension",
                   "doctor_id": "doc-1", "medicines": "none"})
        u["temp"]["bp_history"] = []
        await _init_comorbid(make_update("нет"), u, "нет")
        assert u["patient_id"] == "pat-new"
        assert u["state"] is None
        mock_state.assert_called_once_with("pat-new", "idle")

    @pytest.mark.asyncio
    @patch("bot.api_client.create_patient", new_callable=AsyncMock)
    async def test_init_comorbid_api_failure(self, mock_create):
        mock_create.side_effect = Exception("500")
        u = users[CHAT_ID]
        u.update({"state": INIT_COMORBID, "name": "Test", "age": 40,
                   "lang": "ru", "diagnosis_type": "hypertension",
                   "doctor_id": "doc-1", "medicines": "none"})
        u["temp"]["bp_history"] = []
        update = make_update("нет")
        await _init_comorbid(update, u, "нет")
        assert u["state"] is None
        update.message.reply_text.assert_called_once()


# ── 4. Daily check flow ───────────────────────────────────────────────────────

class TestDailyCheck:
    def setup_method(self):
        setup_user(state=DAILY_SBP)
        users[CHAT_ID]["temp"] = {}

    def teardown_method(self):
        teardown_user()

    @pytest.mark.asyncio
    async def test_sbp_non_digit(self):
        u = users[CHAT_ID]
        update = make_update("abc")
        await _daily_sbp(update, u, "abc")
        assert u["state"] == DAILY_SBP

    @pytest.mark.asyncio
    @pytest.mark.parametrize("val,valid", [
        ("49", False), ("50", True), ("300", True), ("301", False)
    ])
    async def test_sbp_boundaries(self, val, valid):
        u = users[CHAT_ID]
        u["state"] = DAILY_SBP
        await _daily_sbp(make_update(val), u, val)
        assert (u["state"] == DAILY_DBP) == valid

    @pytest.mark.asyncio
    @pytest.mark.parametrize("val,valid", [
        ("29", False), ("30", True), ("200", True), ("201", False)
    ])
    async def test_dbp_boundaries(self, val, valid):
        u = users[CHAT_ID]
        u["state"] = DAILY_DBP
        u["temp"]["sbp"] = 130
        await _daily_dbp(make_update(val), u, val)
        assert (u["state"] == DAILY_PULSE) == valid

    @pytest.mark.asyncio
    @pytest.mark.parametrize("val,valid", [
        ("29", False), ("30", True), ("250", True), ("251", False)
    ])
    async def test_pulse_boundaries(self, val, valid):
        u = users[CHAT_ID]
        u["state"] = DAILY_PULSE
        u["temp"] = {"sbp": 130, "dbp": 80}
        await _daily_pulse(make_update(val), u, val)
        if valid:
            assert u["state"] in (DAILY_GLUCOSE, DAILY_MED)
        else:
            assert u["state"] == DAILY_PULSE

    @pytest.mark.asyncio
    async def test_pulse_hypertension_skips_glucose(self):
        u = users[CHAT_ID]
        u["diagnosis_type"] = "hypertension"
        u["temp"] = {"sbp": 130, "dbp": 80}
        await _daily_pulse(make_update("72"), u, "72")
        assert u["state"] == DAILY_MED

    @pytest.mark.asyncio
    @pytest.mark.parametrize("diag", ["diabetes", "both"])
    async def test_pulse_diabetes_asks_glucose(self, diag):
        u = users[CHAT_ID]
        u["diagnosis_type"] = diag
        u["temp"] = {"sbp": 130, "dbp": 80}
        await _daily_pulse(make_update("72"), u, "72")
        assert u["state"] == DAILY_GLUCOSE

    @pytest.mark.asyncio
    async def test_glucose_invalid_string(self):
        u = users[CHAT_ID]
        u["state"] = DAILY_GLUCOSE
        update = make_update("abc")
        await _daily_glucose(update, u, "abc")
        assert u["state"] == DAILY_GLUCOSE

    @pytest.mark.asyncio
    @pytest.mark.parametrize("val,valid", [
        ("0.9", False), ("1.0", True), ("30.0", True), ("30.1", False)
    ])
    async def test_glucose_boundaries(self, val, valid):
        u = users[CHAT_ID]
        u["state"] = DAILY_GLUCOSE
        await _daily_glucose(make_update(val), u, val)
        assert (u["state"] == DAILY_MED) == valid

    @pytest.mark.asyncio
    async def test_glucose_comma_converted(self):
        u = users[CHAT_ID]
        u["state"] = DAILY_GLUCOSE
        await _daily_glucose(make_update("5,6"), u, "5,6")
        assert u["temp"]["glucose"] == pytest.approx(5.6)
        assert u["state"] == DAILY_MED

    @pytest.mark.asyncio
    async def test_med_taken_yes(self):
        u = users[CHAT_ID]
        u["state"] = DAILY_MED
        await _daily_med(make_update("да"), u, "да")
        assert u["temp"]["med_taken"] is True
        assert u["state"] == DAILY_SYMPTOMS

    @pytest.mark.asyncio
    async def test_med_taken_no(self):
        u = users[CHAT_ID]
        u["state"] = DAILY_MED
        await _daily_med(make_update("нет"), u, "нет")
        assert u["temp"]["med_taken"] is False

    @pytest.mark.asyncio
    async def test_symptoms_missing_patient_id(self):
        u = users[CHAT_ID]
        u["patient_id"] = None
        u["temp"] = {"sbp": 130, "dbp": 80, "pulse": 72, "med_taken": True}
        update = make_update("нет")
        await _daily_symptoms(update, u, "нет")
        assert u["state"] is None
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("bot.api_client.submit_reading", new_callable=AsyncMock)
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_symptoms_no_match_sends_none(self, mock_state, mock_submit):
        mock_submit.return_value = {"risk_level": "low"}
        u = users[CHAT_ID]
        u["temp"] = {"sbp": 130, "dbp": 80, "pulse": 72, "med_taken": True}
        await _daily_symptoms(make_update("всё хорошо"), u, "всё хорошо")
        payload = mock_submit.call_args[0][0]
        assert payload["symptoms"] is None

    @pytest.mark.asyncio
    @patch("bot.api_client.submit_reading", new_callable=AsyncMock)
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_symptoms_ru_headache(self, mock_state, mock_submit):
        mock_submit.return_value = {"risk_level": "low"}
        u = users[CHAT_ID]
        u["temp"] = {"sbp": 130, "dbp": 80, "pulse": 72, "med_taken": True}
        await _daily_symptoms(make_update("головная боль"), u, "головная боль")
        payload = mock_submit.call_args[0][0]
        assert "headache" in payload["symptoms"]

    @pytest.mark.asyncio
    @patch("bot.api_client.submit_reading", new_callable=AsyncMock)
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_symptoms_kz_headache(self, mock_state, mock_submit):
        mock_submit.return_value = {"risk_level": "low"}
        u = users[CHAT_ID]
        u["temp"] = {"sbp": 130, "dbp": 80, "pulse": 72, "med_taken": True}
        await _daily_symptoms(make_update("бас ауру"), u, "бас ауру")
        payload = mock_submit.call_args[0][0]
        assert "headache" in payload["symptoms"]

    @pytest.mark.asyncio
    @patch("bot.api_client.submit_reading", new_callable=AsyncMock)
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_symptoms_multiple(self, mock_state, mock_submit):
        mock_submit.return_value = {"risk_level": "medium"}
        u = users[CHAT_ID]
        u["temp"] = {"sbp": 130, "dbp": 80, "pulse": 72, "med_taken": False}
        text = "головная боль и головокружение"
        await _daily_symptoms(make_update(text), u, text)
        payload = mock_submit.call_args[0][0]
        assert "headache" in payload["symptoms"]
        assert "dizziness" in payload["symptoms"]

    @pytest.mark.asyncio
    @patch("bot.api_client.submit_reading", new_callable=AsyncMock)
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_symptoms_api_success_state_reset(self, mock_state, mock_submit):
        mock_submit.return_value = {"risk_level": "high"}
        u = users[CHAT_ID]
        u["temp"] = {"sbp": 180, "dbp": 110, "pulse": 95, "med_taken": False}
        await _daily_symptoms(make_update("нет"), u, "нет")
        assert u["state"] is None
        mock_state.assert_called_with("pat-1", "idle")

    @pytest.mark.asyncio
    @patch("bot.api_client.submit_reading", new_callable=AsyncMock)
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_symptoms_api_failure_defaults_low(self, mock_state, mock_submit):
        mock_submit.side_effect = Exception("API down")
        u = users[CHAT_ID]
        u["temp"] = {"sbp": 130, "dbp": 80, "pulse": 72, "med_taken": True}
        update = make_update("нет")
        await _daily_symptoms(update, u, "нет")
        assert u["state"] is None
        # Should show risk_low message (no crash)
        update.message.reply_text.assert_called_once()


# ── 5. Cron job ───────────────────────────────────────────────────────────────

class TestCronJob:
    def teardown_method(self):
        teardown_user()

    @pytest.mark.asyncio
    @patch("bot.api_client.get_idle_patients", new_callable=AsyncMock)
    async def test_cron_triggers_idle_patients(self, mock_idle):
        mock_idle.return_value = [{"telegram_id": CHAT_ID}]
        setup_user(state=None, patient_id="pat-1")
        ctx = MagicMock()
        ctx.bot.send_message = AsyncMock()
        with patch("bot.api_client.set_patient_state", new_callable=AsyncMock):
            await daily_check_job(ctx)
        assert users[CHAT_ID]["state"] == DAILY_SBP

    @pytest.mark.asyncio
    @patch("bot.api_client.get_idle_patients", new_callable=AsyncMock)
    async def test_cron_api_failure_uses_memory(self, mock_idle):
        mock_idle.side_effect = Exception("API down")
        setup_user(state=None, patient_id="pat-1")
        ctx = MagicMock()
        ctx.bot.send_message = AsyncMock()
        with patch("bot.api_client.set_patient_state", new_callable=AsyncMock):
            await daily_check_job(ctx)  # should not raise

    @pytest.mark.asyncio
    async def test_start_daily_skips_no_patient_id(self):
        bot_mock = MagicMock()
        bot_mock.send_message = AsyncMock()
        u = make_user(patient_id=None)
        await _start_daily_check_for(bot_mock, CHAT_ID, u)
        bot_mock.send_message.assert_not_called()

    @pytest.mark.asyncio
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_start_daily_sets_in_check(self, mock_state):
        bot_mock = MagicMock()
        bot_mock.send_message = AsyncMock()
        setup_user(state=None)
        await _start_daily_check_for(bot_mock, CHAT_ID, users[CHAT_ID])
        mock_state.assert_called_once_with("pat-1", "in_check")
        assert users[CHAT_ID]["state"] == DAILY_SBP

    @pytest.mark.asyncio
    @patch("bot.api_client.set_patient_state", new_callable=AsyncMock)
    async def test_start_daily_sends_messages(self, mock_state):
        bot_mock = MagicMock()
        bot_mock.send_message = AsyncMock()
        setup_user(state=None)
        await _start_daily_check_for(bot_mock, CHAT_ID, users[CHAT_ID])
        assert bot_mock.send_message.call_count == 2


# ── 6. Startup ────────────────────────────────────────────────────────────────

class TestStartup:
    def teardown_method(self):
        teardown_user()
        users.pop(777, None)

    @pytest.mark.asyncio
    @patch("bot.api_client.get_all_patients", new_callable=AsyncMock)
    async def test_startup_populates_users(self, mock_all):
        mock_all.return_value = [
            {"id": "pat-1", "telegram_id": CHAT_ID, "language": "kz", "diagnosis": "diabetes"},
            {"id": "pat-2", "telegram_id": 777,     "language": "ru", "diagnosis": "hypertension"},
        ]
        users.pop(CHAT_ID, None)
        users.pop(777, None)
        await on_startup(MagicMock())
        assert users[CHAT_ID]["patient_id"] == "pat-1"
        assert users[CHAT_ID]["lang"] == "kz"
        assert users[CHAT_ID]["diagnosis_type"] == "diabetes"
        assert users[777]["patient_id"] == "pat-2"

    @pytest.mark.asyncio
    @patch("bot.api_client.get_all_patients", new_callable=AsyncMock)
    async def test_startup_api_failure_no_crash(self, mock_all):
        mock_all.side_effect = Exception("API down")
        await on_startup(MagicMock())  # should not raise

    @pytest.mark.asyncio
    @patch("bot.api_client.get_all_patients", new_callable=AsyncMock)
    async def test_startup_skips_no_telegram_id(self, mock_all):
        mock_all.return_value = [
            {"id": "pat-1", "telegram_id": None, "language": "ru", "diagnosis": "hypertension"},
        ]
        count_before = len(users)
        await on_startup(MagicMock())
        assert len(users) == count_before  # nothing added


# ── 7. handle_message router ─────────────────────────────────────────────────

class TestMessageRouter:
    def teardown_method(self):
        teardown_user()

    @pytest.mark.asyncio
    async def test_unknown_user_prompts_start(self):
        users.pop(CHAT_ID, None)
        update = make_update("hello")
        ctx = MagicMock()
        await handle_message(update, ctx)
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_idle_user_gets_hint(self):
        setup_user(state=None)
        update = make_update("hello")
        await handle_message(update, MagicMock())
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_state_routes_to_handler(self):
        setup_user(state=NAME)
        update = make_update("Аскар Сейткали")
        await handle_message(update, MagicMock())
        assert users[CHAT_ID]["name"] == "Аскар Сейткали"
        assert users[CHAT_ID]["state"] == AGE
