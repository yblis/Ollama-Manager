import requests
from requests.exceptions import RequestException, ConnectionError, HTTPError
import time
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.base_url = self._get_server_url()
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.connection_status = self.check_connection()

    def _get_server_url(self):
        """Get server URL from environment or default"""
        return os.environ.get('OLLAMA_SERVER_URL', 'http://localhost:11434')

    def set_server_url(self, url):
        """Update server URL and check connection"""
        self.base_url = url
        self.connection_status = self.check_connection()
        return self.connection_status

    def check_connection(self):
        """Check if Ollama server is available"""
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=2)
            response.raise_for_status()
            return {"status": "connected", "url": self.base_url}
        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            return {
                "status": "disconnected",
                "url": self.base_url,
                "message": "Le serveur Ollama n'est pas disponible. Veuillez démarrer le service Ollama."
            }

    def _make_request(self, method, endpoint, json=None, retry_count=0):
        """Make HTTP request with retries and proper error handling"""
        if self.connection_status["status"] == "disconnected":
            return {"error": self.connection_status["message"]}

        try:
            response = requests.request(
                method=method,
                url=f"{self.base_url}{endpoint}",
                json=json,
                timeout=10
            )
            response.raise_for_status()
            return response.json() if response.text else {}

        except HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Endpoint not found: {endpoint}")
                return {"error": f"API endpoint '{endpoint}' not found"}
            error_msg = f"HTTP error occurred: {str(e)}"
            logger.error(error_msg)
            if retry_count < self.max_retries - 1:
                time.sleep(self.retry_delay)
                return self._make_request(method, endpoint, json, retry_count + 1)
            return {"error": error_msg}

        except ConnectionError:
            error_msg = "Impossible de se connecter au serveur Ollama"
            logger.error(error_msg)
            if retry_count < self.max_retries - 1:
                time.sleep(self.retry_delay)
                return self._make_request(method, endpoint, json, retry_count + 1)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Erreur inattendue: {str(e)}"
            logger.error(error_msg)
            if retry_count < self.max_retries - 1:
                time.sleep(self.retry_delay)
                return self._make_request(method, endpoint, json, retry_count + 1)
            return {"error": error_msg}

    def get_connection_status(self):
        """Get current connection status"""
        self.connection_status = self.check_connection()
        return self.connection_status

    def list_models(self):
        """List all available models"""
        try:
            response = self._make_request("GET", "/api/tags")
            if response is None or "error" in response:
                return {
                    "models": [],
                    "error": response.get("error") if response else "Aucun modèle disponible"
                }

            models = []
            if isinstance(response, list):
                for model in response:
                    if isinstance(model, dict):
                        models.append({
                            "name": model.get("name", "unknown"),
                            "size": model.get("size", 0),
                            "digest": model.get("digest", ""),
                            "modified_at": model.get("modified_at", "")
                        })
            return {"models": models}
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return {"models": [], "error": f"Impossible de lister les modèles: {str(e)}"}

    def list_running_models(self):
        """List all currently running model instances"""
        try:
            response = self._make_request("GET", "/api/tags")
            if response is None:
                return {"models": [], "error": "Aucun modèle en cours d'exécution"}

            if "error" in response:
                return {
                    "models": [],
                    "error": "Aucun modèle en cours d'exécution"
                }

            models = []
            if isinstance(response, list):
                for model in response:
                    if isinstance(model, dict) and model.get("status") == "ready":
                        models.append({
                            "name": model.get("name", "unknown"),
                            "status": "en cours",
                            "size": model.get("size", 0)
                        })

            return {"models": models}

        except Exception as e:
            logger.error(f"Failed to list running models: {str(e)}")
            return {
                "models": [],
                "error": f"Impossible de lister les modèles en cours d'exécution: {str(e)}"
            }

    def stop_model(self, model_name):
        """Stop a running model instance"""
        try:
            response = self._make_request("POST", "/api/stop", json={"name": model_name})
            if response is None or "error" in response:
                return {
                    "status": "error",
                    "error": response.get("error") if response else "Erreur d'arrêt du modèle"
                }
            return {"status": "success", "message": f"Modèle {model_name} arrêté avec succès"}
        except Exception as e:
            logger.error(f"Failed to stop model {model_name}: {str(e)}")
            return {
                "status": "error",
                "error": f"Impossible d'arrêter le modèle {model_name}: {str(e)}"
            }

    def generate_text(self, model_name, prompt):
        """Generate text using a model"""
        try:
            response = self._make_request("POST", "/api/generate", json={
                "model": model_name,
                "prompt": prompt
            })
            if response is None or "error" in response:
                return {
                    "error": response.get("error") if response else "Erreur de génération"
                }
            return response
        except Exception as e:
            logger.error(f"Failed to generate text: {str(e)}")
            return {"error": f"Impossible de générer le texte: {str(e)}"}
