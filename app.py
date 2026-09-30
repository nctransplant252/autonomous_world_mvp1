import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from simulator import AutonomousWorld, load_scenario

load_dotenv()

app = Flask(__name__)
world = AutonomousWorld(load_scenario("harry_test"))

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/state")
def state():
    return jsonify(world.snapshot())

@app.post("/api/reset")
def reset():
    global world
    scenario = request.json.get("scenario", "harry_test") if request.is_json else "harry_test"
    world = AutonomousWorld(load_scenario(scenario))
    return jsonify(world.snapshot())

@app.post("/api/step")
def step():
    try:
        event = world.step()
        return jsonify({"event": event, "state": world.snapshot()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

@app.post("/api/run")
def run():
    try:
        count = int(request.json.get("steps", 10))
        count = max(1, min(count, 100))
        events = world.run(count)
        return jsonify({"events": events, "state": world.snapshot()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

@app.post("/api/save")
def save():
    path = Path("simulation_result.json")
    world.save(path)
    return jsonify({"saved": str(path)})

if __name__ == "__main__":
    print("Autonomous World MVP")
    print("Open http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
