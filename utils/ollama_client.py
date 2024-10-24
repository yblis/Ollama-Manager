import requests
from requests.exceptions import RequestException, ConnectionError, HTTPError
import time
import os
import logging
import subprocess
import json

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
            # Try to execute 'ollama --version' to check if ollama is installed and accessible
            result = subprocess.run(['ollama', '--version'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return {"status": "connected", "url": self.base_url}
            else:
                raise Exception("Ollama non disponible")
        except subprocess.TimeoutExpired:
            logger.error("Timeout lors de la vérification d'Ollama")
            return {
                "status": "disconnected",
                "url": self.base_url,
                "message": "Le serveur Ollama ne répond pas. Veuillez vérifier qu'il est en cours d'exécution."
            }
        except subprocess.SubprocessError as e:
            logger.error(f"Erreur lors de l'exécution d'Ollama: {str(e)}")
            return {
                "status": "disconnected",
                "url": self.base_url,
                "message": "Impossible d'exécuter Ollama. Veuillez vérifier l'installation."
            }
        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            return {
                "status": "disconnected",
                "url": self.base_url,
                "message": "Le serveur Ollama n'est pas disponible. Veuillez vérifier l'installation."
            }

    def _execute_command(self, command, args=None, timeout=10):
        """Execute ollama command with proper error handling"""
        if self.connection_status["status"] == "disconnected":
            return {"error": self.connection_status["message"]}

        try:
            cmd = ['ollama'] + command.split() + (args if args else [])
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            logger.debug(f"Command output: {result.stdout}")
            if result.stderr:
                logger.error(f"Command error: {result.stderr}")

            if result.returncode != 0:
                raise subprocess.SubprocessError(f"Erreur: {result.stderr}")
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            error_msg = "Le délai d'exécution a expiré"
            logger.error(error_msg)
            return {"error": error_msg}
            
        except subprocess.SubprocessError as e:
            error_msg = f"Erreur lors de l'exécution de la commande: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
            
        except Exception as e:
            error_msg = f"Erreur inattendue: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def list_models(self):
        """List all available models using 'ollama list' command"""
        try:
            output = self._execute_command('list')
            if isinstance(output, dict) and "error" in output:
                return {
                    "models": [],
                    "error": output["error"]
                }

            # Parse the command output
            models = []
            for line in output.splitlines()[1:]:  # Skip header line
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    size = self._parse_size(parts[1]) if len(parts) > 1 else 0
                    models.append({
                        "name": name,
                        "size": size,
                        "digest": parts[2] if len(parts) > 2 else "",
                        "modified_at": " ".join(parts[3:]) if len(parts) > 3 else ""
                    })

            logger.info(f"Found {len(models)} models")
            return {"models": models}
            
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return {
                "models": [],
                "error": f"Impossible de lister les modèles: {str(e)}"
            }

    def list_running_models(self):
        """List running models using 'ollama ps' command"""
        try:
            output = self._execute_command('ps')
            if isinstance(output, dict) and "error" in output:
                return {
                    "models": [],
                    "error": output["error"]
                }

            # Parse the command output
            models = []
            for line in output.splitlines()[1:]:  # Skip header line
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 2:
                    models.append({
                        "name": parts[0],
                        "status": "en cours",
                        "size": 0  # Size not available in ps output
                    })

            logger.info(f"Found {len(models)} running models")
            return {"models": models}
            
        except Exception as e:
            logger.error(f"Failed to list running models: {str(e)}")
            return {
                "models": [],
                "error": f"Impossible de lister les modèles en cours d'exécution: {str(e)}"
            }

    def stop_model(self, model_name):
        """Stop a running model"""
        try:
            output = self._execute_command('kill', [model_name])
            if isinstance(output, dict) and "error" in output:
                return {
                    "status": "error",
                    "error": output["error"]
                }
            return {
                "status": "success",
                "message": f"Modèle {model_name} arrêté avec succès"
            }
        except Exception as e:
            logger.error(f"Failed to stop model {model_name}: {str(e)}")
            return {
                "status": "error",
                "error": f"Impossible d'arrêter le modèle {model_name}: {str(e)}"
            }

    def _parse_size(self, size_str):
        """Parse size string (e.g., '1.2GB') to bytes"""
        try:
            if not size_str:
                return 0
                
            units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
            number = float(''.join(filter(lambda x: x.isdigit() or x == '.', size_str)))
            unit = ''.join(filter(str.isalpha, size_str)).upper()
            
            return int(number * units.get(unit, 1))
        except Exception:
            return 0

    def generate_text(self, model_name, prompt):
        """Generate text using a model through API"""
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
