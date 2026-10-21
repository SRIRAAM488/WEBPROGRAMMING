# DailyFlow

**An all-in-one personal life organizer.** Four focused modules and one dashboard that answers a single question every morning: *what needs my attention today?*

DailyFlow is a full-stack web app — a **FastAPI + SQLite** backend and a **React (Vite)** frontend. Every number on screen comes from a real database query through a REST API. There is no mock or hard-coded data anywhere in the UI.

---

## The four modules

| Module | What it tracks | Colour |
| :-- | :-- | :-- |
| **BillBell** | Recurring and one-off bills — amounts, due dates, payment history, outstanding totals | Coral |
| **DateGuard** | Expiring documents (IDs, licences, passports, insurance) — lead times and renewal history | Amber |
| **DoseNote** | Medication schedules and daily dose logs — adherence tracking with a rolling chart | Violet |
| **AquaHabit** | Water intake — quick-add logging against a personal daily goal, with a 7-day trend | Turquoise |

Plus a **Dashboard** that rolls all four together, a **Reminder Centre** that surfaces what's due, and a **Settings** page for currency, theme, hydration goal and reminder preferences.

### Design decisions worth knowing

- **Money is stored as `Decimal`** and never converted between currencies. You pick one display currency; amounts are formatted, not transformed.
- **Recurring bills never auto-create the next cycle.** The system suggests it; you confirm it.
- **Document renewals keep the previous expiry date** in history rather than overwriting it — you can always see what the old date was.
- **Document numbers are masked** in list views (`•••• 4821`) and only revealed in the detail view.
- **DoseNote is not medical advice.** It carries a visible disclaimer: it records what you tell it and reminds you, nothing more. Never change medication based on an app.
- **The hydration goal is a personal preference**, not a medical target.
- **Reminders are in-app only.** There is no email or SMS service configured. Browser notifications are available but require an **explicit opt-in** — DailyFlow never prompts for them automatically.

---

## Tech stack

**Backend** — Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, SQLite, pytest
**Frontend** — React 18, Vite 6, React Router 6, Axios, Recharts, Lucide icons

---

## Project structure

```
dailyflow-webpgm/
├── backend/
│   ├── app/
│   │   ├── main.py            # App factory, CORS, table creation, seeding
│   │   ├── core/config.py     # Environment-driven settings
│   │   ├── db/                # Engine, session, table initialisation
│   │   ├── models/            # 9 SQLAlchemy tables
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── routers/           # 46 REST endpoints, grouped by module
│   │   ├── services/          # All business logic lives here
│   │   └── utils/             # Dates, masking, constants
│   ├── scripts/
│   │   ├── seed_data.py       # Idempotent demo data
│   │   └── smoke_test.py      # 81 live API checks against a running server
│   ├── tests/                 # 156 pytest tests
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/               # One Axios module per backend resource
│   │   ├── pages/             # Dashboard, Bills, Documents, Medications, Hydration, Settings…
│   │   ├── components/        # dashboard/ documents/ bills/ medications/ common/ layout/
│   │   ├── context/           # Toast + settings/theme state
│   │   ├── hooks/             # useAsync, useDebounced
│   │   └── index.css          # Full design system (CSS custom properties)
│   ├── .env.example
│   └── vite.config.js
│
└── docs/
```

---

## Getting started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm

### 1. Start the backend

```bash
cd backend
python -m venv venv

# Windows PowerShell
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

Tables are created and demo data is seeded automatically on first boot. Set `SEED_ON_STARTUP=false` if you'd rather start with a clean database.

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** (or whichever port Vite prints — any `localhost` port is accepted by the API by default).

### 3. Verify the API

- API docs (Swagger): <http://127.0.0.1:8010/docs>
- Health check: <http://127.0.0.1:8010/api/health>

---

## Configuration

All settings are optional — the app runs with sensible defaults.

**Frontend** (`frontend/.env`)

| Variable | Purpose | Default |
| :-- | :-- | :-- |
| `VITE_API_BASE_URL` | Where the backend lives | `http://127.0.0.1:8010` |

**Backend** (`backend/.env`)

| Variable | Purpose | Default |
| :-- | :-- | :-- |
| `DATABASE_URL` | SQLite connection string | `sqlite:///./dailyflow.db` |
| `CORS_ORIGINS` | Comma-separated allowed origins | localhost:5173/5175 |
| `CORS_ALLOW_ANY_LOCALHOST` | Accept any `localhost` port while developing | `true` |
| `SEED_ON_STARTUP` | Create tables + demo data on boot | `true` |

> `CORS_ALLOW_ANY_LOCALHOST=true` is a development convenience. Turn it **off** for anything beyond a local demo.

---

## Testing

```bash
cd backend

# 156 unit + integration tests
python -m pytest

# 81 live API checks (needs the server running on port 8010)
python -m scripts.smoke_test http://127.0.0.1:8010
```

The test suite covers each module's CRUD flows, validation, masking, and a set of **concurrency tests** — the dashboard fires several requests in parallel, so dose generation uses an atomic `INSERT … ON CONFLICT DO NOTHING` to guarantee duplicates are impossible rather than merely unlikely.

---

## Building for production

```bash
cd frontend
npm run build     # outputs to frontend/dist/
npm run preview   # serve the production build locally
```

The bundle is code-split into separate `react`, `charts` and app chunks.

---

## API overview

46 endpoints across seven route groups:

| Group | Prefix | Highlights |
| :-- | :-- | :-- |
| Dashboard | `/api/dashboard` | `summary`, `charts`, `activity` |
| Bills | `/api/bills` | CRUD, payments, summary |
| Documents | `/api/documents` | CRUD, renewals, expiring soon |
| Medications | `/api/medications` | schedules, `today` (dose generation), `taken`, adherence |
| Hydration | `/api/hydration` | `today`, quick-add, entries, 7-day history |
| Reminders | `/api/reminders` | grouped list, `summary`, mark-dismissed |
| Settings | `/api/settings` | profile, preferences, theme |

Full request/response schemas are at `/docs`.

---

## Licence

This project is provided as-is for personal and educational use.
