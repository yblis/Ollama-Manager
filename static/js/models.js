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

    async refreshModelsList() {
        try {
            const response = await fetch('/api/models');
            const data = await response.json();
            this.updateModelsList(data.models || []);
        } catch (error) {
            console.error('Failed to fetch models:', error);
        }
    }

    async pullModel(modelName) {
        try {
            const response = await fetch(`/api/models/pull/${modelName}`, {
                method: 'POST'
            });
            const result = await response.json();
            if (result.status === 'success') {
                this.refreshModelsList();
            }
        } catch (error) {
            console.error('Failed to pull model:', error);
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
            const result = await response.json();
            if (result.status === 'success') {
                this.refreshModelsList();
            }
        } catch (error) {
            console.error('Failed to delete model:', error);
        }
    }

    updateModelsList(models) {
        const tbody = document.getElementById('models-list');
        tbody.innerHTML = '';

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
