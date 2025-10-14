const fdc_filer_radius = 0.75

function computeEdgeCenter(geometry) {
  if (!geometry || !geometry.coordinates) return null
  
  const coords = geometry.coordinates
  if (!coords || coords.length === 0) return null
  
  // Find the bounds of the edge
  let minLon = Infinity, minLat = Infinity
  let maxLon = -Infinity, maxLat = -Infinity
  
  for (const [lon, lat] of coords) {
    if (lon < minLon) minLon = lon
    if (lat < minLat) minLat = lat
    if (lon > maxLon) maxLon = lon
    if (lat > maxLat) maxLat = lat
  }
  
  return {
    lon: (minLon + maxLon) / 2,
    lat: (minLat + maxLat) / 2
  }
}

function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371 // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

export function updateFcdFilterShape(netData, closedRoads) {
  // Collect all closed edge centers
  if (!netData || !netData.features || !closedRoads.length) {
    return null
  }
  
  const centers = []
  for (const closedRoad of closedRoads) {
    const edge = netData.features.find(f => {
      const id = f.properties?.id || f.properties?.osm_id
      return String(id) === closedRoad.id
    })
    
    if (edge && edge.geometry) {
      const center = computeEdgeCenter(edge.geometry)
      if (center) centers.push(center)
    }
  }
  
  if (centers.length === 0) {
    return null
  }
  
  if (centers.length === 1) {
    // Single edge: 1km radius circle
    return {
      centerLon: centers[0].lon,
      centerLat: centers[0].lat,
      radiusKm: fdc_filer_radius
    }
  } else {
    // Multiple edges: find centroid and expand radius to include all edges + 1km buffer
    const centroidLon = centers.reduce((sum, c) => sum + c.lon, 0) / centers.length
    const centroidLat = centers.reduce((sum, c) => sum + c.lat, 0) / centers.length
    
    // Find max distance from centroid to any edge center
    let maxDistance = 0
    for (const center of centers) {
      const dist = haversineDistance(centroidLat, centroidLon, center.lat, center.lon)
      if (dist > maxDistance) maxDistance = dist
    }
    
    // Add 1km buffer to ensure all edges are fully covered
    return {
      centerLon: centroidLon,
      centerLat: centroidLat,
      radiusKm: maxDistance + fdc_filer_radius
    }
  }
}

