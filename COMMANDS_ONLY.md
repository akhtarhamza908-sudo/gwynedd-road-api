# Commands Only - Gwynedd Road Network API

## ONE-TIME SETUP (First Time Only)

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment file
copy .env.example .env

# 5. Edit .env and update DATABASE_URL with your password
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/gwynedd_roads

# 6. Create database tables
python recreate_tables.py

# 7. Start server
python -m uvicorn app.main:app --reload

# 8. In NEW PowerShell window - Sync data
curl.exe -s http://localhost:8000/api/v1/admin/sync -X POST
```

---

## DAILY USAGE (After Setup)

```powershell
# Navigate and activate
cd "C:\Users\[USERNAME]\Desktop\gwynedd-road-Project"
venv\Scripts\activate

# Start server
python -m uvicorn app.main:app --reload
```

Or simply double-click: `QUICK_START.bat`

---

## DATABASE COMMANDS (PostgreSQL)

```sql
-- Create database
CREATE DATABASE gwynedd_roads;

-- Enable PostGIS
\c gwynedd_roads;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify PostGIS
SELECT PostGIS_Version();
```

---

## API TEST COMMANDS

```powershell
# Check total roads
(irm http://localhost:8000/api/v1/roads -Method GET | Select-Object -ExpandProperty total)

# Get roads list
irm http://localhost:8000/api/v1/roads -Method GET

# Search road
irm "http://localhost:8000/api/v1/roads/search?q=A487" -Method GET

# Get road by ID
irm http://localhost:8000/api/v1/roads/1 -Method GET

# Get road segments
irm http://localhost:8000/api/v1/roads/1/segments -Method GET

# Get GeoJSON
irm http://localhost:8000/api/v1/roads/geojson -Method GET
```

---

## TROUBLESHOOTING COMMANDS

```powershell
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID [PID_NUMBER] /F

# Recreate tables
python recreate_tables.py

# Re-sync data
curl.exe -s http://localhost:8000/api/v1/admin/sync -X POST
```

---

## URLS

- API Base: `http://localhost:8000/api/v1`
- Documentation: `http://localhost:8000/docs`
- Admin Sync: `POST http://localhost:8000/api/v1/admin/sync`
