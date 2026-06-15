import asyncio
import logging
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

ZONE_NAMES = {
    'B1': 'South Bronx', 'B2': 'West/Central Bronx', 'B3': 'East Bronx',
    'B4': 'North Bronx', 'B5': 'Riverdale',
    'K1': 'Southern Brooklyn', 'K2': 'Park Slope', 'K3': 'Bushwick',
    'K4': 'East New York', 'K5': 'Bed-Stuy', 'K6': 'Borough Park', 'K7': 'Williamsburg',
    'M1': 'Lower Manhattan', 'M2': 'Midtown South', 'M3': 'Midtown',
    'M4': 'Murray Hill', 'M5': 'Upper East Side S', 'M6': 'Upper East Side N',
    'M7': 'Harlem', 'M8': 'Washington Heights S', 'M9': 'Washington Heights N',
    'Q1': 'Far Rockaway', 'Q2': 'Flushing', 'Q3': 'Forest Hills',
    'Q4': 'Ridgewood', 'Q5': 'Jamaica', 'Q6': 'Astoria', 'Q7': 'Whitestone',
    'S1': 'North Shore SI', 'S2': 'Mid-Island SI', 'S3': 'South Shore SI',
}

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

HIGH_ACUITY_DEFAULTS = {
    'B1': 0.29, 'B2': 0.28, 'B3': 0.26, 'B4': 0.24, 'B5': 0.22,
    'K1': 0.21, 'K2': 0.23, 'K3': 0.27, 'K4': 0.27, 'K5': 0.25, 'K6': 0.22, 'K7': 0.21,
    'M1': 0.20, 'M2': 0.19, 'M3': 0.20, 'M4': 0.19, 'M5': 0.18,
    'M6': 0.18, 'M7': 0.25, 'M8': 0.24, 'M9': 0.23,
    'Q1': 0.22, 'Q2': 0.21, 'Q3': 0.20, 'Q4': 0.21, 'Q5': 0.22, 'Q6': 0.21, 'Q7': 0.19,
    'S1': 0.19, 'S2': 0.18, 'S3': 0.17,
}

AVG_RESPONSE_DEFAULTS = {
    'B1': 641, 'B2': 638, 'B3': 629, 'B4': 598, 'B5': 589,
    'K1': 521, 'K2': 548, 'K3': 571, 'K4': 579, 'K5': 562, 'K6': 534, 'K7': 542,
    'M1': 489, 'M2': 498, 'M3': 512, 'M4': 503, 'M5': 495,
    'M6': 490, 'M7': 558, 'M8': 541, 'M9': 528,
    'Q1': 502, 'Q2': 518, 'Q3': 509, 'Q4': 513, 'Q5': 516, 'Q6': 525, 'Q7': 499,
    'S1': 468, 'S2': 449, 'S3': 431,
}


def _build_heatmap_from_predictions(
    predicted_counts: dict,
    hour: int, dow: int, month: int,
    zone_geom_cache: dict,
    zone_stats_df,
) -> dict:
    counts = list(predicted_counts.values())
    min_count = min(counts) if counts else 0
    max_count = max(counts) if counts else 1
    spread = max_count - min_count + 0.001

    features = []
    for zone, count in predicted_counts.items():
        normalized = (count - min_count) / spread

        svi = SVI_DEFAULTS.get(zone, 0.5)
        high_acuity = HIGH_ACUITY_DEFAULTS.get(zone, 0.22)
        avg_response = AVG_RESPONSE_DEFAULTS.get(zone, 540)

        if zone_stats_df is not None:
            row = zone_stats_df[zone_stats_df["INCIDENT_DISPATCH_AREA"] == zone]
            if not row.empty:
                if "svi_score" in row.columns:
                    svi = float(row["svi_score"].iloc[0])
                if "high_acuity_ratio" in row.columns:
                    high_acuity = float(row["high_acuity_ratio"].iloc[0])
                if "avg_response_seconds" in row.columns:
                    avg_response = float(row["avg_response_seconds"].iloc[0])

        geom = zone_geom_cache.get(zone)

        features.append({
            "type": "Feature",
            "properties": {
                "zone": zone,
                "borough": ZONE_BOROUGH.get(zone, "UNKNOWN"),
                "zone_name": ZONE_NAMES.get(zone, zone),
                "predicted_count": round(count, 2),
                "normalized_intensity": round(normalized, 4),
                "svi_score": svi,
                "historical_avg_response_sec": avg_response,
                "high_acuity_ratio": high_acuity,
            },
            "geometry": geom,
        })

    return {
        "type": "FeatureCollection",
        "query_params": {"hour": hour, "dow": dow, "month": month},
        "features": features,
    }


@router.get("/heatmap")
async def get_heatmap(
    hour: int = Query(..., ge=0, le=23),
    dow: int = Query(..., ge=0, le=6),
    month: int = Query(..., ge=1, le=12),
    temperature: float = Query(default=15.0),
    precipitation: float = Query(default=0.0),
    windspeed: float = Query(default=10.0),
    ambulances: int = Query(default=5, ge=1, le=10),
):
    from main import ARTIFACTS, MOCK_DATA, ZONE_GEOM_CACHE

    if ARTIFACTS["demand_model"] is None or ARTIFACTS["baselines"] is None:
        logger.info("Heatmap: model not loaded, returning mock data")
        return JSONResponse(
            content=MOCK_DATA["heatmap"],
            headers={"X-Data-Source": "mock"},
        )

    try:
        from models.demand_forecaster import DemandForecaster
        forecaster = DemandForecaster(ARTIFACTS["demand_model"])

        predicted_counts = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: forecaster.predict_all_zones(
                    hour, dow, month,
                    temperature, precipitation, windspeed,
                    ARTIFACTS["zone_stats"],
                    ARTIFACTS["baselines"],
                ),
            ),
            timeout=5.0,
        )

        result = _build_heatmap_from_predictions(
            predicted_counts, hour, dow, month,
            ZONE_GEOM_CACHE, ARTIFACTS["zone_stats"],
        )
        return JSONResponse(content=result, headers={"X-Data-Source": "model"})

    except asyncio.TimeoutError:
        logger.error("Heatmap inference timed out")
        return JSONResponse(
            content=MOCK_DATA["heatmap"],
            headers={"X-Data-Source": "mock", "X-Warning": "inference-timeout"},
        )
    except Exception as exc:
        logger.exception("Heatmap inference error: %s", exc)
        return JSONResponse(
            content=MOCK_DATA["heatmap"],
            headers={"X-Data-Source": "mock", "X-Warning": "inference-error"},
        )
