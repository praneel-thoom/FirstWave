import asyncio
import logging
import math
import random
from functools import lru_cache

import numpy as np
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

try:
    from scipy.stats import lognorm as _lognorm_dist
except ImportError:
    _lognorm_dist = None

logger = logging.getLogger(__name__)
router = APIRouter()

BOROUGH_KEYS = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "RICHMOND / STATEN ISLAND"]

ZONE_BOROUGH = {
    'B1': 'BRONX', 'B2': 'BRONX', 'B3': 'BRONX', 'B4': 'BRONX', 'B5': 'BRONX',
    'K1': 'BROOKLYN', 'K2': 'BROOKLYN', 'K3': 'BROOKLYN', 'K4': 'BROOKLYN',
    'K5': 'BROOKLYN', 'K6': 'BROOKLYN', 'K7': 'BROOKLYN',
    'M1': 'MANHATTAN', 'M2': 'MANHATTAN', 'M3': 'MANHATTAN', 'M4': 'MANHATTAN',
    'M5': 'MANHATTAN', 'M6': 'MANHATTAN', 'M7': 'MANHATTAN', 'M8': 'MANHATTAN', 'M9': 'MANHATTAN',
    'Q1': 'QUEENS', 'Q2': 'QUEENS', 'Q3': 'QUEENS', 'Q4': 'QUEENS',
    'Q5': 'QUEENS', 'Q6': 'QUEENS', 'Q7': 'QUEENS',
    'S1': 'RICHMOND / STATEN ISLAND', 'S2': 'RICHMOND / STATEN ISLAND', 'S3': 'RICHMOND / STATEN ISLAND',
}

SVI_DEFAULTS = {
    'B1': 0.94, 'B2': 0.89, 'B3': 0.87, 'B4': 0.72, 'B5': 0.68,
    'K1': 0.52, 'K2': 0.58, 'K3': 0.82, 'K4': 0.84, 'K5': 0.79, 'K6': 0.60, 'K7': 0.45,
    'M1': 0.31, 'M2': 0.18, 'M3': 0.15, 'M4': 0.20, 'M5': 0.12,
    'M6': 0.14, 'M7': 0.73, 'M8': 0.65, 'M9': 0.61,
    'Q1': 0.71, 'Q2': 0.44, 'Q3': 0.38, 'Q4': 0.55, 'Q5': 0.67, 'Q6': 0.48, 'Q7': 0.41,
    'S1': 0.38, 'S2': 0.32, 'S3': 0.28,
}

AVG_RESPONSE_DEFAULTS = {
    'B1': 641, 'B2': 638, 'B3': 629, 'B4': 598, 'B5': 589,
    'K1': 521, 'K2': 548, 'K3': 571, 'K4': 579, 'K5': 562, 'K6': 534, 'K7': 542,
    'M1': 489, 'M2': 498, 'M3': 512, 'M4': 503, 'M5': 495,
    'M6': 490, 'M7': 558, 'M8': 541, 'M9': 528,
    'Q1': 502, 'Q2': 518, 'Q3': 509, 'Q4': 513, 'Q5': 516, 'Q6': 525, 'Q7': 499,
    'S1': 468, 'S2': 449, 'S3': 431,
}

# Dispatch/travel split defaults (~38% dispatch, ~62% travel based on citywide ratio)
AVG_DISPATCH_DEFAULTS = {z: round(v * 0.38) for z, v in AVG_RESPONSE_DEFAULTS.items()}
AVG_TRAVEL_DEFAULTS = {z: v - round(v * 0.38) for z, v in AVG_RESPONSE_DEFAULTS.items()}

ZONE_CENTROIDS = {
    'B1': (-73.9101, 40.8116), 'B2': (-73.9196, 40.8448), 'B3': (-73.8784, 40.8189),
    'B4': (-73.8600, 40.8784), 'B5': (-73.9056, 40.8651),
    'K1': (-73.9857, 40.5995), 'K2': (-73.9442, 40.6501), 'K3': (-73.9075, 40.6929),
    'K4': (-73.9015, 40.6501), 'K5': (-73.9283, 40.6801), 'K6': (-73.9645, 40.6401),
    'K7': (-73.9573, 40.7201),
    'M1': (-74.0060, 40.7128), 'M2': (-74.0000, 40.7484), 'M3': (-73.9857, 40.7580),
    'M4': (-73.9784, 40.7484), 'M5': (-73.9584, 40.7701), 'M6': (-73.9484, 40.7884),
    'M7': (-73.9428, 40.8048), 'M8': (-73.9373, 40.8284), 'M9': (-73.9312, 40.8484),
    'Q1': (-73.7840, 40.6001), 'Q2': (-73.8284, 40.7501), 'Q3': (-73.8784, 40.7201),
    'Q4': (-73.9073, 40.7101), 'Q5': (-73.8073, 40.6901), 'Q6': (-73.9173, 40.7701),
    'Q7': (-73.8373, 40.7701),
    'S1': (-74.1115, 40.6401), 'S2': (-74.1515, 40.5901), 'S3': (-74.1915, 40.5301),
}


def _weather_travel_factor(precipitation: float, windspeed: float) -> float:
    """Compute a multiplier > 1.0 that slows travel based on weather conditions.
    +1.2% per mm/hr precipitation, +0.2% per km/h wind above 15."""
    precip_penalty = 0.012 * precipitation
    wind_penalty = 0.002 * max(0, windspeed - 15)
    return 1.0 + precip_penalty + wind_penalty


def _haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _svi_quartile(svi):
    if svi <= 0.25:
        return "Q1"
    elif svi <= 0.50:
        return "Q2"
    elif svi <= 0.75:
        return "Q3"
    return "Q4"


def _estimate_pct_under_threshold(mean_seconds, threshold=480, cv=0.95):
    """Estimate fraction of incidents under threshold given zone mean response time.
    Uses lognormal CDF with cv~0.95 (calibrated to match real EMS data where
    citywide ~61% of incidents are under 8 min despite averages above 8 min)."""
    if mean_seconds <= 0:
        return 1.0
    sigma = math.sqrt(math.log(1 + cv ** 2))
    mu = math.log(mean_seconds) - sigma ** 2 / 2
    if _lognorm_dist is not None:
        return float(_lognorm_dist.cdf(threshold, s=sigma, scale=math.exp(mu)))
    # Fallback: approximate via normal CDF on log-space
    z = (math.log(threshold) - mu) / sigma
    return float(0.5 * (1.0 + math.erf(z / math.sqrt(2))))


@lru_cache(maxsize=256)
def _compute_dynamic_counterfactual(
    hour: int, dow: int, month: int,
    temperature: float, precipitation: float, windspeed: float,
    ambulances: int,
):
    from main import ARTIFACTS
    from models.demand_forecaster import DemandForecaster
    from models.staging_optimizer import StagingOptimizer

    forecaster = DemandForecaster(ARTIFACTS["demand_model"])
    predicted_counts = forecaster.predict_all_zones(
        hour, dow, month,
        temperature, precipitation, windspeed,
        ARTIFACTS["zone_stats"],
        ARTIFACTS["baselines"],
    )

    optimizer = StagingOptimizer()
    staging_points = optimizer.compute_staging(predicted_counts, K=ambulances)

    drive_time = ARTIFACTS.get("drive_time")
    zone_stats_df = ARTIFACTS.get("zone_stats")

    # Collect all staging point coordinates
    all_staging_coords = [(sp["lon"], sp["lat"]) for sp in staging_points]

    # Per-zone: compute static response time and staged response time
    zone_data = []
    for zone in predicted_counts:
        demand = predicted_counts[zone]
        borough = ZONE_BOROUGH.get(zone, "UNKNOWN")
        svi = SVI_DEFAULTS.get(zone, 0.5)

        # Static response time: split into dispatch + travel components
        dispatch_sec = AVG_DISPATCH_DEFAULTS.get(zone, 205)
        travel_sec = AVG_TRAVEL_DEFAULTS.get(zone, 335)
        if zone_stats_df is not None:
            row = zone_stats_df[zone_stats_df["INCIDENT_DISPATCH_AREA"] == zone]
            if not row.empty:
                if "avg_dispatch_seconds" in row.columns:
                    dispatch_sec = float(row["avg_dispatch_seconds"].iloc[0])
                if "avg_travel_seconds" in row.columns:
                    travel_sec = float(row["avg_travel_seconds"].iloc[0])
                if "svi_score" in row.columns:
                    svi = float(row["svi_score"].iloc[0])

        # Apply weather penalty to travel component
        weather_factor = _weather_travel_factor(precipitation, windspeed)
        travel_sec *= weather_factor
        static_time = dispatch_sec + travel_sec

        # Staged travel time: drive from the nearest staging point to this zone
        dst_lon, dst_lat = ZONE_CENTROIDS.get(zone, (0, 0))

        best_drive = float("inf")
        for stg_lon, stg_lat in all_staging_coords:
            # Try drive_time matrix: find nearest zone centroid to this staging point
            if drive_time:
                for src_zone in ZONE_CENTROIDS:
                    if (src_zone, zone) in drive_time:
                        sz_lon, sz_lat = ZONE_CENTROIDS[src_zone]
                        if _haversine_km(stg_lon, stg_lat, sz_lon, sz_lat) < 2.0:
                            best_drive = min(best_drive, drive_time[(src_zone, zone)])
            # Haversine fallback from staging point to zone centroid
            dist_km = _haversine_km(stg_lon, stg_lat, dst_lon, dst_lat)
            effective_speed = 25.0 / weather_factor
            t = dist_km / effective_speed * 3600
            best_drive = min(best_drive, t)

        # Staging only improves travel component; dispatch stays the same
        # Floor at 120s — no ambulance reaches a scene in under 2 min in NYC
        if best_drive < float("inf"):
            staged_travel_component = max(best_drive, 120)
        else:
            staged_travel_component = travel_sec  # no improvement if no data
        staged_time = dispatch_sec + staged_travel_component
        # Staged time can never be worse than static (staging is additive, not replacing)
        staged_time = min(staged_time, static_time)
        seconds_saved = max(0, static_time - staged_time)

        zone_data.append({
            "zone": zone,
            "borough": borough,
            "svi": svi,
            "demand": demand,
            "static_time": static_time,
            "staged_time": staged_time,
            "seconds_saved": seconds_saved,
        })

    # Demand-weighted aggregation
    total_demand = sum(zd["demand"] for zd in zone_data)
    if total_demand < 0.01:
        total_demand = 1.0

    # Overall metrics
    weighted_saved = sum(zd["seconds_saved"] * zd["demand"] for zd in zone_data) / total_demand
    demand_static_within_8 = sum(
        zd["demand"] * _estimate_pct_under_threshold(zd["static_time"])
        for zd in zone_data
    )
    demand_staged_within_8 = sum(
        zd["demand"] * _estimate_pct_under_threshold(zd["staged_time"])
        for zd in zone_data
    )
    pct_static = demand_static_within_8 / total_demand * 100
    pct_staged = demand_staged_within_8 / total_demand * 100

    # Median seconds saved (demand-weighted by repeating values)
    expanded_saved = []
    for zd in zone_data:
        count = max(1, round(zd["demand"]))
        expanded_saved.extend([zd["seconds_saved"]] * count)
    median_saved = float(np.median(expanded_saved)) if expanded_saved else 0.0

    # By borough
    by_borough = {}
    for borough in BOROUGH_KEYS:
        b_zones = [zd for zd in zone_data if zd["borough"] == borough]
        if not b_zones:
            continue
        b_demand = sum(zd["demand"] for zd in b_zones)
        if b_demand < 0.01:
            b_demand = 1.0
        b_static_8 = sum(
            zd["demand"] * _estimate_pct_under_threshold(zd["static_time"])
            for zd in b_zones
        ) / b_demand * 100
        b_staged_8 = sum(
            zd["demand"] * _estimate_pct_under_threshold(zd["staged_time"])
            for zd in b_zones
        ) / b_demand * 100
        b_saved_exp = []
        for zd in b_zones:
            b_saved_exp.extend([zd["seconds_saved"]] * max(1, round(zd["demand"])))
        by_borough[borough] = {
            "static": round(b_static_8, 1),
            "staged": round(b_staged_8, 1),
            "median_saved_sec": round(float(np.median(b_saved_exp)), 1),
        }

    # By SVI quartile
    by_svi_quartile = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        q_zones = [zd for zd in zone_data if _svi_quartile(zd["svi"]) == q]
        if not q_zones:
            by_svi_quartile[q] = {"median_saved_sec": 0.0}
            continue
        q_saved_exp = []
        for zd in q_zones:
            q_saved_exp.extend([zd["seconds_saved"]] * max(1, round(zd["demand"])))
        by_svi_quartile[q] = {
            "median_saved_sec": round(float(np.median(q_saved_exp)), 1),
        }

    # Histogram: demand-weighted per-zone response times
    histogram_baseline = []
    histogram_staged = []
    for zd in zone_data:
        count = max(1, round(zd["demand"]))
        # Add slight jitter for visual distribution spread
        for _ in range(count):
            jitter = random.gauss(0, 15)
            histogram_baseline.append(round(zd["static_time"] + jitter))
            histogram_staged.append(round(zd["staged_time"] + jitter))

    # Sample down to ~50 values for the histogram arrays
    if len(histogram_baseline) > 50:
        rng = random.Random(42)
        indices = rng.sample(range(len(histogram_baseline)), 50)
        histogram_baseline = [histogram_baseline[i] for i in sorted(indices)]
        histogram_staged = [histogram_staged[i] for i in sorted(indices)]

    by_zone = {
        zd["zone"]: {
            "static_time": round(zd["static_time"], 1),
            "staged_time": round(zd["staged_time"], 1),
            "seconds_saved": round(zd["seconds_saved"], 1),
        }
        for zd in zone_data
    }

    return {
        "hour": hour,
        "dayofweek": dow,
        "median_seconds_saved": round(median_saved, 1),
        "pct_within_8min_static": round(pct_static, 1),
        "pct_within_8min_staged": round(pct_staged, 1),
        "by_borough": by_borough,
        "by_svi_quartile": by_svi_quartile,
        "histogram_baseline_seconds": histogram_baseline,
        "histogram_staged_seconds": histogram_staged,
        "by_zone": by_zone,
    }


@router.get("/counterfactual")
async def get_counterfactual(
    hour: int = Query(..., ge=0, le=23),
    dow: int = Query(..., ge=0, le=6),
    month: int = Query(default=10, ge=1, le=12),
    temperature: float = Query(default=15.0),
    precipitation: float = Query(default=0.0),
    windspeed: float = Query(default=10.0),
    ambulances: int = Query(default=5, ge=1, le=10),
):
    from main import ARTIFACTS, MOCK_DATA

    # Dynamic computation if demand model + baselines are available
    if ARTIFACTS.get("demand_model") is not None and ARTIFACTS.get("baselines") is not None:
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: _compute_dynamic_counterfactual(
                        hour, dow, month,
                        round(temperature, 1), round(precipitation, 1), round(windspeed, 1),
                        ambulances,
                    ),
                ),
                timeout=5.0,
            )
            return JSONResponse(content=result, headers={"X-Data-Source": "dynamic"})
        except asyncio.TimeoutError:
            logger.error("Dynamic counterfactual timed out, falling back")
        except Exception as exc:
            logger.exception("Dynamic counterfactual error: %s", exc)

    # Fallback: precomputed parquet data
    summary_df = ARTIFACTS.get("counterfactual_summary")
    raw_df = ARTIFACTS.get("counterfactual_raw")

    if summary_df is None:
        logger.info("Counterfactual: artifact not loaded, returning mock data")
        return JSONResponse(
            content=MOCK_DATA.get("counterfactual", {}),
            headers={"X-Data-Source": "mock"},
        )

    try:
        row = summary_df[
            (summary_df["hour"] == hour) & (summary_df["dayofweek"] == dow)
        ]
        if row.empty:
            return JSONResponse(
                content=MOCK_DATA.get("counterfactual", {}),
                headers={"X-Data-Source": "mock", "X-Warning": "no-row-found"},
            )

        r = row.iloc[0]
        result = {
            "hour": hour,
            "dayofweek": dow,
            "median_seconds_saved": float(r["median_seconds_saved"]),
            "pct_within_8min_static": float(r["pct_within_8min_static"]),
            "pct_within_8min_staged": float(r["pct_within_8min_staged"]),
            "by_borough": {},
            "by_svi_quartile": {},
            "histogram_baseline_seconds": [],
            "histogram_staged_seconds": [],
            "by_zone": {},
        }

        if raw_df is not None:
            if "borough" in raw_df.columns:
                for borough in BOROUGH_KEYS:
                    b = raw_df[raw_df["borough"] == borough]
                    if not b.empty:
                        result["by_borough"][borough] = {
                            "static": float(b["baseline_within_8min"].mean() * 100) if "baseline_within_8min" in b.columns else 0.0,
                            "staged": float(b["staged_within_8min"].mean() * 100) if "staged_within_8min" in b.columns else 0.0,
                            "median_saved_sec": float(b["seconds_saved"].median()) if "seconds_saved" in b.columns else 0.0,
                        }

            if "svi_quartile" in raw_df.columns:
                for q in ["Q1", "Q2", "Q3", "Q4"]:
                    qdata = raw_df[raw_df["svi_quartile"] == q]
                    if not qdata.empty:
                        result["by_svi_quartile"][q] = {
                            "median_saved_sec": float(qdata["seconds_saved"].median()) if "seconds_saved" in qdata.columns else 0.0,
                        }

        if not result["by_borough"]:
            result["by_borough"] = MOCK_DATA.get("counterfactual", {}).get("by_borough", {})
        if not result["by_svi_quartile"]:
            result["by_svi_quartile"] = MOCK_DATA.get("counterfactual", {}).get("by_svi_quartile", {})
        if not result["histogram_baseline_seconds"]:
            result["histogram_baseline_seconds"] = MOCK_DATA.get("counterfactual", {}).get("histogram_baseline_seconds", [])
            result["histogram_staged_seconds"] = MOCK_DATA.get("counterfactual", {}).get("histogram_staged_seconds", [])

        return JSONResponse(content=result, headers={"X-Data-Source": "parquet"})

    except Exception as exc:
        logger.exception("Counterfactual error: %s", exc)
        return JSONResponse(
            content=MOCK_DATA.get("counterfactual", {}),
            headers={"X-Data-Source": "mock", "X-Warning": "lookup-error"},
        )
