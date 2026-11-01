"""CityRouteX: fastest and fewest-transfer routes on the Delhi Metro.

    flask --app app run
"""
from flask import Flask, jsonify, render_template, request

from routing.fares import DAYS
from routing.planner import MODES, Planner, RouteError

MODE_LABELS = {"fastest": "Fastest", "fewest_transfers": "Fewest transfers"}


def create_app(planner=None):
    app = Flask(__name__)
    planner = planner or Planner()
    network = planner.network
    station_names = sorted(s.name for s in network.stations)

    def solve(args):
        origin, destination = (args.get("from") or "").strip(), (args.get("to") or "").strip()
        mode, day = args.get("mode") or "fastest", args.get("day") or "mon_to_sat"
        if not origin or not destination:
            return None
        return planner.plan(origin, destination, mode, day)

    @app.get("/")
    def index():
        route, error = None, None
        try:
            route = solve(request.args)
        except RouteError as e:
            error = str(e)
        return render_template("index.html", stations=station_names, modes=MODE_LABELS, days=DAYS, route=route,
                               error=error, form=request.args, lines=network.colours,
                               drawing=network_drawing(network))

    @app.get("/api/route")
    def api_route():
        try:
            route = solve(request.args)
        except RouteError as e:
            return jsonify(error=str(e)), 400
        if route is None:
            return jsonify(error="Give both 'from' and 'to'."), 400
        return jsonify(route.as_dict())

    @app.get("/api/stations")
    def api_stations():
        return jsonify([{"name": s.name, "lat": s.lat, "lon": s.lon, "lines": list(s.lines)}
                        for s in network.stations])

    @app.get("/api/modes")
    def api_modes():
        return jsonify(list(MODES))

    return app


def network_drawing(network):
    """Every line segment as coordinates, for the faint background map."""
    return [{"colour": network.colours.get(line, "#888888"),
             "coords": [[network.stations[a].lat, network.stations[a].lon],
                        [network.stations[b].lat, network.stations[b].lon]]}
            for line, a, b, _ in network.segments]


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
