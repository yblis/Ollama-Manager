import requests
from requests.exceptions import RequestException, ConnectionError, HTTPError
import time
import os
import logging
import subprocess
import json
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.base_url = self._get_server_url()
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.timeout = 10  # seconds
        self.connection_status = None
        self._check_and_set_connection()

    def _get_server_url(self):
        """Get server URL from environment or default"""
        return os.environ.get('OLLAMA_SERVER_URL', 'http://localhost:11434')

    def _check_and_set_connection(self):
        """Check connection and set status"""
        self.connection_status = self.check_connection()
        return self.connection_status

    def create_error_response(self, message, code, details=None):
        """Create a standardized error response"""
        error_obj = {
            "message": message,
            "code": code,
            "details": details or "Aucun détail supplémentaire disponible"
        }
        logger.error(f"Error response generated: {error_obj}")
        return {"error": error_obj}

    def _check_ollama_installed(self):
        """Check if Ollama is installed and available"""
        try:
            # First try connecting to the configured server
            try:
                response = requests.get(f"{self.base_url}/api/version", timeout=2)
                response.raise_for_status()
                return True, {
                    "version": response.text.strip(),
                    "server": self.base_url
                }
            except requests.exceptions.RequestException as e:
                logger.debug(f"Server check failed: {str(e)}, checking local installation")

            # If server not accessible, check local installation
            result = subprocess.run(['which', 'ollama'],
                                capture_output=True,
                                text=True,
                                timeout=2)
            
            logger.debug(f"Installation check output - stdout: {result.stdout}, stderr: {result.stderr}")
            
            if result.returncode != 0:
                return False, self.create_error_response(
                    "Ollama n'est pas installé sur le système",
                    "INSTALLATION_ERROR",
                    "Veuillez installer Ollama depuis https://ollama.ai/download"
                )["error"]
            
            # Check version
            version_result = subprocess.run(['ollama', 'version'],
                                       capture_output=True,
                                       text=True,
                                       timeout=2)
            
            if version_result.returncode == 0:
                return True, {
                    "version": version_result.stdout.strip(),
                    "local": True
                }
            return True, {"version": "Version inconnue", "local": True}
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout checking Ollama installation")
            return False, self.create_error_response(
                "Délai d'attente dépassé lors de la vérification",
                "TIMEOUT_ERROR",
                "La commande de vérification n'a pas répondu dans le délai imparti"
            )["error"]
            
        except Exception as e:
            logger.error(f"Error checking Ollama installation: {str(e)}")
            return False, self.create_error_response(
                "Erreur lors de la vérification de l'installation",
                "INSTALLATION_CHECK_ERROR",
                str(e)
            )["error"]

    def check_connection(self):
        """Check if Ollama server is available"""
        try:
            # First check if we can connect to the server
            try:
                response = requests.get(f"{self.base_url}/api/version",
                                    timeout=2)
                response.raise_for_status()
                return {
                    "status": "connected",
                    "version": response.text.strip(),
                    "server": self.base_url
                }
            except requests.exceptions.RequestException:
                pass

            # If server not accessible, check local installation and service
            is_installed, install_info = self._check_ollama_installed()
            if not is_installed:
                return {
                    "status": "disconnected",
                    "error": install_info
                }

            # Check if service is running
            service_check = subprocess.run(['pgrep', 'ollama'],
                                       capture_output=True,
                                       text=True)
                                       
            if service_check.returncode != 0:
                return {
                    "status": "disconnected",
                    "error": self.create_error_response(
                        "Le service Ollama n'est pas démarré",
                        "SERVICE_NOT_RUNNING",
                        "Démarrez le service avec la commande: ollama serve"
                    )["error"]
                }
                
            return {
                "status": "disconnected",
                "error": self.create_error_response(
                    "Impossible de se connecter au serveur Ollama",
                    "CONNECTION_ERROR",
                    "Le serveur est peut-être en cours de démarrage ou mal configuré"
                )["error"]
            }

        except Exception as e:
            logger.error(f"Unexpected error in check_connection: {str(e)}")
            return {
                "status": "disconnected",
                "error": self.create_error_response(
                    "Erreur inattendue lors de la vérification",
                    "UNEXPECTED_ERROR",
                    str(e)
                )["error"]
            }

    def list_running_models(self):
        """List running models using 'ollama ls'"""
        logger.info("Fetching running models...")
        
        try:
            # First try API endpoint
            status = self._check_and_set_connection()
            if status["status"] == "connected":
                try:
                    response = requests.get(f"{self.base_url}/api/tags",
                                       timeout=self.timeout)
                    response.raise_for_status()
                    models_data = response.json()
                    
                    running_models = []
                    for model in models_data:
                        if isinstance(model, dict) and model.get("status") == "running":
                            running_models.append({
                                "name": model.get("name", "unknown"),
                                "id": model.get("id"),
                                "status": "en cours"
                            })
                    
                    logger.info(f"Successfully listed {len(running_models)} running models via API")
                    return {"models": running_models}
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"API request failed: {str(e)}, falling back to command")
            
            # Fallback to command line
            cmd = ['ollama', 'ls']
            result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=self.timeout)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if "not found" in error_msg.lower():
                    return self.create_error_response(
                        "Ollama n'est pas installé sur le système",
                        "INSTALLATION_ERROR",
                        "Veuillez installer Ollama depuis https://ollama.ai/download"
                    )
                return self.create_error_response(
                    "Erreur lors de la récupération des modèles en cours",
                    "COMMAND_ERROR",
                    error_msg or "La commande a échoué"
                )
            
            models = []
            lines = result.stdout.strip().splitlines()
            
            # Skip header row if present
            if lines and any(header in lines[0].upper() for header in ["NAME", "ID", "STATUS"]):
                lines = lines[1:]
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 3:  # NAME ID STATUS format
                    model_info = {
                        "name": parts[0],
                        "id": parts[1],
                        "status": "en cours" if parts[2].lower() == "running" else parts[2]
                    }
                    models.append(model_info)
            
            logger.info(f"Found {len(models)} running models")
            return {"models": models}
            
        except subprocess.TimeoutExpired:
            return self.create_error_response(
                "Délai d'attente dépassé",
                "TIMEOUT_ERROR",
                "La commande n'a pas répondu dans le délai imparti"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in list_running_models: {str(e)}")
            return self.create_error_response(
                "Erreur lors de la récupération des modèles en cours",
                "LIST_ERROR",
                str(e)
            )

    def list_models(self):
        """List all available models"""
        logger.info("Attempting to list models...")
        
        try:
            # First try API endpoint
            status = self._check_and_set_connection()
            if status["status"] == "connected":
                try:
                    response = requests.get(f"{self.base_url}/api/tags",
                                       timeout=self.timeout)
                    response.raise_for_status()
                    models_data = response.json()
                    
                    models = []
                    for model in models_data:
                        if isinstance(model, dict):
                            models.append({
                                "name": model.get("name", "unknown"),
                                "size": model.get("size", 0),
                                "modified_at": model.get("modified_at", "")
                            })
                    
                    logger.info(f"Successfully listed {len(models)} models via API")
                    return {"models": models}
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"API request failed: {str(e)}, falling back to command")
            
            # Fallback to command line
            cmd = ['ollama', 'list']
            result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=self.timeout)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if "not found" in error_msg.lower():
                    return self.create_error_response(
                        "Ollama n'est pas installé sur le système",
                        "INSTALLATION_ERROR",
                        "Veuillez installer Ollama depuis https://ollama.ai/download"
                    )
                return self.create_error_response(
                    "Erreur lors de la récupération des modèles",
                    "COMMAND_ERROR",
                    error_msg or "La commande a échoué"
                )
            
            models = []
            lines = result.stdout.strip().splitlines()
            
            # Skip header if present
            if lines and "NAME" in lines[0].upper():
                lines = lines[1:]
            
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 1:
                        models.append({
                            "name": parts[0],
                            "modified_at": parts[1] if len(parts) > 1 else ""
                        })
            
            return {"models": models}
            
        except subprocess.TimeoutExpired:
            return self.create_error_response(
                "Délai d'attente dépassé",
                "TIMEOUT_ERROR",
                "La commande n'a pas répondu dans le délai imparti"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in list_models: {str(e)}")
            return self.create_error_response(
                "Erreur lors du listage des modèles",
                "LIST_ERROR",
                str(e)
            )

    def stop_model(self, model_name):
        """Stop a running model"""
        if not model_name:
            return self.create_error_response(
                "Nom du modèle non spécifié",
                "VALIDATION_ERROR"
            )

        try:
            # Try API endpoint first
            status = self._check_and_set_connection()
            if status["status"] == "connected":
                try:
                    response = requests.post(
                        f"{self.base_url}/api/stop",
                        json={"name": model_name},
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        return {
                            "status": "success",
                            "message": f"Modèle {model_name} arrêté avec succès"
                        }
                    
                    return self.create_error_response(
                        f"Erreur lors de l'arrêt du modèle {model_name}",
                        "STOP_ERROR",
                        response.text
                    )
                except requests.exceptions.RequestException as e:
                    logger.warning(f"API request failed: {str(e)}, falling back to command")

            # Fallback to command line
            cmd = ['ollama', 'stop', model_name]
            result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=self.timeout)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if "not found" in error_msg.lower():
                    return self.create_error_response(
                        "Ollama n'est pas installé sur le système",
                        "INSTALLATION_ERROR",
                        "Veuillez installer Ollama depuis https://ollama.ai/download"
                    )
                return self.create_error_response(
                    f"Erreur lors de l'arrêt du modèle {model_name}",
                    "STOP_ERROR",
                    error_msg or "La commande a échoué"
                )

            return {
                "status": "success",
                "message": f"Modèle {model_name} arrêté avec succès"
            }

        except subprocess.TimeoutExpired:
            return self.create_error_response(
                "Délai d'attente dépassé",
                "TIMEOUT_ERROR",
                "La commande n'a pas répondu dans le délai imparti"
            )

        except Exception as e:
            logger.error(f"Failed to stop model {model_name}: {str(e)}")
            return self.create_error_response(
                f"Impossible d'arrêter le modèle {model_name}",
                "STOP_ERROR",
                str(e)
            )
