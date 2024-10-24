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
                        document.getElementById('models-list')
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
        const errorType = this.getErrorType(error);
        
        alert.className = `alert ${errorType.alertClass} mb-3`;
        alert.innerHTML = `
            <h5 class="alert-heading">${errorType.title}</h5>
            <p>${error.message}</p>
            ${errorType.extraContent || ''}
            ${error.details ? `<hr><small class="text-muted">${error.details}</small>` : ''}
        `;
        
        container.parentNode.insertBefore(alert, container);
        
        if (isTransient && !errorType.persistent) {
            setTimeout(() => alert?.remove(), 5000);
        }
    }

    getErrorType(error) {
        switch(error.code) {
            case "INSTALLATION_ERROR":
                return {
                    alertClass: 'alert-danger',
                    title: "Installation d'Ollama requise",
                    extraContent: `
                        <hr>
                        <p class="mb-0">
                            Pour installer Ollama, suivez les instructions sur 
                            <a href="https://ollama.ai/download" target="_blank" class="alert-link">
                                le site officiel d'Ollama
                            </a>
                        </p>
                    `,
                    persistent: true
                };
            
            case "SERVICE_NOT_RUNNING":
            case "CONNECTION_ERROR":
                return {
                    alertClass: 'alert-warning',
                    title: "Service Ollama non démarré",
                    extraContent: `
                        <hr>
                        <p class="mb-0">
                            Pour démarrer le service, exécutez la commande:
                            <code>ollama serve</code>
                        </p>
                    `,
                    persistent: true
                };
            
            case "TIMEOUT_ERROR":
                return {
                    alertClass: 'alert-warning',
                    title: "Délai d'attente dépassé",
                    persistent: false
                };
            
            default:
                return {
                    alertClass: 'alert-danger',
                    title: error.message || "Une erreur s'est produite",
                    persistent: false
                };
        }
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
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw {
                        message: errorData.error?.message || "Erreur de communication avec le serveur",
                        code: errorData.error?.code || "SERVER_ERROR",
                        details: errorData.error?.details
                    };
                }
                
                const data = await response.json();
                if (data.error) {
                    // Don't retry for certain errors
                    if (["INSTALLATION_ERROR", "SERVICE_NOT_RUNNING"].includes(data.error.code)) {
                        this.showError(data.error, targetElement);
                        throw data.error;
                    }
                    throw data.error;
                }
                
                return data;
            } catch (error) {
                console.error(`Operation failed (attempt ${retryCount + 1}/${maxRetries}):`, error);
                
                // Don't retry for certain errors
                if (["INSTALLATION_ERROR", "SERVICE_NOT_RUNNING"].includes(error.code)) {
                    this.showError(error, targetElement);
                    throw error;
                }
                
                retryCount++;
                const isLastAttempt = retryCount === maxRetries;
                
                const retryError = {
                    ...error,
                    message: error.message || baseErrorMessage,
                    details: !isLastAttempt ? 
                        `Tentative ${retryCount}/${maxRetries}. Nouvelle tentative dans ${delay/1000}s...` :
                        error.details
                };
                
                this.showError(retryError, targetElement, !isLastAttempt);
                
                if (retryCount < maxRetries) {
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
        } catch (error) {
            console.error('Failed to fetch models:', error);
            // Don't clear the list for certain errors
            if (!["INSTALLATION_ERROR", "SERVICE_NOT_RUNNING"].includes(error.code)) {
                this.updateModelsList([]);
            }
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
        } catch (error) {
            console.error('Failed to fetch running models:', error);
            // Don't clear the list for certain errors
            if (!["INSTALLATION_ERROR", "SERVICE_NOT_RUNNING"].includes(error.code)) {
                this.updateRunningModelsList([]);
            }
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
