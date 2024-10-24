from flask import Flask, render_template, jsonify, Response, request
import json
import logging
from utils.gpu_monitor import GPUMonitor
from utils.ollama_client import OllamaClient
from utils.benchmark import ModelBenchmark
import time
import traceback
from urllib.parse import urlparse

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

@app.route('/api/models')
def get_models():
    try:
        result = ollama_client.list_models()
        if not isinstance(result, dict):
            return jsonify({
                "error": {
                    "message": "Format de réponse invalide",
                    "code": "INVALID_RESPONSE",
                    "details": "La réponse du serveur n'est pas au format attendu"
                }
            })

        if "error" in result:
            logger.error(f"Error listing models: {result['error']}")
            return jsonify({"error": result["error"]})

        models = result.get('models', [])
        logger.info(f"Successfully listed {len(models)} models")
        return jsonify({"models": models})

    except Exception as e:
        logger.error(f"Failed to get models: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": {
                "message": "Impossible de récupérer les modèles",
                "code": "MODEL_FETCH_ERROR",
                "details": str(e)
            }
        })

@app.route('/api/models/running')
def get_running_models():
    try:
        logger.info("Fetching running models...")
        result = ollama_client.list_running_models()
        
        if not isinstance(result, dict):
            return jsonify({
                "error": {
                    "message": "Format de réponse invalide",
                    "code": "INVALID_RESPONSE",
                    "details": "La réponse du service n'est pas au format attendu"
                }
            })

        if "error" in result:
            logger.error(f"Error listing running models: {result['error']}")
            return jsonify({"error": result["error"]})

        models = result.get('models', [])
        logger.info(f"Successfully retrieved {len(models)} running models")
        return jsonify({"models": models})

    except Exception as e:
        logger.error(f"Unexpected error in get_running_models: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": {
                "message": "Une erreur inattendue s'est produite",
                "code": "UNEXPECTED_ERROR",
                "details": str(e)
            }
        })

@app.route('/api/models/stop/<model_name>', methods=['POST'])
def stop_model(model_name):
    try:
        if not model_name:
            return jsonify({
                "error": {
                    "message": "Nom du modèle non spécifié",
                    "code": "MISSING_MODEL_NAME"
                }
            }), 400

        logger.info(f"Attempting to stop model: {model_name}")
        result = ollama_client.stop_model(model_name)
        
        if not isinstance(result, dict):
            return jsonify({
                "error": {
                    "message": "Format de réponse invalide",
                    "code": "INVALID_RESPONSE",
                    "details": "La réponse du service n'est pas au format attendu"
                }
            })

        if "error" in result:
            logger.error(f"Error stopping model {model_name}: {result['error']}")
            return jsonify({"error": result["error"]})

        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to stop model {model_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": {
                "message": f"Impossible d'arrêter le modèle {model_name}",
                "code": "MODEL_STOP_ERROR",
                "details": str(e)
            }
        })

@app.route('/api/models/benchmark/<model_name>', methods=['POST'])
def benchmark_model(model_name):
    try:
        if not model_name:
            return jsonify({
                "error": {
                    "message": "Nom du modèle non spécifié",
                    "code": "MISSING_MODEL_NAME"
                }
            }), 400

        logger.info(f"Starting benchmark for model: {model_name}")
        result = model_benchmark.start_benchmark(model_name)
        
        if not isinstance(result, dict):
            return jsonify({
                "error": {
                    "message": "Format de réponse invalide",
                    "code": "INVALID_RESPONSE",
                    "details": "La réponse du service n'est pas au format attendu"
                }
            })

        if "error" in result:
            logger.error(f"Error benchmarking model {model_name}: {result['error']}")
            return jsonify({"error": result["error"]})

        return jsonify({
            "status": "success",
            "result": result
        })

    except Exception as e:
        logger.error(f"Failed to benchmark model {model_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": {
                "message": f"Impossible de lancer le benchmark pour {model_name}",
                "code": "BENCHMARK_ERROR",
                "details": str(e)
            }
        })

@app.route('/api/models/benchmark/results')
def get_benchmark_results():
    try:
        result = model_benchmark.get_all_results()
        if not isinstance(result, dict):
            return jsonify({
                "error": {
                    "message": "Format de réponse invalide",
                    "code": "INVALID_RESPONSE",
                    "details": "La réponse du service n'est pas au format attendu"
                }
            })

        if "error" in result:
            return jsonify({"error": result["error"]})

        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to get benchmark results: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": {
                "message": "Impossible de récupérer les résultats",
                "code": "BENCHMARK_RESULTS_ERROR",
                "details": str(e)
            }
        })

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
                logger.error(f"Traceback: {traceback.format_exc()}")
                error_response = {
                    "error": {
                        "message": "Erreur lors de la génération des statistiques GPU",
                        "code": "GPU_STATS_ERROR",
                        "details": str(e)
                    }
                }
                yield f"data: {json.dumps(error_response)}\n\n"
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')
