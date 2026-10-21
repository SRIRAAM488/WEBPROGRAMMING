"""DailyFlow API - FastAPI application entry point.

Run in development with:

    uvicorn app.main:app --reload

Then open:
  * API root ....... http://127.0.0.1:8000
  * Swagger docs ... http://127.0.0.1:8000/docs
  * ReDoc .......... http://127.0.0.1:8000/redoc
"""

import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.routers import (
    bills,
    dashboard,
    documents,
    hydration,
    medications,
    reminders,
    settings as settings_router,
)
from app.utils.dates import utc_now

logger = logging.getLogger("dailyflow")

DESCRIPTION = """
**DailyFlow** is an all-in-one personal life organizer built for a college web
programming demonstration. It combines four modules on one dashboard:

| Module | What it does |
| --- | --- |
| **BillBell** | Tracks bills, due dates, amounts and payment status. |
| **DateGuard** | Tracks important documents and warns before they expire. |
| **DoseNote** | Tracks a medication schedule you entered and logs each dose. |
| **AquaHabit** | Tracks daily water intake against a goal you choose. |

### Things worth knowing

* **Single user, local only.** There is no login. All data lives in a single
  SQLite file on this machine. Do not expose this API to the internet.
* **Reminders are in-app.** They are generated from the current database state
  while the page is open. DailyFlow does not send push notifications, email or
  SMS, and nothing runs in the background when the browser is closed.
* **DoseNote is not medical advice.** It records the schedule you entered. It
  does not recommend medications or doses.
* **AquaHabit goals are personal preferences**, not medical recommendations.
* Money is stored with SQLAlchemy `Numeric` (Python `Decimal`), so currency
  arithmetic does not suffer from binary floating-point errors.
* Dates and times are stored in UTC. Send the `X-Client-Utc-Offset` header (in
  minutes, e.g. `330` for UTC+5:30) so "today" matches the user's own clock.
"""

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Run once when the server starts and once when it stops.

    On start-up we create the tables and add demo data if the database is empty,
    so a fresh clone of the project works with no extra setup commands.
    """
    from app.db.init_db import init_db

    init_db()
    logger.info("%s v%s started.", settings.APP_NAME, settings.APP_VERSION)

    if settings.SEED_ON_STARTUP:
        try:
            from scripts.seed_data import seed_all

            seed_all()
            logger.info("Demo data ready (seeded if the database was empty).")
        except Exception:  # pragma: no cover - seeding must never block startup
            logger.exception("Seeding failed; the API still runs with an empty database.")

    logger.info("Server date (UTC): %s", utc_now().isoformat())
    yield
    logger.info("%s shutting down.", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={"name": "DailyFlow (college project)"},
    license_info={"name": "For educational demonstration"},
)


# --------------------------------------------------------------- middleware


# Any http://localhost:<port> or http://127.0.0.1:<port> origin.
# This lets Vite start on a different port (5174, 5175, ...) without editing
# the CORS settings, which is handy when port 5173 is already in use.
LOCALHOST_ORIGIN = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")


def _is_allowed_origin(origin: str) -> bool:
    """Decide whether a browser origin may call this API."""
    if settings.CORS_ALLOW_ANY_LOCALHOST and LOCALHOST_ORIGIN.match(origin):
        return True
    return origin in settings.CORS_ORIGINS


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    if settings.CORS_ALLOW_ANY_LOCALHOST
    else None,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Client-Utc-Offset"],
)


@app.middleware("http")
async def add_no_store_header(request: Request, call_next):
    """Ask browsers not to cache API responses, so the UI always shows fresh data."""
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ------------------------------------------------------------ error handlers


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return a consistent JSON error body and never leak a stack trace."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": _STATUS_TEXT.get(exc.status_code, "Request failed"),
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Turn Pydantic errors into a friendly, field-level message the UI can show
    directly under the offending input."""
    fields: dict[str, str] = {}
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part not in ("body", "query", "path")]
        key = ".".join(location) if location else "request"
        fields[key] = error.get("msg", "Invalid value")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation failed",
            "detail": "Please correct the highlighted fields.",
            "fields": fields,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log the real error server-side, return a safe message to the browser."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": "Something went wrong on the server. Check the backend terminal for details.",
        },
    )


_STATUS_TEXT = {
    400: "Bad request",
    401: "Not authorised",
    403: "Forbidden",
    404: "Not found",
    405: "Method not allowed",
    409: "Conflict",
    422: "Validation failed",
    500: "Internal server error",
}


# ------------------------------------------------------------------- routes

app.include_router(bills.router)
app.include_router(documents.router)
app.include_router(medications.router)
app.include_router(hydration.router)
app.include_router(dashboard.router)
app.include_router(reminders.router)
app.include_router(settings_router.router)


@app.get("/", tags=["General"], summary="API index")
def read_root() -> dict:
    """A small index so hitting the API URL directly is not a dead end."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "tagline": "Stay on top of everyday life.",
        "docs": "/docs",
        "health": "/api/health",
        "modules": {
            "billbell": "/api/bills",
            "dateguard": "/api/documents",
            "dosenote": "/api/medications",
            "aquahabit": "/api/hydration",
            "dashboard": "/api/dashboard/summary",
            "reminders": "/api/reminders",
            "settings": "/api/settings",
        },
    }