import itertools
import random

import networkx as nx
import pytest

from routing.network import Network, Params, Station
from routing.planner import Planner, RouteError


def tiny_network():
    """0 -P- 1 -Q- 2 is the short way (one transfer at 1); line R goes 0 -> 3 -> 2 without
    changing, but 3 is far to the north, so R is much longer."""
    pts = {0: (0.0, 0.0), 1: (0.0, 0.01), 2: (0.0, 0.02), 3: (0.2, 0.01)}
    lines = {0: ("P", "R"), 1: ("P", "Q"), 2: ("Q", "R"), 3: ("R",)}
    stations = [Station(i, f"S{i}", *pts[i], lines[i], ()) for i in pts]
    net = Network(stations, [], {"P": "#111111", "Q": "#222222", "R": "#333333"})
    for line, a, b in [("P", 0, 1), ("Q", 1, 2), ("R", 0, 3), ("R", 3, 2)]:
        net.segments.append((line, a, b, net.straight_km(a, b)))
    return net


@pytest.fixture(scope="module")
def planner():
    return Planner()


@pytest.fixture(scope="module")
def reference(planner):
    """The same weights in networkx, as an independent check on every shortest-path answer."""
    g = planner.graph
    G = nx.DiGraph()
    for u, edges in enumerate(g.adj):
        for v, w, _, _ in edges:
            G.add_edge(u, v, weight=w)
    return G


def best_cost(planner, reference, a, b):
    g = planner.graph
    return min(nx.shortest_path_length(reference, s, t, weight="weight")
               for s in g.at_station[a] for t in g.at_station[b])


def test_network_is_the_expected_size_and_fully_connected(planner):
    net = planner.network
    assert len(net.stations) == 244
    G = nx.Graph()
    G.add_nodes_from(range(len(net.stations)))
    G.add_edges_from((a, b) for _, a, b, _ in net.segments)
    assert nx.is_connected(G)
    assert all(s.lines for s in net.stations)


def test_names_are_matched_loosely_and_old_names_still_work(planner):
    net = planner.network
    assert net.find("rajiv chowk") == net.find("Rajiv  Chowk") == net.find("RAJIV-CHOWK")
    assert net.find("HUDA City Centre") == net.find("Millennium City Centre Gurugram") is not None
    assert net.find("Nowhere") is None


def test_fastest_matches_networkx_on_random_pairs(planner, reference):
    rng = random.Random(0)
    n = len(planner.network.stations)
    for _ in range(300):
        a, b = rng.sample(range(n), 2)
        assert planner.search(a, b)[0] == pytest.approx(best_cost(planner, reference, a, b))


def test_astar_gives_the_same_cost_as_dijkstra_and_settles_fewer_nodes(planner):
    astar = Planner(planner.network, algorithm="astar")
    rng = random.Random(1)
    n = len(planner.network.stations)
    fewer = 0
    for _ in range(300):
        a, b = rng.sample(range(n), 2)
        d, h = planner.search(a, b), astar.search(a, b)
        assert h[0] == pytest.approx(d[0])
        fewer += h[2] <= d[2]
    assert fewer >= 270


def test_route_legs_add_up_to_the_search_cost(planner):
    r = planner.plan("Rithala", "Hauz Khas")
    a, b = planner.station_id("Rithala"), planner.station_id("Hauz Khas")
    assert r.minutes == pytest.approx(planner.search(a, b)[0])
    assert r.legs[0].stations[0] == "Rithala" and r.legs[-1].stations[-1] == "Hauz Khas"
    assert r.stops == sum(len(l.stations) - 1 for l in r.legs)
    assert [l.stations[-1] for l in r.legs[:-1]] == [l.stations[0] for l in r.legs[1:]]


def test_transfer_cost_decides_between_a_short_route_and_a_direct_one():
    net = tiny_network()
    cheap = Planner(net, Params(transfer_min=5)).plan("S0", "S2", "fastest")
    assert [l.line for l in cheap.legs] == ["P", "Q"] and cheap.transfers == 1
    costly = Planner(net, Params(transfer_min=500)).plan("S0", "S2", "fastest")
    assert [l.line for l in costly.legs] == ["R"] and costly.transfers == 0
    fewest = Planner(net, Params(transfer_min=5)).plan("S0", "S2", "fewest_transfers")
    assert [l.line for l in fewest.legs] == ["R"] and fewest.minutes > cheap.minutes


def test_fewest_transfers_never_has_more_transfers_than_fastest(planner):
    rng = random.Random(2)
    names = [s.name for s in planner.network.stations]
    for _ in range(150):
        a, b = rng.sample(names, 2)
        fast, few = planner.plan(a, b, "fastest"), planner.plan(a, b, "fewest_transfers")
        assert few.transfers <= fast.transfers
        assert few.minutes >= fast.minutes - 1e-9


def test_a_line_change_is_only_charged_between_different_lines(planner):
    r = planner.plan("Rajiv Chowk", "Hauz Khas")
    assert r.transfers == 0 and r.legs[0].line == "Yellow Line"


def test_bad_requests_raise_clear_errors(planner):
    with pytest.raises(RouteError, match="Nowhere"):
        planner.plan("Nowhere", "Rajiv Chowk")
    with pytest.raises(RouteError, match="different"):
        planner.plan("Rajiv Chowk", "rajiv chowk")
    with pytest.raises(RouteError, match="mode"):
        planner.plan("Rajiv Chowk", "Hauz Khas", "scenic")


def test_every_ordered_pair_in_a_sample_of_stations_is_reachable(planner):
    names = [s.name for s in planner.network.stations][::12]
    for a, b in itertools.permutations(names, 2):
        assert planner.plan(a, b).minutes > 0


def test_a_walkway_between_two_stations_counts_as_a_transfer_with_walking_time(planner):
    r = planner.plan("Delhi Aerocity", "Naraina Vihar")
    assert [l.line for l in r.legs] == ["Airport Express Line", "Pink Line"]
    assert r.legs[0].stations[-1] == "Dhaula Kuan" and r.legs[1].stations[0] == "Durgabai Deshmukh South Campus"
    assert r.transfers == 1 and r.transfer_minutes == pytest.approx(5 + 1.2 / 4.5 * 60)


def test_two_stations_joined_only_by_a_walkway_say_so(planner):
    with pytest.raises(RouteError, match="walkway"):
        planner.plan("Dhaula Kuan", "Durgabai Deshmukh South Campus")


def test_fare_slabs_follow_the_dmrc_table_at_every_boundary(planner):
    f = planner.fares
    assert [f.slab(km, "mon_to_sat") for km in (0.5, 2, 2.01, 5, 5.01, 12, 12.01, 21, 21.01, 32, 32.01, 80)] == \
        [11, 11, 21, 21, 32, 32, 43, 43, 54, 54, 64, 64]
    assert [f.slab(km, "sunday_and_holidays") for km in (2, 5, 12, 21, 32, 40)] == [11, 11, 21, 32, 43, 54]


def test_airport_express_table_is_symmetric_and_has_every_pair(planner):
    t = planner.fares.airport
    assert len(t) == 49 and all(t[(a, b)] == t[(b, a)] for a, b in t)
    assert t[(planner.station_id("New Delhi"), planner.station_id("IGI Airport"))] == 64


def test_fare_depends_on_the_stations_not_on_the_route_mode(planner):
    for a, b in [("Rithala", "Hauz Khas"), ("Vaishali", "Saket"), ("Noida City Centre", "Kashmere Gate")]:
        assert planner.plan(a, b, "fastest").fare.total == planner.plan(a, b, "fewest_transfers").fare.total
        assert planner.plan(a, b).fare.total == planner.plan(b, a).fare.total


def test_long_journey_costs_the_top_slab_and_sunday_is_one_slab_cheaper(planner):
    assert planner.plan("Rithala", "Huda City Centre").fare.total == 64
    assert planner.plan("Rithala", "Huda City Centre", day="sunday_and_holidays").fare.total == 54


def test_a_journey_using_the_airport_express_is_priced_as_separate_tickets(planner):
    r = planner.plan("Delhi Aerocity", "Naraina Vihar")
    assert [p["rupees"] for p in r.fare.parts] == [21, 32] and r.fare.total == 53
    direct = planner.plan("New Delhi", "IGI Airport")
    assert direct.fare.total == 64 and len(direct.fare.parts) == 1


def test_an_unknown_day_type_is_rejected(planner):
    with pytest.raises(RouteError, match="day"):
        planner.plan("Rithala", "Hauz Khas", day="holiday-ish")
