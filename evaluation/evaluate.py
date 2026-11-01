"""Measure the routing code and compare it with the original version of this project.

    python evaluation/evaluate.py

Writes results.json, route_comparison.csv, sensitivity.csv and results.png to evaluation/results/.

What is measured
  1. Data: the original 229-station adjacency matrix against the OpenStreetMap network.
  2. Correctness: heap Dijkstra and A* against networkx on every ordered pair of stations.
  3. Original algorithm: does its route reconstruction survive weighted edges? how long are the
     routes it picks when they are timed with the weighted model?
  4. Speed: original O(V^2) Dijkstra, heap Dijkstra and A* on the same graph and the same queries.
  5. Fastest versus fewest-transfers routes over every pair of stations.
  6. Sensitivity: how many routes change when the travel-time assumptions change.
  7. Fares: how they spread over the network, what the Airport Express adds, and how often a
     fare would change if the modelled distances were a few percent off.
"""
import itertools
import json
import random
import statistics
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import legacy  # noqa: E402  (the original backend.py)
from routing.network import Params  # noqa: E402
from routing.planner import Planner, RouteError  # noqa: E402

RESULTS = HERE / "results"
SEED = 0
TIMING_QUERIES = 2000
LEGACY_WEIGHTED_QUERIES = 500


def round_(x, n=2):
    return round(float(x), n)


def pct(a, b):
    return round(100 * a / b, 1)


def timed_ms(fn, items):
    start = time.perf_counter()
    for item in items:
        fn(item)
    return 1000 * (time.perf_counter() - start) / len(items)


# --- 1. data audit ---------------------------------------------------------------------------

def audit_data(planner):
    net = planner.network
    old = pd.read_csv(HERE / "original_cp_metro.csv", index_col=0, encoding="utf-8-sig")
    ids = {name: net.find(name) for name in old.index}
    unmatched = [n for n, i in ids.items() if i is None]
    old_edges = {tuple(sorted((ids[a], ids[b]))) for a in old.index for b in old.columns
                 if old.loc[a, b] == 1 and a != b}
    new_edges = {tuple(sorted((a, b))) for _, a, b, _ in net.segments} | {tuple(sorted((a, b))) for a, b, _ in net.links}
    skips = sorted((a, b) for a, b in old_edges - new_edges)
    unique = {tuple(sorted((a, b))): km for _, a, b, km in net.segments}
    km = sum(unique.values())
    return {
        "original_stations": len(old.index), "original_stations_unmatched_after_renames": len(unmatched),
        "original_edges": len(old_edges), "original_edges_in_the_network_now": len(old_edges & new_edges),
        "original_edges_not_in_the_network_now": len(old_edges - new_edges),
        "of_which_skip_a_station_that_is_there_now": len(skips),
        "stations_now": len(net.stations), "edges_now": len(new_edges),
        "stations_not_in_original": len(net.stations) - len(set(ids.values())),
        "edges_not_in_original": len(new_edges - old_edges),
        "original_matrix_asymmetric_pairs": int(
            sum(1 for a in old.index for b in old.columns if old.loc[a, b] == 1 and old.loc[b, a] == 0)),
        "straight_line_km_between_stations": round_(km, 1),
    }, ids, old


# --- 2. correctness --------------------------------------------------------------------------

def reference_graph(graph):
    G = nx.DiGraph()
    for u, edges in enumerate(graph.adj):
        for v, w, _, _ in edges:
            G.add_edge(u, v, weight=w)
    return G


def check_correctness(planner):
    g, n = planner.graph, len(planner.network.stations)
    astar = Planner(planner.network, algorithm="astar")
    G = reference_graph(g)
    bad_d = bad_a = 0
    pairs = 0
    for a in range(n):
        lengths = nx.multi_source_dijkstra_path_length(G, g.at_station[a], weight="weight")
        for b in range(n):
            if a == b:
                continue
            truth = min(lengths[t] for t in g.at_station[b])
            pairs += 1
            bad_d += abs(planner.search(a, b)[0] - truth) > 1e-6
            bad_a += abs(astar.search(a, b)[0] - truth) > 1e-6
    return {"ordered_pairs_checked": pairs, "dijkstra_mismatches_vs_networkx": int(bad_d),
            "astar_mismatches_vs_networkx": int(bad_a)}


# --- 3. the original algorithm ----------------------------------------------------------------

def station_weighted_legacy(planner):
    """The original Graph class holding the new network with travel-time weights (station level)."""
    best = {}
    for line, a, b, straight in planner.network.segments:
        km = straight * planner.graph.params.circuity
        minutes = km / planner.graph.params.speed(line) * 60 + planner.graph.params.dwell_min
        best[(a, b)] = min(best.get((a, b), 1e9), minutes)
    g = legacy.Graph()
    for s in planner.network.stations:
        g.add_node(s.id)
    for (a, b), w in best.items():
        g.add_edge(a, b, w)
    return g, best


def legacy_route_minutes(planner, station_path):
    """Time of a given station sequence in the weighted model, choosing the best line at each hop.
    Returns None if two consecutive stations are not joined by any line."""
    g = planner.graph
    transfer = g.params.transfer_min
    first = g.at_station[station_path[0]]
    dp = {u: 0.0 for u in first}
    for s, t in zip(station_path, station_path[1:]):
        arrive = {}
        for u, cost in dp.items():
            for v, w, line, _ in g.adj[u]:
                if g.platform[v][0] == t:
                    arrive[v] = min(arrive.get(v, 1e18), cost + w)
        if not arrive:
            return None
        best = min(arrive.values())
        dp = {v: min(arrive.get(v, 1e18), best + transfer) for v in g.at_station[t]}
    return min(dp.values())


def station_neighbours(planner):
    g = planner.graph
    out = {}
    for sid, nodes in enumerate(g.at_station):
        out[sid] = {g.platform[v][0] for u in nodes for v, _, _, _ in g.adj[u]} - {sid}
    return out


def repair(path, near):
    """Put back a station that the original data skipped: if two consecutive stations are not
    neighbours but share exactly one common neighbour, insert it. Returns (path, stations added)."""
    fixed, added = [path[0]], 0
    for s, t in zip(path, path[1:]):
        if t not in near[s]:
            common = near[s] & near[t]
            if len(common) == 1:
                fixed.append(next(iter(common)))
                added += 1
        fixed.append(t)
    return fixed, added


def evaluate_original(planner, ids, old):
    net = planner.network
    near = station_neighbours(planner)
    old_graph = legacy.load_graph_from_csv(str(HERE / "original_cp_metro.csv"))   # every edge weighs 1
    names = sorted(old_graph.nodes)
    rows, invalid, skipped_a_station = [], 0, 0
    for a, b in itertools.combinations(names, 2):
        sa, sb = ids[a], ids[b]
        route = legacy.shortest_route(old_graph, a, b)
        stations, added = repair([ids[x] for x in route], near)
        skipped_a_station += added > 0
        minutes = legacy_route_minutes(planner, stations)
        if minutes is None:
            invalid += 1
            continue
        try:
            best = planner.plan(net.stations[sa].name, net.stations[sb].name, "fastest")
        except RouteError:                      # the one pair joined by a walkway, not a train
            continue
        rows.append({"from": a, "to": b, "original_stops": len(route) - 1, "original_minutes": minutes,
                     "fastest_minutes": best.minutes, "fastest_stops": best.stops,
                     "fastest_transfers": best.transfers})
    df = pd.DataFrame(rows)
    df["extra_minutes"] = df.original_minutes - df.fastest_minutes
    df.round(2).to_csv(RESULTS / "route_comparison.csv", index=False)
    slower = df[df.extra_minutes > 0.01]
    summary = {
        "pairs_compared": len(df), "pairs_that_could_not_be_timed": invalid,
        "pairs_whose_original_route_skips_a_station_pct": pct(skipped_a_station, len(df) + invalid),
        "original_route_not_the_fastest_pct": pct(len(slower), len(df)),
        "mean_extra_minutes_over_all_pairs": round_(df.extra_minutes.mean()),
        "mean_extra_minutes_when_slower": round_(slower.extra_minutes.mean()),
        "p90_extra_minutes": round_(df.extra_minutes.quantile(0.9)),
        "max_extra_minutes": round_(df.extra_minutes.max()),
        "mean_minutes_original": round_(df.original_minutes.mean()), "mean_minutes_fastest": round_(df.fastest_minutes.mean()),
    }
    return summary, df


def legacy_on_weights(planner):
    """The original path reconstruction (walk back to the neighbour with the smallest distance)
    on weighted edges: how often does it return a path that is not the cheapest?"""
    g, best = station_weighted_legacy(planner)
    rng = random.Random(SEED)
    n = len(planner.network.stations)
    cost = lambda a, b: best.get((a, b), best.get((b, a)))
    wrong = broken = 0
    pairs = [tuple(rng.sample(range(n), 2)) for _ in range(LEGACY_WEIGHTED_QUERIES)]
    G = nx.Graph()
    for (a, b), w in best.items():
        G.add_edge(a, b, weight=w)
    for a, b in pairs:
        dist = legacy.dijkstra(g, a)
        path, current, steps = [b], b, 0
        while current != a and steps < 500:
            current = min(g.edges[current], key=lambda e: dist[e[0]])[0]
            path.append(current)
            steps += 1
        if current != a:
            broken += 1
            continue
        got = sum(cost(x, y) for x, y in zip(path, path[1:]))
        if got > nx.shortest_path_length(G, a, b, weight="weight") + 1e-6:
            wrong += 1
    return {"queries": len(pairs), "wrong_path_pct": pct(wrong + broken, len(pairs)),
            "never_reached_the_start_pct": pct(broken, len(pairs))}


# --- 4. speed ---------------------------------------------------------------------------------

def benchmark(planner):
    g, n = planner.graph, len(planner.network.stations)
    rng = random.Random(SEED)
    pairs = [tuple(rng.sample(range(n), 2)) for _ in range(TIMING_QUERIES)]
    astar = Planner(planner.network, algorithm="astar")
    # the original O(V^2) Dijkstra on the same platform graph and weights
    old = legacy.Graph()
    for u in range(len(g)):
        old.add_node(u)
    for u, edges in enumerate(g.adj):
        for v, w, _, _ in edges:
            old.edges[u].append((v, w))
    legacy_ms = timed_ms(lambda p: legacy.dijkstra(old, g.at_station[p[0]][0]), pairs[:300])
    heap_ms = timed_ms(lambda p: planner.search(*p), pairs)
    astar_ms = timed_ms(lambda p: astar.search(*p), pairs)
    d = [planner.search(*p)[2] for p in pairs]
    a = [astar.search(*p)[2] for p in pairs]
    return {"queries": len(pairs), "platform_nodes": len(g),
            "original_dijkstra_ms_per_query": round_(legacy_ms, 3), "heap_dijkstra_ms_per_query": round_(heap_ms, 3),
            "astar_ms_per_query": round_(astar_ms, 3),
            "heap_speedup_over_original": round_(legacy_ms / heap_ms, 1),
            "dijkstra_nodes_settled_mean": round_(statistics.mean(d), 1), "astar_nodes_settled_mean": round_(statistics.mean(a), 1),
            "astar_fewer_nodes_pct": round_(100 * (1 - statistics.mean(a) / statistics.mean(d)), 1)}


# --- 5. fastest versus fewest transfers -------------------------------------------------------

def route_key(route):
    return tuple((l.line, l.stations[0], l.stations[-1]) for l in route.legs)


def all_pairs(planner):
    """Every pair of stations a train connects (the pair joined only by a walkway is left out)."""
    walkways = {frozenset((a, b)) for a, b, _ in planner.network.links}
    return [p for p in itertools.combinations(range(len(planner.network.stations)), 2) if frozenset(p) not in walkways]


def mode_tradeoff(planner):
    rows = []
    names = [s.name for s in planner.network.stations]
    for a, b in all_pairs(planner):
        fast, few = planner.plan(names[a], names[b], "fastest"), planner.plan(names[a], names[b], "fewest_transfers")
        rows.append((fast.minutes, few.minutes, fast.transfers, few.transfers, route_key(fast) != route_key(few)))
    df = pd.DataFrame(rows, columns=["fast_min", "few_min", "fast_tr", "few_tr", "differs"])
    diff = df[df.differs]
    return {"pairs": len(df), "mean_minutes_fastest": round_(df.fast_min.mean()),
            "mean_transfers_fastest": round_(df.fast_tr.mean()), "mean_transfers_fewest": round_(df.few_tr.mean()),
            "pairs_with_a_different_route_pct": pct(len(diff), len(df)),
            "when_different_extra_minutes_mean": round_((diff.few_min - diff.fast_min).mean()),
            "when_different_transfers_saved_mean": round_((diff.fast_tr - diff.few_tr).mean()),
            "max_transfers_fastest": int(df.fast_tr.max()), "pairs_needing_3_or_more_transfers_pct": pct((df.fast_tr >= 3).sum(), len(df))}


# --- 6. sensitivity ---------------------------------------------------------------------------

VARIANTS = {
    "baseline": {},
    "transfer 0 min": {"transfer_min": 0.0}, "transfer 3 min": {"transfer_min": 3.0},
    "transfer 8 min": {"transfer_min": 8.0}, "transfer 10 min": {"transfer_min": 10.0},
    "transfer 15 min": {"transfer_min": 15.0},
    "running speed 30 km/h": {"run_kmh": 30.0}, "running speed 50 km/h": {"run_kmh": 50.0},
    "airport express 60 km/h": {"airport_run_kmh": 60.0}, "airport express 100 km/h": {"airport_run_kmh": 100.0},
    "dwell 0.25 min": {"dwell_min": 0.25}, "dwell 1 min": {"dwell_min": 1.0},
}


def sensitivity(planner):
    names = [s.name for s in planner.network.stations]
    pairs = all_pairs(planner)
    keys = {}
    rows = []
    for label, changes in VARIANTS.items():
        p = Planner(planner.network, Params(**changes))
        routes = [p.plan(names[a], names[b]) for a, b in pairs]
        keys[label] = [route_key(r) for r in routes]
        same = sum(k == b for k, b in zip(keys[label], keys["baseline"]))
        rows.append({"variant": label, "same_route_as_baseline_pct": pct(same, len(pairs)),
                     "mean_minutes": round_(statistics.mean(r.minutes for r in routes)),
                     "mean_transfers": round_(statistics.mean(r.transfers for r in routes))})
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "sensitivity.csv", index=False)
    return df


# --- 7. fares ---------------------------------------------------------------------------------

def fares_summary(planner):
    f, names = planner.fares, [s.name for s in planner.network.stations]
    rows = []
    for a, b in all_pairs(planner):
        route = planner.plan(names[a], names[b])
        km = f.distance_km(a, b)                       # None when an end is only on the Airport Express
        rows.append({"fare": route.fare.total, "km": km, "airport": any(l.line == "Airport Express Line" for l in route.legs),
                     "ordinary_fare": None if km is None else f.slab(km, "mon_to_sat")})
    df = pd.DataFrame(rows)
    both = df[df.km.notna()]
    airport = both[both.airport]
    unchanged = {}
    for change in (0.95, 1.05, 0.9, 1.1):
        same = sum(f.slab(k * change, "mon_to_sat") == f.slab(k, "mon_to_sat") for k in both.km)
        unchanged[f"{int(round((change - 1) * 100)):+d}%"] = pct(same, len(both))
    return {"pairs": len(df), "mean_fare_rupees": round_(df.fare.mean(), 1),
            "share_of_pairs_at_each_fare_pct": {int(k): pct(v, len(df)) for k, v in df.fare.value_counts().sort_index().items()},
            "pairs_where_the_fastest_route_uses_the_airport_express_pct": pct(df.airport.sum(), len(df)),
            "of_those_with_an_ordinary_route_mean_extra_rupees": round_((airport.fare - airport.ordinary_fare).mean(), 1),
            "of_those_pairs_that_pay_more_than_the_ordinary_fare_pct": pct((airport.fare > airport.ordinary_fare).sum(), max(len(airport), 1)),
            "fare_unchanged_if_distances_are_off_by": unchanged}


# --- output -----------------------------------------------------------------------------------

def figure(comparison, sens):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    ax = axes[0]
    extra = comparison.extra_minutes
    ax.hist(extra, bins=np.arange(-0.5, extra.max() + 2, 2), color="#4169E1")
    ax.axvline(extra.mean(), color="black", ls="--", lw=1, label=f"mean {extra.mean():.1f} min")
    ax.set_xlabel("Minutes the original route takes beyond the fastest route")
    ax.set_ylabel("Pairs of stations")
    ax.set_title("Original (fewest-stops) routes timed with the weighted model")
    ax.legend()
    ax = axes[1]
    s = sens[sens.variant != "baseline"].sort_values("same_route_as_baseline_pct")
    ax.barh(s.variant, s.same_route_as_baseline_pct, color="#008000")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Station pairs whose fastest route is unchanged (%)")
    ax.set_title("Sensitivity to the travel-time assumptions")
    fig.tight_layout()
    fig.savefig(RESULTS / "results.png", dpi=150)


def main():
    RESULTS.mkdir(exist_ok=True)
    planner = Planner()
    out = {"seed": SEED, "assumptions": vars(planner.graph.params) | {"circuity": round(planner.graph.params.circuity, 4)}}
    out["data"], ids, old = audit_data(planner)
    print("data", out["data"])
    out["correctness"] = check_correctness(planner)
    print("correctness", out["correctness"])
    out["original_algorithm_on_weighted_edges"] = legacy_on_weights(planner)
    print("legacy on weights", out["original_algorithm_on_weighted_edges"])
    out["original_routes_vs_fastest"], comparison = evaluate_original(planner, ids, old)
    print("original vs fastest", out["original_routes_vs_fastest"])
    out["speed"] = benchmark(planner)
    print("speed", out["speed"])
    out["fastest_vs_fewest_transfers"] = mode_tradeoff(planner)
    print("modes", out["fastest_vs_fewest_transfers"])
    out["fares"] = fares_summary(planner)
    print("fares", out["fares"])
    sens = sensitivity(planner)
    print(sens.to_string(index=False))
    figure(comparison, sens)
    (RESULTS / "results.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
