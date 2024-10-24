import requests
from requests.exceptions import RequestException
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
            except RequestException as e:
                if attempt == self.max_retries - 1:
                    error_msg = "Failed to connect to Ollama server"
                    if hasattr(e.response, 'text'):
                        error_msg += f": {e.response.text}"
                    elif str(e):
                        error_msg += f": {str(e)}"
                    raise Exception(error_msg)
                time.sleep(self.retry_delay)

    def list_models(self):
        """List all available models"""
        try:
            response = self._make_request("GET", "/api/tags")
            return response
        except Exception as e:
            raise Exception(f"Failed to list models: {str(e)}")

    def pull_model(self, model_name):
        """Pull a new model"""
        try:
            self._make_request("POST", "/api/pull", json={"name": model_name})
            return {
                "status": "success",
                "message": f"Model {model_name} pulled successfully"
            }
        except Exception as e:
            raise Exception(f"Failed to pull model {model_name}: {str(e)}")

    def delete_model(self, model_name):
        """Delete an existing model"""
        try:
            self._make_request("DELETE", "/api/delete", json={"name": model_name})
            return {
                "status": "success",
                "message": f"Model {model_name} deleted successfully"
            }
        except Exception as e:
            raise Exception(f"Failed to delete model {model_name}: {str(e)}")
