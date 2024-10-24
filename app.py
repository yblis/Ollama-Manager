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

def validate_url(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except:
        return False

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
        
        url = data['url']
        if not validate_url(url):
            return jsonify({
                "status": "error",
                "message": "Format d'URL invalide"
            }), 400
        
        status = ollama_client.set_server_url(url)
        return jsonify(status)
    except Exception as e:
        logger.error(f"Server check failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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
        
        url = data['url']
        if not validate_url(url):
            return jsonify({
                "status": "error",
                "message": "Format d'URL invalide"
            }), 400
        
        status = ollama_client.set_server_url(url)
        return jsonify(status)
    except Exception as e:
        logger.error(f"Server configuration failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": f"Erreur lors de la configuration du serveur: {str(e)}"
        }), 500

@app.route('/api/models')
def get_models():
    try:
        result = ollama_client.list_models()
        if not isinstance(result, dict):
            logger.error(f"Invalid response format from list_models: {result}")
            return jsonify({
                "models": [],
                "error": "Format de réponse invalide"
            })

        if "error" in result:
            logger.error(f"Error listing models: {result['error']}")
            return jsonify({
                "models": [],
                "error": result["error"]
            })

        models = result.get('models', [])
        logger.info(f"Successfully listed {len(models)} models")
        return jsonify({"models": models})

    except Exception as e:
        logger.error(f"Failed to get models: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "models": [],
            "error": f"Impossible de récupérer les modèles: {str(e)}"
        })

@app.route('/api/models/running')
def get_running_models():
    try:
        logger.info("Fetching running models...")
        result = ollama_client.list_running_models()
        
        # Log the complete response for debugging
        logger.debug(f"Running models response: {result}")
        
        if not isinstance(result, dict):
            logger.error(f"Invalid response format: {result}")
            return jsonify({
                "models": [],
                "error": "Format de réponse invalide du service Ollama"
            })

        models = result.get('models', [])
        error = result.get('error')
        
        if error:
            logger.error(f"Error listing running models: {error}")
            return jsonify({
                "models": [],
                "error": error if isinstance(error, str) else "Erreur lors de la récupération des modèles"
            })

        logger.info(f"Successfully retrieved {len(models)} running models")
        return jsonify({
            "models": models
        })

    except Exception as e:
        logger.error(f"Unexpected error in get_running_models: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "models": [],
            "error": f"Une erreur inattendue s'est produite lors de la récupération des modèles: {str(e)}"
        })

@app.route('/api/models/stop/<model_name>', methods=['POST'])
def stop_model(model_name):
    try:
        if not model_name:
            return jsonify({
                "status": "error",
                "error": "Nom du modèle non spécifié"
            }), 400

        logger.info(f"Attempting to stop model: {model_name}")
        result = ollama_client.stop_model(model_name)
        
        if not isinstance(result, dict):
            return jsonify({
                "status": "error",
                "error": "Format de réponse invalide"
            })

        if "error" in result:
            logger.error(f"Error stopping model {model_name}: {result['error']}")
            return jsonify({
                "status": "error",
                "error": result["error"]
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to stop model {model_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "error": f"Impossible d'arrêter le modèle {model_name}: {str(e)}"
        })

@app.route('/api/models/benchmark/<model_name>', methods=['POST'])
def benchmark_model(model_name):
    try:
        if not model_name:
            return jsonify({
                "status": "error",
                "error": "Nom du modèle non spécifié"
            }), 400

        logger.info(f"Starting benchmark for model: {model_name}")
        result = model_benchmark.start_benchmark(model_name)
        
        if not isinstance(result, dict):
            return jsonify({
                "status": "error",
                "error": "Format de réponse invalide"
            })

        if "error" in result:
            logger.error(f"Error benchmarking model {model_name}: {result['error']}")
            return jsonify({
                "status": "error",
                "error": result["error"]
            })

        return jsonify({
            "status": "success",
            "result": result
        })

    except Exception as e:
        logger.error(f"Failed to benchmark model {model_name}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "error": f"Impossible de lancer le benchmark pour {model_name}: {str(e)}"
        })

@app.route('/api/models/benchmark/results')
def get_benchmark_results():
    try:
        result = model_benchmark.get_all_results()
        if not isinstance(result, dict):
            return jsonify({
                "status": "error",
                "error": "Format de réponse invalide"
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Failed to get benchmark results: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "error": f"Impossible de récupérer les résultats du benchmark: {str(e)}"
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
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')
