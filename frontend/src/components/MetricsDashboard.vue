<template>
  <div class="metrics-dashboard">
    <div v-if="!metrics && !hasCongestionData" class="no-metrics">
      <p>📊 No analysis data available for this simulation</p>
      <p style="font-size: 0.9em; opacity: 0.7;">
        Traffic analysis is only available for simulations run with the new backend version.
      </p>
    </div>

    <div v-else class="metrics-container">
      <!-- Header -->
      <div class="dashboard-header">
        <h2>Traffic Impact Analysis</h2>
        <div class="metadata">
          <span v-if="metadata.num_closed_edges">
            🚧 {{ metadata.num_closed_edges }} closed edge(s)
          </span>
          <span>
            ⏱️ {{ formatDuration(metadata.simulation_duration_s) }}
          </span>
          <span>
            🚗 Insertion rate: {{ metadata.insertion_rate }}
          </span>
        </div>
      </div>

      <!-- Traffic Congestion Maps -->
      <div v-if="hasCongestionData" class="congestion-maps-section">
        <h3>🗺️ Traffic Congestion Maps</h3>
        <div class="maps-grid">
          <div class="map-container">
            <h4>Without Road Closures</h4>
            <TrafficMap
              v-if="store.congestionWout"
              :congestionData="store.congestionWout"
              title="Baseline Scenario"
            />
          </div>
          <div class="map-container">
            <h4>With Road Closures</h4>
            <TrafficMap
              v-if="store.congestionWith"
              :congestionData="store.congestionWith"
              title="Impact Scenario"
            />
          </div>
        </div>
      </div>

      <!-- Key Impact Cards -->
      <div class="impact-cards">
        <div class="impact-card delay">
          <div class="card-icon">⏱️</div>
          <div class="card-content">
            <div class="card-label">Total Delay Increase</div>
            <div class="card-value">
              +{{ comparison.delay_increase_vh }} <span class="unit">veh·h</span>
            </div>
            <div class="card-change" :class="getChangeClass(comparison.delay_increase_pct)">
              {{ comparison.delay_increase_pct >= 0 ? '+' : '' }}{{ comparison.delay_increase_pct }}%
            </div>
          </div>
        </div>

        <div class="impact-card travel-time">
          <div class="card-icon">🚗</div>
          <div class="card-content">
            <div class="card-label">Avg Travel Time Increase</div>
            <div class="card-value">
              +{{ comparison.travel_time_increase_min }} <span class="unit">min</span>
            </div>
            <div class="card-change" :class="getChangeClass(comparison.travel_time_increase_pct)">
              {{ comparison.travel_time_increase_pct >= 0 ? '+' : '' }}{{ comparison.travel_time_increase_pct }}%
            </div>
          </div>
        </div>

        <div class="impact-card throughput">
          <div class="card-icon">✅</div>
          <div class="card-content">
            <div class="card-label">Throughput Change</div>
            <div class="card-value">
              {{ comparison.throughput_decrease_pct >= 0 ? '+' : '' }}{{ comparison.throughput_decrease_pct }} <span class="unit">%</span>
            </div>
            <div class="card-change" :class="getChangeClass(-comparison.throughput_decrease_pct)">
              {{ comparison.throughput_decrease_pct < 0 ? 'Decreased' : 'Increased' }}
            </div>
          </div>
        </div>

        <div class="impact-card emissions">
          <div class="card-icon">🌱</div>
          <div class="card-content">
            <div class="card-label">CO₂ Emissions Increase</div>
            <div class="card-value">
              +{{ comparison.co2_increase_kg }} <span class="unit">kg</span>
            </div>
            <div class="card-change" :class="getChangeClass(comparison.co2_increase_pct)">
              {{ comparison.co2_increase_pct >= 0 ? '+' : '' }}{{ comparison.co2_increase_pct }}%
            </div>
          </div>
        </div>
      </div>

      <!-- Detailed Comparison -->
      <div class="comparison-section">
        <h3>Detailed Comparison</h3>
        
        <div class="comparison-grid">
          <!-- Travel Time Metrics -->
          <div class="metric-group">
            <h4>⏱️ Travel Time Metrics</h4>
            <table class="metrics-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th class="scenario-col baseline">Without Closures</th>
                  <th class="scenario-col impacted">With Closures</th>
                  <th class="delta-col">Δ</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Average Travel Time</td>
                  <td class="baseline">{{ withoutClosures.avg_travel_time_min }} min</td>
                  <td class="impacted">{{ withClosures.avg_travel_time_min }} min</td>
                  <td class="delta" :class="getChangeClass(comparison.travel_time_increase_pct)">
                    +{{ comparison.travel_time_increase_min }} min
                  </td>
                </tr>
                <tr>
                  <td>95th Percentile Time</td>
                  <td class="baseline">{{ withoutClosures.percentile_95_travel_time_min }} min</td>
                  <td class="impacted">{{ withClosures.percentile_95_travel_time_min }} min</td>
                  <td class="delta">
                    {{ (withClosures.percentile_95_travel_time_min - withoutClosures.percentile_95_travel_time_min).toFixed(2) }} min
                  </td>
                </tr>
                <tr>
                  <td>Total Delay</td>
                  <td class="baseline">{{ withoutClosures.total_delay_vh }} veh·h</td>
                  <td class="impacted">{{ withClosures.total_delay_vh }} veh·h</td>
                  <td class="delta" :class="getChangeClass(comparison.delay_increase_pct)">
                    +{{ comparison.delay_increase_vh }} veh·h
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Throughput Metrics -->
          <div class="metric-group">
            <h4>📊 Throughput & Completion</h4>
            <table class="metrics-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th class="scenario-col baseline">Without Closures</th>
                  <th class="scenario-col impacted">With Closures</th>
                  <th class="delta-col">Δ</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Completed Trips</td>
                  <td class="baseline">{{ withoutClosures.completed_trips }} / {{ withoutClosures.total_demand }}</td>
                  <td class="impacted">{{ withClosures.completed_trips }} / {{ withClosures.total_demand }}</td>
                  <td class="delta">
                    {{ withClosures.completed_trips - withoutClosures.completed_trips }}
                  </td>
                </tr>
                <tr>
                  <td>Throughput</td>
                  <td class="baseline">{{ withoutClosures.throughput_pct }}%</td>
                  <td class="impacted">{{ withClosures.throughput_pct }}%</td>
                  <td class="delta" :class="getChangeClass(-comparison.throughput_decrease_pct)">
                    {{ comparison.throughput_decrease_pct >= 0 ? '+' : '' }}{{ comparison.throughput_decrease_pct }}%
                  </td>
                </tr>
                <tr>
                  <td>Average Speed</td>
                  <td class="baseline">{{ withoutClosures.avg_speed_kmh }} km/h</td>
                  <td class="impacted">{{ withClosures.avg_speed_kmh }} km/h</td>
                  <td class="delta">
                    {{ (withClosures.avg_speed_kmh - withoutClosures.avg_speed_kmh).toFixed(2) }} km/h
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Congestion Metrics -->
          <div class="metric-group">
            <h4>🚦 Congestion Metrics</h4>
            <table class="metrics-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th class="scenario-col baseline">Without Closures</th>
                  <th class="scenario-col impacted">With Closures</th>
                  <th class="delta-col">Δ</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Avg Detour Length</td>
                  <td class="baseline">0.00 km</td>
                  <td class="impacted">{{ withClosures.avg_detour_km }} km</td>
                  <td class="delta highlight">
                    +{{ withClosures.avg_detour_km }} km
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Environmental Impact -->
          <div class="metric-group">
            <h4>🌱 Environmental Impact</h4>
            <table class="metrics-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th class="scenario-col baseline">Without Closures</th>
                  <th class="scenario-col impacted">With Closures</th>
                  <th class="delta-col">Δ</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>CO₂ Emissions</td>
                  <td class="baseline">{{ withoutClosures.co2_kg }} kg</td>
                  <td class="impacted">{{ withClosures.co2_kg }} kg</td>
                  <td class="delta" :class="getChangeClass(comparison.co2_increase_pct)">
                    +{{ comparison.co2_increase_kg }} kg
                  </td>
                </tr>
                <tr>
                  <td>Total Distance</td>
                  <td class="baseline">{{ withoutClosures.total_distance_km }} km</td>
                  <td class="impacted">{{ withClosures.total_distance_km }} km</td>
                  <td class="delta">
                    +{{ (withClosures.total_distance_km - withoutClosures.total_distance_km).toFixed(2) }} km
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Summary Box -->
      <div class="summary-box">
        <h4>📋 Impact Summary</h4>
        <ul>
          <li v-if="comparison.delay_increase_pct > 0">
            Road closures caused a <strong>{{ comparison.delay_increase_pct }}%</strong> increase in total delay 
            (<strong>+{{ comparison.delay_increase_vh }} veh·h</strong>)
          </li>
          <li v-if="comparison.travel_time_increase_pct > 0">
            Average travel time increased by <strong>{{ comparison.travel_time_increase_min }} minutes</strong> 
            (<strong>{{ comparison.travel_time_increase_pct }}%</strong>)
          </li>
          <li v-if="withClosures.avg_detour_km > 0">
            Vehicles had to detour an average of <strong>{{ withClosures.avg_detour_km }} km</strong>
          </li>
          <li v-if="comparison.throughput_decrease_pct < 0">
            Throughput decreased by <strong>{{ Math.abs(comparison.throughput_decrease_pct) }}%</strong> 
            (<strong>{{ withoutClosures.completed_trips - withClosures.completed_trips }} fewer trips completed</strong>)
          </li>
          <li v-if="comparison.co2_increase_pct > 0">
            CO₂ emissions increased by <strong>{{ comparison.co2_increase_kg }} kg</strong> 
            (<strong>{{ comparison.co2_increase_pct }}%</strong>)
          </li>
          
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store } from '../store'
import TrafficMap from './TrafficMap.vue'

const metrics = computed(() => store.metrics)
const withoutClosures = computed(() => metrics.value?.scenario_without_closures || {})
const withClosures = computed(() => metrics.value?.scenario_with_closures || {})
const comparison = computed(() => metrics.value?.comparison || {})
const metadata = computed(() => metrics.value?.metadata || {})
const hasCongestionData = computed(() => !!(store.congestionWith && store.congestionWout))

function getChangeClass(percentChange) {
  if (percentChange === 0) return 'neutral'
  if (percentChange > 0 && percentChange < 10) return 'low-increase'
  if (percentChange >= 10 && percentChange < 30) return 'medium-increase'
  if (percentChange >= 30) return 'high-increase'
  return 'decrease'
}

function formatDuration(seconds) {
  if (!seconds) return 'N/A'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}
</script>

<style scoped>
.metrics-dashboard {
  height: 100%;
  overflow-y: auto;
  background: #f5f5f5;
  padding: 20px;
}

.no-metrics {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.metrics-container {
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 24px;
}

.dashboard-header h2 {
  margin: 0 0 12px 0;
  color: #333;
}

.metadata {
  display: flex;
  gap: 24px;
  font-size: 0.9em;
  color: #666;
}

.congestion-maps-section {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 24px;
}

.congestion-maps-section h3 {
  margin: 0 0 20px 0;
  color: #333;
}

.maps-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.map-container {
  min-height: 500px;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.map-container h4 {
  margin: 0;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #ddd;
  font-size: 1em;
  font-weight: 600;
  color: #555;
}

.impact-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.impact-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  gap: 16px;
  align-items: start;
  border-left: 4px solid #ddd;
}

.impact-card.delay {
  border-left-color: #ff6b6b;
}

.impact-card.travel-time {
  border-left-color: #ffa500;
}

.impact-card.throughput {
  border-left-color: #4ecdc4;
}

.impact-card.emissions {
  border-left-color: #95e1d3;
}

.card-icon {
  font-size: 2em;
  line-height: 1;
}

.card-content {
  flex: 1;
}

.card-label {
  font-size: 0.85em;
  color: #666;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-value {
  font-size: 1.8em;
  font-weight: bold;
  color: #333;
  margin-bottom: 4px;
}

.card-value .unit {
  font-size: 0.5em;
  font-weight: normal;
  color: #999;
}

.card-change {
  font-size: 0.9em;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}

.card-change.low-increase {
  background: #fff3cd;
  color: #856404;
}

.card-change.medium-increase {
  background: #ffe5b4;
  color: #d97706;
}

.card-change.high-increase {
  background: #ffcccc;
  color: #c92a2a;
}

.card-change.decrease {
  background: #d4edda;
  color: #155724;
}

.card-change.neutral {
  background: #e9ecef;
  color: #495057;
}

.comparison-section {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 24px;
}

.comparison-section h3 {
  margin: 0 0 24px 0;
  color: #333;
}

.comparison-grid {
  display: grid;
  gap: 24px;
}

.metric-group h4 {
  margin: 0 0 12px 0;
  color: #555;
  font-size: 1em;
}

.metrics-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9em;
}

.metrics-table th,
.metrics-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.metrics-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #555;
  font-size: 0.85em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metrics-table td.baseline {
  background: #e8f5e9;
}

.metrics-table td.impacted {
  background: #ffebee;
}

.metrics-table td.delta {
  font-weight: 600;
}

.metrics-table td.delta.low-increase {
  color: #d97706;
}

.metrics-table td.delta.medium-increase {
  color: #ea580c;
}

.metrics-table td.delta.high-increase {
  color: #c92a2a;
}

.metrics-table td.delta.highlight {
  background: #fff3cd;
}

.scenario-col {
  width: 150px;
}

.delta-col {
  width: 120px;
}

.summary-box {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #4ecdc4;
}

.summary-box h4 {
  margin: 0 0 16px 0;
  color: #333;
}

.summary-box ul {
  margin: 0;
  padding-left: 20px;
}

.summary-box li {
  margin-bottom: 10px;
  line-height: 1.6;
  color: #555;
}

.summary-box strong {
  color: #333;
}

@media (max-width: 768px) {
  .metrics-dashboard {
    padding: 12px;
  }
  
  .impact-cards {
    grid-template-columns: 1fr;
  }
  
  .maps-grid {
    grid-template-columns: 1fr;
  }
  
  .map-container {
    min-height: 400px;
  }
  
  .metrics-table {
    font-size: 0.8em;
  }
  
  .metrics-table th,
  .metrics-table td {
    padding: 8px 4px;
  }
}
</style>

