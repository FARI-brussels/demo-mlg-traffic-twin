<template>
  <div id="app" style="display:flex; height:100%">
    <div style="flex:1; position:relative;">
      <div id="map" style="width:100%; height:100%;"></div>
      <div v-if="networkLoading" style="position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(255,255,255,0.7); display:flex; align-items:center; justify-content:center; z-index:10;">
        <span style="font-size:1.2em; font-weight:500; color:#333;">Loading road network…</span>
      </div>
      
      <!-- Legend moved to bottom center of map -->
      <div style="position:absolute; bottom:20px; left:50%; transform:translateX(-50%); background:rgba(255,255,255,0.95); padding:12px 16px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.15); z-index:5;">
        <h4 style="margin:0 0 8px 0; font-size:14px; font-weight:600;">Legend</h4>
        <div style="display:flex; flex-direction:column; gap:6px; font-size:13px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="display:inline-block; width:18px; height:12px; background:#fff000; border:1px solid #ccc;"></span>
            <span>Bus/taxi lane</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="display:inline-block; width:18px; height:12px; background:#0068ff; border:1px solid #ccc;"></span>
            <span>Tunnel lane</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="display:inline-block; width:18px; height:12px; background:#ff0000; border:1px solid #ccc;"></span>
            <span>Closed lane</span>
          </div>
        </div>
      </div>
      
      <!-- Box select overlay -->
      <div v-if="boxSelectMode" 
           @mousedown="handleBoxSelectStart" 
           @mousemove="handleBoxSelectMove" 
           @mouseup="handleBoxSelectEnd"
           style="position:absolute; top:0; left:0; width:100%; height:100%; cursor:crosshair; z-index:15;">
        <div v-if="boxSelectStart && boxSelectEnd" 
             :style="{
               position: 'absolute',
               left: Math.min(boxSelectStart.x, boxSelectEnd.x) + 'px',
               top: Math.min(boxSelectStart.y, boxSelectEnd.y) + 'px',
               width: Math.abs(boxSelectEnd.x - boxSelectStart.x) + 'px',
               height: Math.abs(boxSelectEnd.y - boxSelectStart.y) + 'px',
               border: '2px dashed #2196F3',
               background: 'rgba(33, 150, 243, 0.1)',
               pointerEvents: 'none'
             }">
        </div>
      </div>
    </div>
    <div id="info" style="width:320px; padding:12px; border-left:1px solid #ddd; font:14px/1.4 system-ui;">
      

      <h3>Network</h3>
      <div style="display:flex; flex-direction:column; gap:8px;">
        <div>
          <label for="network-select" style="display:block; margin-bottom:4px;">Select Network:</label>
          <select id="network-select" v-model="selectedNetwork" @change="loadSelectedNetwork" :disabled="loading" style="width:100%; padding:4px;">
            <option value="">-- Choose a network --</option>
            <option v-for="net in availableNetworks" :key="net" :value="net">{{ net }}</option>
          </select>
        </div>
        <div>
          <label for="network-upload" style="display:block; margin-bottom:4px;">Upload Network (.net.xml):</label>
          <input type="file" id="network-upload" accept=".xml,.net.xml" @change="handleNetworkUpload" :disabled="loading" style="width:100%;">
        </div>
        <div>
          <button @click="toggleBoxSelect" :disabled="loading" style="width:100%; padding:6px; background:#2196F3; color:white; border:none; border-radius:4px; cursor:pointer;">
            {{ boxSelectMode ? 'Cancel Box Select' : 'Draw Bounding Box' }}
          </button>
        </div>
      </div>
      <hr>

      <h3>Calibrated Routes</h3>
      <div style="display:flex; flex-direction:column; gap:8px;">
        <div>
          <label for="route-select" style="display:block; margin-bottom:4px;">Select Route:</label>
          <select id="route-select" v-model="selectedRoute" @change="loadSelectedRoute" :disabled="loading || availableRoutes.length === 0" style="width:100%; padding:4px;">
            <option value="">-- No route (generate random) --</option>
            <option v-for="route in availableRoutes" :key="route" :value="route">{{ route }}</option>
          </select>
        </div>
        <div>
          <label for="route-upload" style="display:block; margin-bottom:4px;">Upload Custom Routes (.xml):</label>
          <input type="file" id="route-upload" accept=".xml" @change="handleRouteUpload" :disabled="loading" style="width:100%;">
        </div>
      </div>
      <hr>

      <h3>Closed Roads</h3>
      <div id="closed-roads-list" style="max-height:220px; overflow:auto; border:1px solid #ddd; padding:4px;">
        <div v-for="item in closedRoads" :key="item.id" class="closed-item" style="display:flex; align-items:center; gap:8px; padding:4px 6px; border-bottom:1px solid #eee;">
          <span class="label" style="flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:500;">{{ item.label }}</span>
          <button @click="removeClosed(item.id)" aria-label="Remove" title="Remove" style="background:none; border:none; cursor:pointer; color:#a00; font-size:16px;">🗑️</button>
        </div>
      </div>
      <div v-if="selectedId" style="margin:6px 0; color:#333;">Selected edge: {{ selectedId }}</div>

      <button :disabled="!selectedId" @click="addSelected" id="add-selected-btn" style="margin-top:6px">Add to closed list</button>
      <hr>

      <h3>Deviations</h3>
      <div>
        <button @click="getCurrentDeviations" :disabled="loading">Get current deviations</button>
      </div>
      <hr>

      <h3>Simulation</h3>
      <div>
        <label for="start-time">Start Time:</label>
        <input type="time" id="start-time" step="1" v-model="startTime">
      </div>
      <div>
        <label for="stop-time">Stop Time:</label>
        <input type="time" id="stop-time" step="1" v-model="stopTime">
      </div>
      <div v-if="!store.routes">
        <label for="insertion-rate">Insertion rate (veh/hr):</label>
        <input type="number" id="insertion-rate" min="100" step="100" v-model.number="insertionRate">
      </div>
      <div style="margin-top:10px;">
        <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
          <input type="checkbox" v-model="computeAllFcd" style="cursor:pointer;">
          <span>Compute all FCD</span>
        </label>
      </div>
      <div style="margin-top:10px;">
        <button @click="simulate" :disabled="loading">{{ loading ? 'Simulating…' : 'Simulate' }}</button>
      </div>
      <div style="margin-top:8px; display:flex; flex-direction:column; gap:6px;">
        <button @click="loadPrecomputed('simulation1')" :disabled="loading">Tulipe flagey blocked, synthetic</button>
        <button @click="loadPrecomputed('simulation2')" :disabled="loading">Load simulation 2</button>
        <button @click="loadPrecomputed('simulation3')" :disabled="loading">Load simulation 3</button>
      </div>
      <div v-if="loading" style="margin-top:8px; color:#666;">Processing… Please wait.</div>
      <div v-if="error" style="margin-top:8px; color:#a00;">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import { prepareSumoNetworkGeojson, buildSumoNetworkLayers } from '../utils.js'
import { updateFcdFilterShape } from '../create_fcd_filter.js'

const router = useRouter()

const selectedId = ref(null)
const selectedProps = ref(null)
const hoveredId = ref(null)
const closedRoads = ref([])
const loading = ref(false)
const networkLoading = ref(true)
const error = ref('')
const startTime = ref('00:00:00')
const stopTime = ref('01:00:00')
const insertionRate = ref(store.insertionRate || 3000)
const computeAllFcd = ref(false)
let deckgl = null
const currentViewState = ref(null)
const deviationsData = ref(null)
const sumoNetworkData = ref(null)
let hoverRafId = null

// Network selection state
const networkConfigs = ref({})
const availableNetworks = ref([])
const selectedNetwork = ref('')

// Route selection state
const availableRoutes = ref([])
const selectedRoute = ref('')

// Box select state
const boxSelectMode = ref(false)
const boxSelectStart = ref(null)
const boxSelectEnd = ref(null)
const isDragging = ref(false)



function timeToSeconds(t) {
  const [h, m, s] = t.split(':').map(Number)
  return h * 3600 + m * 60 + s
}

function addSelected() {
  if (!selectedId.value || !selectedProps.value) return
  if (closedRoads.value.find(x => x.id === selectedId.value)) return
  const label = selectedProps.value.name ? `${selectedProps.value.name} (${selectedId.value})` : selectedId.value
  closedRoads.value = [...closedRoads.value, { id: selectedId.value, label }]
  
  // Update the FCD filter shape (circular area)
  const filterShape = updateFcdFilterShape(store.netData, closedRoads.value)
  store.fcd_filter_shape = filterShape
  console.log('Updated FCD filter shape:', store.fcd_filter_shape)
}

function removeClosed(id) {
  closedRoads.value = closedRoads.value.filter(x => x.id !== id)
  // Recalculate filter shape after removal
  const filterShape = updateFcdFilterShape(store.netData, closedRoads.value)
  store.fcd_filter_shape = filterShape
  console.log('Updated FCD filter shape:', store.fcd_filter_shape)
}

async function loadAvailableNetworks() {
  try {
    const res = await fetch('/configs.json')
    if (res.ok) {
      const data = await res.json()
      networkConfigs.value = data
      availableNetworks.value = Object.keys(data)
    }
  } catch (e) {
    console.error('Failed to load network configs:', e)
  }
}

async function loadSelectedNetwork() {
  if (!selectedNetwork.value) return
  loading.value = true
  error.value = ''
  try {
    const folder = selectedNetwork.value
    const netDataRes = await fetch(`/networks/${folder}/network.geojson`)
    const sumoDataRes = await fetch(`/networks/${folder}/network_lanes.json`)
    const netXmlRes = await fetch(`/networks/${folder}/network.net.xml`)
    
    if (!netDataRes.ok || !sumoDataRes.ok || !netXmlRes.ok) {
      throw new Error('Failed to load network files')
    }
    
    store.netData = await netDataRes.json()
    store.sumoNetworkData = await sumoDataRes.json()
    store.netXmlContent = await netXmlRes.text()
    
    // Update available routes for this network
    const config = networkConfigs.value[folder]
    availableRoutes.value = config?.routes || []
    selectedRoute.value = ''
    store.routes = null
    
    deckgl.setProps({ layers: renderLayers() })
    fitToGeojson(store.netData)
  } catch (e) {
    error.value = `Failed to load network: ${e.message}`
  } finally {
    loading.value = false
  }
}

async function handleNetworkUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  
  loading.value = true
  error.value = ''
  try {
    const content = await file.text()
    
    // Create a zip file containing the XML
    const zip = new window.JSZip()
    zip.file('network.net.xml', content)
    const zipBlob = await zip.generateAsync({ type: 'blob' })
    
    // Send the zipped file
    const formData = new FormData()
    formData.append('network_zip', zipBlob, 'network.zip')
    
    const res = await fetch('http://localhost:8000/generate_network_geojson', {
      method: 'POST',
      body: formData
    })
    
    if (!res.ok) throw new Error(`Backend error: ${res.status}`)
    
    // Backend now returns a ZIP file
    const blob = await res.blob()
    const resultZip = await window.JSZip.loadAsync(blob)
    
    // Extract files from the ZIP
    const geojsonFile = resultZip.file('network.geojson')
    const netXmlFile = resultZip.file('network.net.xml')
    
    if (!geojsonFile || !netXmlFile) {
      throw new Error('Missing required files in response ZIP')
    }
    
    const geojsonText = await geojsonFile.async('string')
    const netXmlText = await netXmlFile.async('string')
    
    const geojsonData = JSON.parse(geojsonText)
    
    store.netData = geojsonData
    store.sumoNetworkData = prepareSumoNetworkGeojson(geojsonData)
    store.netXmlContent = netXmlText
    
    // Clear routes when uploading a new network
    availableRoutes.value = []
    selectedRoute.value = ''
    store.routes = null
    
    deckgl.setProps({ layers: renderLayers() })
    fitToGeojson(store.netData)
  } catch (e) {
    error.value = `Upload failed: ${e.message}`
  } finally {
    loading.value = false
    // Reset file input
    event.target.value = ''
  }
}

function toggleBoxSelect() {
  boxSelectMode.value = !boxSelectMode.value
  boxSelectStart.value = null
  boxSelectEnd.value = null
  isDragging.value = false
  
  if (boxSelectMode.value) {
    // Disable deck.gl controller when in box select mode
    if (deckgl) {
      deckgl.setProps({ controller: false })
    }
  } else {
    // Re-enable deck.gl controller
    if (deckgl) {
      deckgl.setProps({ controller: true })
    }
  }
}

function handleBoxSelectStart(event) {
  boxSelectStart.value = { x: event.offsetX, y: event.offsetY }
  boxSelectEnd.value = { x: event.offsetX, y: event.offsetY }
  isDragging.value = true
}

function handleBoxSelectMove(event) {
  if (isDragging.value && boxSelectStart.value) {
    boxSelectEnd.value = { x: event.offsetX, y: event.offsetY }
  }
}

function handleBoxSelectEnd(event) {
  if (!boxSelectStart.value || !boxSelectEnd.value || !isDragging.value) return
  
  // Stop dragging - this locks the box in place
  isDragging.value = false
  
  // Convert screen coordinates to geographic coordinates
  const mapContainer = document.getElementById('map')
  if (!mapContainer || !deckgl) return
  
  const viewState = currentViewState.value
  if (!viewState) return
  
  // Get the two corner points
  const x1 = boxSelectStart.value.x
  const y1 = boxSelectStart.value.y
  const x2 = boxSelectEnd.value.x
  const y2 = boxSelectEnd.value.y
  
  // Unproject screen coordinates to longitude/latitude
  const viewport = new window.deck.WebMercatorViewport({
    ...viewState,
    width: mapContainer.clientWidth,
    height: mapContainer.clientHeight
  })
  const [lon1, lat1] = viewport.unproject([x1, y1])
  const [lon2, lat2] = viewport.unproject([x2, y2])
  
  // Create bounding box [min_lon, min_lat, max_lon, max_lat]
  const bbox = [
    Math.min(lon1, lon2),
    Math.min(lat1, lat2),
    Math.max(lon1, lon2),
    Math.max(lat1, lat2)
  ]
  
  // Call the backend with the bounding box
  generateNetworkFromBoundingBox(bbox)
}

async function generateNetworkFromBoundingBox(bbox) {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('http://localhost:8000/generate_network_from_bounding_box', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ bbox })
    })
    
    if (!res.ok) throw new Error(`Backend error: ${res.status}`)
    
    // Backend returns a ZIP file
    const blob = await res.blob()
    const resultZip = await window.JSZip.loadAsync(blob)
    
    // Extract files from the ZIP
    const geojsonFile = resultZip.file('network.geojson')
    const netXmlFile = resultZip.file('network.net.xml')
    
    if (!geojsonFile || !netXmlFile) {
      throw new Error('Missing required files in response ZIP')
    }
    
    const geojsonText = await geojsonFile.async('string')
    const netXmlText = await netXmlFile.async('string')
    
    const geojsonData = JSON.parse(geojsonText)
    
    store.netData = geojsonData
    store.sumoNetworkData = prepareSumoNetworkGeojson(geojsonData)
    store.netXmlContent = netXmlText
    
    // Clear routes when generating a new network
    availableRoutes.value = []
    selectedRoute.value = ''
    store.routes = null
    
    deckgl.setProps({ layers: renderLayers() })
    fitToGeojson(store.netData)
  } catch (e) {
    error.value = `Failed to generate network: ${e.message}`
  } finally {
    loading.value = false
    boxSelectMode.value = false
    boxSelectStart.value = null
    boxSelectEnd.value = null
    if (deckgl) {
      deckgl.setProps({ controller: true })
    }
  }
}

async function loadSelectedRoute() {
  if (!selectedRoute.value) {
    store.routes = null
    return
  }
  
  loading.value = true
  error.value = ''
  try {
    const routePath = `/routes/${selectedRoute.value}`
    console.log('Loading route from:', routePath)
    const res = await fetch(routePath)
    
    if (!res.ok) {
      throw new Error('Failed to load route file')
    }
    
    store.routes = await res.text()
  } catch (e) {
    error.value = `Failed to load route: ${e.message}`
    selectedRoute.value = ''
    store.routes = null
  } finally {
    loading.value = false
  }
}

async function handleRouteUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  
  loading.value = true
  error.value = ''
  try {
    const content = await file.text()
    store.routes = content
    selectedRoute.value = '' // Clear dropdown selection when uploading custom
  } catch (e) {
    error.value = `Failed to upload route: ${e.message}`
  } finally {
    loading.value = false
    // Reset file input
    event.target.value = ''
  }
}

function renderLayers() {

  const deviationsLayer = deviationsData.value ? new window.deck.GeoJsonLayer({
    id: 'deviations',
    data: deviationsData.value,
    pickable: false,
    stroked: true,
    filled: false,
    lineWidthUnits: 'pixels',
    getLineWidth: 4,
    getLineColor: [255, 0, 0, 255]
  }) : null

  const layers = []

  if (store.sumoNetworkData) {
    const sumoHandlers = {
      onHover: info => {
        if (hoverRafId) cancelAnimationFrame(hoverRafId)
        hoverRafId = requestAnimationFrame(() => {
          const id = info.object ? String(info.object.properties.id || info.object.properties.osm_id) : null
          if (id !== hoveredId.value) {
            hoveredId.value = id
            deckgl.setProps({ layers: renderLayers() })
          }
        })
      },
      onClick: info => {
        if (!info.object) return
        const props = info.object.properties
        selectedId.value = String(props.id || props.osm_id)
        selectedProps.value = props
        deckgl.setProps({ layers: renderLayers() })
      },
    }
    const updateTriggers = {
      getFillColor: [selectedId.value, closedRoads.value.map(x => x.id).join(',')],
      getLineColor: [hoveredId.value]
    }
    const sumoLayers = buildSumoNetworkLayers(
      store.sumoNetworkData,
      window.deck,
      {
        ...sumoHandlers,
        updateTriggers,
        getClosedPredicate: props => {
          const laneId = String((props && (props.id || props.osm_id)) || '')
          const baseLaneId = laneId.replace(/_\d+$/, '')
          return closedRoads.value.some(entry => {
            const closedId = typeof entry === 'string' ? entry : String(entry.id || '')
            if (!closedId) return false
            return closedId === laneId || closedId === baseLaneId
          })
        },
        getSelectedId: () => selectedId.value,
        getHoveredId: () => hoveredId.value,
      }
    )
    for (const l of sumoLayers) layers.push(l)
  }

  if (deviationsLayer) layers.push(deviationsLayer)
  return layers
}


function computeBoundsFromGeojson(gj) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  function visitCoords(coords) {
    if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      const x = coords[0], y = coords[1]
      if (x < minX) minX = x
      if (y < minY) minY = y
      if (x > maxX) maxX = x
      if (y > maxY) maxY = y
    } else { for (const c of coords) visitCoords(c) }
  }
  for (const f of gj.features || []) {
    const g = f.geometry
    if (g && g.coordinates) visitCoords(g.coordinates)
  }
  return { minX, minY, maxX, maxY }
}

function fitToGeojson(gj) {
  const { minX, minY, maxX, maxY } = computeBoundsFromGeojson(gj)
  if (!isFinite(minX)) return
  const viewState = { longitude: (minX + maxX) / 2, latitude: (minY + maxY) / 2, zoom: 13, pitch: 0, bearing: 0 }
  currentViewState.value = viewState
  deckgl.setProps({ viewState: currentViewState.value })
}



async function getCurrentDeviations() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('http://localhost:8000/get_current_deviations')
    if (!res.ok) throw new Error(`Backend error: ${res.status}`)
    const gj = await res.json()
    deviationsData.value = gj

    // Auto-add closed edges that are part of the current network
    try {
      if (store.netData && Array.isArray(store.netData.features) && gj && Array.isArray(gj.features)) {
        const netIds = new Set(
          store.netData.features
            .map(f => (f && f.properties) ? String(f.properties.id || f.properties.osm_id || '') : '')
            .filter(id => id)
        )
        const toAdd = []
        for (const f of gj.features) {
          const eid = f && f.properties ? String(f.properties.edge_id || '') : ''
          if (eid && netIds.has(eid) && !closedRoads.value.find(x => x.id === eid)) {
            const label = (f.properties.location_fr ? `${f.properties.location_fr} (${eid})` : eid)
            toAdd.push({ id: eid, label })
          }
        }
        if (toAdd.length) {
          closedRoads.value = [...closedRoads.value, ...toAdd]
        }
      }
    } catch (_) {}

    deckgl.setProps({ layers: renderLayers() })
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}

async function simulate() {
  loading.value = true
  error.value = ''
  try {
    if (!store.netXmlContent) {
      throw new Error('No network loaded. Please select or upload a network first.')
    }

    const begin = timeToSeconds(startTime.value)
    const end = timeToSeconds(stopTime.value)
    const closed = [...new Set(closedRoads.value.map(x => x.id.replace(/_\d+$/, '')))]
    // persist selections for results view
    store.closedEdges = closed
    store.insertionRate = insertionRate.value

    // Create a zip file containing the network XML
    const networkZip = new window.JSZip()
    networkZip.file('network.net.xml', store.netXmlContent)
    const networkZipBlob = await networkZip.generateAsync({ type: 'blob' })

    // Send simulation request with zipped network
    const formData = new FormData()
    formData.append('network_zip', networkZipBlob, 'network.zip')
    formData.append('begin_time', begin.toString())
    formData.append('end_time', end.toString())
    formData.append('closed_edges', JSON.stringify(closed))
    
    // Add filter shape if computeAllFcd is false and filter shape exists
    if (!computeAllFcd.value && store.fcd_filter_shape) {
      formData.append('fcd_filter_shape', JSON.stringify(store.fcd_filter_shape))
    }
    
    // Add routes if they exist
    if (store.routes) {
      const routesZip = new window.JSZip()
      routesZip.file('routes.xml', store.routes)
      const routesZipBlob = await routesZip.generateAsync({ type: 'blob' })
      formData.append('routes_zip', routesZipBlob, 'routes.zip')
    } else {
      // Only send insertion_rate if no routes are provided (for random generation)
      formData.append('insertion_rate', insertionRate.value.toString())
    }

    const res = await fetch('http://localhost:8000/simulate', {
      method: 'POST',
      body: formData
    })

    if (!res.ok) throw new Error(`Backend error: ${res.status}`)
    const blob = await res.blob()
    const resultZip = await window.JSZip.loadAsync(blob)

    async function readText(name) {
      const file = resultZip.file(name)
      if (!file) return null
      return await file.async('string')
    }

    const tripsWithText = await readText('fcd_trips_with.json')
    const tripsWoutText = await readText('fcd_trips_without.json')
    const metricsText = await readText('metrics.json')
    const congestionWithText = await readText('congestion_with.geojson')
    const congestionWoutText = await readText('congestion_without.geojson')

    store.tripsWith = tripsWithText ? JSON.parse(tripsWithText) : null
    store.tripsWout = tripsWoutText ? JSON.parse(tripsWoutText) : null
    store.metrics = metricsText ? JSON.parse(metricsText) : null
    store.congestionWith = congestionWithText ? JSON.parse(congestionWithText) : null
    store.congestionWout = congestionWoutText ? JSON.parse(congestionWoutText) : null

    router.push('/results')
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}

async function loadPrecomputed(simName) {
  loading.value = true
  error.value = ''
  try {
    async function fetchText(url) {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Failed to fetch ${url}`)
      return await res.text()
    }
    const base = `/simulations/${simName}`
    const tripsWithText = await fetchText(`${base}/fcd_trips_with.json`)
    const tripsWoutText = await fetchText(`${base}/fcd_trips_without.json`)
    const metricsText = await fetchText(`${base}/metrics.json`)
    const congestionWithText = await fetchText(`${base}/congestion_with.geojson`)
    const congestionWoutText = await fetchText(`${base}/congestion_without.geojson`)
    const netXmlText = await fetchText(`${base}/network.net.xml`)
    const netDataText = await fetchText(`${base}/network.geojson`)
    const netNetworkDataText = await fetchText(`${base}/network_lanes.json`)
    

    store.tripsWith = tripsWithText ? JSON.parse(tripsWithText) : null
    store.tripsWout = tripsWoutText ? JSON.parse(tripsWoutText) : null
    store.metrics = metricsText ? JSON.parse(metricsText) : null
    store.congestionWith = congestionWithText ? JSON.parse(congestionWithText) : null
    store.congestionWout = congestionWoutText ? JSON.parse(congestionWoutText) : null
    store.netXmlContent = netXmlText
    store.netData = netDataText ? JSON.parse(netDataText) : null
    store.sumoNetworkData = netNetworkDataText ? JSON.parse(netNetworkDataText) : null


    // Optional: derive and persist metadata for consistency
    try {
      const meta = (store.tripsWith && store.tripsWith.metadata) ? store.tripsWith.metadata : null
      if (meta) {
        store.closedEdges = Array.isArray(meta.closed_edges) ? meta.closed_edges : []
        if (typeof meta.insertion_rate === 'number') store.insertionRate = meta.insertion_rate
      }
    } catch (e) { /* ignore */ }

    router.push('/results')
  } catch (e) {
    error.value = String(e)
  } finally {
    loading.value = false
  }
}



onMounted(async () => {
  const initialViewState = { longitude: 4.35, latitude: 50.85, zoom: 12, pitch: 0, bearing: 0 }
  currentViewState.value = initialViewState

  deckgl = new window.deck.DeckGL({
    container: 'map',
    views: [new window.deck.MapView({ repeat: true })],
    controller: true,
    mapStyle: 'mapbox://styles/mapbox/light-v11',
    mapboxApiAccessToken: import.meta.env.VITE_MAPBOX_TOKEN,
    viewState: currentViewState.value,
    onViewStateChange: ({viewState}) => {
      currentViewState.value = viewState
      deckgl.setProps({ viewState })
    }
  })


  // Render base map immediately; other layers will be added when data is ready
  deckgl.setProps({ layers: renderLayers() })

  // Load available networks
  await loadAvailableNetworks()

  // Auto-select brussels_main_roads
  selectedNetwork.value = 'tulipe'
  await loadSelectedNetwork()
  networkLoading.value = false
})

onBeforeUnmount(() => {
  if (deckgl) { deckgl.finalize(); deckgl = null }
})



</script> 