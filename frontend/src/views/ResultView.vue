<template>
  <div style="position:relative; width:100%; height:100%; display:flex; flex-direction:column;">
    <!-- Top Navigation Bar -->
    <div class="nav-bar">
      <button @click="$router.push('/')" class="back-btn">← Back</button>
      <button @click="downloadSimulation" class="download-btn">📥 Download simulation</button>
      
      <!-- View Mode Tabs -->
      <div class="view-tabs">
        <button 
          :class="['tab-btn', { active: viewMode === 'visualization' }]"
          @click="viewMode = 'visualization'"
        >
          🗺️ Visualization
        </button>
        <button 
          :class="['tab-btn', { active: viewMode === 'analysis' }]"
          @click="viewMode = 'analysis'"
          :disabled="!hasAnalysisData"
          :title="!hasAnalysisData ? 'No analysis data available for this simulation' : ''"
        >
          📊 Traffic Analysis
        </button>
      </div>

      <!-- Visualization Controls (only shown in visualization mode) -->
      <div v-if="viewMode === 'visualization'" class="viz-controls">
        <label class="control-label">
          <input type="radio" value="with" v-model="scenario"> With roadworks
        </label>
        <label class="control-label">
          <input type="radio" value="without" v-model="scenario"> Without roadworks
        </label>
      </div>
    </div>

    <!-- Content Area -->
    <div style="flex:1; position:relative; min-height:0; overflow:hidden;">
      <!-- Visualization View -->
      <UnifiedVisualization v-if="viewMode === 'visualization'" :dataset="scenario" />

      <!-- Traffic Analysis View -->
      <MetricsDashboard v-else-if="viewMode === 'analysis'" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store } from '../store'
import UnifiedVisualization from '../components/UnifiedVisualization.vue'
import MetricsDashboard from '../components/MetricsDashboard.vue'
import JSZip from 'jszip'

const scenario = computed({ get: () => store.scenario, set: v => { store.scenario = v } })
const viewMode = computed({ get: () => store.resultViewMode, set: v => { store.resultViewMode = v } })
const hasAnalysisData = computed(() => !!(store.metrics || (store.congestionWith && store.congestionWout)))

const downloadSimulation = async () => {
  try {
    const zip = new JSZip()
    
    // Add network data
    if (store.netData) {
      zip.file('network.geojson', JSON.stringify(store.netData, null, 2))
    }
    
    if (store.sumoNetworkData) {
      zip.file('network_lanes.json', JSON.stringify(store.sumoNetworkData, null, 2))
    }
    
    if (store.netXmlContent) {
      zip.file('network.net.xml', store.netXmlContent)
    }
    
    // Add trips data
    if (store.tripsWith) {
      zip.file('fcd_trips_with.json', JSON.stringify(store.tripsWith, null, 2))
    }
    
    if (store.tripsWout) {
      zip.file('fcd_trips_without.json', JSON.stringify(store.tripsWout, null, 2))
    }
    
    // Add metrics
    if (store.metrics) {
      zip.file('metrics.json', JSON.stringify(store.metrics, null, 2))
    }
    
    // Add congestion data
    if (store.congestionWith) {
      zip.file('congestion_with.geojson', JSON.stringify(store.congestionWith, null, 2))
    }
    
    if (store.congestionWout) {
      zip.file('congestion_without.geojson', JSON.stringify(store.congestionWout, null, 2))
    }
    
    // Generate and download the zip file
    const content = await zip.generateAsync({ type: 'blob' })
    const url = URL.createObjectURL(content)
    const a = document.createElement('a')
    a.href = url
    a.download = `simulation_${new Date().toISOString().split('T')[0]}.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error downloading simulation:', error)
    alert('Error creating zip file. Please try again.')
  }
}
</script>

<style scoped>
.nav-bar {
  padding: 12px 16px;
  border-bottom: 1px solid #ddd;
  display: flex;
  gap: 16px;
  align-items: center;
  background: white;
  flex-wrap: wrap;
}

.back-btn,
.download-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.back-btn:hover,
.download-btn:hover {
  background: #f5f5f5;
}

.download-btn {
  background: #4ecdc4;
  color: white;
  border-color: #4ecdc4;
}

.download-btn:hover {
  background: #3db8af;
  border-color: #3db8af;
}

.view-tabs {
  display: flex;
  gap: 8px;
  padding: 0 16px;
  border-left: 1px solid #ddd;
  border-right: 1px solid #ddd;
}

.tab-btn {
  padding: 8px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}

.tab-btn:hover:not(:disabled) {
  color: #333;
  background: #f5f5f5;
}

.tab-btn.active {
  color: #4ecdc4;
  border-bottom-color: #4ecdc4;
}

.tab-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.viz-controls {
  display: flex;
  gap: 16px;
  align-items: center;
  flex: 1;
}

.control-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 14px;
}

.control-label input[type="radio"],
.control-label input[type="checkbox"] {
  cursor: pointer;
}

@media (max-width: 768px) {
  .nav-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .view-tabs {
    border-left: none;
    border-right: none;
    border-top: 1px solid #ddd;
    padding: 8px 0;
    justify-content: center;
  }
  
  .viz-controls {
    border-top: 1px solid #ddd;
    padding-top: 8px;
    flex-wrap: wrap;
  }
}
</style> 