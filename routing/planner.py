"""Turn a search result into a route a person can follow: legs by line, stops, minutes, transfers."""
from dataclasses import dataclass, field

from .network import Graph, Network
from .search import astar, dijkstra

MODES = ("fastest", "fewest_transfers")
FEWEST_TRANSFERS_COST = 1000.0       # a line change outweighs any possible ride, so transfers are minimised first


class RouteError(ValueError):
    """The request cannot be answered (unknown station, same station, no connection)."""


@dataclass
class Leg:
    line: str
    colour: str
    stations: list                      # station names from boarding to alighting
    coords: list                        # [lat, lon] for each of those stations
    minutes: float
    km: float

    @property
    def stops(self):
        return len(self.stations) - 1


@dataclass
class Route:
    origin: str
    destination: str
    mode: str
    legs: list = field(default_factory=list)
    settled: int = 0                    # nodes the search finished (work done)
    transfer_minutes: float = 0.0       # waiting and walking at line changes

    @property
    def minutes(self):
        return self.ride_minutes + self.transfer_minutes

    @property
    def ride_minutes(self):
        return sum(leg.minutes for leg in self.legs)

    @property
    def km(self):
        return sum(leg.km for leg in self.legs)

    @property
    def stops(self):
        return sum(leg.stops for leg in self.legs)

    @property
    def transfers(self):
        return len(self.legs) - 1

    def station_path(self):
        names = []
        for leg in self.legs:
            names.extend(leg.stations if not names else leg.stations[1:])
        return names

    def as_dict(self):
        return {"origin": self.origin, "destination": self.destination, "mode": self.mode,
                "minutes": round(self.minutes), "km": round(self.km, 1), "stops": self.stops,
                "transfers": self.transfers, "transfer_minutes": round(self.transfer_minutes),
                "legs": [{"line": l.line, "colour": l.colour, "stations": l.stations, "coords": l.coords,
                          "minutes": round(l.minutes), "stops": l.stops, "km": round(l.km, 1)} for l in self.legs]}


class Planner:
    def __init__(self, network=None, params=None, algorithm="dijkstra"):
        self.network = network or Network.load()
        self.graph = Graph(self.network, params) if params else Graph(self.network)
        self.algorithm = algorithm

    def station_id(self, name):
        sid = self.network.find(name)
        if sid is None:
            raise RouteError(f"I don't know a station called '{name}'.")
        return sid

    def search(self, a, b, mode="fastest"):
        """Raw search between two station ids: (cost, node path, settled nodes) or None."""
        if mode not in MODES:
            raise RouteError(f"Unknown mode '{mode}'. Choose one of: {', '.join(MODES)}.")
        g = self.graph
        cost = FEWEST_TRANSFERS_COST if mode == "fewest_transfers" else None
        if self.algorithm == "astar":
            return astar(g, g.at_station[a], g.at_station[b], b, cost)
        return dijkstra(g, g.at_station[a], g.at_station[b], cost)

    def plan(self, origin, destination, mode="fastest"):
        a, b = self.station_id(origin), self.station_id(destination)
        if a == b:
            raise RouteError("Pick two different stations.")
        found = self.search(a, b, mode)
        if found is None:
            raise RouteError("No connection between those stations.")
        _, path, settled = found
        route = self._route(path, mode, settled)
        if not route.legs:
            raise RouteError(f"{route.origin} and {route.destination} are joined by a walkway, not a train "
                             f"(about {route.transfer_minutes:.0f} minutes on foot).")
        return route

    def _route(self, path, mode, settled):
        g, net = self.graph, self.network
        route = Route(net.stations[g.platform[path[0]][0]].name, net.stations[g.platform[path[-1]][0]].name,
                      mode, settled=settled)
        leg = None
        for u, v in zip(path, path[1:]):
            _, minutes, line, km = next(e for e in g.adj[u] if e[0] == v)
            if line is None:
                leg = None
                route.transfer_minutes += minutes
                continue
            if leg is None:
                s = net.stations[g.platform[u][0]]
                leg = Leg(line, net.colours.get(line, "#888888"), [s.name], [[s.lat, s.lon]], 0.0, 0.0)
                route.legs.append(leg)
            t = net.stations[g.platform[v][0]]
            leg.stations.append(t.name)
            leg.coords.append([t.lat, t.lon])
            leg.minutes += minutes
            leg.km += km
        return route
