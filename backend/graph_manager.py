import osmnx as ox
import networkx as nx
import functools

def geocode_address(address):
    """
    Converts a text address into a (lat, lon) coordinate.
    """
    try:
        # ox.geocode returns (lat, lon)
        return ox.geocode(address)
    except Exception as e:
        return None

@functools.lru_cache(maxsize=32)
def download_dynamic_graph(coordinates):
    """
    Downloads and caches the street network using a bounding box
    that covers all provided coordinates.
    """
    lats = [c[0] for c in coordinates]
    lons = [c[1] for c in coordinates]
    
    # Calculate bounding box with a ~500m buffer (0.005 degrees)
    # Reducing this buffer drastically speeds up map download times
    buffer = 0.005
    north = max(lats) + buffer
    south = min(lats) - buffer
    east = max(lons) + buffer
    west = min(lons) - buffer
    
    # Download graph within bounding box
    # OSMnx 2.x bbox format is (west, south, east, north)
    G = ox.graph_from_bbox(bbox=(west, south, east, north), network_type='drive')
    
    # Impute missing edge speeds and travel times
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    
    # Ensure it's strongly connected to avoid unreachable nodes
    largest_cc = max(nx.strongly_connected_components(G), key=len)
    G = G.subgraph(largest_cc).copy()
    
    return G

def snap_to_nodes(G, coordinates):
    """
    Snaps a list of (lat, lon) coordinates to the nearest network nodes.
    Returns a list of node IDs.
    """
    lats = [c[0] for c in coordinates]
    lons = [c[1] for c in coordinates]
    
    # ox.distance.nearest_nodes takes (G, X, Y) where X=lons, Y=lats
    nodes = ox.distance.nearest_nodes(G, X=lons, Y=lats)
    return nodes

def get_node_coordinates(G, node_id):
    """
    Returns the (lat, lon) for a given node ID.
    """
    node = G.nodes[node_id]
    return node['y'], node['x']
