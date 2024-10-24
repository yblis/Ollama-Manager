import requests
from requests.exceptions import RequestException, ConnectionError
import time


class OllamaClient:

    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def _make_request(self, method, endpoint, json=None):
        """Make HTTP request with retries and proper error handling"""
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=f"{self.base_url}{endpoint}",
                    json=json,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
            except ConnectionError:
                error_msg = "Failed to connect to Ollama server - Please make sure Ollama is running"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return {"error": error_msg}
            except RequestException as e:
                error_msg = "Failed to connect to Ollama server"
                if hasattr(e, 'response') and e.response is not None:
                    error_msg += f": {e.response.text}"
                elif str(e):
                    error_msg += f": {str(e)}"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return {"error": error_msg}

    def list_models(self):
        """List all available models"""
        try:
            response = self._make_request("GET", "/api/tags")
            if "error" in response:
                return {"models": [], "error": response["error"]}
            return response
        except Exception as e:
            return {"models": [], "error": f"Failed to list models: {str(e)}"}

    def list_running_models(self):
        """List all currently running model instances"""
        try:
            response = self._make_request("GET", "/api/show")
            if "error" in response:
                return {"models": [], "error": response["error"]}
            
            models = []
            if response and isinstance(response, dict):
                for model_name, status in response.items():
                    models.append({
                        "name": model_name,
                        "status": "running" if status.get("status") == "ready" else status.get("status", "unknown")
                    })
            return {"models": models}
        except Exception as e:
            return {"models": [], "error": f"Failed to list running models: {str(e)}"}

    def stop_model(self, model_name):
        """Stop a running model instance"""
        try:
            response = self._make_request("POST", "/api/stop", json={"name": model_name})
            if "error" in response:
                return {"status": "error", "error": response["error"]}
            return {
                "status": "success",
                "message": f"Model {model_name} stopped successfully"
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to stop model {model_name}: {str(e)}"}

    def pull_model(self, model_name):
        """Pull a new model"""
        try:
            response = self._make_request("POST", "/api/pull", json={"name": model_name})
            if "error" in response:
                return {"status": "error", "error": response["error"]}
            return {
                "status": "success",
                "message": f"Model {model_name} pulled successfully"
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to pull model {model_name}: {str(e)}"}

    def delete_model(self, model_name):
        """Delete an existing model"""
        try:
            response = self._make_request("DELETE", "/api/delete", json={"name": model_name})
            if "error" in response:
                return {"status": "error", "error": response["error"]}
            return {
                "status": "success",
                "message": f"Model {model_name} deleted successfully"
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to delete model {model_name}: {str(e)}"}
