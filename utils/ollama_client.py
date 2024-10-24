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
            logger.debug(f"Connection check output: {result.stdout}")
            if result.returncode == 0:
                return {"status": "connected", "url": self.base_url}
            else:
                logger.error(f"Connection check failed with return code: {result.returncode}")
                raise Exception("Ollama non disponible")
        except subprocess.TimeoutExpired:
            logger.error("Timeout lors de la vérification d'Ollama")
            return {
                "status": "disconnected",
                "url": self.base_url,
                "message": "Le serveur Ollama ne répond pas. Veuillez vérifier qu'il est en cours d'exécution."
            }
        except FileNotFoundError:
            logger.error("Ollama command not found")
            return {
                "status": "disconnected",
                "url": self.base_url,
                "message": "Ollama n'est pas installé sur le système. Veuillez l'installer avant de continuer."
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
            error_msg = self.connection_status.get("message", "Service Ollama non disponible")
            logger.error(f"Command execution failed - disconnected: {error_msg}")
            return {"error": error_msg}

        try:
            cmd = ['ollama'] + command.split() + (args if args else [])
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            logger.debug(f"Command stdout: {result.stdout}")
            if result.stderr:
                logger.error(f"Command stderr: {result.stderr}")

            if result.returncode != 0:
                error_msg = f"Erreur lors de l'exécution de la commande: {result.stderr or 'Code de retour non nul'}"
                logger.error(error_msg)
                return {"error": error_msg}
                
            if not result.stdout.strip():
                return []  # Empty output is valid for some commands
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            error_msg = "Le délai d'exécution de la commande a expiré"
            logger.error(error_msg)
            return {"error": error_msg}
            
        except FileNotFoundError:
            error_msg = "Ollama n'est pas installé sur le système"
            logger.error(error_msg)
            return {"error": error_msg}
            
        except subprocess.SubprocessError as e:
            error_msg = f"Erreur lors de l'exécution de la commande: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
            
        except Exception as e:
            error_msg = f"Erreur inattendue lors de l'exécution de la commande: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def list_running_models(self):
        """List running models using 'ollama ps' command"""
        try:
            logger.info("Fetching running models...")
            output = self._execute_command('ps')
            
            # Check if output is an error response
            if isinstance(output, dict) and "error" in output:
                error_msg = output["error"]
                logger.error(f"Failed to list running models: {error_msg}")
                return {
                    "models": [],
                    "error": error_msg
                }
            
            # Handle empty output
            if not output or (isinstance(output, list) and len(output) == 0):
                logger.info("No running models found")
                return {"models": []}

            # Parse the command output
            models = []
            # Skip first line (header) if output has content
            lines = output.splitlines()[1:] if isinstance(output, str) else []
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 1:
                    model_info = {
                        "name": parts[0],
                        "status": "en cours",
                        "size": 0  # Size not available in ps output
                    }
                    if len(parts) >= 2:
                        model_info["id"] = parts[1]
                    models.append(model_info)

            logger.info(f"Found {len(models)} running models")
            return {"models": models}
            
        except Exception as e:
            error_msg = f"Impossible de lister les modèles en cours d'exécution: {str(e)}"
            logger.error(f"Unexpected error in list_running_models: {str(e)}")
            return {
                "models": [],
                "error": error_msg
            }
