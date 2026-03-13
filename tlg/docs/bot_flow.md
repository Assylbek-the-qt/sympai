# SympAI Bot — User Interaction Flow

> All flows are bilingual (🇰🇿 Қазақша / 🇷🇺 Русский). Examples shown in Russian unless noted.
> **Select** = keyboard button (user taps).  **Text** = user types freely.

---

## Trigger: `/start`

```
User sends /start
      │
      ├─ Already registered? → "Для ежедневной проверки введите /check."  ← END
      │
      └─ New user → REGISTRATION FLOW ↓
```

---

## Flow A — Registration (11 steps)

### Step 1 — Language
| | |
|---|---|
| **Type** | Select (keyboard) |
| **Prompt** | `Тілді таңдаңыз / Выберите язык:` |
| **Options** | `🇰🇿 Қазақша` · `🇷🇺 Русский` |

---

### Step 2 — Full name
| | |
|---|---|
| **Type** | Free text |
| **Prompt** | `Введите ваше ФИО:` |
| **Expected** | Full name, any characters |
| **Examples** | `Иванов Иван Петрович` · `Сейткали Аскар` |
| **Validation** | None — any non-empty text accepted |

---

### Step 3 — Age
| | |
|---|---|
| **Type** | Free text (number) |
| **Prompt** | `Введите ваш возраст:` |
| **Expected** | Positive integer |
| **Examples** | `52` · `34` · `71` |
| **Validation** | Must be digits only — re-asks on `abc`, `5.5`, etc. |

---

### Step 4 — Doctor
| | |
|---|---|
| **Type** | Select (keyboard — loaded from API) |
| **Prompt** | `Выберите вашего врача:` |
| **Options** | One button per doctor from `GET /doctors` — e.g. `Ахметов Ержан` |
| **Validation** | Only keyboard values accepted — free-text re-shows the keyboard |

---

### Step 5 — Diagnosis
| | |
|---|---|
| **Type** | Select (keyboard) |
| **Prompt** | `Выберите ваш диагноз:` |
| **Options (ru)** | `Гипертония` · `Диабет` · `Оба` |
| **Options (kz)** | `Гипертония` · `Диабет` · `Екеуі де` |
| **Stored as** | `hypertension` · `diabetes` · `both` |
| **Validation** | Only keyboard values accepted |

---

### Step 6 — BP reading (3 days ago)
| | |
|---|---|
| **Type** | Free text |
| **Prompt** | `Введите давление 3 дня назад (например: 130/80):` |
| **Expected** | `SBP/DBP` — two integers separated by `/` |
| **Examples** | `150/95` · `120/80` · `138/88` |
| **Valid range** | SBP: 50–300 · DBP: 30–200 |
| **Validation** | Wrong format or out-of-range → `Неверный формат. Например: 130/80` — re-asks |

---

### Step 7 — BP reading (2 days ago)
Same format as Step 6.
Prompt: `Введите давление 2 дня назад (например: 130/80):`

---

### Step 8 — BP reading (yesterday)
Same format as Step 6.
Prompt: `Введите давление вчера (например: 130/80):`

---

### Step 9 — Current medications
| | |
|---|---|
| **Type** | Free text |
| **Prompt** | `Какие лекарства принимаете? (название и дозировку):` |
| **Expected** | Medication name(s) and dose |
| **Examples** | `Лизиноприл 10мг` · `Метформин 500мг, Амлодипин 5мг` · `нет` |
| **Validation** | None — any text accepted |

---

### Step 10 — Other conditions (comorbidities)
| | |
|---|---|
| **Type** | Free text |
| **Prompt** | `Есть ли другие заболевания? (если нет, напишите «нет»):` |
| **Expected** | Free-text description, or negative keyword |
| **Examples** | `Семейный диабет` · `Ожирение 2 степени` · `нет` · `жоқ` · `no` |
| **Note** | `нет` / `жоқ` / `no` → stored as `NULL` in DB; anything else stored verbatim |

---

### Registration complete
Bot replies:
```
✅ Регистрация завершена!

Ежедневный мониторинг будет в 08:00.
Для ручного запуска введите /check.
```
Patient is created in DB and state set to `idle`.

---

## Flow B — Daily Check

**Triggered automatically** every day at **08:00 Almaty time (UTC+5)** for all idle patients,
or **manually** at any time via `/check`.

```
Bot sends: "🏥 Время ежедневной проверки!"
then immediately asks Step 1 below
```

---

### Step 1 — Systolic BP (upper)
| | |
|---|---|
| **Type** | Free text (number) |
| **Prompt** | `Введите систолическое (верхнее) давление:` |
| **Expected** | Integer |
| **Examples** | `145` · `128` · `160` |
| **Valid range** | 50–300 |
| **Validation** | Non-digit or out-of-range → `Введите только цифры.` — re-asks |

---

### Step 2 — Diastolic BP (lower)
| | |
|---|---|
| **Type** | Free text (number) |
| **Prompt** | `Введите диастолическое (нижнее) давление:` |
| **Expected** | Integer |
| **Examples** | `90` · `82` · `95` |
| **Valid range** | 30–200 |
| **Validation** | Same as Step 1 |

---

### Step 3 — Pulse
| | |
|---|---|
| **Type** | Free text (number) |
| **Prompt** | `Введите пульс:` |
| **Expected** | Integer |
| **Examples** | `72` · `85` · `68` |
| **Valid range** | 30–250 |
| **Validation** | Same as Step 1 |

---

### Step 4 — Blood glucose ⚠️ diabetes/both patients only
| | |
|---|---|
| **Type** | Free text (decimal) |
| **Prompt** | `Введите уровень сахара в крови (ммоль/л, например: 5.6):` |
| **Expected** | Decimal number, comma or dot separator |
| **Examples** | `5.6` · `7,2` · `12.0` · `4.8` |
| **Valid range** | 1.0–30.0 mmol/L |
| **Validation** | Non-numeric, `0`, or out-of-range → `Введите только цифры.` — re-asks |
| **Skipped for** | `hypertension`-only patients |

---

### Step 5 — Medication taken today
| | |
|---|---|
| **Type** | Select (keyboard) |
| **Prompt** | `Вы приняли лекарство сегодня?` |
| **Options (ru)** | `Да` · `Нет` |
| **Options (kz)** | `Иә` · `Жоқ` |
| **Note** | Any text containing `да`, `иә`, or `yes` counts as Yes |

---

### Step 6 — Symptoms
| | |
|---|---|
| **Type** | Select (keyboard) |
| **Prompt** | `Есть ли симптомы? (выберите наиболее важный):` |
| **Options (ru)** | `Головная боль` · `Головокружение` · `Боль в груди` · `Нет` |
| **Options (kz)** | `Бас ауру` · `Көз қарауыту` · `Кеуде ауру` · `Жоқ` |
| **Stored as** | `headache` · `dizziness` · `chest_pain` · `null` |
| **Note** | Only one symptom can be selected (single-tap keyboard) |

---

### Daily check complete — risk response

Reading is submitted to the API, which scores it automatically. Bot replies based on result:

| Risk level | Response |
|---|---|
| `low` | `✅ Состояние в норме. Не забывайте принимать лекарства!` |
| `medium` | `⚠️ Внимание! Давление повышено. Обратитесь к врачу.` |
| `high` | `🚨 ОПАСНОСТЬ! Срочно обратитесь к врачу! При ухудшении вызовите скорую: 103` |

Patient state is reset to `idle` after this step.

---

## Edge cases & error handling

| Situation | Bot behaviour |
|---|---|
| Unknown user sends any message | `Для начала введите /start.` |
| Registered user sends random text while idle | `Для ежедневной проверки введите /check.` |
| User sends `/check` while already in a flow | `Сначала ответьте на текущие вопросы.` |
| User sends `/start` again (already registered) | `Для ежедневной проверки введите /check.` — no re-registration |
| API unreachable during registration | `Ошибка при регистрации. Введите /start заново.` — state reset |
| Doctor list fails to load | `Не удалось загрузить список врачей. Попробуйте позже.` — stays on age step |
| Bot restarts | All patient data reloaded from API on startup — no re-registration needed |

---

## Full flow summary (hypertension patient, Russian)

```
/start
  → [🇷🇺 Русский]
  → "Иванов Иван Петрович"
  → "52"
  → [Ахметов Ержан]          ← doctor from keyboard
  → [Гипертония]
  → "150/95"                  ← BP 3 days ago
  → "148/92"                  ← BP 2 days ago
  → "145/90"                  ← BP yesterday
  → "Лизиноприл 10мг"
  → "нет"
  ✅ Регистрация завершена!

--- next day, 08:00 ---

🏥 Время ежедневной проверки!
  → "145"                     ← SBP
  → "90"                      ← DBP
  → "78"                      ← pulse
  (glucose skipped — hypertension only)
  → [Да]                      ← med taken
  → [Нет]                     ← no symptoms
  ✅ Состояние в норме.
```

## Full flow summary (diabetes patient, Kazakh)

```
/start
  → [🇰🇿 Қазақша]
  → "Сейткали Аскар"
  → "45"
  → [Ахметов Ержан]
  → [Диабет]
  → "130/80" · "128/82" · "132/79"
  → "Метформин 500мг"
  → "жоқ"
  ✅ Тіркелу аяқталды!

--- next day, 08:00 ---

🏥 Күнделікті тексеру уақыты!
  → "138"                     ← SBP
  → "88"                      ← DBP
  → "72"                      ← pulse
  → "6,2"                     ← glucose (asked because diagnosis=diabetes)
  → [Иә]
  → [Жоқ]
  ✅ Жағдайыңыз қалыпты.
```
