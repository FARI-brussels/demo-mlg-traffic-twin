# Traffic Scenario Generator - MLG Traffic Twin Demo

A traffic simulation and visualization tool using SUMO (Simulation of Urban MObility) for backend simulations and Vue 3 + Deck.gl for interactive 3D/2D visualization.

## Overview

This application allows you to:
- Generate traffic simulations with and without roadworks/closures
- Visualize traffic scenarios in 2D and 3D with animated vehicles
- Compare traffic metrics between scenarios
- Upload and manage multiple network configurations
- Analyze congestion patterns and traffic flow

## Prerequisites

- **Python 3.9+**
- **Node.js 18+** and npm
- **SUMO** installed with CLI tools (`netconvert`, `sumo`, `osmGet.py`, etc.) on PATH
  - Set `SUMO_HOME` environment variable (e.g., `/usr/share/sumo`)
- **Git LFS** - This repository uses Git LFS for large files (`.json`, `.geojson`, `.xml`)

### Git LFS Setup

If you haven't already, install and initialize Git LFS:

```bash
# Install git-lfs (Ubuntu/Debian)
sudo apt-get install git-lfs

# Or on macOS
brew install git-lfs

# Initialize Git LFS
git lfs install

git clone https://github.com/FARI-brussels/demo-mlg-traffic-twin.git
```

## Project Structure 

```bash
demo-mlg-traffic-twin/
├── backend/                  # Python Flask API
│   ├── main.py              # Main Flask application
│   ├── extract_osm.py       # OSM data extraction utilities
│   ├── fcd_to_trips.py      # FCD to trips conversion
│   ├── calculate_metrics.py # Traffic metrics computation
│   ├── generate_congestion_map.py
│   ├── get_osiris_closed_edges.py
│   ├── net2geojson.py       # Network to GeoJSON conversion
│   └── rerouters_fix.py
├── frontend/                 # Vue 3 + Deck.gl frontend
│   ├── src/
│   │   ├── App.vue          # Main app component
│   │   ├── components/      # Reusable Vue components
│   │   ├── views/           # Route views
│   │   ├── store.js         # State management
│   │   └── utils.js         # Utility functions
│   ├── public/
│   │   ├── networks/        # Network configurations (tracked with Git LFS)
│   │   │   ├── brussels_full/
│   │   │   ├── brussels_main_roads/
│   │   │   └── tulipe/
│   │   ├── routes/          # Route definitions
│   │   ├── simulations/     # Simulation outputs (gitignored)
│   │   ├── cars/            # 3D vehicle models (.glb)
│   │   └── configs.json     # Network configuration metadata
│   └── package.json
├── pyproject.toml           # Python dependencies
└── README.md

```

## Backend Setup

The backend uses Flask to provide an API for running SUMO simulations and processing results.

### 1. Create & activate a virtual environment

Using `uv` (recommended):

```bash
uv sync
source .venv/bin/activate
```

Or using standard Python:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```


This will install all dependencies including:
- Flask and Flask-CORS for the API
- requests, geojson, lxml for data processing
- numpy, pandas for numerical operations
- Development tools (pytest, black, ruff) if using `[dev]`

### 3. Configure SUMO environment

Ensure SUMO is properly configured:

```bash
# Set SUMO_HOME (adjust path as needed)
export SUMO_HOME=/usr/share/sumo

# Verify SUMO tools are accessible
which netconvert
which sumo
ls $SUMO_HOME/tools/
```

### 4. Run the backend server

You can run the backend in several ways:

```bash
# Option 1: Direct Python execution
cd backend
python main.py
```

The Flask API will be available at `http://0.0.0.0:8000`

**Main endpoints:**
- `POST /simulate` - Run traffic simulation
- `POST /upload_network` - Upload new network configuration
- `POST /fetch_closed_edges` - Fetch closed edges from external API
- And more...

## Frontend Setup

The frontend is built with Vue 3, Vite, and Deck.gl for high-performance 3D/2D visualization.

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure Mapbox Token

Create a `.env` file in the `frontend/` directory and add your Mapbox access token:

```bash
# frontend/.env
VITE_MAPBOX_TOKEN=your_mapbox_token_here
```

You can get a free Mapbox token by signing up at [mapbox.com](https://www.mapbox.com/).

**Note:** The `.env` file is gitignored and will not be committed to the repository.

### 3. Start development server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### 4. Build for production

```bash
npm run build
```

Built files will be in `frontend/dist/`

## Using the Application

### 1. Generate Simulation

1. Navigate to the **Generate Simulation** view
2. Select a network configuration from the dropdown
3. Click on road segments to select them
4. Add selected roads to the closed list
5. Configure simulation parameters:
   - Start time and end time
   - Insertion rate (vehicles/hour)
6. Click **Simulate** to run the simulation

### 2. View Results

After simulation completes, you'll be redirected to the **Results** view where you can:
- Toggle between "with roadworks" and "without roadworks" scenarios
- Switch between 2D and 3D visualization
- Play/pause/seek through the simulation timeline
- View animated vehicles (3D models in 3D view)
- Compare congestion maps and metrics
- Analyze traffic flow differences

### 3. Network Management

Networks are stored in `frontend/public/networks/` with the following structure:

```
networks/
└── <network_name>/
    ├── network.geojson      # Road network geometry
    ├── network_lanes.json   # Lane-level data
    └── network.net.xml      # SUMO network file
```

Networks are configured in `frontend/public/configs.json`

## Key Technologies

### Backend
- **Flask** - Web framework
- **SUMO** - Traffic simulation engine
- **Python 3.9+** - Core language

### Frontend
- **Vue 3** - UI framework
- **Deck.gl** - WebGL-based visualization
- **Mapbox GL** - Base maps
- **Vue Router** - Navigation
- **Vite** - Build tool

## Troubleshooting

### Map not displaying / Mapbox errors
Ensure you have set up your Mapbox token in `frontend/.env`:
```bash
VITE_MAPBOX_TOKEN=your_mapbox_token_here
```
Get a free token at [mapbox.com](https://www.mapbox.com/).

### SUMO not found
Ensure SUMO is installed and `SUMO_HOME` is set:
```bash
export SUMO_HOME=/usr/share/sumo
```

### Missing network files
If network files are not loading, ensure Git LFS is properly initialized and files are pulled:
```bash
git lfs pull
```

### Backend errors
Check that all Python dependencies are installed and SUMO tools are accessible:
```bash
python -c "import sys; print(sys.path)"
which netconvert sumo
```

### CORS issues
Ensure the backend is running on port 8000 and CORS is enabled (already configured in `main.py`)

### Large simulation output
Simulation outputs are stored in `backend/output/` and `frontend/public/simulations/`. These directories are gitignored. Adjust the insertion rate to control traffic volume.

## Development Notes

- Lane selection in frontend vs edge selection in backend (see `NOTES.txt`)
- Simulation outputs are automatically cleaned up but can be configured
- 3D vehicle models are in `frontend/public/cars/`
- Network configurations can be uploaded via the UI

## License

[Add your license information here] 