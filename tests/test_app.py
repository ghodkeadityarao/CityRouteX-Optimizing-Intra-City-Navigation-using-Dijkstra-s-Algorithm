import pytest

from app import create_app


@pytest.fixture(scope="module")
def client():
    return create_app().test_client()


def test_home_page_lists_the_stations(client):
    html = client.get("/").get_data(as_text=True)
    assert "244 stations" in html and 'value="Rajiv Chowk"' in html


def test_a_route_page_shows_lines_stops_and_transfers(client):
    html = client.get("/?from=Rithala&to=Hauz+Khas").get_data(as_text=True)
    assert "Red Line" in html and "Yellow Line" in html and "Change at" in html
    assert 'value="Rithala"' in html


def test_the_api_returns_the_route_as_json(client):
    r = client.get("/api/route?from=Vaishali&to=Hauz Khas&mode=fewest_transfers")
    data = r.get_json()
    assert r.status_code == 200 and data["origin"] == "Vaishali" and data["destination"] == "Hauz Khas"
    assert data["transfers"] == len(data["legs"]) - 1 and data["minutes"] > 0


@pytest.mark.parametrize("query", ["from=Nowhere&to=Rajiv+Chowk", "from=Rajiv+Chowk&to=Rajiv+Chowk",
                                   "from=Rajiv+Chowk&to=Hauz+Khas&mode=scenic", "from=Rajiv+Chowk"])
def test_bad_requests_give_a_400_with_a_message(client, query):
    r = client.get("/api/route?" + query)
    assert r.status_code == 400 and r.get_json()["error"]


def test_the_page_shows_errors_instead_of_crashing_and_escapes_what_was_typed(client):
    r = client.get("/?from=<script>alert(1)</script>&to=Rajiv+Chowk")
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "I don&#39;t know a station" in html and "<script>alert(1)" not in html


def test_requests_do_not_share_state(client):
    first = client.get("/api/route?from=Rithala&to=Hauz+Khas").get_json()
    client.get("/api/route?from=Vaishali&to=Saket")
    assert client.get("/api/route?from=Rithala&to=Hauz+Khas").get_json() == first


def test_a_walk_between_stations_is_shown_as_a_walk(client):
    html = client.get("/?from=Delhi+Aerocity&to=Naraina+Vihar").get_data(as_text=True)
    assert "Walk from Dhaula Kuan to Durgabai Deshmukh South Campus" in html


def test_the_page_and_api_show_the_fare_and_take_the_day_type(client):
    html = client.get("/?from=Rithala&to=Huda+City+Centre").get_data(as_text=True)
    assert "₹64" in html
    sunday = client.get("/api/route?from=Rithala&to=Huda+City+Centre&day=sunday_and_holidays").get_json()
    assert sunday["fare_rupees"] == 54
    assert client.get("/api/route?from=Rithala&to=Hauz+Khas&day=never").status_code == 400
