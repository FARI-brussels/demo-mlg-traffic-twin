<template>
  <div id="container" style="position:relative; width:100%; height:100%">
    <div ref="mapContainer" :id="containerId" style="position:absolute; inset:0"></div>
    
    <div id="controls" style="position:absolute; top:12px; left:12px; z-index:10; background:rgba(255,255,255,0.9); border-radius:8px; padding:10px 12px; box-shadow:0 2px 8px rgba(0,0,0,0.15); min-width: 320px;">
      <!-- 2D/3D Toggle -->
      <div class="row" style="display:flex; align-items:center; gap:8px; margin:6px 0; padding-bottom:8px; border-bottom:1px solid #ddd;">
        <label for="mode">Mode</label>
        <select id="mode" v-model="mode">
          <option value="2d">2D</option>
          <option value="3d">3D</option>
        </select>
      </div>
      
      <!-- Playback Controls -->
      <div class="row" style="display:flex; align-items:center; gap:8px; margin:6px 0;">
        <button @click="playing = true">Play</button>
        <button @click="playing = false">Pause</button>
        <label for="speed">Speed</label>
        <select id="speed" v-model.number="speed">
          <option :value="0.5">0.5x</option>
          <option :value="1">1x</option>
          <option :value="2">2x</option>
          <option :value="5">5x</option>
          <option :value="10">10x</option>
          <option :value="30">30x</option>
          <option :value="60">60x</option>
        </select>
      </div>
      
      <!-- Time Control -->
      <div class="row" style="display:flex; align-items:center; gap:8px; margin:6px 0;">
        <label for="time">Time</label>
        <input id="time" type="range" :min="minTime" :max="maxTime" step="0.1" v-model.number="currentTime">
        <div style="min-width:64px; text-align:right;">{{ currentTime.toFixed(1) }} s</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import { store } from '../store'
import { buildSumoNetworkLayers } from '../utils.js'

const props = defineProps({
  dataset: { type: String, required: true } // 'with' | 'without'
})

// UI State
const mode = ref('2d') // '2d' or '3d'
const mapContainer = ref(null)
const currentTime = ref(0)
const playing = ref(true)
const speed = ref(1)

// Data
let trips = []
let minTime = ref(0), maxTime = ref(3600)
const closedEdgesFromTrips = ref([])
const vehicleCarAssignments = new Map() // Map of vehicle ID to car number (1-7)

// Rendering engines
let map = null // Mapbox (3D mode)
let deckgl = null // Standalone deck.gl (2D mode)
let deckOverlay = null // Deck overlay for Mapbox (3D mode)
let animationFrameId = null
let lastTimestamp = null

const containerId = computed(() => mode.value === '3d' ? 'map3d' : 'deck2d')

// ===== SHARED UTILITY FUNCTIONS =====

function interpolateSample(d, t) {
  const path = d.path
  const n = path.length
  if (!n) return null
  if (t < path[0][2] || t > path[n - 1][2]) return null
  
  const getPoint = (p) => ({
    pos: [p[0], p[1]],
    spd_mps: p[3] || 0,
    ratio: p[4] != null ? p[4] : 0,
    angle: p[5] || 0
  })
  
  if (t === path[0][2]) return getPoint(path[0])
  if (t === path[n - 1][2]) return getPoint(path[n - 1])
  
  let lo = 0, hi = n - 1
  while (lo + 1 < hi) {
    const mid = (lo + hi) >> 1
    if (path[mid][2] <= t) lo = mid; else hi = mid
  }
  
  const p0 = path[lo], p1 = path[hi]
  const dt = p1[2] - p0[2]
  const f = dt > 0 ? (t - p0[2]) / dt : 0
  const lon = p0[0] + (p1[0] - p0[0]) * f
  const lat = p0[1] + (p1[1] - p0[1]) * f
  const spd_mps = (p0[3] || 0) + ((p1[3] || 0) - (p0[3] || 0)) * f
  const r0 = p0[4] != null ? p0[4] : null
  const r1 = p1[4] != null ? p1[4] : null
  const ratio = (r0 != null && r1 != null) ? (r0 + (r1 - r0) * f) : (r0 != null ? r0 : (r1 != null ? r1 : 0))
  const angle = (p0[5] || 0) + ((p1[5] || 0) - (p0[5] || 0)) * f
  
  return { pos: [lon, lat], spd_mps, ratio, angle }
}

function clamp(v, a, b) { 
  return Math.max(a, Math.min(b, v)) 
}

function colorFromFraction(frac) {
  const t = clamp(frac, 0, 1)
  const stops = [[215,25,28], [255,255,191], [26,150,65]]
  const seg = Math.min(1, Math.floor(t * 2))
  const lt = (t * 2) - seg
  const a = stops[seg], b = stops[seg + 1]
  const r = Math.round(a[0] + (b[0] - a[0]) * lt)
  const g = Math.round(a[1] + (b[1] - a[1]) * lt)
  const bl = Math.round(a[2] + (b[2] - a[2]) * lt)
  return [r, g, bl, 220]
}

function recomputeRanges() {
  let minT = Infinity, maxT = -Infinity
  for (const t of trips) {
    for (const p of t.path) {
      const ts = p[2]
      if (ts < minT) minT = ts
      if (ts > maxT) maxT = ts
    }
  }
  if (!isFinite(minT) || !isFinite(maxT)) { minT = 0; maxT = 3600 }
  minTime.value = minT
  maxTime.value = maxT
  currentTime.value = minT
}

function loadTrips() {
  const dataObj = (props.dataset === 'with') ? (store.tripsWith || null) : (store.tripsWout || null)
  if (dataObj && Array.isArray(dataObj.trips)) {
    trips = dataObj.trips
    const metaEdges = (dataObj.metadata && Array.isArray(dataObj.metadata.closed_edges)) 
      ? dataObj.metadata.closed_edges : []
    closedEdgesFromTrips.value = metaEdges.map(e => String(e))
  } else {
    trips = []
    closedEdgesFromTrips.value = []
  }
  recomputeRanges()
  updateVisualization()
}

function computeInitialCenter() {
  if (store.netData && Array.isArray(store.netData.features)) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    
    function visitCoords(coords) {
      if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
        const x = coords[0], y = coords[1]
        if (x < minX) minX = x
        if (y < minY) minY = y
        if (x > maxX) maxX = x
        if (y > maxY) maxY = y
      } else { 
        for (const c of coords) visitCoords(c) 
      }
    }
    
    for (const f of store.netData.features) {
      const g = f && f.geometry
      if (g && g.coordinates) visitCoords(g.coordinates)
    }
    
    if (isFinite(minX) && isFinite(minY) && isFinite(maxX) && isFinite(maxY)) {
      return [(minX + maxX) / 2, (minY + maxY) / 2]
    }
  }
  
  if (trips.length > 0 && trips[0].path.length > 0) {
    return [trips[0].path[0][0], trips[0].path[0][1]]
  }
  
  return [4.3667, 50.8219] // Brussels default
}

// ===== 3D MODE (MAPBOX) =====

function getVehiclesData3D() {
  // Group vehicles by car model (1-7)
  const vehiclesByCarModel = {
    1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []
  }
  
  trips.forEach(trip => {
    const sample = interpolateSample(trip, currentTime.value)
    if (sample) {
      const [lon, lat] = sample.pos
      const elevation = 0 // Constant elevation for all vehicles
      
      // Assign car model to vehicle if not already assigned
      if (!vehicleCarAssignments.has(trip.id)) {
        const carNumber = Math.floor(Math.random() * 7) + 1
        vehicleCarAssignments.set(trip.id, carNumber)
      }
      
      const carNumber = vehicleCarAssignments.get(trip.id)
      
      vehiclesByCarModel[carNumber].push({
        position: [lon, lat, elevation],
        angle: sample.angle + 180 || 0,
        id: trip.id
      })
    }
  })
  
  return vehiclesByCarModel
}

function updateLayers3D() {
  if (!deckOverlay || !map || !map.isStyleLoaded()) return
  
  const vehiclesByCarModel = getVehiclesData3D()
  const layers = []
  
  // Add network layers
  if (store.sumoNetworkData) {
    const updateTriggers = {
      getFillColor: [closedEdgesFromTrips.value.join(','), props.dataset],
      getLineColor: []
    }
    const sumoLayers = buildSumoNetworkLayers(
      store.sumoNetworkData,
      window.deck,
      {
        onHover: undefined,
        onClick: undefined,
        updateTriggers,
        getClosedPredicate: props2 => {
          const fullId = String((props2.id || props2.osm_id) || '')
          const baseEdgeId = fullId.replace(/_\d+$/, '')
          return (props.dataset === 'with') && 
            Array.isArray(closedEdgesFromTrips.value) && 
            closedEdgesFromTrips.value.includes(baseEdgeId)
        },
        getSelectedId: () => null,
        getHoveredId: () => null,
      }
    )
    layers.push(...sumoLayers)
  }
  
  // Create 7 separate vehicle layers, one for each car model
  for (let carNumber = 1; carNumber <= 7; carNumber++) {
    layers.push(
      new window.deck.ScenegraphLayer({
        id: `cars-${carNumber}`,
        data: vehiclesByCarModel[carNumber],
        scenegraph: `/cars/car${carNumber}.glb`,
        getPosition: d => d.position,
        getOrientation: d => [0, -d.angle, 90],
        sizeScale: 1,
        _lighting: 'pbr'
      })
    )
  }
  
  deckOverlay.setProps({ layers })
}

// ===== 2D MODE (DECK.GL STANDALONE) =====

function makeLayers2D() {
  const baseMap = new window.deck.TileLayer({
    id: 'osm-tiles', 
    data: 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', 
    minZoom: 0, 
    maxZoom: 19, 
    tileSize: 256,
    renderSubLayers: props => {
      const { bbox: { west, south, east, north } } = props.tile
      return new window.deck.BitmapLayer(props, { 
        data: null, 
        image: props.data, 
        bounds: [west, south, east, north] 
      })
    }
  })

  const vehicles = new window.deck.ScatterplotLayer({
    id: 'vehicles',
    data: trips,
    getPosition: d => {
      const s = interpolateSample(d, currentTime.value)
      return s ? s.pos : null
    },
    getFillColor: d => {
      const s = interpolateSample(d, currentTime.value)
      if (!s) return [0, 0, 0, 0]
      const frac = (typeof s.ratio === 'number') ? s.ratio : 0
      return colorFromFraction(frac)
    },
    getRadius: 6,
    radiusUnits: 'pixels',
    stroked: true,
    getLineColor: [0, 0, 0],
    lineWidthUnits: 'pixels',
    lineWidthMinPixels: 1,
    updateTriggers: {
      getPosition: [currentTime.value],
      getFillColor: [currentTime.value]
    }
  })

  const layers = [baseMap]
  
  if (store.sumoNetworkData) {
    const updateTriggers = {
      getFillColor: [closedEdgesFromTrips.value.join(','), props.dataset],
      getLineColor: []
    }
    const sumoLayers = buildSumoNetworkLayers(
      store.sumoNetworkData,
      window.deck,
      {
        onHover: undefined,
        onClick: undefined,
        updateTriggers,
        getClosedPredicate: props2 => {
          const fullId = String((props2.id || props2.osm_id) || '')
          const baseEdgeId = fullId.replace(/_\d+$/, '')
          return (props.dataset === 'with') && 
            Array.isArray(closedEdgesFromTrips.value) && 
            closedEdgesFromTrips.value.includes(baseEdgeId)
        },
        getSelectedId: () => null,
        getHoveredId: () => null,
      }
    )
    layers.push(...sumoLayers)
  }

  layers.push(vehicles)
  return layers
}

function updateLayers2D() {
  if (!deckgl) return
  deckgl.setProps({ layers: makeLayers2D() })
}

// ===== UNIFIED UPDATE =====

function updateVisualization() {
  if (mode.value === '3d') {
    updateLayers3D()
  } else {
    updateLayers2D()
  }
}

// ===== ANIMATION =====

function animate(timestamp) {
  if (!playing.value) {
    animationFrameId = requestAnimationFrame(animate)
    lastTimestamp = timestamp
    return
  }
  
  if (lastTimestamp === null) lastTimestamp = timestamp
  
  const deltaTime = (timestamp - lastTimestamp) / 1000
  lastTimestamp = timestamp
  currentTime.value += deltaTime * speed.value
  
  if (currentTime.value > maxTime.value) {
    currentTime.value = minTime.value
  }
  
  updateVisualization()
  animationFrameId = requestAnimationFrame(animate)
}

// ===== INITIALIZATION & CLEANUP =====

async function init3D() {
  if (!window.mapboxgl) {
    console.error('Mapbox GL JS not loaded')
    return
  }
  
  const [initialLongitude, initialLatitude] = computeInitialCenter()
  
  window.mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN
  
  map = new window.mapboxgl.Map({
    container: mapContainer.value,
    style: 'mapbox://styles/mapbox/standard',
    center: [initialLongitude, initialLatitude],
    zoom: 14,
    pitch: 60,
    bearing: 0,
    antialias: true
  })
  
  map.addControl(new window.mapboxgl.NavigationControl(), 'top-right')
  
  if (window.deck && window.deck.MapboxOverlay) {
    deckOverlay = new window.deck.MapboxOverlay({ interleaved: true, layers: [] })
    map.addControl(deckOverlay)
  } else {
    console.error('MapboxOverlay not available')
  }
  
  map.on('load', () => {
    map.setConfigProperty('basemap', 'showPlaceLabels', false)
    map.setConfigProperty('basemap', 'showRoadLabels', true)
    map.setFog({
      range: [0.5, 10],
      color: '#ffffff',
      'horizon-blend': 0.1,
      'high-color': '#add8e6',
      'space-color': '#d8f2ff',
      'star-intensity': 0.0
    })
    
    // Set building extrusion opacity to 1
    const layers = map.getStyle().layers
    for (const layer of layers) {
      if (layer.type === 'fill-extrusion' && layer.id.includes('building')) {
        map.setPaintProperty(layer.id, 'fill-extrusion-opacity', 1)
      }
    }
    
    console.log('Mapbox 3D environment loaded')
    updateLayers3D()
  })
}

function init2D() {
  const [centerLon, centerLat] = computeInitialCenter()
  
  const initialViewState = {
    longitude: centerLon,
    latitude: centerLat,
    zoom: 13,
    pitch: 45,
    bearing: 0
  }
  
  deckgl = new window.deck.DeckGL({
    container: mapContainer.value,
    views: [new window.deck.MapView({ repeat: true })],
    controller: true,
    initialViewState
  })
  
  updateLayers2D()
}

function cleanup3D() {
  if (map) {
    map.remove()
    map = null
  }
  deckOverlay = null
}

function cleanup2D() {
  if (deckgl) {
    deckgl.finalize()
    deckgl = null
  }
}

async function switchMode() {
  // Stop animation
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
  lastTimestamp = null
  
  // Cleanup previous mode
  cleanup3D()
  cleanup2D()
  
  // Wait for DOM update
  await new Promise(resolve => setTimeout(resolve, 100))
  
  // Initialize new mode
  if (mode.value === '3d') {
    await init3D()
  } else {
    init2D()
  }
  
  // Restart animation
  animationFrameId = requestAnimationFrame(animate)
}

// ===== LIFECYCLE =====

onMounted(async () => {
  loadTrips()
  
  // Initialize based on mode
  if (mode.value === '3d') {
    await init3D()
  } else {
    init2D()
  }
  
  animationFrameId = requestAnimationFrame(animate)
})

onBeforeUnmount(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  cleanup3D()
  cleanup2D()
})

// ===== WATCHERS =====

watch(() => props.dataset, () => { loadTrips() })

watch(currentTime, () => {
  if (!playing.value) {
    updateVisualization()
  }
})

watch(mode, () => {
  switchMode()
})
</script>

<style scoped>
button {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
button:hover {
  background: #f0f0f0;
}
button:active {
  background: #e0e0e0;
}
label {
  font-size: 13px;
  font-weight: 500;
}
select, input[type="range"] {
  font-size: 13px;
}
</style>

