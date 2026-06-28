from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import graph_manager as gm
import traffic_ml as tml
import optimizer as opt
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RouteRequest(BaseModel):
    start: str
    stops: List[str]
    end: str
    time_of_day: str
    weather: str

@app.get("/api/search")
def search_location(q: str):
    headers = {"User-Agent": "RouteOptimizerApp/1.0"}
    try:
        response = requests.get(
            f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=5", 
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error searching location: {e}")
        return []

@app.get("/api/search")
def search_location(q: str):
    try:
        headers = {
            'User-Agent': 'RouteOptimiserApp/1.0 (ankit.route.optimizer@gmail.com)'
        }
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=5"
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data:
            results.append({
                "display_name": item.get("display_name"),
                "lat": item.get("lat"),
                "lon": item.get("lon")
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/optimize")
def optimize_route(req: RouteRequest):
    try:
        # Geocode all locations
        addresses = [req.start] + [s.strip() for s in req.stops if s.strip()] + [req.end]
        coords = []
        for addr in addresses:
            c = gm.geocode_address(addr)
            if c:
                coords.append(c)
            else:
                raise HTTPException(status_code=400, detail=f"Could not geocode {addr}")
                
        if len(coords) < 2:
            raise HTTPException(status_code=400, detail="Need at least a start and end location")
            
        # Download Graph
        # Using tuple of tuples so it's hashable for lru_cache
        hashable_coords = tuple((float(c[0]), float(c[1])) for c in coords)
        G = gm.download_dynamic_graph(hashable_coords)
        
        # Snap to nodes
        delivery_nodes = gm.snap_to_nodes(G, coords)
        
        # Traffic ML
        G_traffic = G.copy()
        G_traffic = tml.simulate_and_predict_traffic(G_traffic, req.time_of_day, req.weather)
        
        # Static Optimization
        start_idx = 0
        end_idx = len(delivery_nodes) - 1
        
        static_matrix, static_paths = opt.compute_distance_matrix(G_traffic, delivery_nodes, weight_attribute='length')
        static_order, static_dist = opt.solve_tsp(static_matrix, start_idx=start_idx, end_idx=end_idx)
        static_full_path = opt.get_full_route_path(static_order, delivery_nodes, static_paths) if static_order else []
        
        # AI Optimization
        ai_matrix, ai_paths = opt.compute_distance_matrix(G_traffic, delivery_nodes, weight_attribute='ai_travel_time')
        ai_order, ai_time = opt.solve_tsp(ai_matrix, start_idx=start_idx, end_idx=end_idx)
        ai_full_path = opt.get_full_route_path(ai_order, delivery_nodes, ai_paths) if ai_order else []
        
        # Map nodes back to coordinates for frontend rendering
        static_coords = []
        for node in static_full_path:
            lat, lon = gm.get_node_coordinates(G, node)
            static_coords.append([float(lat), float(lon)]) # Leaflet uses [lat, lon]
            
        ai_coords = []
        for node in ai_full_path:
            lat, lon = gm.get_node_coordinates(G, node)
            ai_coords.append([float(lat), float(lon)])
            
        # Gather Stop Coordinates for markers
        marker_coords = []
        for i, node in enumerate(delivery_nodes):
            lat, lon = gm.get_node_coordinates(G, node)
            marker_coords.append({
                "lat": float(lat),
                "lon": float(lon),
                "address": addresses[i]
            })
            
        # Extract actual times
        actual_static_time = 0.0
        if static_order:
            for i in range(len(static_full_path)-1):
                u, v = static_full_path[i], static_full_path[i+1]
                if G_traffic.is_multigraph():
                    min_t = min([float(G_traffic[u][v][k].get('ai_travel_time', 0)) for k in G_traffic[u][v]])
                    actual_static_time += min_t
                else:
                    actual_static_time += float(G_traffic[u][v].get('ai_travel_time', 0))
    
        actual_ai_time = 0.0
        if ai_order:
            for i in range(len(ai_full_path)-1):
                u, v = ai_full_path[i], ai_full_path[i+1]
                if G_traffic.is_multigraph():
                    min_t = min([float(G_traffic[u][v][k].get('ai_travel_time', 0)) for k in G_traffic[u][v]])
                    actual_ai_time += min_t
                else:
                    actual_ai_time += float(G_traffic[u][v].get('ai_travel_time', 0))
                    
        # Extract traffic congestion edges for rendering
        traffic_edges = []
        for u, v, data in G_traffic.edges(data=True):
            level = float(data.get('congestion_level', 0))
            if level > 0.4:
                if 'geometry' in data:
                    coords_seq = [[float(lat), float(lon)] for lon, lat in data['geometry'].coords]
                    traffic_edges.append({"coords": coords_seq, "level": level})
                else:
                    lat_u, lon_u = G_traffic.nodes[u]['y'], G_traffic.nodes[u]['x']
                    lat_v, lon_v = G_traffic.nodes[v]['y'], G_traffic.nodes[v]['x']
                    traffic_edges.append({"coords": [[float(lat_u), float(lon_u)], [float(lat_v), float(lon_v)]], "level": level})
    
        return {
            "static_route_coords": static_coords,
            "ai_route_coords": ai_coords,
            "markers": marker_coords,
            "traffic_heatmap": traffic_edges,
            "metrics": {
                "static_time_mins": round(actual_static_time / 60, 2),
                "ai_time_mins": round(actual_ai_time / 60, 2),
                "saved_time_mins": max(0, round((actual_static_time - actual_ai_time) / 60, 2))
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
