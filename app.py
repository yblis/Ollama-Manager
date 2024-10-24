from flask import Flask, render_template, jsonify, Response, request
import json
from utils.gpu_monitor import GPUMonitor
from utils.ollama_client import OllamaClient
from utils.benchmark import ModelBenchmark
import time

app = Flask(__name__)
gpu_monitor = GPUMonitor()
ollama_client = OllamaClient()
model_benchmark = ModelBenchmark(ollama_client)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings/check', methods=['POST'])
def check_server():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"status": "error", "message": "URL du serveur manquante"}), 400
    
    status = ollama_client.set_server_url(data['url'])
    return jsonify(status)

@app.route('/api/settings/server', methods=['POST'])
def set_server():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"status": "error", "message": "URL du serveur manquante"}), 400
    
    status = ollama_client.set_server_url(data['url'])
    return jsonify(status)

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

@app.route('/api/models/benchmark/<model_name>', methods=['POST'])
def benchmark_model(model_name):
    try:
        result = model_benchmark.start_benchmark(model_name)
        if "error" in result:
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/benchmark/<model_name>/status')
def get_benchmark_status(model_name):
    try:
        result = model_benchmark.get_benchmark_status(model_name)
        if "error" in result:
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/benchmark/results')
def get_benchmark_results():
    try:
        result = model_benchmark.get_all_results()
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
