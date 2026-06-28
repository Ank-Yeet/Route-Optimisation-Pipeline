# Intelligent Route Optimization App 🚚

This application is an end-to-end route optimization system that combines Geographic Information Systems (GIS), Graph Neural Networks (GNNs), and Combinatorial Optimization to solve a dynamic version of the Traveling Salesman Problem (TSP).

## Technical Architecture & Algorithms

### 1. GIS & Graph Network Extraction (`graph_manager.py`)
This module handles spatial data and transforms real-world maps into mathematical graphs.
- **Geocoding:** Uses OpenStreetMap's Nominatim API (via OSMnx) to translate textual addresses into `(latitude, longitude)` tuples.
- **Graph Extraction:** Uses **OSMnx** to query the Overpass API and download the road network within a dynamically calculated bounding box (extending slightly beyond the min/max coordinates of the requested stops). The road network is modeled as a **NetworkX MultiDiGraph**, where nodes are intersections and edges are road segments.
- **Spatial Snapping:** Uses `ox.distance.nearest_nodes` (which relies on spatial indexing structures like Ball Trees/KD-Trees from scikit-learn) to map the raw GPS coordinates of the delivery stops to the nearest valid nodes in the road graph.

### 2. Traffic Prediction via Graph Neural Networks (`traffic_ml.py`)
Traffic conditions are not uniform; congestion propagates through adjacent intersections. To model this, the application uses **PyTorch Geometric (PyG)** to implement a **Graph Convolutional Network (GCN)**.
- **Network Architecture:** The model `TrafficGNN` consists of two `GCNConv` layers. This architecture performs "message passing," where each node aggregates information from its immediate neighbors. The final layer uses a Sigmoid activation function to output a normalized congestion severity score `[0, 1]` for every intersection (node).
- **Feature Engineering:** Node features are synthetically generated using normalized spatial coordinates and base modifiers driven by categorical inputs (Time of Day and Weather).
- **Edge Weight Modification:** The GNN predicts node-level congestion, which is then mapped to the edges (roads) by averaging the severity of connecting nodes. If the congestion breaches a threshold (e.g., > 0.55), an exponential multiplier is applied to the base travel time of that road, simulating a localized traffic bottleneck.

### 3. Combinatorial Optimization (`optimizer.py`)
This module solves the routing problem by finding the optimal sequence of stops.
- **All-Pairs Shortest Path Matrix:** Before solving the TSP, the graph must be simplified into a distance matrix containing only the delivery stops. It uses the **A* (A-Star) Algorithm** (`nx.astar_path`) to compute the shortest path travel time between all pairs of required stops. It uses a Euclidean distance heuristic based on the spatial coordinates of the map nodes to intelligently guide the search toward the destination, reducing the search space compared to unguided algorithms. It does this twice: once for static distance, and once for AI-predicted travel times.
- **Solving the TSP:** Formulates the problem using **Google OR-Tools Constraint Programming (CP-SAT) Routing Solver**. 
- **Solution Strategy:** It uses the `PATH_CHEAPEST_ARC` heuristic as its first solution strategy. This algorithm iteratively connects nodes using the lowest-cost available edge that doesn't create a sub-tour, eventually forming a complete circuit (or open path, if the start and end nodes differ).
- **Path Reconstruction:** Once OR-Tools returns the optimal sequence of stops (e.g., `[Stop A -> Stop C -> Stop B]`), the application pieces together the full geographical route by retrieving the node-by-node path segments that were cached during the A* phase.

## Summary

In short, the application works by:
1. Converting locations into a topological graph using **OSMnx**.
2. Simulating traffic cascades using a **PyTorch GCN** (Graph Convolutional Network).
3. Computing a reduced distance matrix using the **A* (A-Star) Algorithm**.
4. Finding the optimal visiting sequence using the **Google OR-Tools TSP Solver**.
