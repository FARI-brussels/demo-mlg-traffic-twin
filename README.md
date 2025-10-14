# Traffic Scenario Generator (SUMO + Vue)

## Prerequisites

- Python 3.9+
- Node.js 18+ and npm
- SUMO installed (CLI tools `netconvert` and `sumo` on PATH)
  - Set `SUMO_HOME` if not automatically detected (e.g., `/usr/share/sumo`)

## Backend (Flask)

You can use either pip or `uv` to manage the Python environment.

### Option A: pip + venv

1. Create & activate a virtual environment (recommended):

```bash
uv venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
uv sync
```

3. Ensure SUMO is available:

- `netconvert` and `sumo` must be in your PATH
- `SUMO_HOME` should point to your SUMO install (used to locate `tools/`)  
  Example:

```bash
export SUMO_HOME=/usr/share/sumo
```

4. Run the backend:

```bash
python backend.py
```

- The API will listen on `http://0.0.0.0:8000`
- Endpoint used by the frontend: `POST /simulate`


## Frontend (Vue 3 + Vite)

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Start the dev server:

```bash
npm run dev
```

- The app runs at `http://localhost:5173`
- The frontend loads `net.geojson` from `frontend/public/net.geojson` (or `frontend/net.geojson`).
- It communicates with the backend at `http://localhost:8000`.

## Using the App

1. Visit the frontend URL in your browser.
2. On the left map (Generate Simulation):
   - Click road segments to select, then "Add to closed list" to mark them as closed.
   - Set start/stop times and optionally adjust insertion rate.
   - Click "Simulate" to run the pipeline.
3. After the simulation completes, you are redirected to the results screen:
   - Use the toggle to view "with roadworks" or "without roadworks".
   - 2D view colors vehicles by speed/max-speed ratio (computed on the backend).
   - Closed roads render in red only in the "with roadworks" scenario.

## Troubleshooting

- Missing SUMO tools: Ensure `netconvert`, `sumo`, and `SUMO_HOME/tools` exist and are accessible.
- Missing `net.geojson`: Place your network file at `frontend/public/net.geojson` (preferred) or `frontend/net.geojson`.
- Large runs: The pipeline writes intermediate files to `output/`. Adjust `insertion_rate` to control traffic volume.
- CORS errors: Ensure the backend is running on port 8000 and CORS is enabled. 