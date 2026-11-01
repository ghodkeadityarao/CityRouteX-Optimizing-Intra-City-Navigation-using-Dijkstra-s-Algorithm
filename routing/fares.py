"""Delhi Metro fares (DMRC, fares in force from 25 August 2025; tables in data/).

DMRC charges by the shortest distance between the two stations, not by the path taken, so the
fare depends only on where you start and end. The Airport Express has its own station-to-station
fares and is ticketed separately, so a journey that uses it is priced as: the Airport Express
fare for each Airport Express leg, plus the ordinary fare for each stretch before, between and
after those legs.
"""
import csv
import heapq
from dataclasses import dataclass, field

from .network import DATA

AIRPORT = "Airport Express Line"
DAYS = {"mon_to_sat": "Monday to Saturday", "sunday_and_holidays": "Sunday and national holidays"}


@dataclass
class Fare:
    total: int
    parts: list = field(default_factory=list)       # [{"what": ..., "rupees": ...}]


class Fares:
    def __init__(self, network, circuity, folder=DATA):
        self.network, self.circuity = network, circuity
        with open(folder / "fares.csv", newline="") as f:
            self.slabs = [(float(r["up_to_km"]) if r["up_to_km"] else float("inf"),
                           {d: int(r[d]) for d in DAYS}) for r in csv.DictReader(f)]
        with open(folder / "airport_express_fares.csv", newline="") as f:
            rows = list(csv.reader(f))
        names = [network.find(n) for n in rows[0][1:]]
        self.airport = {(names[i], names[j]): int(v) for i, r in enumerate(rows[1:]) for j, v in enumerate(r[1:])}
        self.adj = {s.id: [] for s in network.stations}              # ordinary lines only, weight km
        for line, a, b, straight in network.segments:
            if line != AIRPORT:
                self.adj[a].append((b, straight * circuity))
                self.adj[b].append((a, straight * circuity))

    def distance_km(self, a, b):
        """Shortest riding distance between two stations on the ordinary lines, or None."""
        best, heap = {a: 0.0}, [(0.0, a)]
        while heap:
            d, u = heapq.heappop(heap)
            if u == b:
                return d
            if d > best[u]:
                continue
            for v, km in self.adj[u]:
                if d + km < best.get(v, float("inf")):
                    best[v] = d + km
                    heapq.heappush(heap, (d + km, v))
        return None

    def slab(self, km, day):
        return next(rupees[day] for limit, rupees in self.slabs if km <= limit)

    def for_route(self, route, day="mon_to_sat"):
        """Fare for a planned route (a Route from routing.planner), or None if it cannot be priced."""
        net = self.network
        stretches, group = [], []                              # [(kind, from, to)]
        for leg in route.legs + [None]:
            if leg is not None and leg.line != AIRPORT:
                group.append(leg)
                continue
            if group:
                stretches.append(("ordinary", group[0].stations[0], group[-1].stations[-1]))
                group = []
            if leg is not None:
                stretches.append(("airport", leg.stations[0], leg.stations[-1]))
        parts = []
        for kind, a, b in stretches:
            ia, ib = net.find(a), net.find(b)
            if kind == "airport":
                parts.append({"what": f"Airport Express, {a} to {b}", "rupees": self.airport[(ia, ib)]})
            else:
                km = self.distance_km(ia, ib)
                if km is None:
                    return None
                parts.append({"what": f"{a} to {b} ({km:.0f} km)", "rupees": self.slab(km, day)})
        return Fare(sum(p["rupees"] for p in parts), parts)
