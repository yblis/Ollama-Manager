import requests
from requests.exceptions import RequestException, ConnectionError
import time
import os


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
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            response.raise_for_status()
            return {"status": "connected", "url": self.base_url}
        except Exception as e:
            return {
                "status":
                "disconnected",
                "url":
                self.base_url,
                "message":
                "Le serveur Ollama n'est pas en cours d'exécution. Veuillez démarrer le service Ollama pour activer la gestion des modèles."
            }

    def _make_request(self, method, endpoint, json=None):
        """Make HTTP request with retries and proper error handling"""
        if self.connection_status["status"] == "disconnected":
            return {"error": self.connection_status["message"]}

        for attempt in range(self.max_retries):
            try:
                response = requests.request(method=method,
                                            url=f"{self.base_url}{endpoint}",
                                            json=json,
                                            timeout=10)
                response.raise_for_status()
                return response.json() if response.text else {}
            except ConnectionError:
                error_msg = "Impossible de se connecter au serveur Ollama - Assurez-vous qu'Ollama est en cours d'exécution"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return {"error": error_msg}
            except RequestException as e:
                error_msg = "Échec de la connexion au serveur Ollama"
                if hasattr(e, 'response') and e.response is not None:
                    error_msg += f": {e.response.text}"
                elif str(e):
                    error_msg += f": {str(e)}"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
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
                    "error":
                    response.get("error")
                    if response else "Erreur de réponse vide"
                }
            return response
        except Exception as e:
            return {
                "models": [],
                "error": f"Impossible de lister les modèles: {str(e)}"
            }

    def list_running_models(self):
        """List all currently running model instances"""
        try:
            response = self._make_request("GET", "/api/show")
            if response is None:
                return {
                    "models": [],
                    "error": "Aucun modèle en cours d'exécution"
                }
            if "error" in response:
                return {"models": [], "error": response["error"]}

            models = []
            if isinstance(response, dict):
                for model_name, status in response.items():
                    if isinstance(status, dict):
                        models.append({
                            "name":
                            model_name,
                            "status":
                            "en cours" if status.get("status") == "ready" else
                            status.get("status", "inconnu")
                        })
            return {"models": models}
        except Exception as e:
            return {
                "models": [],
                "error":
                f"Impossible de lister les modèles en cours d'exécution: {str(e)}"
            }

    def stop_model(self, model_name):
        """Stop a running model instance"""
        try:
            response = self._make_request("POST",
                                          "/api/stop",
                                          json={"name": model_name})
            if response is None or "error" in response:
                return {
                    "status":
                    "error",
                    "error":
                    response.get("error")
                    if response else "Erreur d'arrêt du modèle"
                }
            return {
                "status": "success",
                "message": f"Modèle {model_name} arrêté avec succès"
            }
        except Exception as e:
            return {
                "status": "error",
                "error":
                f"Impossible d'arrêter le modèle {model_name}: {str(e)}"
            }

    def pull_model(self, model_name):
        """Pull a new model"""
        try:
            response = self._make_request("POST",
                                          "/api/pull",
                                          json={"name": model_name})
            if response is None or "error" in response:
                return {
                    "status":
                    "error",
                    "error":
                    response.get("error")
                    if response else "Erreur de téléchargement"
                }
            return {
                "status": "success",
                "message": f"Modèle {model_name} téléchargé avec succès"
            }
        except Exception as e:
            return {
                "status":
                "error",
                "error":
                f"Impossible de télécharger le modèle {model_name}: {str(e)}"
            }

    def delete_model(self, model_name):
        """Delete an existing model"""
        try:
            response = self._make_request("DELETE",
                                          "/api/delete",
                                          json={"name": model_name})
            if response is None or "error" in response:
                return {
                    "status":
                    "error",
                    "error":
                    response.get("error")
                    if response else "Erreur de suppression"
                }
            return {
                "status": "success",
                "message": f"Modèle {model_name} supprimé avec succès"
            }
        except Exception as e:
            return {
                "status":
                "error",
                "error":
                f"Impossible de supprimer le modèle {model_name}: {str(e)}"
            }

    def generate_text(self, model_name, prompt):
        """Generate text using a model"""
        try:
            response = self._make_request("POST",
                                          "/api/generate",
                                          json={
                                              "model": model_name,
                                              "prompt": prompt
                                          })
            if response is None or "error" in response:
                return {
                    "error":
                    response.get("error")
                    if response else "Erreur de génération"
                }
            return response
        except Exception as e:
            return {"error": f"Impossible de générer le texte: {str(e)}"}
