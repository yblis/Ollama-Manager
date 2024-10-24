class ModelManager {
    constructor() {
        this.setupEventListeners();
        this.refreshModelsList();
    }

    setupEventListeners() {
        document.getElementById('pull-model').addEventListener('click', () => {
            const modelName = document.getElementById('model-name').value.trim();
            if (modelName) {
                this.pullModel(modelName);
            }
        });
    }

    showError(message) {
        const modelsTable = document.getElementById('models-list').closest('.table-responsive');
        const existingAlert = modelsTable.previousElementSibling;
        if (existingAlert && existingAlert.classList.contains('alert')) {
            existingAlert.remove();
        }

        const alert = document.createElement('div');
        alert.className = 'alert alert-danger mb-3';
        alert.textContent = message;
        modelsTable.parentNode.insertBefore(alert, modelsTable);
        
        // Auto-hide after 5 seconds
        setTimeout(() => alert.remove(), 5000);
    }

    async refreshModelsList() {
        try {
            const response = await fetch('/api/models');
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            this.updateModelsList(data.models || []);
        } catch (error) {
            console.error('Failed to fetch models:', error);
            this.showError(`Failed to fetch models: ${error.message}`);
            this.updateModelsList([]);  // Clear the list on error
        }
    }

    async pullModel(modelName) {
        try {
            const response = await fetch(`/api/models/pull/${modelName}`, {
                method: 'POST'
            });
            if (!response.ok) {
                throw new Error(`Failed to pull model: ${response.statusText}`);
            }
            const result = await response.json();
            if (result.error) {
                throw new Error(result.error);
            }
            if (result.status === 'success') {
                this.refreshModelsList();
            }
        } catch (error) {
            console.error('Failed to pull model:', error);
            this.showError(`Failed to pull model ${modelName}: ${error.message}`);
        }
    }

    async deleteModel(modelName) {
        if (!confirm(`Are you sure you want to delete ${modelName}?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/models/delete/${modelName}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error(`Failed to delete model: ${response.statusText}`);
            }
            const result = await response.json();
            if (result.error) {
                throw new Error(result.error);
            }
            if (result.status === 'success') {
                this.refreshModelsList();
            }
        } catch (error) {
            console.error('Failed to delete model:', error);
            this.showError(`Failed to delete model ${modelName}: ${error.message}`);
        }
    }

    updateModelsList(models) {
        const tbody = document.getElementById('models-list');
        tbody.innerHTML = '';

        if (models.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="3" class="text-center text-muted">No models available</td>';
            tbody.appendChild(row);
            return;
        }

        models.forEach(model => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${model.name}</td>
                <td>${this.formatSize(model.size)}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="modelManager.deleteModel('${model.name}')">
                        Delete
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    formatSize(bytes) {
        const sizes = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        let size = bytes;
        while (size >= 1024 && i < sizes.length - 1) {
            size /= 1024;
            i++;
        }
        return `${size.toFixed(2)} ${sizes[i]}`;
    }
}
