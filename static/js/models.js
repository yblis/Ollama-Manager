class ModelManager {
    constructor() {
        this.setupEventListeners();
        this.refreshModelsList();
        this.refreshRunningModelsList();
        this.retryCount = 0;
        this.maxRetries = 3;
        this.retryDelay = 2000; // 2 seconds
        this.retryMultiplier = 1.5; // Exponential backoff multiplier
        // Refresh running models list every 5 seconds
        this.refreshInterval = setInterval(() => this.refreshRunningModelsList(), 5000);
    }

    setupEventListeners() {
        const pullButton = document.getElementById('pull-model');
        if (pullButton) {
            pullButton.addEventListener('click', () => {
                const modelName = document.getElementById('model-name')?.value?.trim();
                if (modelName) {
                    this.pullModel(modelName);
                }
            });
        }
    }

    showError(message, targetElement, isTransient = false) {
        if (!targetElement) return;
        
        const container = targetElement.closest('.table-responsive');
        if (!container) return;

        const existingAlert = container.previousElementSibling;
        if (existingAlert?.classList?.contains('alert')) {
            existingAlert.remove();
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${isTransient ? 'warning' : 'danger'} mb-3`;
        alert.textContent = message || "Une erreur inattendue s'est produite";
        container.parentNode.insertBefore(alert, container);
        
        if (isTransient) {
            setTimeout(() => alert?.remove(), 5000);
        }
    }

    getErrorMessage(error, defaultMessage = "Une erreur s'est produite") {
        if (!error) return defaultMessage;
        if (typeof error === 'string') return error;
        if (error.message) return error.message;
        if (typeof error === 'object') {
            return Object.values(error).filter(v => v).join('. ') || defaultMessage;
        }
        return defaultMessage;
    }

    async retryOperation(operation, errorMessage, targetElement) {
        let retryCount = 0;
        const maxRetries = this.maxRetries;
        let retryDelay = this.retryDelay;

        while (retryCount < maxRetries) {
            try {
                const response = await operation();
                if (!response) {
                    throw new Error("Aucune réponse reçue du serveur");
                }
                
                if (response.ok) {
                    const data = await response.json();
                    if (!data) {
                        throw new Error("Données de réponse vides");
                    }
                    return data;
                }
                
                if (response.status === 404) {
                    throw new Error("Service non disponible. Veuillez vérifier la configuration du serveur.");
                }
                
                throw new Error(`Le serveur a répondu avec le statut: ${response.status}`);
            } catch (error) {
                retryCount++;
                console.error(`Tentative ${retryCount}/${maxRetries} échouée:`, error);
                
                if (retryCount < maxRetries) {
                    const errorMsg = this.getErrorMessage(error);
                    this.showError(
                        `${errorMessage} - Tentative ${retryCount}/${maxRetries}... (${errorMsg})`, 
                        targetElement, 
                        true
                    );
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                    retryDelay *= this.retryMultiplier; // Exponential backoff
                    continue;
                }
                throw error;
            }
        }
    }

    async refreshModelsList() {
        try {
            const data = await this.retryOperation(
                () => fetch('/api/models'),
                "Tentative de reconnexion aux modèles",
                document.getElementById('models-list')
            );
            
            if (!data) {
                throw new Error("Aucune donnée reçue du serveur");
            }

            if (data.error) {
                const errorMsg = this.getErrorMessage(data.error);
                throw new Error(errorMsg);
            }
            this.updateModelsList(data.models || []);
            this.retryCount = 0;
        } catch (error) {
            console.error('Failed to fetch models:', error);
            const errorMsg = this.getErrorMessage(error);
            this.showError(
                `Impossible de récupérer les modèles: ${errorMsg}`,
                document.getElementById('models-list')
            );
            this.updateModelsList([]);
        }
    }

    async refreshRunningModelsList() {
        try {
            const data = await this.retryOperation(
                () => fetch('/api/models/running'),
                "Tentative de reconnexion aux modèles en cours d'exécution",
                document.getElementById('running-models-list')
            );
            
            if (!data) {
                throw new Error("Aucune donnée reçue du serveur");
            }

            if (data.error) {
                const errorMsg = this.getErrorMessage(data.error);
                throw new Error(errorMsg);
            }

            this.updateRunningModelsList(data.models || []);
            this.retryCount = 0;
        } catch (error) {
            console.error('Failed to fetch running models:', error);
            const errorMsg = this.getErrorMessage(error);
            this.showError(
                `Impossible de récupérer les modèles en cours d'exécution: ${errorMsg}`,
                document.getElementById('running-models-list')
            );
            this.updateRunningModelsList([]);
        }
    }

    async pullModel(modelName) {
        if (!modelName) return;
        
        try {
            const data = await this.retryOperation(
                () => fetch(`/api/models/pull/${modelName}`, { method: 'POST' }),
                `Tentative de téléchargement du modèle ${modelName}`,
                document.getElementById('models-list')
            );
            
            if (!data || data.error) {
                const errorMsg = this.getErrorMessage(data?.error);
                throw new Error(errorMsg);
            }
            if (data.status === 'success') {
                this.refreshModelsList();
            }
        } catch (error) {
            console.error('Failed to pull model:', error);
            const errorMsg = this.getErrorMessage(error);
            this.showError(
                `Impossible de télécharger le modèle ${modelName}: ${errorMsg}`,
                document.getElementById('models-list')
            );
        }
    }

    async stopModel(modelName) {
        if (!modelName) return;
        
        try {
            const data = await this.retryOperation(
                () => fetch(`/api/models/stop/${modelName}`, { method: 'POST' }),
                `Tentative d'arrêt du modèle ${modelName}`,
                document.getElementById('running-models-list')
            );
            
            if (!data || data.error) {
                const errorMsg = this.getErrorMessage(data?.error);
                throw new Error(errorMsg);
            }
            if (data.status === 'success') {
                this.refreshRunningModelsList();
            }
        } catch (error) {
            console.error('Failed to stop model:', error);
            const errorMsg = this.getErrorMessage(error);
            this.showError(
                `Impossible d'arrêter le modèle ${modelName}: ${errorMsg}`,
                document.getElementById('running-models-list')
            );
        }
    }

    async deleteModel(modelName) {
        if (!modelName || !confirm(`Êtes-vous sûr de vouloir supprimer ${modelName}?`)) {
            return;
        }

        try {
            const data = await this.retryOperation(
                () => fetch(`/api/models/delete/${modelName}`, { method: 'DELETE' }),
                `Tentative de suppression du modèle ${modelName}`,
                document.getElementById('models-list')
            );
            
            if (!data || data.error) {
                const errorMsg = this.getErrorMessage(data?.error);
                throw new Error(errorMsg);
            }
            if (data.status === 'success') {
                this.refreshModelsList();
            }
        } catch (error) {
            console.error('Failed to delete model:', error);
            const errorMsg = this.getErrorMessage(error);
            this.showError(
                `Impossible de supprimer le modèle ${modelName}: ${errorMsg}`,
                document.getElementById('models-list')
            );
        }
    }

    updateModelsList(models) {
        const tbody = document.getElementById('models-list');
        if (!tbody) return;
        
        tbody.innerHTML = '';

        if (!Array.isArray(models) || models.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="3" class="text-center text-muted">Aucun modèle disponible</td>';
            tbody.appendChild(row);
            return;
        }

        models.forEach(model => {
            if (!model?.name) return;
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${model.name}</td>
                <td>${this.formatSize(model.size || 0)}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-secondary" onclick="benchmarkManager.startBenchmark('${model.name}')">
                            Benchmark
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="modelManager.deleteModel('${model.name}')">
                            Supprimer
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    updateRunningModelsList(models) {
        const tbody = document.getElementById('running-models-list');
        if (!tbody) return;
        
        tbody.innerHTML = '';

        if (!Array.isArray(models) || models.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="3" class="text-center text-muted">Aucun modèle en cours d\'exécution</td>';
            tbody.appendChild(row);
            return;
        }

        models.forEach(model => {
            if (!model?.name) return;
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${model.name}</td>
                <td><span class="badge bg-success">${model.status || 'en cours'}</span></td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-secondary" onclick="benchmarkManager.startBenchmark('${model.name}')">
                            Benchmark
                        </button>
                        <button class="btn btn-sm btn-warning" onclick="modelManager.stopModel('${model.name}')">
                            Arrêter
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    formatSize(bytes) {
        if (typeof bytes !== 'number' || isNaN(bytes)) {
            return '0 B';
        }
        
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