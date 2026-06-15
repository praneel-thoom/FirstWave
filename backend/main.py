import json
import logging
import os
import pickle
import traceback
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "./artifacts"))
MOCK_DATA_PATH = Path(__file__).parent.parent / "data" / "mock_api_responses.json"

# ── Shared state ──────────────────────────────────────────────────────────────

ARTIFACTS: dict = {
    "demand_model": None,
    "drive_time": None,
    "baselines": None,
    "zone_stats": None,
    "counterfactual_summary": None,
    "counterfactual_raw": None,
}

MOCK_DATA: dict = {}
ZONE_GEOM_CACHE: dict = {}   # zone_code → GeoJSON geometry dict
BREAKDOWN_CACHE: list = []   # pre-computed at startup from zone_stats


# ── Artifact loading ──────────────────────────────────────────────────────────

def load_all_artifacts():
    global ARTIFACTS, BREAKDOWN_CACHE

    artifact_configs = [
        ("demand_model", ARTIFACTS_DIR / "demand_model.pkl", "joblib"),
        ("drive_time", ARTIFACTS_DIR / "drive_time_matrix.pkl", "pickle"),
        ("baselines", ARTIFACTS_DIR / "zone_baselines.parquet", "parquet"),
        ("zone_stats", ARTIFACTS_DIR / "zone_stats.parquet", "parquet"),
        ("counterfactual_summary", ARTIFACTS_DIR / "counterfactual_summary.parquet", "parquet"),
        ("counterfactual_raw", ARTIFACTS_DIR / "counterfactual_raw.parquet", "parquet"),
    ]

    for key, path, loader in artifact_configs:
        if not path.exists():
            logger.warning("⚠  %s not found at %s — using mock", key, path)
            continue
        try:
            if loader == "joblib":
                obj = joblib.load(path)
            elif loader == "pickle":
                with open(path, "rb") as f:
                    obj = pickle.load(f)
            else:
                obj = pd.read_parquet(path)

            # Sanity checks
            if loader == "joblib" and hasattr(obj, "predict"):
                # quick dummy predict to verify model works
                dummy = pd.DataFrame([{
                    "hour_sin": 0.0, "hour_cos": 1.0,
                    "dow_sin": 0.0, "dow_cos": 1.0,
                    "month_sin": 0.0, "month_cos": 1.0,
                    "is_weekend": 0,
                    "temperature_2m": 15.0, "precipitation": 0.0, "windspeed_10m": 10.0,
                    "is_severe_weather": 0,
                    "svi_score": 0.5, "zone_baseline_avg": 5.0,
                    "high_acuity_ratio": 0.23, "held_ratio": 0.07,
                    "is_holiday": 0, "is_major_event": 0, "is_school_day": 1,
                    "is_heat_emergency": 0, "is_extreme_heat": 0,
                    "subway_disruption_idx": 0.5,
                }])
                _ = obj.predict(dummy)

            elif loader == "parquet" and isinstance(obj, pd.DataFrame):
                assert len(obj) > 0, f"{key} parquet is empty"

            ARTIFACTS[key] = obj
            logger.info("✓  loaded %s", key)

        except Exception as exc:
            logger.error("⚠  failed to load %s: %s — using mock", key, exc)
            ARTIFACTS[key] = None

    # Pre-compute breakdown cache
    if ARTIFACTS["zone_stats"] is not None:
        try:
            from routers.breakdown import _compute_breakdown
            BREAKDOWN_CACHE = _compute_breakdown(ARTIFACTS["zone_stats"])
            logger.info("✓  breakdown cache built (%d boroughs)", len(BREAKDOWN_CACHE))
        except Exception as exc:
            logger.error("⚠  breakdown cache failed: %s", exc)


def _load_mock_data():
    global MOCK_DATA
    try:
        with open(MOCK_DATA_PATH, "r") as f:
            MOCK_DATA = json.load(f)
        logger.info("✓  mock data loaded from %s", MOCK_DATA_PATH)
    except Exception as exc:
        logger.error("FATAL: could not load mock data: %s", exc)
        MOCK_DATA = {}


def _populate_zone_geom_cache():
    """
    Load zone geometries from PostGIS into memory at startup.
    If DB is unavailable, fall back to bounding-box approximations.
    """
    global ZONE_GEOM_CACHE
    database_url = os.getenv("DATABASE_URL", "")

    if database_url:
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            cur = conn.cursor()
            cur.execute("""
                SELECT zone_code, ST_AsGeoJSON(geom)::json
                FROM dispatch_zone_boundaries
            """)
            for zone_code, geom in cur.fetchall():
                ZONE_GEOM_CACHE[zone_code] = geom
            cur.close()
            conn.close()
            logger.info("✓  zone geometry cache loaded (%d zones)", len(ZONE_GEOM_CACHE))
            return
        except Exception as exc:
            logger.warning("⚠  PostGIS unavailable (%s) — using centroid fallback geometries", exc)

    # Fallback: use mock heatmap geometries
    if MOCK_DATA and "heatmap" in MOCK_DATA:
        for feature in MOCK_DATA["heatmap"].get("features", []):
            zone = feature["properties"]["zone"]
            ZONE_GEOM_CACHE[zone] = feature["geometry"]
        logger.info("✓  zone geometry cache populated from mock data (%d zones)", len(ZONE_GEOM_CACHE))


# ── App setup ─────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_mock_data()
    load_all_artifacts()
    _populate_zone_geom_cache()
    logger.info("FirstWave API startup complete")
    yield


app = FastAPI(
    title="FirstWave API",
    version="2.0.0",
    description="Predictive ambulance staging dashboard — NYC EMS",
    lifespan=lifespan,
)

# Comma-separated list, e.g. ALLOWED_ORIGINS=http://localhost:3000,https://firstwave.example.com
_DEFAULT_ORIGINS = "http://localhost:3000,http://localhost:3004,http://localhost:5173,http://localhost:5174"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────

from routers import heatmap, staging, counterfactual, historical, breakdown, stations, ai_panel  # noqa: E402

app.include_router(heatmap.router, prefix="/api")
app.include_router(staging.router, prefix="/api")
app.include_router(counterfactual.router, prefix="/api")
app.include_router(historical.router, prefix="/api")
app.include_router(breakdown.router, prefix="/api")
app.include_router(stations.router, prefix="/api")
app.include_router(ai_panel.router, prefix="/api")


# ── Health + Reload ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "artifacts": {
            "demand_model": ARTIFACTS["demand_model"] is not None,
            "drive_time": ARTIFACTS["drive_time"] is not None,
            "baselines": ARTIFACTS["baselines"] is not None,
            "zone_stats": ARTIFACTS["zone_stats"] is not None,
            "counterfactual": ARTIFACTS["counterfactual_summary"] is not None,
        },
    }


@app.post("/reload")
async def reload_artifacts():
    load_all_artifacts()
    _populate_zone_geom_cache()

    # Clear computation caches — they hold results built from the old artifacts
    from routers.staging import _cached_heatmap_and_staging
    from routers.counterfactual import _compute_dynamic_counterfactual
    _cached_heatmap_and_staging.cache_clear()
    _compute_dynamic_counterfactual.cache_clear()

    return {
        "status": "reloaded",
        "artifacts": {
            "demand_model": ARTIFACTS["demand_model"] is not None,
            "drive_time": ARTIFACTS["drive_time"] is not None,
            "baselines": ARTIFACTS["baselines"] is not None,
            "zone_stats": ARTIFACTS["zone_stats"] is not None,
            "counterfactual": ARTIFACTS["counterfactual_summary"] is not None,
        },
    }


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid query parameters", "detail": str(exc)},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "path": str(request.url.path)},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s\n%s", request.url.path, exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
        headers={"X-Warning": "unhandled-exception"},
    )
