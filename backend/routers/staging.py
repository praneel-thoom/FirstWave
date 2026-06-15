import asyncio
import logging
from functools import lru_cache
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache(maxsize=168)
def _cached_heatmap_and_staging(
    hour: int, dow: int, month: int,
    temperature: float, precipitation: float, windspeed: float,
    ambulances: int,
):
    """
    Cached combined heatmap+staging computation keyed by param tuple.
    168 = 24 hours × 7 days of caching capacity.
    """
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
    return staging_points


@router.get("/staging")
async def get_staging(
    hour: int = Query(..., ge=0, le=23),
    dow: int = Query(..., ge=0, le=6),
    month: int = Query(..., ge=1, le=12),
    temperature: float = Query(default=15.0),
    precipitation: float = Query(default=0.0),
    windspeed: float = Query(default=10.0),
    ambulances: int = Query(default=5, ge=1, le=10),
):
    from main import ARTIFACTS, MOCK_DATA

    if ARTIFACTS["demand_model"] is None or ARTIFACTS["baselines"] is None:
        logger.info("Staging: model not loaded, returning mock data")
        return JSONResponse(
            content=MOCK_DATA["staging"],
            headers={"X-Data-Source": "mock"},
        )

    try:
        staging_points = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: _cached_heatmap_and_staging(
                    hour, dow, month,
                    round(temperature, 1), round(precipitation, 1), round(windspeed, 1),
                    ambulances,
                ),
            ),
            timeout=5.0,
        )

        features = []
        for pt in staging_points:
            features.append({
                "type": "Feature",
                "properties": {
                    "staging_index": pt["staging_index"],
                    "coverage_radius_m": pt["coverage_radius_m"],
                    "predicted_demand_coverage": pt["predicted_demand_coverage"],
                    "cluster_zones": pt["cluster_zones"],
                    "zone_count": pt["zone_count"],
                },
                # GeoJSON Point coordinates MUST be [lon, lat]
                "geometry": {
                    "type": "Point",
                    "coordinates": [pt["lon"], pt["lat"]],
                },
            })

        result = {
            "type": "FeatureCollection",
            "ambulance_count": ambulances,
            "features": features,
        }
        return JSONResponse(content=result, headers={"X-Data-Source": "model"})

    except asyncio.TimeoutError:
        logger.error("Staging inference timed out")
        return JSONResponse(
            content=MOCK_DATA["staging"],
            headers={"X-Data-Source": "mock", "X-Warning": "inference-timeout"},
        )
    except Exception as exc:
        logger.exception("Staging inference error: %s", exc)
        return JSONResponse(
            content=MOCK_DATA["staging"],
            headers={"X-Data-Source": "mock", "X-Warning": "inference-error"},
        )
