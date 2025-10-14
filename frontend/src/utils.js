import * as turf from '@turf/turf'

export function prepareSumoNetworkGeojson(gj) {
  try {
    if (!gj || gj.type !== 'FeatureCollection' || !Array.isArray(gj.features)) return null
    const laneFeatures = gj.features.filter(f => {
      if (!f || !f.properties || f.properties.element !== 'lane' || !f.geometry || f.geometry.type !== 'LineString') return false
      const allow = (f.properties.allow || '').split(',').map(s => s.trim())
      return allow.includes('bus') || allow.includes('private')
    })
    const junctionFeatures = gj.features
      .filter(f => f && f.properties && f.properties.element === 'junction' && f.geometry && f.geometry.coordinates && f.geometry.coordinates.length > 2)
      .map(f => ({ ...f, geometry: { type: 'Polygon', coordinates: [f.geometry.coordinates] } }))

    const lanePolygonFeatures = laneFeatures.map(f => {
      const width = (f.properties && f.properties.width) || 3.2
      const bufferedFeature = turf.buffer(f, width / 2, { units: 'meters', endType: 'flat' })
      if (bufferedFeature.geometry.type === 'MultiPolygon') {
        let largestPolygonCoords = null, maxArea = 0
        bufferedFeature.geometry.coordinates.forEach(polyCoords => {
          const polygon = turf.polygon(polyCoords)
          const area = turf.area(polygon)
          if (area > maxArea) { maxArea = area; largestPolygonCoords = polyCoords }
        })
        if (largestPolygonCoords) {
          bufferedFeature.geometry.type = 'Polygon'
          bufferedFeature.geometry.coordinates = largestPolygonCoords
        }
      }
      // preserve original lane properties on polygon for coloring/ids
      bufferedFeature.properties = { ...(bufferedFeature.properties || {}), ...(f.properties || {}) }
      return bufferedFeature
    })

    function buildArrowTriangles(features) {
      const size = 0.000025, width = size * 0.6, stemLength = size * 2, triFeatures = []
      for (const f of features) {
        const coords = (f.geometry && f.geometry.coordinates) || []
        if (coords.length < 2) continue
        const p2 = coords[coords.length - 1], p1 = coords[coords.length - 2]
        const dx = p2[0] - p1[0], dy = p2[1] - p1[1]
        const len = Math.hypot(dx, dy) || 1
        const ux = dx / len, uy = dy / len
        const px = -uy, py = ux
        const tip = [p2[0] - ux * size, p2[1] - uy * size]
        const stemBase = [tip[0] - ux * stemLength, tip[1] - uy * stemLength]
        const left = [tip[0] - ux * size + px * width, tip[1] - uy * size + py * width]
        const right = [tip[0] - ux * size - px * width, tip[1] - uy * size - py * width]
        // Add triangle for arrowhead
        triFeatures.push({ 
          type: 'Feature', 
          properties: f.properties, 
          geometry: { type: 'Polygon', coordinates: [[tip, left, right, tip]] } 
        })
        // Add line for stem
        triFeatures.push({
          type: 'Feature',
          properties: { ...f.properties, element: 'arrow-stem' },
          geometry: { type: 'LineString', coordinates: [stemBase, tip] }
        })
      }
      return { type: 'FeatureCollection', features: triFeatures }
    }

    return {
      lanes: { type: 'FeatureCollection', features: lanePolygonFeatures },
      arrows: buildArrowTriangles(laneFeatures),
      junctions: { type: 'FeatureCollection', features: junctionFeatures }
    }
  } catch (e) {
    console.error('Error preparing SUMO network geojson', e)
    return null
  }
}

export function getDefaultLaneFillColor(props, { selectedId, isClosed }) {
  const id = String((props && (props.id || props.osm_id)) || '')
  if (selectedId && id === selectedId) return [255, 106, 0, 255]
  if (isClosed) return [255, 0, 0, 255]
  if (props && props.tunnel === 'yes') return [0, 0, 255, 255]
  const allow = ((props && props.allow) || '').split(',').map(s => s.trim())
  if (allow.includes('bus') && !allow.includes('private')) return [255, 255, 0, 255]
  if (allow.includes('private')) return [150, 150, 150, 255]
  return [0, 0, 0, 255]
}

export function buildSumoNetworkLayers(networkData, deck, { onHover, onClick, getLaneColor, updateTriggers, getClosedPredicate, getSelectedId, getHoveredId } = {}) {
  try {
    if (!networkData) return []

    function markingColor(props) { return [255, 255, 255, 255] }

    const lanesLayer = new deck.GeoJsonLayer({
      id: 'sumo-lanes',
      data: networkData.lanes,
      pickable: true,
      stroked: true,
      filled: true,
      lineWidthUnits: 'pixels',
      lineWidthMinPixels: 0.5,
      parameters: { depthTest: true },
      getFillColor: f => {
        if (getLaneColor) return getLaneColor(f, 'fill')
        const props = f.properties || {}
        const isClosed = getClosedPredicate ? getClosedPredicate(props) : false
        const selectedId = getSelectedId ? getSelectedId() : null
        return getDefaultLaneFillColor(props, { selectedId, isClosed })
      },
      getLineColor: f => {
        if (getLaneColor) return getLaneColor(f, 'line')
        const props = f.properties || {}
        const hoveredId = getHoveredId ? getHoveredId() : null
        const id = String((props.id || props.osm_id) || '')
        return (hoveredId && id === hoveredId) ? [0, 255, 255, 255] : [0, 0, 0, 50]
      },
      onHover,
      onClick,
      updateTriggers
    })

    const arrowsLayer = new deck.GeoJsonLayer({
      id: 'sumo-arrows',
      data: networkData.arrows,
      pickable: false,
      stroked: true,
      filled: true,
      lineWidthUnits: 'pixels',
      lineWidthMinPixels: 1,
      parameters: { depthTest: true },
      getFillColor: f => f.properties.element === 'arrow-stem' ? [0, 0, 0, 0] : markingColor(f.properties),
      getLineColor: f => f.properties.element === 'arrow-stem' ? markingColor(f.properties) : [0, 0, 0, 0]
    })

    const junctionsLayer = new deck.GeoJsonLayer({
      id: 'sumo-junctions',
      data: networkData.junctions,
      pickable: false,
      stroked: false,
      filled: true,
      parameters: { depthTest: true },
      getFillColor: [60, 60, 60, 255]
    })

    return [junctionsLayer, lanesLayer, arrowsLayer]
  } catch (_) {
    return []
  }
} 