import networkx as nx
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import math

def compute_distance_matrix(G, delivery_nodes, weight_attribute='travel_time'):
    """
    Computes the shortest path travel time between all pairs of delivery nodes.
    Returns a matrix (list of lists) and a dictionary of the actual paths.
    """
    n = len(delivery_nodes)
    matrix = [[0] * n for _ in range(n)]
    paths = {}
    
    # Heuristic for A* based on Euclidean distance
    def heuristic(u, v):
        try:
            u_y, u_x = G.nodes[u]['y'], G.nodes[u]['x']
            v_y, v_x = G.nodes[v]['y'], G.nodes[v]['x']
            # Approximate meters (rough heuristic to guide A*)
            dist_meters = math.sqrt((u_y - v_y)**2 + (u_x - v_x)**2) * 111000
            
            if weight_attribute == 'length':
                return dist_meters
            else:
                # If weight is time-based, convert meters to seconds using max speed
                # Assume a generous max speed like 120 km/h (33.33 m/s) to be admissible
                return dist_meters / 33.33
        except KeyError:
            return 0

    # Using A* Algorithm to compute paths point-to-point. 
    # Note: A* computes one source-target pair at a time (O(n^2) calls).
    for i in range(n):
        source = delivery_nodes[i]
        for j in range(n):
            if i == j:
                matrix[i][j] = 0
            else:
                target = delivery_nodes[j]
                try:
                    path = nx.astar_path(G, source, target, heuristic=heuristic, weight=weight_attribute)
                    
                    # Compute path length
                    length = 0
                    for u, v in zip(path[:-1], path[1:]):
                        if G.is_multigraph():
                            length += min([edge_data.get(weight_attribute, 0) for edge_data in G[u][v].values()])
                        else:
                            length += G[u][v].get(weight_attribute, 0)
                            
                    matrix[i][j] = int(length * 100)
                    paths[(source, target)] = path
                except nx.NetworkXNoPath:
                    matrix[i][j] = 9999999
                    paths[(source, target)] = []
                except Exception:
                    matrix[i][j] = 9999999
                    paths[(source, target)] = []
                    
    return matrix, paths

def solve_tsp(distance_matrix, start_idx=0, end_idx=None):
    """
    Uses Google OR-Tools to solve the Traveling Salesman Problem.
    If end_idx is provided, it solves an Open Path TSP (Start -> Stops -> End).
    If end_idx is None, it solves a Closed Loop TSP (Start -> Stops -> Start).
    """
    n = len(distance_matrix)
    
    if end_idx is not None:
        manager = pywrapcp.RoutingIndexManager(n, 1, [start_idx], [end_idx])
    else:
        manager = pywrapcp.RoutingIndexManager(n, 1, start_idx)

    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        
        # Append the final node (either the End Node or returning to the Start Node)
        route.append(manager.IndexToNode(index))
        
        total_cost = solution.ObjectiveValue() / 100.0
        return route, total_cost
    else:
        return None, None

def get_full_route_path(ordered_indices, delivery_nodes, paths_dict):
    """
    Reconstructs the full node-by-node path in the graph based on the optimal stop order.
    """
    full_path = []
    for i in range(len(ordered_indices) - 1):
        source_idx = ordered_indices[i]
        target_idx = ordered_indices[i+1]
        
        source_node = delivery_nodes[source_idx]
        target_node = delivery_nodes[target_idx]
        
        segment = paths_dict.get((source_node, target_node), [])
        
        if i == 0:
            full_path.extend(segment)
        else:
            full_path.extend(segment[1:])
            
    return full_path
