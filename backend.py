import pandas as pd

class Graph:
    def __init__(self):
        self.nodes = set()
        self.edges = {}

    def add_node(self, value):
        self.nodes.add(value)
        self.edges[value] = []

    def add_edge(self, from_node, to_node, weight):
        self.edges[from_node].append((to_node, weight))
        self.edges[to_node].append((from_node, weight))  # Assuming an undirected graph

def load_graph_from_csv(file_path):
    df = pd.read_csv(file_path, index_col=0)
    graph = Graph()

    for node in df.index:
        graph.add_node(node)

    for from_node in df.index:
        for to_node, weight in df.loc[from_node].items():
            if pd.notna(weight) and weight > 0:
                graph.add_edge(from_node, to_node, weight)

    return graph

def dijkstra(graph, start):
    dist = {node: float('infinity') for node in graph.nodes}
    dist[start] = 0
    visited = set()

    while len(visited) < len(graph.nodes):
        current = min((node for node in graph.nodes if node not in visited), key=lambda node: dist[node])

        for neighbor, weight in graph.edges[current]:
            new_distance = dist[current] + weight
            if new_distance < dist[neighbor]:
                dist[neighbor] = new_distance

        visited.add(current)

    return dist

def shortest_route(graph, start, end):
    distances = dijkstra(graph, start)
    if end not in distances:
        return None
    path = [end]
    current = end
    while current != start:
        neighbors = graph.edges[current]
        previous = min(neighbors, key=lambda neighbor: distances[neighbor[0]])
        path.insert(0, previous[0])
        current = previous[0]

    return path


# csv_file_path = 'cp_metro.csv'
# graph = load_graph_from_csv(csv_file_path)

# start_node = input("Enter the starting metro station: ")
# end_node = input("Enter the destination metro station: ")

# if start_node not in graph.nodes or end_node not in graph.nodes:
#     print("Invalid station names. Please make sure the station names are correct.")
# else:
#     route = shortest_route(graph, start_node, end_node)
#     if route:
#         print(f"Shortest route from {start_node} to {end_node}: {route}")
#     else:
#         print(f"No route found from {start_node} to {end_node}.")