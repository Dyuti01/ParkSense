def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ParkSense AI" in data["app"]

def test_overview(client):
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_violations" in data
    assert "total_hotspots" in data
    assert "critical_zones" in data
    assert "enforcement_coverage_pct" in data
    assert "top_station" in data
    assert "peak_hour_ist" in data

def test_stations(client):
    response = client.get("/api/stations")
    assert response.status_code == 200
    data = response.json()
    # Assuming standard paginated or dictionary wrapped response for endpoints:
    stations = data.get("stations", data)
    assert isinstance(stations, list)
    if len(stations) > 0:
        station = stations[0]
        assert "police_station" in station
        assert "total_violations" in station

def test_hotspots(client):
    response = client.get("/api/hotspots")
    assert response.status_code == 200
    data = response.json()
    hotspots = data.get("hotspots", data)
    assert isinstance(hotspots, list)
    if len(hotspots) > 0:
        hotspot = hotspots[0]
        assert "centroid_lat" in hotspot
        assert "centroid_lon" in hotspot
        assert "cis_tier" in hotspot

def test_enforcement_priorities(client):
    response = client.get("/api/enforcement/priorities")
    assert response.status_code == 200
    data = response.json()
    priorities = data.get("priorities", data)
    assert isinstance(priorities, list)
    if len(priorities) > 0:
        zone = priorities[0]
        assert "priority_score" in zone
