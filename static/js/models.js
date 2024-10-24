class ModelManager {
    constructor() {
        this.setupEventListeners();
        this.refreshModelsList();
        this.refreshRunningModelsList();
        this.retryCount = 0;
        this.maxRetries = 3;
        this.retryDelay = 2000;
        this.retryMultiplier = 1.5;
        this.refreshInterval = setInterval(() => this.refreshRunningModelsList(), 5000);
    }

    setupEventListeners() {
        const pullButton = document.getElementById('pull-model');
        if (pullButton) {
            pullButton.addEventListener('click', () => {
                const modelName = document.getElementById('model-name')?.value?.trim();
                if (modelName) {
                    this.pullModel(modelName);
                } else {
                    this.showError(
                        {
                            message: "Veuillez entrer un nom de modèle valide",
                            code: "INVALID_INPUT"
                        },
                        document.getElementById('models-list'),
                        true
                    );
                }
            });
        }
    }

    showError(error, targetElement, isTransient = false) {
        if (!targetElement) return;
        
        const container = targetElement.closest('.table-responsive');
        if (!container) return;

        const existingAlert = container.previousElementSibling;
        if (existingAlert?.classList?.contains('alert')) {
            existingAlert.remove();
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${isTransient ? 'warning' : 'danger'} mb-3`;
        
        const errorMessage = this.formatErrorMessage(error);
        
        if (errorMessage.includes("n'est pas installé")) {
            alert.innerHTML = `
                <h5 class="alert-heading">Installation requise</h5>
                <p>${errorMessage}</p>
                <hr>
                <p class="mb-0">
                    Pour installer Ollama, suivez les instructions sur 
                    <a href="https://ollama.ai/download" target="_blank" class="alert-link">
                        le site officiel
                    </a>.
                </p>
            `;
        } else if (errorMessage.includes("n'est pas démarré")) {
            alert.innerHTML = `
                <h5 class="alert-heading">Service non démarré</h5>
                <p>${errorMessage}</p>
                <hr>
                <p class="mb-0">
                    Pour démarrer le service, exécutez la commande:
                    <code>ollama serve</code>
                </p>
            `;
        } else {
            if (error.code) {
                alert.innerHTML = `
                    <h5 class="alert-heading">${errorMessage}</h5>
                    <p class="mb-0">
                        <small class="text-muted">Code: ${error.code}</small>
                        ${error.details ? `<br><small class="text-muted">Détails: ${error.details}</small>` : ''}
                    </p>
                `;
            } else {
                alert.textContent = errorMessage;
            }
        }
        
        container.parentNode.insertBefore(alert, container);
        
        if (isTransient) {
            setTimeout(() => alert?.remove(), 5000);
        }
    }

    formatErrorMessage(error) {
        if (!error) return "Une erreur inattendue s'est produite";
        if (typeof error === 'string') return error;
        
        if (typeof error === 'object') {
            if (error.error && typeof error.error === 'object') {
                return error.error.message || "Une erreur inattendue s'est produite";
            }
            if (error.message) return error.message;
            
            const messages = Object.values(error).filter(v => v);
            return messages.length ? messages.join('. ') : "Une erreur inattendue s'est produite";
        }
        return "Une erreur inattendue s'est produite";
    }

    async retryOperation(operation, context) {
        const {
            baseErrorMessage,
            targetElement,
            maxRetries = this.maxRetries,
            initialDelay = this.retryDelay
        } = context;
        
        let retryCount = 0;
        let delay = initialDelay;

        while (retryCount < maxRetries) {
            try {
                console.log(`Attempting operation (try ${retryCount + 1}/${maxRetries})`);
                
                const response = await operation();
                if (!response) {
                    throw {
                        message: "Aucune réponse reçue du serveur",
                        code: "NO_RESPONSE"
                    };
                }
                
                const data = await response.json();
                if (!data) {
                    throw {
                        message: "Données de réponse vides",
                        code: "EMPTY_RESPONSE"
                    };
                }
                
                if (data.error) {
                    throw data.error;
                }
                
                return data;
            } catch (error) {
                retryCount++;
                console.error(
                    `Operation failed (attempt ${retryCount}/${maxRetries}):`,
                    error
                );
                
                const isLastAttempt = retryCount === maxRetries;
                const errorObj = {
                    message: baseErrorMessage,
                    code: error.code || "OPERATION_FAILED",
                    details: error.message || error.details || `Tentative ${retryCount}/${maxRetries}`
                };
                
                this.showError(errorObj, targetElement, !isLastAttempt);
                
                if (retryCount < maxRetries) {
                    console.log(`Waiting ${delay}ms before retry...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    delay *= this.retryMultiplier;
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
                {
                    baseErrorMessage: "Impossible de récupérer la liste des modèles",
                    targetElement: document.getElementById('models-list')
                }
            );
            
            this.updateModelsList(data.models || []);
            this.retryCount = 0;
        } catch (error) {
            console.error('Failed to fetch models:', error);
            this.updateModelsList([]);
        }
    }

    async refreshRunningModelsList() {
        try {
            const data = await this.retryOperation(
                () => fetch('/api/models/running'),
                {
                    baseErrorMessage: "Impossible de récupérer les modèles en cours d'exécution",
                    targetElement: document.getElementById('running-models-list')
                }
            );
            
            this.updateRunningModelsList(data.models || []);
            this.retryCount = 0;
        } catch (error) {
            console.error('Failed to fetch running models:', error);
            this.updateRunningModelsList([]);
        }
    }

    async pullModel(modelName) {
        if (!modelName) {
            this.showError(
                {
                    message: "Veuillez spécifier un nom de modèle",
                    code: "INVALID_INPUT"
                },
                document.getElementById('models-list'),
                true
            );
            return;
        }
        
        try {
            const data = await this.retryOperation(
                () => fetch(`/api/models/pull/${modelName}`, { method: 'POST' }),
                {
                    baseErrorMessage: `Impossible de télécharger le modèle ${modelName}`,
                    targetElement: document.getElementById('models-list')
                }
            );
            
            if (data.status === 'success') {
                this.refreshModelsList();
            }
        } catch (error) {
            console.error('Failed to pull model:', error);
        }
    }

    async stopModel(modelName) {
        if (!modelName) {
            this.showError(
                {
                    message: "Nom du modèle non spécifié",
                    code: "INVALID_INPUT"
                },
                document.getElementById('running-models-list'),
                true
            );
            return;
        }
        
        try {
            const data = await this.retryOperation(
                () => fetch(`/api/models/stop/${modelName}`, { method: 'POST' }),
                {
                    baseErrorMessage: `Impossible d'arrêter le modèle ${modelName}`,
                    targetElement: document.getElementById('running-models-list')
                }
            );
            
            if (data.status === 'success') {
                this.refreshRunningModelsList();
            }
        } catch (error) {
            console.error('Failed to stop model:', error);
        }
    }

    async deleteModel(modelName) {
        if (!modelName || !confirm(`Êtes-vous sûr de vouloir supprimer ${modelName}?`)) {
            return;
        }

        try {
            const data = await this.retryOperation(
                () => fetch(`/api/models/delete/${modelName}`, { method: 'DELETE' }),
                {
                    baseErrorMessage: `Impossible de supprimer le modèle ${modelName}`,
                    targetElement: document.getElementById('models-list')
                }
            );
            
            if (data.status === 'success') {
                this.refreshModelsList();
            }
        } catch (error) {
            console.error('Failed to delete model:', error);
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

        if (!Array.isArray(models)) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="3" class="text-center text-muted">Erreur lors de la récupération des modèles</td>';
            tbody.appendChild(row);
            return;
        }

        if (models.length === 0) {
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
                <td>
                    <span class="badge bg-success">
                        ${model.id ? `En cours (${model.id})` : 'En cours'}
                    </span>
                </td>
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