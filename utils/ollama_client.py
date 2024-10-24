import requests

class OllamaClient:
    def __init__(self):
        self.base_url = "http://localhost:11434"

    def list_models(self):
        response = requests.get(f"{self.base_url}/api/tags")
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to list models: {response.text}")

    def pull_model(self, model_name):
        response = requests.post(
            f"{self.base_url}/api/pull",
            json={"name": model_name}
        )
        if response.status_code == 200:
            return {"status": "success", "message": f"Model {model_name} pulled successfully"}
        raise Exception(f"Failed to pull model: {response.text}")

    def delete_model(self, model_name):
        response = requests.delete(
            f"{self.base_url}/api/delete",
            json={"name": model_name}
        )
        if response.status_code == 200:
            return {"status": "success", "message": f"Model {model_name} deleted successfully"}
        raise Exception(f"Failed to delete model: {response.text}")
