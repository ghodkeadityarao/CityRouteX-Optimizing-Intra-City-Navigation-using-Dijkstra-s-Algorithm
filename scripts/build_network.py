"""Build data/stations.csv, data/segments.csv and data/lines.csv from an OpenStreetMap snapshot.

    python scripts/build_network.py            # rebuild the CSVs from data/osm_delhi_metro.json
    python scripts/build_network.py --refresh  # download a fresh snapshot first

The snapshot holds every Delhi Metro route relation (the stops of each line in running order) and
the coordinates of those stops. Stops of different lines that are the same interchange station are
merged into one station: two stops merge when they carry the same name and lie within 1 km, or when
they are on different lines and lie within 250 m of each other. Stops on the same line never merge
unless they share a name.

Data (c) OpenStreetMap contributors, ODbL.
"""
import argparse
import collections
import csv
import itertools
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from routing.geo import haversine_km  # noqa: E402

DATA = ROOT / "data"
SNAPSHOT = DATA / "osm_delhi_metro.json"
OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = """[out:json][timeout:180];
(
 relation["type"="route"]["route"~"subway|light_rail|train"]["operator:wikidata"="Q1029339"];
 relation["type"="route"]["route"~"subway|light_rail|train"]["network"~"Delhi Metro",i];
)->.r;
.r out body;
node(r.r)->.n;
.n out;"""
SAME_NAME_KM = 1.0
INTERCHANGE_KM = 0.25
LINE_SUFFIX = re.compile(r"\s*\((?:[A-Za-z ]+ Line|Airport Express)\)")


def refresh():
    req = urllib.request.Request(OVERPASS, urllib.parse.urlencode({"data": QUERY}).encode(),
                                 {"User-Agent": "CityRouteX/1.0 (route planner project)"})
    raw = json.load(urllib.request.urlopen(req, timeout=240))
    nodes = {e["id"]: e for e in raw["elements"] if e["type"] == "node"}
    relations = []
    for e in raw["elements"]:
        if e["type"] != "relation":
            continue
        stops = [m["ref"] for m in e["members"] if m["type"] == "node" and m["ref"] in nodes]
        relations.append({"id": e["id"], "name": e["tags"]["name"], "colour": e["tags"].get("colour", ""),
                          "ref": e["tags"].get("ref", ""), "stops": stops})
    snapshot = {"source": "OpenStreetMap via Overpass API (ODbL)", "fetched": date.today().isoformat(),
                "relations": relations,
                "nodes": {str(i): [n["tags"]["name"], n["lat"], n["lon"]] for i, n in nodes.items() if "name" in n["tags"]}}
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=0))


def clean(name):
    return LINE_SUFFIX.sub("", name).strip()


def normal(name):
    return re.sub(r"[^a-z0-9]", "", clean(name).lower())


def build():
    snap = json.loads(SNAPSHOT.read_text())
    nodes = {int(i): v for i, v in snap["nodes"].items()}
    lines, stop_line = {}, {}
    for rel in snap["relations"]:
        line = re.sub(r" \(.*", "", rel["name"])
        lines.setdefault(line, rel["colour"])
        for s in rel["stops"]:
            stop_line[s] = line
    ids = [i for i in stop_line if i in nodes]

    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in itertools.combinations(ids, 2):
        (na, la, oa), (nb, _, ob) = nodes[a], nodes[b]
        same_name = normal(na) == normal(nb)
        if stop_line[a] == stop_line[b] and not same_name:
            continue
        d = haversine_km(la, oa, nodes[b][1], ob)
        if (same_name and d < SAME_NAME_KM) or (stop_line[a] != stop_line[b] and d < INTERCHANGE_KM):
            parent[find(a)] = find(b)

    groups = collections.defaultdict(list)
    for i in ids:
        groups[find(i)].append(i)
    stations = []
    for members in groups.values():
        names = collections.Counter(clean(nodes[i][0]) for i in members)
        name = sorted(names, key=lambda n: (-names[n], len(n), n))[0]
        stations.append({"name": name, "aliases": sorted(set(names) - {name}),
                         "lat": sum(nodes[i][1] for i in members) / len(members),
                         "lon": sum(nodes[i][2] for i in members) / len(members),
                         "lines": sorted({stop_line[i] for i in members}), "members": members})
    stations.sort(key=lambda s: s["name"].lower())
    station_of = {i: n for n, s in enumerate(stations) for i in s["members"]}

    segments = {}
    for rel in snap["relations"]:
        line = re.sub(r" \(.*", "", rel["name"])
        for a, b in zip(rel["stops"], rel["stops"][1:]):
            u, v = station_of[a], station_of[b]
            if u != v:
                segments[(line, *sorted((u, v)))] = None
    rows = []
    for (line, u, v) in sorted(segments):
        su, sv = stations[u], stations[v]
        rows.append([line, u, v, round(haversine_km(su["lat"], su["lon"], sv["lat"], sv["lon"]), 4)])

    with open(DATA / "stations.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "lat", "lon", "lines", "aliases"])
        for n, s in enumerate(stations):
            w.writerow([n, s["name"], round(s["lat"], 6), round(s["lon"], 6), "|".join(s["lines"]), "|".join(s["aliases"])])
    with open(DATA / "segments.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["line", "from_id", "to_id", "straight_km"])
        w.writerows(rows)
    with open(DATA / "lines.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["line", "colour"])
        w.writerows(sorted(lines.items()))
    print(f"{len(stations)} stations, {len(rows)} segments, {len(lines)} lines "
          f"(snapshot {snap['fetched']})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    if ap.parse_args().refresh:
        refresh()
    build()
