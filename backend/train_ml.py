import torch
import torch.nn as nn
import torch.optim as optim
import networkx as nx
import random
import os
import sys

# Import the model architecture
from traffic_ml import TrafficGNN

def generate_synthetic_data(num_graphs=100):
    print(f"Generating {num_graphs} synthetic graphs for training...")
    dataset = []
    
    # Time scenarios: time_modifier drives the east/west spatial bias
    # Morning Rush -> high time_modifier -> east side congested
    # Evening Rush -> low time_modifier -> west side congested
    scenarios = [
        {"name": "Morning Rush", "time_mod": 0.9,  "east_heavy": True,  "west_heavy": False, "night": False},
        {"name": "Evening Rush", "time_mod": -0.9, "east_heavy": False, "west_heavy": True,  "night": False},
        {"name": "Night",        "time_mod": 0.0,  "east_heavy": False, "west_heavy": False, "night": True},
    ]

    # Weather: independent spatial biases
    # Rain   -> northern roads more congested
    # Storm  -> western/coastal roads more congested + overall high
    # Clear  -> no weather contribution
    weathers = [
        {"name": "Clear", "rain": 0.0, "storm": 0.0, "north_heavy": False, "coast_heavy": False, "base_add": 0.0},
        {"name": "Rain",  "rain": 1.0, "storm": 0.0, "north_heavy": True,  "coast_heavy": False, "base_add": 0.2},
        {"name": "Storm", "rain": 0.0, "storm": 1.0, "north_heavy": False, "coast_heavy": True,  "base_add": 0.4},
    ]

    for _ in range(num_graphs):
        # Create a grid graph to simulate city blocks
        # Grid is 10x10. Coordinates from 0 to 9.
        grid_size = 10
        G = nx.grid_2d_graph(grid_size, grid_size)
        
        scenario = random.choice(scenarios)
        weather = random.choice(weathers)
        
        node_features = []
        target_labels = []
        
        nodes_list = list(G.nodes())
        node_to_idx = {node: i for i, node in enumerate(nodes_list)}
        
        for node in nodes_list:
            x, y = node  # x is like lon, y is like lat
            
            # Normalize to 0.0 - 1.0 (mirrors traffic_ml.py normalization)
            lat = y / float(grid_size - 1)
            lon = x / float(grid_size - 1)
            
            # 5 features matching traffic_ml.py exactly
            feat1 = lat
            feat2 = lon
            feat3 = scenario["time_mod"]              # time signal
            feat4 = weather["rain"]                    # rain flag
            feat5 = weather["storm"]                   # storm flag
            node_features.append([feat1, feat2, feat3, feat4, feat5])
            
            # Build ground truth label from spatial rules
            base_target = weather["base_add"]
            if scenario["night"]:
                base_target = max(0.0, base_target - 0.3)

            # Time-of-day spatial bias
            if scenario["east_heavy"] and lon >= 0.5:
                base_target = min(1.0, base_target + 0.55)
            if scenario["west_heavy"] and lon < 0.5:
                base_target = min(1.0, base_target + 0.55)

            # Weather spatial bias
            if weather["north_heavy"] and lat >= 0.5:   # rain -> northern roads
                base_target = min(1.0, base_target + 0.4)
            if weather["coast_heavy"] and lon <= 0.2:   # storm -> coastal/western roads
                base_target = min(1.0, base_target + 0.5)

            # Add a little noise for realism
            target = max(0.0, min(1.0, base_target + random.uniform(-0.08, 0.08)))
            target_labels.append(target)
            
        # Build edge_index
        source_nodes = []
        target_nodes = []
        for u, v in G.edges():
            # Undirected graph, so add both directions
            source_nodes.append(node_to_idx[u])
            target_nodes.append(node_to_idx[v])
            source_nodes.append(node_to_idx[v])
            target_nodes.append(node_to_idx[u])
            
        edge_index = torch.tensor([source_nodes, target_nodes], dtype=torch.long)
        x_tensor = torch.tensor(node_features, dtype=torch.float)
        y_tensor = torch.tensor(target_labels, dtype=torch.float)
        
        dataset.append((x_tensor, edge_index, y_tensor))
        
    return dataset

def train_model():
    dataset = generate_synthetic_data(num_graphs=500)
    
    # Initialize the model
    model = TrafficGNN(in_channels=5, hidden_channels=16, out_channels=1)
    
    # Define loss function and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    epochs = 150
    print("\nStarting training loop...")
    
    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        
        # Shuffle dataset for each epoch
        random.shuffle(dataset)
        
        for x, edge_index, y in dataset:
            optimizer.zero_grad()
            
            # Forward pass
            out = model(x, edge_index).squeeze()
            
            # Calculate loss
            loss = criterion(out, y)
            
            # Backward pass and optimize
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        avg_loss = total_loss / len(dataset)
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch [{epoch+1}/{epochs}] - Loss: {avg_loss:.4f}")
            
    print("\nTraining complete!")
    
    # Save the trained weights
    save_path = os.path.join(os.path.dirname(__file__), "traffic_model.pt")
    torch.save(model.state_dict(), save_path)
    print(f"Saved trained model to {save_path}")

if __name__ == "__main__":
    train_model()
