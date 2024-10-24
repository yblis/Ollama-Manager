from flask import Flask, render_template, jsonify, Response, request
import json
import logging
from utils.gpu_monitor import GPUMonitor
from utils.ollama_client import OllamaClient
from utils.benchmark import ModelBenchmark
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
gpu_monitor = GPUMonitor()
ollama_client = OllamaClient()
model_benchmark = ModelBenchmark(ollama_client)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings/check', methods=['POST'])
def check_server():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                "status": "error",
                "message": "URL du serveur manquante"
            }), 400
        
        status = ollama_client.set_server_url(data['url'])
        return jsonify(status)
    except Exception as e:
        logger.error(f"Server check failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Erreur lors de la vérification du serveur: {str(e)}"
        }), 500

@app.route('/api/settings/server', methods=['POST'])
def set_server():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                "status": "error",
                "message": "URL du serveur manquante"
            }), 400
        
        status = ollama_client.set_server_url(data['url'])
        return jsonify(status)
    except Exception as e:
        logger.error(f"Server configuration failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Erreur lors de la configuration du serveur: {str(e)}"
        }), 500

@app.route('/api/models')
def get_models():
    try:
        result = ollama_client.list_models()
        logger.info(f"Listed models: {len(result.get('models', []))} found")
        if "error" in result:
            logger.error(f"Error listing models: {result['error']}")
            return jsonify({"models": [], "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get models: {str(e)}")
        return jsonify({"models": [], "error": str(e)})

@app.route('/api/models/running')
def get_running_models():
    try:
        result = ollama_client.list_running_models()
        logger.info(f"Listed running models: {len(result.get('models', []))} found")
        if "error" in result:
            logger.error(f"Error listing running models: {result['error']}")
            return jsonify({
                "models": [],
                "error": result["error"]
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get running models: {str(e)}")
        return jsonify({
            "models": [],
            "error": f"Failed to fetch running models: {str(e)}"
        })

@app.route('/api/models/stop/<model_name>', methods=['POST'])
def stop_model(model_name):
    try:
        logger.info(f"Attempting to stop model: {model_name}")
        result = ollama_client.stop_model(model_name)
        if "error" in result:
            logger.error(f"Error stopping model {model_name}: {result['error']}")
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to stop model {model_name}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/pull/<model_name>', methods=['POST'])
def pull_model(model_name):
    try:
        logger.info(f"Attempting to pull model: {model_name}")
        result = ollama_client.pull_model(model_name)
        if "error" in result:
            logger.error(f"Error pulling model {model_name}: {result['error']}")
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to pull model {model_name}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/delete/<model_name>', methods=['DELETE'])
def delete_model(model_name):
    try:
        logger.info(f"Attempting to delete model: {model_name}")
        result = ollama_client.delete_model(model_name)
        if "error" in result:
            logger.error(f"Error deleting model {model_name}: {result['error']}")
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to delete model {model_name}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/benchmark/<model_name>', methods=['POST'])
def benchmark_model(model_name):
    try:
        logger.info(f"Starting benchmark for model: {model_name}")
        result = model_benchmark.start_benchmark(model_name)
        if "error" in result:
            logger.error(f"Error benchmarking model {model_name}: {result['error']}")
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        logger.error(f"Failed to benchmark model {model_name}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/benchmark/<model_name>/status')
def get_benchmark_status(model_name):
    try:
        result = model_benchmark.get_benchmark_status(model_name)
        if "error" in result:
            logger.error(f"Error getting benchmark status for {model_name}: {result['error']}")
            return jsonify({"status": "error", "error": result["error"]})
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get benchmark status for {model_name}: {str(e)}")
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/models/benchmark/results')
def get_benchmark_results():
    try:
        result = model_benchmark.get_all_results()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get benchmark results: {str(e)}")
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/gpu/stats')
def gpu_stats_stream():
    def generate():
        while True:
            try:
                stats = gpu_monitor.get_stats()
                data = json.dumps(stats)
                yield f"data: {data}\n\n"
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error generating GPU stats: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')
