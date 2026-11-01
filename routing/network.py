"""The metro network and the weighted graph that routes are searched on.

A node of the graph is one line at one station (a "platform"). Riding to the next station on the
same line costs travel time; moving between two lines at an interchange costs the transfer time.
That is what lets the search count and price transfers instead of only counting stops.
"""
import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .geo import haversine_km

DATA = Path(__file__).resolve().parent.parent / "data"

# The published length of the Delhi Metro's own network (374.466 km) over the summed straight-line
# distance between consecutive stations in data/segments.csv (344.5 km): track is longer than the
# straight line between stops. Used to turn straight-line distance into riding distance.
OFFICIAL_NETWORK_KM = 374.466
STRAIGHT_NETWORK_KM = 344.5


@dataclass(frozen=True)
class Params:
    """Assumptions of the travel-time model. None of them is measured; see the README."""
    run_kmh: float = 40.0                 # average running speed between stops
    airport_run_kmh: float = 80.0         # the Airport Express runs faster
    dwell_min: float = 0.5                # time standing at each station
    transfer_min: float = 5.0             # walking between platforms plus waiting for the next train
    circuity: float = OFFICIAL_NETWORK_KM / STRAIGHT_NETWORK_KM
    walk_kmh: float = 4.5                 # walking pace on a walkway between two stations

    def speed(self, line):
        return self.airport_run_kmh if line == "Airport Express Line" else self.run_kmh


@dataclass(frozen=True)
class Station:
    id: int
    name: str
    lat: float
    lon: float
    lines: tuple
    aliases: tuple


def key(name):
    """Lower-case letters and digits only, so 'R.K. Puram' and 'rk puram' compare equal."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


class Network:
    def __init__(self, stations, segments, colours, links=()):
        self.stations = stations                       # list, index == id
        self.segments = segments                       # (line, from_id, to_id, straight_km)
        self.colours = colours                         # line -> hex colour
        self.links = list(links)                       # (from_id, to_id, walk_km): walkways between stations
        self._by_key = {}
        for s in stations:
            for n in (s.name, *s.aliases):
                self._by_key.setdefault(key(n), s.id)

    @classmethod
    def load(cls, folder=DATA):
        with open(Path(folder) / "stations.csv", newline="") as f:
            stations = [Station(int(r["id"]), r["name"], float(r["lat"]), float(r["lon"]),
                                tuple(r["lines"].split("|")), tuple(a for a in r["aliases"].split("|") if a))
                        for r in csv.DictReader(f)]
        with open(Path(folder) / "segments.csv", newline="") as f:
            segments = [(r["line"], int(r["from_id"]), int(r["to_id"]), float(r["straight_km"]))
                        for r in csv.DictReader(f)]
        with open(Path(folder) / "lines.csv", newline="") as f:
            colours = {r["line"]: r["colour"] for r in csv.DictReader(f)}
        net = cls(stations, segments, colours)
        with open(Path(folder) / "aliases.csv", newline="") as f:      # older and alternative names
            for r in csv.DictReader(f):
                net._by_key.setdefault(key(r["alias"]), net._by_key[key(r["station"])])
        with open(Path(folder) / "links.csv", newline="") as f:        # interchanges between separate stations
            net.links = [(net.find(r["from"]), net.find(r["to"]), float(r["walk_km"])) for r in csv.DictReader(f)]
        return net

    def find(self, name):
        """The station id for a name (any spelling of letters and spaces), or None."""
        return self._by_key.get(key(name or ""))

    def straight_km(self, a, b):
        sa, sb = self.stations[a], self.stations[b]
        return haversine_km(sa.lat, sa.lon, sb.lat, sb.lon)


class Graph:
    """Platform graph. adj[u] is a list of (v, minutes, line_or_None, km); line None marks a transfer
    (a change of line at one station, or a walk to a linked station)."""

    def __init__(self, network, params=Params()):
        self.network, self.params = network, params
        self.node_of = {}                              # (station id, line) -> node number
        self.platform = []                             # node number -> (station id, line)
        self.at_station = [[] for _ in network.stations]
        for line, a, b, _ in network.segments:
            for s in (a, b):
                if (s, line) not in self.node_of:
                    self.node_of[(s, line)] = len(self.platform)
                    self.platform.append((s, line))
                    self.at_station[s].append(self.node_of[(s, line)])
        self.adj = [[] for _ in self.platform]
        for line, a, b, straight in network.segments:
            km = straight * params.circuity
            minutes = km / params.speed(line) * 60 + params.dwell_min
            u, v = self.node_of[(a, line)], self.node_of[(b, line)]
            self.adj[u].append((v, minutes, line, km))
            self.adj[v].append((u, minutes, line, km))
        for nodes in self.at_station:
            for u in nodes:
                for v in nodes:
                    if u != v:
                        self.adj[u].append((v, params.transfer_min, None, 0.0))
        for a, b, walk_km in network.links:
            walk = params.transfer_min + walk_km / params.walk_kmh * 60
            for u in self.at_station[a]:
                for v in self.at_station[b]:
                    self.adj[u].append((v, walk, None, 0.0))
                    self.adj[v].append((u, walk, None, 0.0))
        self.max_kmh = max(params.run_kmh, params.airport_run_kmh)

    def __len__(self):
        return len(self.platform)
