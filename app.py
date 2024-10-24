from flask import Flask, render_template, jsonify, Response
import json
from utils.gpu_monitor import GPUMonitor
from utils.ollama_client import OllamaClient
import time

app = Flask(__name__)
gpu_monitor = GPUMonitor()
ollama_client = OllamaClient()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models')
def get_models():
    try:
        result = ollama_client.list_models()
        if "error" in result:
            return jsonify({"models": [], "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        return jsonify({"models": [], "error": str(e)})

@app.route('/api/models/running')
def get_running_models():
    try:
        result = ollama_client.list_running_models()
        if "error" in result:
            return jsonify({"models": [], "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        return jsonify({"models": [], "error": str(e)})

@app.route('/api/models/stop/<model_name>', methods=['POST'])
def stop_model(model_name):
    try:
        result = ollama_client.stop_model(model_name)
        if "error" in result:
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/pull/<model_name>', methods=['POST'])
def pull_model(model_name):
    try:
        result = ollama_client.pull_model(model_name)
        if "error" in result:
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/delete/<model_name>', methods=['DELETE'])
def delete_model(model_name):
    try:
        result = ollama_client.delete_model(model_name)
        if "error" in result:
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/gpu/stats')
def gpu_stats_stream():
    def generate():
        while True:
            stats = gpu_monitor.get_stats()
            data = json.dumps(stats)
            yield f"data: {data}\n\n"
            time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')
