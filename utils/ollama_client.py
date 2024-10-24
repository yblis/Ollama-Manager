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
        self.connection_status = self.check_connection()

    def _get_server_url(self):
        """Get server URL from environment or default"""
        return os.environ.get('OLLAMA_SERVER_URL', 'http://localhost:11434')

    def create_error_response(self, message, code="ERROR", details=None):
        """Create a standardized error response"""
        error_obj = {
            "message": message or "Une erreur inconnue s'est produite",
            "code": code,
            "details": details or "Aucun détail supplémentaire disponible"
        }
        logger.error(f"Error response generated: {error_obj}")
        return {"error": error_obj}

    def _validate_url(self, url):
        """Validate URL format"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "L'URL du serveur est invalide. Format attendu: http(s)://host:port"
            if result.scheme not in ['http', 'https']:
                return False, "Le protocole doit être HTTP ou HTTPS"
            return True, None
        except Exception as e:
            logger.error(f"URL validation failed: {str(e)}")
            return False, "Format d'URL invalide"

    def _check_ollama_installed(self):
        """Check if Ollama is installed on the system"""
        try:
            result = subprocess.run(['which', 'ollama'],
                                 capture_output=True,
                                 text=True,
                                 timeout=2)
            
            logger.debug(f"Installation check result: {result.stdout}, {result.stderr}")
            
            if result.returncode != 0:
                logger.error("Ollama not found in system PATH")
                return False, "Ollama n'est pas installé. Veuillez installer Ollama avant de continuer: https://ollama.ai/download"
            return True, None
        except subprocess.TimeoutExpired:
            logger.error("Timeout checking Ollama installation")
            return False, "Le délai de vérification de l'installation a expiré"
        except Exception as e:
            logger.error(f"Error checking Ollama installation: {str(e)}")
            return False, f"Erreur lors de la vérification de l'installation: {str(e)}"

    def check_connection(self):
        """Check if Ollama server is available"""
        try:
            is_installed, error = self._check_ollama_installed()
            if not is_installed:
                return {
                    "status": "disconnected",
                    "url": self.base_url,
                    "message": error
                }

            is_valid, error = self._validate_url(self.base_url)
            if not is_valid:
                return {
                    "status": "disconnected",
                    "url": self.base_url,
                    "message": error
                }

            try:
                response = requests.get(f"{self.base_url}/api/version", timeout=2)
                response.raise_for_status()
                logger.info("Successfully connected to Ollama API")
                return {"status": "connected", "url": self.base_url}
            except requests.exceptions.ConnectionError:
                logger.error("Connection to API failed, checking service status")
                service_check = subprocess.run(['pgrep', 'ollama'],
                                           capture_output=True,
                                           text=True)
                if service_check.returncode != 0:
                    return {
                        "status": "disconnected",
                        "url": self.base_url,
                        "message": "Le service Ollama n'est pas démarré. Veuillez démarrer le service avec la commande 'ollama serve'"
                    }
            except Exception as e:
                logger.error(f"API check failed: {str(e)}")
                return {
                    "status": "disconnected",
                    "url": self.base_url,
                    "message": f"Erreur de connexion à l'API: {str(e)}. Vérifiez que le service est démarré."
                }

        except Exception as e:
            logger.error(f"Unexpected error in check_connection: {str(e)}")
            return {
                "status": "disconnected",
                "url": self.base_url,
                "message": f"Erreur inattendue lors de la vérification de la connexion: {str(e)}"
            }

    def set_server_url(self, url):
        """Update server URL and check connection"""
        is_valid, error = self._validate_url(url)
        if not is_valid:
            logger.error(f"Invalid server URL: {error}")
            return self.create_error_response(error, "URL_VALIDATION_ERROR")

        self.base_url = url
        self.connection_status = self.check_connection()
        return self.connection_status

    def _make_request(self, method, endpoint, json=None, retry_count=0):
        """Make HTTP request with retries and proper error handling"""
        if self.connection_status["status"] == "disconnected":
            logger.error(f"Cannot make request - disconnected: {self.connection_status['message']}")
            return self.create_error_response(self.connection_status['message'], "CONNECTION_ERROR")

        try:
            logger.info(f"Making {method} request to {endpoint}")
            if json:
                logger.debug(f"Request payload: {json}")
                
            response = requests.request(method=method,
                                    url=f"{self.base_url}{endpoint}",
                                    json=json,
                                    timeout=self.timeout)
            
            logger.debug(f"Response status: {response.status_code}")
            if response.text:
                logger.debug(f"Response content: {response.text[:500]}")
                
            response.raise_for_status()
            return response.json() if response.text else {}

        except requests.exceptions.ConnectTimeout:
            error_msg = "Le délai de connexion au serveur a expiré"
            logger.error(error_msg)
            if retry_count < self.max_retries - 1:
                logger.info(f"Retrying request ({retry_count + 1}/{self.max_retries})")
                time.sleep(self.retry_delay)
                return self._make_request(method, endpoint, json, retry_count + 1)
            return self.create_error_response(error_msg, "TIMEOUT_ERROR")

        except requests.exceptions.ConnectionError:
            error_msg = "Impossible de se connecter au serveur Ollama. Vérifiez que le service est démarré."
            logger.error(error_msg)
            if retry_count < self.max_retries - 1:
                logger.info(f"Retrying request ({retry_count + 1}/{self.max_retries})")
                time.sleep(self.retry_delay)
                return self._make_request(method, endpoint, json, retry_count + 1)
            return self.create_error_response(error_msg, "CONNECTION_ERROR")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                error_msg = f"Service non trouvé: {endpoint}"
            else:
                error_msg = f"Erreur HTTP {e.response.status_code}"
            logger.error(f"{error_msg}: {str(e)}")
            return self.create_error_response(error_msg, "HTTP_ERROR", str(e))

        except Exception as e:
            error_msg = f"Erreur inattendue: {str(e)}"
            logger.error(f"{error_msg}")
            if retry_count < self.max_retries - 1:
                logger.info(f"Retrying request ({retry_count + 1}/{self.max_retries})")
                time.sleep(self.retry_delay)
                return self._make_request(method, endpoint, json, retry_count + 1)
            return self.create_error_response(error_msg, "REQUEST_ERROR", str(e))

    def _execute_command(self, command, args=None):
        """Execute Ollama command with proper error handling"""
        try:
            is_installed, error = self._check_ollama_installed()
            if not is_installed:
                return self.create_error_response(error, "INSTALLATION_ERROR")

            cmd = ['ollama'] + command.split() + (args if args else [])
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=self.timeout)
            
            logger.debug(f"Command stdout: {result.stdout}")
            logger.debug(f"Command stderr: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Erreur lors de l'exécution de la commande"
                logger.error(f"Command failed: {error_msg}")
                return self.create_error_response(error_msg, "COMMAND_EXECUTION_ERROR", f"Code de retour: {result.returncode}")
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            error_msg = "Le délai d'exécution de la commande a expiré"
            logger.error(error_msg)
            return self.create_error_response(error_msg, "COMMAND_TIMEOUT")
            
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la commande: {str(e)}"
            logger.error(error_msg)
            return self.create_error_response(error_msg, "COMMAND_ERROR", str(e))

    def list_models(self):
        """List all available models with API fallback to command line"""
        logger.info("Attempting to list models...")
        
        is_installed, error = self._check_ollama_installed()
        if not is_installed:
            return self.create_error_response(error, "INSTALLATION_ERROR")

        try:
            response = self._make_request("GET", "/api/tags")
            if response and "error" not in response:
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
                
                logger.info(f"Successfully listed {len(models)} models via API")
                return {"models": models}
                
        except Exception as e:
            logger.warning(f"API request failed, falling back to command: {str(e)}")
        
        try:
            output = self._execute_command('list')
            if isinstance(output, dict) and "error" in output:
                return output
                
            models = []
            lines = output.splitlines() if isinstance(output, str) else []
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 2:
                    model_info = {
                        "name": parts[0],
                        "size": 0,
                        "modified_at": parts[1] if len(parts) > 1 else ""
                    }
                    models.append(model_info)
            
            logger.info(f"Successfully listed {len(models)} models via command")
            return {"models": models}
            
        except Exception as e:
            error_msg = f"Impossible de lister les modèles: {str(e)}"
            logger.error(error_msg)
            return self.create_error_response(error_msg, "MODEL_LIST_ERROR", str(e))

    def list_running_models(self):
        """List only currently running models using 'ollama ps' command"""
        logger.info("Fetching running models...")

        is_installed, error = self._check_ollama_installed()
        if not is_installed:
            return self.create_error_response(error, "INSTALLATION_ERROR")
            
        try:
            cmd = ['ollama', 'ps']
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=self.timeout)
            
            logger.debug(f"Command stdout: {result.stdout}")
            logger.debug(f"Command stderr: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Erreur lors de la récupération des modèles en cours d'exécution"
                logger.error(f"Command failed: {error_msg}")
                return self.create_error_response(error_msg, "RUNNING_MODELS_ERROR", f"Code de retour: {result.returncode}")
            
            models = []
            lines = result.stdout.strip().splitlines()
            
            if lines and "NAME" in lines[0].upper():
                lines = lines[1:]
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 1:
                    model_info = {
                        "name": parts[0],
                        "status": "en cours",
                        "id": parts[1] if len(parts) > 1 else ""
                    }
                    models.append(model_info)
            
            logger.info(f"Found {len(models)} running models")
            return {"models": models}
            
        except subprocess.TimeoutExpired:
            error_msg = "Le délai d'attente a expiré lors de la récupération des modèles"
            logger.error(error_msg)
            return self.create_error_response(error_msg, "COMMAND_TIMEOUT")
            
        except Exception as e:
            error_msg = f"Impossible de lister les modèles en cours d'exécution: {str(e)}"
            logger.error(f"Unexpected error in list_running_models: {str(e)}")
            return self.create_error_response(error_msg, "RUNNING_MODELS_ERROR", str(e))

    def stop_model(self, model_name):
        """Stop a running model"""
        if not model_name:
            return self.create_error_response("Nom du modèle non spécifié", "VALIDATION_ERROR")

        is_installed, error = self._check_ollama_installed()
        if not is_installed:
            return self.create_error_response(error, "INSTALLATION_ERROR")

        try:
            response = self._make_request("POST", "/api/stop", json={"name": model_name})
            if not response:
                return self.create_error_response("Aucune réponse du serveur", "SERVER_ERROR")

            if "error" in response:
                return self.create_error_response(response["error"], "STOP_MODEL_ERROR")

            return {
                "status": "success",
                "message": f"Modèle {model_name} arrêté avec succès"
            }

        except Exception as e:
            error_msg = f"Impossible d'arrêter le modèle {model_name}: {str(e)}"
            logger.error(f"Failed to stop model {model_name}: {str(e)}")
            return self.create_error_response(error_msg, "STOP_MODEL_ERROR", str(e))