class GPUMonitor {
    constructor() {
        this.maxRetries = 3;
        this.retryDelay = 2000; // 2 seconds
        this.retryCount = 0;
        this.eventSource = null;
        this.isConnecting = false;
        this.connectSSE();
    }

    connectSSE() {
        if (this.isConnecting) return;
        
        try {
            this.isConnecting = true;
            if (this.eventSource) {
                this.eventSource.close();
            }

            this.eventSource = new EventSource('/api/gpu/stats');
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to create SSE connection:', error);
            this.handleConnectionError(error);
        } finally {
            this.isConnecting = false;
        }
    }

    setupEventListeners() {
        if (!this.eventSource) return;

        this.eventSource.onmessage = (event) => {
            try {
                const stats = JSON.parse(event.data);
                this.updateStats(stats);
                // Reset retry count on successful connection
                this.retryCount = 0;
            } catch (error) {
                console.error('Error processing SSE message:', error);
                this.showError("Erreur de traitement des données GPU");
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
            this.handleConnectionError(error);
        };

        this.eventSource.onopen = () => {
            console.log('SSE connection established');
            this.retryCount = 0;
            // Clear any previous error messages
            const existingAlert = document.querySelector('.gpu-stat').closest('.card').querySelector('.alert');
            if (existingAlert) {
                existingAlert.remove();
            }
        };
    }

    handleConnectionError(error) {
        this.eventSource?.close();
        
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            this.showError(`Connexion au moniteur GPU perdue - Tentative ${this.retryCount}/${this.maxRetries}...`);
            
            setTimeout(() => {
                console.log(`Attempting to reconnect (${this.retryCount}/${this.maxRetries})...`);
                this.connectSSE();
            }, this.retryDelay);
        } else {
            this.showError("La surveillance GPU a échoué. Actualisez la page pour réessayer.");
        }
    }

    showError(message) {
        const gpuCard = document.querySelector('.gpu-stat')?.closest('.card');
        if (!gpuCard) return;

        const existingAlert = gpuCard.querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }

        const alert = document.createElement('div');
        alert.className = 'alert alert-warning mx-3 mb-3';
        alert.textContent = message;
        
        const cardBody = gpuCard.querySelector('.card-body');
        if (cardBody) {
            cardBody.insertBefore(alert, cardBody.querySelector('.row'));
        }
    }

    updateStats(stats) {
        if (!stats) return;

        // Clear any previous error messages
        const existingAlert = document.querySelector('.gpu-stat')?.closest('.card')?.querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }

        if (stats.status === 'no_gpu') {
            this.showNoGPU(stats.message || "Aucun GPU NVIDIA détecté");
            return;
        }

        if (stats.status === 'error' || stats.status === 'timeout') {
            this.showError(stats.message || "Erreur de surveillance GPU");
            this.showNoData();
            return;
        }

        const utilizationEl = document.getElementById('gpu-utilization');
        const memoryEl = document.getElementById('memory-usage');
        const tempEl = document.getElementById('gpu-temp');

        if (utilizationEl) {
            utilizationEl.textContent = Number.isFinite(stats.gpu_utilization) ? 
                `${stats.gpu_utilization.toFixed(1)}%` : '---';
        }
        
        if (memoryEl) {
            memoryEl.textContent = Number.isFinite(stats.memory_used) && Number.isFinite(stats.memory_total) ?
                `${stats.memory_used.toFixed(0)} / ${stats.memory_total.toFixed(0)} MB` : '--- / --- MB';
        }
        
        if (tempEl) {
            tempEl.textContent = Number.isFinite(stats.temperature) ?
                `${stats.temperature.toFixed(1)}°C` : '---°C';
        }
    }

    showNoGPU(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-info mx-3 mb-3';
        alert.textContent = message;
        
        const gpuCard = document.querySelector('.gpu-stat')?.closest('.card');
        if (gpuCard) {
            const cardBody = gpuCard.querySelector('.card-body');
            if (cardBody) {
                cardBody.insertBefore(alert, cardBody.querySelector('.row'));
            }
        }
        this.showNoData();
    }

    showNoData() {
        const elements = {
            'gpu-utilization': '---%',
            'memory-usage': '--- / --- MB',
            'gpu-temp': '---°C'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }
}
