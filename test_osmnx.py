import osmnx as ox

addresses = [
    "Gateway of India, Mumbai",
    "Chhatrapati Shivaji Terminus, Mumbai",
    "Marine Drive, Mumbai"
]

coords = []
for addr in addresses:
    print(f"Geocoding: {addr}")
    c = ox.geocode(addr)
    print(f"Result: {c}")
    coords.append(c)
    
lats = [c[0] for c in coords]
lons = [c[1] for c in coords]

buffer = 0.005
north = max(lats) + buffer
south = min(lats) - buffer
east = max(lons) + buffer
west = min(lons) - buffer

print(f"Bounding box: North={north}, South={south}, East={east}, West={west}")
print(f"Distance approx: lat diff = {north-south}, lon diff = {east-west}")

print("Attempting to download graph...")
G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type='drive')
print(f"Graph downloaded with {len(G.nodes)} nodes and {len(G.edges)} edges.")
