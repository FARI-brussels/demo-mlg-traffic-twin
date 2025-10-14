import { reactive } from 'vue'

export const store = reactive({
  netData: null,
  netXmlContent: null,
  sumoNetworkData: null,
  routes: null,
  tripsWith: null,
  tripsWout: null,
  metrics: null,
  congestionWith: null,
  congestionWout: null,
  // UI selections
  use3D: false,
  engine3D: 'mapbox', // 'cesium' | 'mapbox'
  scenario: 'with', // 'with' | 'without'
  closedEdges: [],
  insertionRate: 3000,
  resultViewMode: 'analysis', // 'visualization' | 'analysis'
  fcd_filter_shape: null // { centerLon, centerLat, radiusKm }
}) 