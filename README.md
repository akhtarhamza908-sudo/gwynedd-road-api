# Gwynedd Road Infrastructure API – Phase 2

A lightweight FastAPI application that queries the OpenStreetMap road network
for **Gwynedd, Wales, UK** and returns road length, coordinates, and attributes.

---

## Phase-2 Features

- **Road Attributes**: Returns classification (highway), surface type, and speed limits.
- **Improved Matching**: Supports partial name matches (e.g. "High" matches "High Street").
- **Input Validation**: Rejects empty or 1-character road names.
- **In-Memory Graph**: Road network is loaded once at startup via OSMnx.

---

## Technical Requirements

- **Python 3.10+**
- **FastAPI**
- **OSMnx**

---

## Environment Setup

### 1. Create a virtual environment (skip if `venv/` already exists)

```bash
python -m venv venv
```

### 2. Activate the virtual environment

**Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
**Windows (CMD):** `venv\Scripts\activate.bat`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Server

```bash
uvicorn app.main:app --reload
```

---

## API Testing

### 1. Swagger UI
Interactive docs at: `http://127.0.0.1:8000/docs`

### 2. Example GET Request
`http://127.0.0.1:8000/road/A487`

### 3. Example Response
```json
{
  "road_name": "A487",
  "total_length_meters": 150256.71,
  "start_point": [52.602173, -3.847566],
  "end_point": [52.99071, -4.266819],
  "classification": ["primary", "trunk"],
  "surface": ["asphalt"],
  "speed_limits": ["30 mph", "40 mph"]
}
```

---

## API Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| **GET** | `/` | Health check / welcome |
| **GET** | `/road/{road_name}` | Look up a road (Partial matches supported) |
| **GET** | `/docs` | Interactive Swagger UI |

