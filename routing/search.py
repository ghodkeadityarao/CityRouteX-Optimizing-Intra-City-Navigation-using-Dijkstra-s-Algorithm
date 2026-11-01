"""Shortest-path search on the platform graph: Dijkstra with a heap, and A* with a distance estimate.

Both start from every platform of the origin station (boarding any line costs nothing) and stop at
the first platform of the destination station they reach.
"""
import heapq


def dijkstra(graph, sources, targets, transfer_cost=None):
    """Cheapest path. Returns (cost, [nodes], settled) or None when the target cannot be reached.

    `transfer_cost` replaces the cost of a line change (used to rank routes by transfers first);
    `settled` is the number of nodes the search finished, a measure of the work done.
    """
    return _search(graph, sources, targets, transfer_cost, heuristic=None)


def astar(graph, sources, targets, target_station, transfer_cost=None):
    """Same answer as dijkstra, guided by the straight-line travel time to the destination.

    The estimate is the straight-line distance at the fastest speed in the model with no stops or
    transfers, which can never exceed the true cost, so the result is still the cheapest path.
    """
    net, speed = graph.network, graph.max_kmh

    def h(node):
        return net.straight_km(graph.platform[node][0], target_station) / speed * 60

    return _search(graph, sources, targets, transfer_cost, heuristic=h)


def _search(graph, sources, targets, transfer_cost, heuristic):
    goal = set(targets)
    dist = {s: 0.0 for s in sources}
    prev = {}
    h = heuristic or (lambda node: 0.0)
    heap = [(h(s), 0.0, s) for s in sources]
    heapq.heapify(heap)
    done, settled = set(), 0
    while heap:
        _, d, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        settled += 1
        if u in goal:
            path = [u]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return d, path[::-1], settled
        for v, w, line, _ in graph.adj[u]:
            if line is None and transfer_cost is not None:
                w = transfer_cost
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd + h(v), nd, v))
    return None
