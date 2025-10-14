"""
Generate Congestion Map Data from SUMO EdgeData

This script processes SUMO edgedata output and network.net.xml to create
a color-coded traffic congestion map with speed/congestion metrics per edge.
Only outputs edges with data, coordinates converted to lon/lat.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import statistics
import sys


def parse_edgedata_summary(edgedata_path: Path) -> Dict[str, Dict[str, float]]:
    """Parse edgedata XML and calculate average metrics per edge.
    
    Returns:
        Dictionary mapping edge_id -> {avg_speed, avg_density, avg_occupancy, avg_travel_time}
    """
    if not edgedata_path.exists():
        return {}
    
    tree = ET.parse(str(edgedata_path))
    root = tree.getroot()
    
    # Collect all measurements per edge
    edge_measurements: Dict[str, List[Dict[str, float]]] = {}
    
    for interval in root.findall('interval'):
        for edge in interval.findall('edge'):
            edge_id = edge.get('id')
            if not edge_id:
                continue
            
            # Extract metrics
            speed = float(edge.get('speed', 0))  # m/s
            density = float(edge.get('density', 0))  # vehicles/km
            occupancy = float(edge.get('occupancy', 0))  # percentage
            traveltime = float(edge.get('traveltime', 0))  # seconds
            sampled_seconds = float(edge.get('sampledSeconds', 0))
            
            if edge_id not in edge_measurements:
                edge_measurements[edge_id] = []
            
            edge_measurements[edge_id].append({
                'speed': speed,
                'density': density,
                'occupancy': occupancy,
                'traveltime': traveltime,
                'sampledSeconds': sampled_seconds
            })
    
    # Calculate averages per edge
    edge_summary = {}
    for edge_id, measurements in edge_measurements.items():
        if not measurements:
            continue
        
        # Weight by sampledSeconds if available
        total_sampled = sum(m['sampledSeconds'] for m in measurements)
        
        if total_sampled > 0:
            # Weighted average
            avg_speed = sum(m['speed'] * m['sampledSeconds'] for m in measurements) / total_sampled
            avg_density = sum(m['density'] * m['sampledSeconds'] for m in measurements) / total_sampled
            avg_occupancy = sum(m['occupancy'] * m['sampledSeconds'] for m in measurements) / total_sampled
            avg_traveltime = sum(m['traveltime'] * m['sampledSeconds'] for m in measurements) / total_sampled
        else:
            # Simple average
            avg_speed = statistics.mean(m['speed'] for m in measurements)
            avg_density = statistics.mean(m['density'] for m in measurements)
            avg_occupancy = statistics.mean(m['occupancy'] for m in measurements)
            avg_traveltime = statistics.mean(m['traveltime'] for m in measurements)
        
        edge_summary[edge_id] = {
            'avg_speed_ms': avg_speed,
            'avg_speed_kmh': avg_speed * 3.6,  # Convert m/s to km/h
            'avg_density': avg_density,
            'avg_occupancy': avg_occupancy,
            'avg_traveltime': avg_traveltime,
            'total_sampled_seconds': total_sampled
        }
    
    return edge_summary


def parse_network_location(network_xml_path: Path) -> Tuple[Tuple[float, float], str]:
    """Parse network location info for coordinate conversion.
    
    Returns:
        (netOffset_x, netOffset_y), projParameter
    """
    tree = ET.parse(str(network_xml_path))
    root = tree.getroot()
    location = root.find('location')
    
    if location is None:
        return (0.0, 0.0), "+proj=longlat +datum=WGS84"
    
    # Parse netOffset: "-588162.19,-5625039.79"
    net_offset_str = location.get('netOffset', '0.0,0.0')
    offset_parts = net_offset_str.split(',')
    net_offset = (float(offset_parts[0]), float(offset_parts[1]))
    
    # Parse projection
    proj_param = location.get('projParameter', '+proj=longlat +datum=WGS84')
    
    return net_offset, proj_param


def convert_shape_to_lonlat(shape_str: str, net_offset: Tuple[float, float], proj_param: str) -> List[List[float]]:
    """Convert SUMO shape string to lon/lat coordinates.
    
    Args:
        shape_str: Space-separated x,y pairs like "100.0,200.0 101.0,201.0"
        net_offset: (offset_x, offset_y) from network location
        proj_param: Projection parameter string
    
    Returns:
        List of [lon, lat] coordinate pairs
    """
    try:
        from pyproj import Transformer
        
        # Create transformer from UTM to WGS84
        transformer = Transformer.from_crs(proj_param, "EPSG:4326", always_xy=True)
        
        coords = []
        for point in shape_str.split():
            x_str, y_str = point.split(',')
            # Add back the offset to get original UTM coordinates
            x_utm = float(x_str) + net_offset[0]
            y_utm = float(y_str) + net_offset[1]
            # Transform to lon/lat
            lon, lat = transformer.transform(x_utm, y_utm)
            coords.append([lon, lat])
        
        return coords
    except ImportError:
        # Fallback: return raw coordinates if pyproj not available
        sys.stderr.write("Warning: pyproj not available, coordinates may be incorrect\n")
        coords = []
        for point in shape_str.split():
            x_str, y_str = point.split(',')
            coords.append([float(x_str), float(y_str)])
        return coords
    except Exception as e:
        sys.stderr.write(f"Warning: coordinate conversion failed: {e}\n")
        return []


def parse_network_edges(network_xml_path: Path) -> Dict[str, Dict[str, Any]]:
    """Parse network.net.xml and extract edge information.
    
    Returns:
        Dictionary mapping edge_id -> {geometry, max_speed_ms, max_speed_kmh}
    """
    net_offset, proj_param = parse_network_location(network_xml_path)
    
    edges = {}
    
    # Use iterparse for memory efficiency
    context = ET.iterparse(str(network_xml_path), events=("start", "end"))
    _, _ = next(context)  # Skip root
    
    for event, elem in context:
        if event == "end" and elem.tag == "edge":
            edge_id = elem.get("id")
            
            # Skip internal edges (junctions)
            if not edge_id or edge_id.startswith(":"):
                elem.clear()
                continue
            
            # Get first lane to extract shape and speed
            lanes = elem.findall("lane")
            if not lanes:
                elem.clear()
                continue
            
            first_lane = lanes[0]
            shape_str = first_lane.get("shape")
            speed_str = first_lane.get("speed")
            
            if not shape_str or not speed_str:
                elem.clear()
                continue
            
            try:
                max_speed_ms = float(speed_str)
                max_speed_kmh = max_speed_ms * 3.6
                
                # Convert coordinates to lon/lat
                coordinates = convert_shape_to_lonlat(shape_str, net_offset, proj_param)
                
                if len(coordinates) >= 2:
                    edges[edge_id] = {
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': coordinates
                        },
                        'max_speed_ms': max_speed_ms,
                        'max_speed_kmh': max_speed_kmh
                    }
            except (ValueError, Exception):
                pass
            
            elem.clear()
    
    sys.stderr.write(f"Loaded {len(edges)} edges from network.net.xml\n")
    return edges


def classify_congestion(speed_kmh: float, max_speed: float = 50.0) -> Dict[str, Any]:
    """Classify congestion level based on speed.
    
    Args:
        speed_kmh: Average speed in km/h
        max_speed: Maximum expected speed for normalization
    
    Returns:
        Dictionary with congestion level, color, and category
    """
    if speed_kmh <= 0:
        return {
            'level': 'no_data',
            'category': 'No Data',
            'color': '#808080',
            'speed_ratio': 0
        }
    
    # Speed ratio (0-1, where 1 is free flow)
    speed_ratio = min(speed_kmh / max_speed, 1.0)
    
    # Classification based on speed ratio
    if speed_ratio >= 0.8:
        # Free flow: 80-100% of max speed
        category = 'free_flow'
        color = '#22c55e'  # Green
        label = 'Free Flow'
    elif speed_ratio >= 0.6:
        # Light congestion: 60-80% of max speed
        category = 'light'
        color = '#84cc16'  # Light green
        label = 'Light Traffic'
    elif speed_ratio >= 0.4:
        # Moderate congestion: 40-60% of max speed
        category = 'moderate'
        color = '#eab308'  # Yellow
        label = 'Moderate Congestion'
    elif speed_ratio >= 0.2:
        # Heavy congestion: 20-40% of max speed
        category = 'heavy'
        color = '#f97316'  # Orange
        label = 'Heavy Congestion'
    else:
        # Severe congestion: < 20% of max speed
        category = 'severe'
        color = '#ef4444'  # Red
        label = 'Severe Congestion'
    
    return {
        'level': category,
        'category': label,
        'color': color,
        'speed_ratio': speed_ratio
    }


def generate_congestion_geojson(
    network_xml_path: Path,
    edgedata_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """Generate a GeoJSON with congestion data for visualization.
    Only outputs edges that have traffic data.
    
    Args:
        network_xml_path: Path to network.net.xml file
        edgedata_path: Path to SUMO edgedata XML
        output_path: Path to write output GeoJSON
    
    Returns:
        Statistics about the congestion data
    """
    # Parse network edges
    network_edges = parse_network_edges(network_xml_path)
    
    # Parse edge data from simulation
    edge_data = parse_edgedata_summary(edgedata_path)
    
    # Statistics
    stats = {
        'total_edges_in_network': len(network_edges),
        'edges_with_data': 0,
        'avg_speed_kmh': 0,
        'congestion_distribution': {
            'free_flow': 0,
            'light': 0,
            'moderate': 0,
            'heavy': 0,
            'severe': 0,
            'no_data': 0
        }
    }
    
    # Build output features - only for edges with data
    output_features = []
    speeds: List[float] = []
    
    for edge_id, data in edge_data.items():
        # Skip if edge not in network
        if edge_id not in network_edges:
            continue
        
        edge_info = network_edges[edge_id]
        speed_kmh = data['avg_speed_kmh']
        speeds.append(speed_kmh)
        
        # Classify congestion
        max_speed_kmh = edge_info['max_speed_kmh']
        congestion = classify_congestion(speed_kmh, max_speed_kmh)
        
        stats['edges_with_data'] += 1
        stats['congestion_distribution'][congestion['level']] += 1
        
        # Create feature
        feature = {
            'type': 'Feature',
            'geometry': edge_info['geometry'],
            'properties': {
                'id': edge_id,
                'avg_speed_kmh': round(speed_kmh, 2),
                'max_speed_kmh': round(max_speed_kmh, 2),
                'avg_density': round(data['avg_density'], 2),
                'avg_occupancy': round(data['avg_occupancy'], 2),
                'avg_traveltime': round(data['avg_traveltime'], 2),
                'congestion_level': congestion['level'],
                'congestion_category': congestion['category'],
                'congestion_color': congestion['color'],
                'speed_ratio': round(congestion['speed_ratio'], 3)
            }
        }
        output_features.append(feature)
    
    # Calculate average speed
    if speeds:
        stats['avg_speed_kmh'] = round(statistics.mean(speeds), 2)
    
    # Create output GeoJSON
    output_geojson = {
        'type': 'FeatureCollection',
        'metadata': {
            'description': 'Traffic congestion map (edges with data only)',
            'generated_from': str(edgedata_path.name),
            'statistics': stats
        },
        'features': output_features
    }
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_geojson, f, indent=2)
    
    return stats


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python generate_congestion_map.py <network.net.xml> <edgedata.xml> <output.geojson>")
        sys.exit(1)
    
    network_path = Path(sys.argv[1])
    edgedata_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    
    stats = generate_congestion_geojson(network_path, edgedata_path, output_path)
    
    print(f"\nCongestion Map Generated: {output_path}")
    print(f"Total edges in network: {stats['total_edges_in_network']}")
    print(f"Edges with data: {stats['edges_with_data']}")
    print(f"Average speed: {stats['avg_speed_kmh']} km/h")
    print("\nCongestion Distribution:")
    for level, count in stats['congestion_distribution'].items():
        print(f"  {level}: {count}")


