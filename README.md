# CityRouteX

A Delhi Metro route planner. Pick two stations and get the fastest route, or the route with the fewest transfers, broken into legs by line with the stops, the minutes and the transfers, drawn on a map.

## What it has

- **A real network:** 244 stations on 9 lines (Red, Yellow, Blue, Green, Violet, Pink, Magenta, Grey, Airport Express), 262 connections, built from OpenStreetMap route data. Interchange stops of different lines are merged into one station, and the 1.2 km walkway between Dhaula Kuan and Durgabai Deshmukh South Campus is modelled as a transfer with walking time.
- **Two route modes:** fastest, and fewest transfers (transfers first, then time).
- **Web app and JSON API:** a Flask page with a map and a step-by-step route (`/?from=Rithala&to=Hauz+Khas`), and `/api/route`, `/api/stations` and `/api/modes` for other programs. Old station names such as "HUDA City Centre" and loose spellings are accepted.
- **Safe by construction:** no state shared between requests; unknown stations, identical stations, unknown modes and walkway-only pairs return a clear message instead of an error.

## How it works

- **Graph.** Each node is one line at one station. Riding to the next station costs travel time; changing line costs the transfer time. Because transfers are edges, the search can count and price them, which a stop-count graph cannot.
- **Search.** Dijkstra with a binary heap, started from every platform of the origin station and stopped at the first platform of the destination. A* with a straight-line estimate is available and returns the same costs.
- **Fewest transfers.** The same search with each transfer priced above any possible ride, so transfers are minimised first.
- **Travel-time model.** Distance between consecutive stations is the straight line from OpenStreetMap coordinates, scaled by 1.087 (the published 374.466 km network length over the 344.5 km of straight-line segments). Assumptions, none of them measured: 40 km/h running speed (80 km/h on the Airport Express), 0.5 min stopped at each station, 5 min per line change plus 4.5 km/h walking on the one walkway.

## Results

Run on a laptop; the full output is in `evaluation/results/`.

| Measure | Result |
|---|---|
| Correctness | 0 disagreements with networkx for both Dijkstra and A* on all 59,292 ordered station pairs |
| Speed | 0.052 ms per query, against 2.037 ms for the original O(V²) Dijkstra on the same graph (2,000 random queries): 39× faster |
| A* | Settles 25% fewer nodes than Dijkstra (103.8 against 138.8) but takes 0.077 ms against 0.052 ms at this size, so Dijkstra is the default |
| Original data | All 229 original stations matched (25 had been renamed, kept as aliases); 240 of its 242 connections are still correct, 2 skip a station that now exists (Nawada, Punjabi Bagh West), 3 matrix entries were one-directional; the network now has 15 more stations and 22 more connections |
| Original routes | Timed with the weighted model over 26,105 station pairs, the original fewest-stops route was not the fastest for 43.2% of pairs: 4.7 minutes slower on average over all pairs, 10.9 minutes when slower, up to 49.8 minutes. 17.6% of its routes passed through a skipped station |
| Original path code | Its route reconstruction returned a non-cheapest path for 4.6% of queries once edges had different weights |
| Fastest vs fewest transfers | The two modes choose different routes for 23.6% of the 29,645 train-connected pairs. Fewest transfers saves 1.15 transfers on average on those pairs and costs 11.6 minutes more. Fastest routes average 1.31 transfers; 7.6% need three or more |
| Sensitivity | The fastest route is unchanged for at least 94.6% of pairs when running speed (30 or 50 km/h), Airport Express speed (60 or 100 km/h) or stop time (0.25 or 1 min) changes, and for 90.8% to 95.1% with a 3, 8 or 10 minute transfer; 86.5% at 15 minutes and 79.3% with free transfers |
| Network check | 244 stations against 243 in Wikipedia's count with interchanges counted once |

## Limits

- Times are model estimates, not timetables. DMRC's own planner could not be queried, so travel times are not validated against it; the one published figure checked is New Delhi to the airport, estimated at 17 minutes against 18 minutes announced when the line opened in 2011.
- No fares, train frequencies, real-time delays or crowding.
- Branches of a line are treated as the same line, so there is no transfer cost at Yamuna Bank or Ashok Park Main.
- Gurugram's Rapid Metro and Noida's Aqua Line are not included. The data is a snapshot dated 1 November 2026.
- Segment lengths use straight-line distance with one network-wide factor, so individual segments are approximate.

## Repository

| Path | Contents |
|---|---|
| `app.py`, `templates/`, `static/` | Flask app, page and styles |
| `routing/network.py` | Network loading, travel-time model, platform graph |
| `routing/search.py` | Heap Dijkstra and A* |
| `routing/planner.py` | Station lookup, route modes, legs and totals |
| `data/` | Stations, segments, lines, aliases, walkway links and the OpenStreetMap snapshot (© OpenStreetMap contributors, ODbL) |
| `scripts/build_network.py` | Builds the data files from the snapshot, merging interchange stops |
| `evaluation/` | The evaluation, its results and figure, and the original code and adjacency matrix it is compared with |
| `tests/` | 22 tests: correctness against networkx, transfer pricing, walkways, bad requests, the web pages and API |
