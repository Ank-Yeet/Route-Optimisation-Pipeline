import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.utils import from_networkx
import networkx as nx
import random
import functools
import math

class TrafficGNN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super(TrafficGNN, self).__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, out_channels)
        
    def forward(self, x, edge_index):
        # x is node features, edge_index is graph structure
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        return torch.sigmoid(x)  # Output between 0 and 1 representing congestion severity

import os

@functools.lru_cache(maxsize=32)
def get_gnn_model():
    """
    Returns an initialized GNN model. Loads trained weights if they exist,
    otherwise falls back to random weights.
    """
    model = TrafficGNN(in_channels=5, hidden_channels=16, out_channels=1)
    
    weights_path = os.path.join(os.path.dirname(__file__), "traffic_model.pt")
    if os.path.exists(weights_path):
        try:
            model.load_state_dict(torch.load(weights_path))
            print(f"Loaded trained traffic model from {weights_path}")
        except Exception as e:
            print(f"Failed to load trained model weights: {e}")
            
    model.eval()
    return model

def simulate_and_predict_traffic(G, time_of_day="Morning (8 AM)", weather="Clear"):
    """
    Simulates traffic conditions using a Graph Neural Network.
    The GNN takes synthetic node features (based on time and weather)
    and predicts congestion for the network.
    """
    # 1. Separate time and weather into independent signals
    time_modifier = 0.0
    if time_of_day == "Morning Rush (8 AM)":
        time_modifier = 0.9   # High signal -> east-heavy congestion
    elif time_of_day == "Evening Rush (6 PM)":
        time_modifier = -0.9  # Low signal -> west-heavy congestion
    elif time_of_day == "Night (11 PM)":
        time_modifier = 0.0   # Neutral -> low overall congestion

    rain_flag = 1.0 if weather == "Rain" else 0.0
    storm_flag = 1.0 if weather == "Storm" else 0.0

    # 2. Assign 5 features to graph nodes for the GNN
    lats = [G.nodes[n].get('y', 0) for n in G.nodes()]
    lons = [G.nodes[n].get('x', 0) for n in G.nodes()]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    for i, node in enumerate(G.nodes()):
        lat, lon = G.nodes[node].get('y', 0), G.nodes[node].get('x', 0)
        # Normalize spatial coordinates to 0.0 - 1.0
        feat1 = (lat - min_lat) / (max_lat - min_lat + 1e-6)  # normalized lat
        feat2 = (lon - min_lon) / (max_lon - min_lon + 1e-6)  # normalized lon
        feat3 = time_modifier   # time-of-day signal
        feat4 = rain_flag       # rain flag
        feat5 = storm_flag      # storm flag

        G.nodes[node]['features'] = [feat1, feat2, feat3, feat4, feat5]

    # Map nodes to indices
    nodes_list = list(G.nodes())
    node_to_idx = {node: i for i, node in enumerate(nodes_list)}
    
    # Build edge_index manually to avoid 'from_networkx' attribute inconsistency errors
    source_nodes = []
    target_nodes = []
    for u, v in G.edges():
        source_nodes.append(node_to_idx[u])
        target_nodes.append(node_to_idx[v])
        
    edge_index = torch.tensor([source_nodes, target_nodes], dtype=torch.long)
    
    # Ensure node features are a tensor
    node_features = []
    for node in nodes_list:
        node_features.append(G.nodes[node]['features'])  # 5 features per node
    x = torch.tensor(node_features, dtype=torch.float)
    
    # 3. Predict Traffic using GNN
    model = get_gnn_model()
    with torch.no_grad():
        node_congestion_pred = model(x, edge_index).squeeze().numpy()
        
    # 4. Map node congestion predictions back to edges
    for u, v, k, data in G.edges(keys=True, data=True):
        base_time = data.get('travel_time', data.get('length', 100) / (30 * 1000 / 3600))
        
        u_idx = node_to_idx[u]
        v_idx = node_to_idx[v]
        
        # Average congestion of the two nodes
        avg_congestion = (node_congestion_pred[u_idx] + node_congestion_pred[v_idx]) / 2.0
        
        # Derive an overall intensity from the time/weather inputs for the multiplier
        # abs(time_modifier) captures rush hour intensity; rain/storm add on top
        intensity = abs(time_modifier) * 0.5 + rain_flag * 0.3 + storm_flag * 0.6

        # Normalize the GNN output
        normalized_cong = min(1.0, max(0.0, float(avg_congestion)))
        
        if normalized_cong > 0.55:
            # Heavy traffic jam — exponential slow-down
            multiplier = 1.0 + (normalized_cong * 15.0) + intensity * 5
        else:
            # Clear road — mild global slowdown from rush/weather
            multiplier = 1.0 + intensity
            
        data['ai_travel_time'] = base_time * multiplier
        data['congestion_level'] = normalized_cong

    return G
