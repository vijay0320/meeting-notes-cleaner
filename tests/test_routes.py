"""
Integration tests for Flask API routes.
Uses an in-memory SQLite DB so real data is not affected.
"""
import sys
import os
import pytest
import sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Patch DB to use in-memory before importing app
import app_v2
app_v2.DB = ":memory:"

from app_v2 import app, init_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            # Reinitialize with in-memory DB
            conn = sqlite3.connect(":memory:")
            app_v2.DB = ":memory:"
        yield client

class TestProcessRoute:
    def test_basic_processing(self, client):
        res = client.post("/process", json={"notes": "troy blocked on API, needs it asap"})
        assert res.status_code == 200
        data = res.get_json()
        assert "points" in data
        assert len(data["points"]) > 0

    def test_high_priority_detected(self, client):
        res = client.post("/process", json={"notes": "critical blocker in production"})
        data = res.get_json()
        assert data["points"][0]["priority"] == "high"

    def test_low_priority_detected(self, client):
        res = client.post("/process", json={"notes": "john finished the documentation"})
        data = res.get_json()
        assert data["points"][0]["priority"] == "low"

    def test_empty_notes(self, client):
        res = client.post("/process", json={"notes": ""})
        data = res.get_json()
        assert "error" in data

    def test_owner_detected(self, client):
        res = client.post("/process", json={"notes": "sara - design review thursday"})
        data = res.get_json()
        assert data["points"][0]["owner"] == "Sara"

    def test_multiple_items(self, client):
        notes = "priya blocked asap\njohn finished module\nsara needs sign off"
        res = client.post("/process", json={"notes": notes})
        data = res.get_json()
        assert len(data["points"]) == 3

    def test_sorted_by_priority(self, client):
        notes = "john finished docs\ndeployment broke critical blocker\nsara needs review"
        res = client.post("/process", json={"notes": notes})
        data = res.get_json()
        priorities = [p["priority"] for p in data["points"]]
        order = {"high": 0, "medium": 1, "low": 2}
        assert priorities == sorted(priorities, key=lambda x: order[x])

class TestIndexRoute:
    def test_homepage_loads(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"Meeting Notes Cleaner" in res.data
