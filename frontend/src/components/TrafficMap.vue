<template>
  <div class="traffic-map-container">
    <div ref="deckContainer" class="map"></div>
    
    <!-- Legend -->
    <div class="legend">
      <div class="legend-title">{{ title }}</div>
      <div class="legend-items">
        <div class="legend-item">
          <span class="legend-color" style="background: #22c55e"></span>
          <span class="legend-label">Free Flow</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #84cc16"></span>
          <span class="legend-label">Light Traffic</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #eab308"></span>
          <span class="legend-label">Moderate</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #f97316"></span>
          <span class="legend-label">Heavy</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #ef4444"></span>
          <span class="legend-label">Severe</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #808080"></span>
          <span class="legend-label">No Data</span>
        </div>
      </div>
    </div>
    
    <!-- Stats overlay -->
    <div v-if="stats" class="stats-overlay">
      <div class="stat">
        <strong>Avg Speed:</strong> {{ stats.avg_speed_kmh }} km/h
      </div>
      <div class="stat">
        <strong>Edges:</strong> {{ stats.edges_with_data }} / {{ stats.total_edges }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'

const props = defineProps({
  congestionData: {
    type: Object,
    required: true
  },
  title: {
    type: String,
    default: 'Traffic Congestion'
  }
})

const deckContainer = ref(null)
let deckgl = null

const stats = computed(() => props.congestionData?.metadata?.statistics || null)

function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result ? [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16)
  ] : [128, 128, 128]
}

function initMap() {
  if (!deckContainer.value || deckgl) return
  
  const {DeckGL, GeoJsonLayer, MapView} = deck
  
  deckgl = new DeckGL({
    container: deckContainer.value,
    views: [new MapView({ repeat: true })],
    mapStyle: 'mapbox://styles/mapbox/light-v11',
    mapboxApiAccessToken: import.meta.env.VITE_MAPBOX_TOKEN,
    initialViewState: {
      longitude: 0,
      latitude: 0,
      zoom: 12,
      pitch: 0,
      bearing: 0
    },
    controller: true
  })
  
  updateLayers()
}

function updateLayers() {
  if (!deckgl || !props.congestionData) return
  
  const {GeoJsonLayer} = deck
  
  // Calculate bounds for initial view
  let minLon = Infinity, maxLon = -Infinity
  let minLat = Infinity, maxLat = -Infinity
  
  props.congestionData.features?.forEach(feature => {
    if (feature.geometry?.type === 'LineString') {
      feature.geometry.coordinates.forEach(([lon, lat]) => {
        minLon = Math.min(minLon, lon)
        maxLon = Math.max(maxLon, lon)
        minLat = Math.min(minLat, lat)
        maxLat = Math.max(maxLat, lat)
      })
    }
  })
  
  // Congestion layer with thick, opaque lines
  const congestionLayer = new GeoJsonLayer({
    id: 'congestion-layer',
    data: props.congestionData,
    pickable: true,
    stroked: true,
    filled: false,
    lineWidthMinPixels: 5,
    lineWidthMaxPixels: 12,
    lineWidthScale: 1,
    getLineColor: d => {
      const color = d.properties?.congestion_color || '#808080'
      return [...hexToRgb(color), 255]  // Fully opaque
    },
    getLineWidth: d => 8,  // Thicker lines
    updateTriggers: {
      getLineColor: props.congestionData
    },
    onClick: info => {
      if (info.object) {
        const props = info.object.properties
        alert(`Edge: ${props.id || props.osm_id}
Category: ${props.congestion_category}
Avg Speed: ${props.avg_speed_kmh} km/h
Density: ${props.avg_density} veh/km
Occupancy: ${props.avg_occupancy}%`)
      }
    }
  })
  
  deckgl.setProps({
    layers: [congestionLayer],
    initialViewState: {
      longitude: (minLon + maxLon) / 2,
      latitude: (minLat + maxLat) / 2,
      zoom: 13,
      pitch: 0,
      bearing: 0
    }
  })
}

onMounted(() => {
  initMap()
})

onBeforeUnmount(() => {
  if (deckgl) {
    deckgl.finalize()
    deckgl = null
  }
})

watch(() => props.congestionData, () => {
  updateLayers()
}, { deep: true })
</script>

<style scoped>
.traffic-map-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
}

.map {
  width: 100%;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.legend {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: white;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  z-index: 1000;
  pointer-events: none;
}

.legend-title {
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 0.9em;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85em;
}

.legend-color {
  display: inline-block;
  width: 20px;
  height: 4px;
  border-radius: 2px;
}

.legend-label {
  color: #555;
}

.stats-overlay {
  position: absolute;
  top: 20px;
  left: 20px;
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  z-index: 1000;
  pointer-events: none;
}

.stat {
  font-size: 0.9em;
  color: #333;
  margin-bottom: 4px;
}

.stat:last-child {
  margin-bottom: 0;
}

@media (max-width: 768px) {
  .legend {
    bottom: 10px;
    right: 10px;
    font-size: 0.85em;
  }
  
  .stats-overlay {
    top: 10px;
    left: 10px;
    font-size: 0.85em;
  }
}
</style>

