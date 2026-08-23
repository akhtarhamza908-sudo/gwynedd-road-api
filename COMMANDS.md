# Gwynedd Road Infrastructure API — Commands & Setup Guide

---

## 1. First-Time Setup

**Create virtual environment:**
```powershell
python -m venv venv
```

**Activate virtual environment:**
```powershell
venv\Scripts\activate
```

**Install all dependencies:**
```powershell
venv\Scripts\pip.exe install -r requirements.txt
```

---

## 2. Database Setup (PostgreSQL)

Run these once before starting the server.

**Step 1 — Create the database** (in psql or pgAdmin):
```sql
CREATE DATABASE gwynedd_roads;
```

**Step 2 — Enable PostGIS extension** (inside gwynedd_roads database):
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

**Step 3 — Create all tables** (run after server dependencies are installed):
```powershell
venv\Scripts\python.exe -c "from app.database.connection import init_db; init_db(); print('Tables created')"
```

---

## 3. Environment Configuration

The `.env` file is already configured. Default values:

```
DATABASE_URL=postgresql://postgres:123@localhost:5432/gwynedd_roads
REDIS_URL=redis://localhost:6379/0
APP_NAME=Gwynedd Road Infrastructure API
DEBUG=false
LOG_LEVEL=INFO
ELEVATION_API_URL=https://api.open-elevation.com/api/v1/lookup
OSM_PLACE=Gwynedd, Wales, United Kingdom
OSM_NETWORK_TYPE=drive
```

Change `DATABASE_URL` if your PostgreSQL username or password is different.

---

## 4. Start the Server

**Development mode (auto-reload on file changes):**
```powershell
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Production mode (multiple workers):**
```powershell
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Quick start (minimal logs):**
```powershell
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning
```

Server runs at: `http://127.0.0.1:8000`

---

## 5. Browser URLs

| Purpose                  | URL                                   |
|--------------------------|---------------------------------------|
| Swagger UI (interactive) | http://127.0.0.1:8000/docs            |
| ReDoc (full schema)      | http://127.0.0.1:8000/redoc           |
| API Root / Info          | http://127.0.0.1:8000/               |
| OpenAPI JSON Schema      | http://127.0.0.1:8000/openapi.json    |

---

## 6. Run All Endpoint Tests

**Quick pass/fail test (all 22 endpoints):**
```powershell
venv\Scripts\python.exe test_endpoints.py
```

**Full test — saves complete JSON responses to `endpoint_results.txt`:**
```powershell
venv\Scripts\python.exe test_results.py
```

**Open the results file:**
```powershell
notepad endpoint_results.txt
```

---

## 7. All API Endpoints

### Admin
| Method | Endpoint                      | Description                        |
|--------|-------------------------------|------------------------------------|
| GET    | /api/v1/admin/health          | Health check (DB + cache status)   |
| POST   | /api/v1/admin/init-db         | Initialize database tables         |
| POST   | /api/v1/admin/sync            | Trigger background OSM data sync   |
| POST   | /api/v1/admin/cache/clear     | Clear all cached data              |

### Roads
| Method | Endpoint                                  | Description                            |
|--------|-------------------------------------------|----------------------------------------|
| GET    | /api/v1/roads                             | List all roads (paginated)             |
| GET    | /api/v1/roads/statistics                  | Count of roads, segments, total length |
| GET    | /api/v1/roads/{road_id}                   | Get a single road by ID                |
| GET    | /api/v1/roads/by-name/{name}              | Get road by exact name                 |
| GET    | /api/v1/roads/{road_id}/segments          | Get all segments of a road             |
| GET    | /api/v1/roads/{road_id}/bbox              | Get bounding box of a road             |
| GET    | /api/v1/roads/{road_id}/geojson           | Export road as GeoJSON                 |
| GET    | /api/v1/roads/{road_id}/analysis          | Aggregated geometry analysis           |
| GET    | /api/v1/roads/{road_id}/elevation-profile | Elevation profile of a road            |
| POST   | /api/v1/roads/{road_id}/analyze           | Re-run analysis on a road              |
| GET    | /api/v1/roads/{road_id}/segments/{seg_id}/analysis | Segment-level geometry analysis |

### Search
| Method | Endpoint                          | Description                          |
|--------|-----------------------------------|--------------------------------------|
| GET    | /api/v1/roads/search?query=       | Smart search by road name or ref     |
| GET    | /api/v1/roads/search/suggestions?query= | Autocomplete suggestions        |
| GET    | /api/v1/roads/nearby?lat=&lon=&radius= | Find roads near GPS coordinates |

### Legacy
| Method | Endpoint            | Description                          |
|--------|---------------------|--------------------------------------|
| GET    | /road/{road_name}   | Redirects to /api/v1/roads/by-name/  |

---

## 8. Individual Endpoint Test Commands

**Health check:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/admin/health'); print(r.text)"
```

**List roads:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads'); print(r.text[:800])"
```

**Road statistics:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/statistics'); print(r.text)"
```

**Search roads:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/search?query=High'); print(r.text)"
```

**Autocomplete suggestions:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/search/suggestions?query=High'); print(r.text)"
```

**Nearby roads (by GPS):**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/nearby?lat=52.9&lon=-4.1&radius=1000'); print(r.text)"
```

**Get road by ID:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/1'); print(r.text)"
```

**Get road segments:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/1/segments'); print(r.text)"
```

**Get bounding box:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/1/bbox'); print(r.text)"
```

**GeoJSON export:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/1/geojson'); print(r.text[:500])"
```

**Road analysis:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/1/analysis'); print(r.text)"
```

**Elevation profile:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/1/elevation-profile'); print(r.text)"
```

**Re-run analysis:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.post('http://127.0.0.1:8000/api/v1/roads/1/analyze'); print(r.text)"
```

**Segment analysis:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/roads/1/segments/1/analysis'); print(r.text)"
```

**Trigger OSM data sync (background, takes 1-3 minutes):**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.post('http://127.0.0.1:8000/api/v1/admin/sync', timeout=10); print(r.text)"
```

**Clear cache:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.post('http://127.0.0.1:8000/api/v1/admin/cache/clear'); print(r.text)"
```

**Initialize database:**
```powershell
venv\Scripts\python.exe -c "import httpx; r=httpx.post('http://127.0.0.1:8000/api/v1/admin/init-db'); print(r.text)"
```

---

## 9. Verify App Loads

**Check all routes are registered:**
```powershell
venv\Scripts\python.exe -c "from app.main import app; print('OK -', len(app.routes), 'routes loaded')"
```

**Print all registered routes:**
```powershell
venv\Scripts\python.exe -c "from app.main import app; [print(m, r.path) for r in app.routes if hasattr(r,'methods') and r.methods for m in r.methods if m!='HEAD']"
```

---

## 10. Common Issues

**PostgreSQL not running:**
Make sure PostgreSQL service is started before running the server.

**Redis authentication error:**
Redis is optional. If Redis requires a password, update `REDIS_URL` in `.env` or leave it out — the app falls back to in-memory caching automatically.

**Port already in use:**
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Module not found:**
Make sure the virtual environment is activated and dependencies are installed:
```powershell
venv\Scripts\activate
venv\Scripts\pip.exe install -r requirements.txt
```
