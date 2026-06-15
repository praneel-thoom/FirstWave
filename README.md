<div align="center">

# FirstWave

**Predictive EMS Staging Dashboard for NYC 911 Response**
Built for Georgia Tech's Data Science Hackathon: Hackalytics '26

<img src="dashboard.png" alt="FirstWave Dashboard" width="800"/>

</div>

---

## The Problem

New York City EMS responds to over **1.5 million 911 calls per year**. Despite that volume, ambulance deployment is still largely reactive  units sit at fixed stations until a call arrives, then race across the borough.

The result:

| Borough | Avg Response | vs. 8-min Clinical Threshold |
|---|---|---|
| Bronx | **10.6 min** | +33% over threshold |
| Manhattan | 10.5 min | +31% over threshold |
| Brooklyn | 9.4 min | +17% over threshold |
| Queens | 9.0 min | +12% over threshold |
| Staten Island | 8.0 min | At threshold |

For cardiac arrest, **every minute past 8 minutes reduces survival probability by ~10%**. The Bronx at 10.6 minutes means patients are already in a range where survival has dropped ~65% compared to a 4-minute response.

The issue isn't a shortage of ambulances. **It's wrong placement.**

Emergency demand is highly predictable  Friday evenings in the Bronx, summer weekends in Brooklyn  but the system doesn't act on those patterns ahead of time.

---

## The Solution

**FirstWave** is a predictive staging dashboard for NYC EMS dispatchers. It forecasts where 911 calls will cluster over the next hour using historical incident patterns, weather, and temporal demand signals  then recommends optimal pre-positioning locations for idle ambulances **before those calls arrive**.

---

## Key Results

Computed from **28.7 million validated NYC EMS incidents (2019–2023)**:

| Metric | Without FirstWave | With FirstWave |
|---|---|---|
| Incidents within 8-min clinical window | 64.7% | **86.0%** |
| Median response time saved |  | **3 min 19 sec** |
| Bronx coverage (worst borough) | 48.2% | **96.7%** |
| SVI Q4 (most vulnerable) savings |  | **299 seconds** |

The equity finding matters: FirstWave disproportionately benefits the city's most vulnerable neighborhoods because high-vulnerability zones overlap with highest-demand zones where staged ambulances are placed.

---

## Features

### Demand Heatmap
A live choropleth map colors all 31 NYC dispatch zones by predicted incident intensity  teal (low) through yellow/orange to red (critical). The forecast updates in real time as you change hour, day, weather, or ambulance count.

### Watch the Wave ▶
Hit the play button next to the hour slider and watch demand animate across 24 hours at 1.5-second intervals. The visual transition from a calm Monday 4AM to a red Friday 8PM is the core argument: demand is predictable, and staging should be proactive.

### Borough-Fair Staging Optimizer
A two-phase weighted K-Means algorithm places K ambulances at the mathematical center of predicted demand:
- **Phase 1:** Guarantees at least one staging point per borough (equity constraint)
- **Phase 2:** Distributes remaining ambulances proportionally to demand
- Each staging location covers a ~3,500m radius (8-minute urban drive at 25 km/h)

### Counterfactual Impact Engine
Compares actual historical response times against simulated drive times from staged locations, weather-adjusted with a travel factor of `1.0 + 0.012 × precip + 0.002 × max(0, wind − 15)`. Gives an honest, data-backed answer to: *how much faster would we have gotten there?*

### AI Dispatcher
A GPT-4o-mini-powered panel in the top-right corner of the dashboard. Two modes:
- **Auto-briefing:** Generates a 3-sentence operational summary every time the map updates (1.5s debounce). Tells dispatchers which zone has peak demand, what the coverage improvement is, and one concrete recommendation.
- **Interactive chat:** Describe any scenario in natural language. "Yankees game Friday night?", the AI responds and updates the map's hour and day controls automatically. If the map changes, an **↩ Undo** button appears in the chat to revert.

### Equity / SVI Layer
A ZIP-level Social Vulnerability Index overlay in a purple gradient (transparent → dark purple for SVI 0→1). The impact panel breaks down response time savings by SVI quartile, proving the algorithm is fair as well as fast.

### FDNY Stations Overlay
Toggle on ~31 FDNY EMS station locations as grey markers on the map. Hover for station name, borough, and address. The spatial gap between fixed station locations and where demand actually concentrates is immediately visible.

### Zone Detail Panel
Click any zone on the map to open a detail panel with its 24-hour demand curve, historical response time decomposition (dispatch vs. travel), SVI score, before/after response times, and acuity breakdown.

---

## Architecture

```
[ 28.7M NYC EMS Incidents (2005–2024) ]
         |
         v
[ DuckDB Pipeline ]  9 quality filters, weather merge, SVI join
         |
         +-- zone_baselines.parquet     rolling demand avg per (zone, hour, dow)
         +-- zone_stats.parquet         per-zone historical response stats
         +-- demand_model.pkl           20-feature XGBoost regressor
         +-- drive_time_matrix.pkl      OSMnx shortest paths, 1,891 zone pairs
         +-- counterfactual_*.parquet   precomputed impact for 168 (hour × dow) combos
         |
         v
[ FastAPI Backend ]   artifacts loaded at startup, all endpoints < 300ms
    GET  /api/heatmap           31-zone demand forecast GeoJSON
    GET  /api/staging           K optimal staging locations GeoJSON
    GET  /api/counterfactual    coverage + time saved + by_borough + by_svi + by_zone
    GET  /api/historical/:zone  per-zone 24-hour demand + response stats
    GET  /api/breakdown         borough-level performance breakdown
    GET  /api/stations          FDNY EMS station locations GeoJSON
    POST /api/ai                GPT-4o-mini auto-briefing / scenario chat
    GET  /health                artifact load status
    POST /reload                hot-reload artifacts without restart
         |
         v
[ React 19 + Mapbox GL JS 3.18 Dashboard ]
    Choropleth demand heatmap (31 dispatch zones, teal → red)
    Staging pins with 8-min coverage circles (3,500m radius)
    Watch the Wave animation (24-hour playback, 1.5s/step)
    FDNY stations overlay (grey markers, hover tooltips)
    Equity / SVI ZIP-level overlay (purple gradient)
    AI Dispatcher panel (auto-briefing + interactive chat + undo)
    Zone detail panel (click any zone)
    Impact metrics panel (coverage bars + histogram + equity chart)
    Control panel (hour slider, day picker, weather, ambulance count)
```

---

## Machine Learning

### Model A  XGBoost Demand Forecaster

**Target:** `incident_count` (incidents per dispatch zone per hour)
**Training:** 2019, 2021, 2022 (~5.6M clean incidents)
**Holdout:** 2023 (~1.5M clean incidents)
**RMSE:** ~6.0 incidents/zone/hour on 2023 holdout

**20 features:**

| Feature | Description |
|---|---|
| `hour_sin`, `hour_cos` | Cyclical hour encoding |
| `dow_sin`, `dow_cos` | Cyclical day-of-week encoding |
| `month_sin`, `month_cos` | Cyclical month encoding |
| `is_weekend` | 1 if Saturday or Sunday |
| `temperature_2m` | °C (Open-Meteo) |
| `precipitation` | mm/hr |
| `windspeed_10m` | km/h |
| `is_severe_weather` | WMO severe weather code flag |
| `svi_score` | CDC Social Vulnerability Index (0–1) |
| `zone_baseline_avg` | **Rolling avg per (zone, hour, dow)  47% feature importance** |
| `high_acuity_ratio` | Historical % of severity codes 1+2 |
| `held_ratio` | Historical % of held calls |
| `is_holiday` | Federal holiday flag |
| `is_major_event` | NYC major event flag |
| `is_school_day` | School session flag |
| `is_heat_emergency` | Temperature ≥ 32°C |
| `is_extreme_heat` | Temperature ≥ 35°C |
| `subway_disruption_idx` | 0–1 MTA disruption level |

### Model B  Borough-Fair Staging Optimizer

Two-phase weighted K-Means:
1. One staging point guaranteed per borough (equity constraint), placed at demand-weighted centroid
2. Remaining K−5 points allocated one-at-a-time to the borough with the highest `demand / current_clusters` ratio
3. Within each borough: K-Means with demand weights when N > 1 cluster

**Coverage radius:** 3,500m (~8-minute urban drive at 25 km/h)

### Counterfactual Engine

For each precomputed (hour, dow) combination:
- Simulates staged response by routing through OSMnx drive-time matrix
- Applies weather travel factor to both static and staged times
- Estimates % within 8-minute threshold using a lognormal CDF (CV = 0.95, calibrated to real EMS distributions)
- Aggregates by borough, SVI quartile, and dispatch zone (demand-weighted)

---

## Data Sources

| Source | What We Used |
|---|---|
| [NYC Open Data  EMS Incident Dispatch Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj) | 28.7M rows, 2005–2024 |
| [Open-Meteo Historical Weather API](https://archive-api.open-meteo.com) | Hourly temperature, precipitation, windspeed for NYC  free, no key |
| [CDC Social Vulnerability Index](https://www.atsdr.cdc.gov/placeandhealth/svi/) | RPL_THEMES composite score per census tract, aggregated to dispatch zone |
| [OpenStreetMap via OSMnx](https://osmnx.readthedocs.io) | Full NYC road network  1,891 zone-pair drive times computed pre-hackathon |

All data sources are free and publicly available. No proprietary data.

---

## Data Quality

9 sequential quality filters applied before training:

```python
df = df[
    (df['VALID_INCIDENT_RSPNS_TIME_INDC'] == 'Y') &       # valid response time flag
    (df['VALID_DISPATCH_RSPNS_TIME_INDC'] == 'Y') &        # valid dispatch time flag
    (df['REOPEN_INDICATOR'] == 'N') &                      # exclude reopened incidents
    (df['TRANSFER_INDICATOR'] == 'N') &                    # exclude transfers
    (df['STANDBY_INDICATOR'] == 'N') &                     # exclude standbys
    (df['INCIDENT_RESPONSE_SECONDS_QY'].between(1, 7200)) &# response time sanity check
    (df['BOROUGH'] != 'UNKNOWN') &                         # known borough
    (df['INCIDENT_DISPATCH_AREA'].isin(VALID_ZONES)) &     # one of 31 clean zones
    (zone_prefix_matches_borough)                          # B→BRONX, K→BROOKLYN, etc.
]
```

- **96.2%** of rows have valid response time flags
- 2020 excluded entirely (COVID anomaly  1.42M rows, structurally different patterns)
- Result: 5.6M clean training rows, 1.5M clean holdout rows

---

## Running the App

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional, for PostGIS zone boundary geometries  graceful fallback without it)
- An OpenAI API key (optional, for AI Dispatcher  panel shows an informative error without it)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:
```
DATABASE_URL=postgresql://pp_user:pp_pass@localhost:5432/firstwave
ARTIFACTS_DIR=./artifacts
OPENAI_API_KEY=sk-...
```

**Optional  PostGIS (for precise zone boundaries):**
```bash
docker run --name firstwave-db \
  -e POSTGRES_DB=firstwave \
  -e POSTGRES_USER=pp_user \
  -e POSTGRES_PASSWORD=pp_pass \
  -p 5432:5432 \
  -d postgis/postgis:15-3.4

python3 backend/scripts/seed_zone_boundaries.py
```
*Without Docker, zone geometries fall back to bounding-box approximations from mock data  the app still runs.*

Start the server:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Health check: `curl http://127.0.0.1:8000/health`

### 2. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:
```
VITE_MAPBOX_TOKEN=pk.eyJ1IjoiLi4u...
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start dev server:
```bash
npm run dev   # http://localhost:3000
```

### 3. Hot-reload ML artifacts

If new model artifacts are dropped into `backend/artifacts/`:
```bash
curl -X POST http://localhost:8000/reload
```

---

## Dispatch Zones

31 clean operational dispatch zones across 5 boroughs:

```
Bronx:        B1  B2  B3  B4  B5
Brooklyn:     K1  K2  K3  K4  K5  K6  K7
Manhattan:    M1  M2  M3  M4  M5  M6  M7  M8  M9
Queens:       Q1  Q2  Q3  Q4  Q5  Q6  Q7
Staten Island: S1  S2  S3
```

---

## Demo Scenarios

| Preset | Hour | Day | What it shows |
|---|---|---|---|
| **Fri 8PM Peak** | 20:00 | Friday | Bronx + Brooklyn go red. 5 staging points cluster around high-demand zones. This is the pitch. |
| **Mon 4AM Quiet** | 04:00 | Monday | Map goes teal-green across all boroughs. Contrast with Friday demonstrates demand is predictable. |
| **Storm** | 18:00 | Wednesday | Weather amplifies demand + travel times. More zones turn orange/red. FirstWave accounts for weather in both forecast and counterfactual. |

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| ML  Demand Forecasting | XGBoost | 2.0.3 |
| ML  Staging Optimizer | scikit-learn (K-Means) | 1.4.1 |
| ML  AI Dispatcher | OpenAI GPT-4o-mini | latest |
| Spatial Routing | OSMnx + NetworkX | 1.9.1 / 3.3 |
| Data Processing | DuckDB, pandas, pyarrow | 1.4+ / 2.2.1 / 16.0 |
| Backend API | FastAPI + Uvicorn | 0.110.0 / 0.29.0 |
| Database | PostgreSQL + PostGIS | 15 + 3.4 |
| Frontend | React | 19.2.0 |
| Map | Mapbox GL JS + react-map-gl | 3.18.1 / 7.1.9 |
| Charts | Plotly.js | 3.4.0 |
| Data Fetching | TanStack React Query | 5.90 |
| HTTP Client | Axios | 1.13.5 |
| Styling | Tailwind CSS | 4.2.0 |
| Build Tool | Vite | 7.3.1 |

---

## Repo Structure

```
firstwave/
├── backend/
│   ├── main.py                 App startup, CORS, artifact loading, health/reload
│   ├── routers/
│   │   ├── heatmap.py          GET /api/heatmap
│   │   ├── staging.py          GET /api/staging
│   │   ├── counterfactual.py   GET /api/counterfactual
│   │   ├── historical.py       GET /api/historical/:zone
│   │   ├── breakdown.py        GET /api/breakdown
│   │   ├── stations.py         GET /api/stations
│   │   └── ai_panel.py         POST /api/ai
│   ├── models/
│   │   ├── demand_forecaster.py    XGBoost inference wrapper (all 31 zones)
│   │   └── staging_optimizer.py    Borough-fair weighted K-Means
│   ├── artifacts/              Pre-computed ML artifacts (pkl + parquet)
│   ├── scripts/
│   │   └── seed_zone_boundaries.py PostGIS seeding
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── App.jsx             Root state manager
│       ├── constants.js        Tokens, zone data, presets
│       ├── components/
│       │   ├── Map/
│       │   │   ├── MapContainer.jsx    Mapbox wrapper + event routing
│       │   │   ├── ZoneChoropleth.jsx  Demand intensity polygon outlines
│       │   │   ├── StagingPins.jsx     Ambulance pins + coverage circles
│       │   │   ├── StationLayer.jsx    FDNY station markers
│       │   │   ├── EquityLayer.jsx     SVI ZIP-level overlay
│       │   │   ├── ZoneTooltip.jsx     Hover tooltip
│       │   │   └── ZoneDetailPanel.jsx Click-to-expand zone stats
│       │   ├── Controls/
│       │   │   ├── ControlPanel.jsx    Left sidebar wrapper
│       │   │   ├── TimeSlider.jsx      Hour slider + Watch the Wave ▶ button
│       │   │   ├── DayPicker.jsx       Mon–Sun selector
│       │   │   ├── WeatherSelector.jsx Clear / Light Rain / Heavy Storm
│       │   │   ├── AmbulanceCount.jsx  K selector (1–10)
│       │   │   └── LayerToggle.jsx     Heatmap / Staging / Coverage / Stations
│       │   ├── Impact/
│       │   │   ├── ImpactPanel.jsx     Bottom impact bar
│       │   │   ├── CoverageBars.jsx    Before/after 8-min coverage bars
│       │   │   ├── ResponseHistogram.jsx Baseline vs. staged histogram
│       │   │   ├── EquityChart.jsx     SVI quartile savings chart
│       │   │   └── OverlayPanel.jsx    Equity layer toggle + legend
│       │   └── Chat/
│       │       └── AiPanel.jsx         AI Dispatcher (pill button → expanded panel)
│       └── hooks/
│           ├── useHeatmap.js
│           ├── useStaging.js
│           ├── useCounterfactual.js
│           ├── useZoneHistory.js
│           └── useStations.js
│
├── pipeline/                   DuckDB pipeline (8 scripts)
│   └── test_artifacts.py       41-check artifact validation suite
│
├── data/
    ├── mock_api_responses.json All endpoints mocked (frozen at Hour 0)
    ├── ems_stations.json       31 FDNY EMS station locations
    └── zone_centroids.json     31 dispatch zone centroids

```

---
