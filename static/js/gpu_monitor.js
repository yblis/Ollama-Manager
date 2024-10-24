class GPUMonitor {
    constructor() {
        this.maxRetries = 3;
        this.retryDelay = 2000; // 2 seconds
        this.retryCount = 0;
        this.connectSSE();
    }

    connectSSE() {
        this.eventSource = new EventSource('/api/gpu/stats');
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.eventSource.onmessage = (event) => {
            const stats = JSON.parse(event.data);
            this.updateStats(stats);
            // Reset retry count on successful connection
            this.retryCount = 0;
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
            this.eventSource.close();
            
            this.showError("GPU monitoring connection lost");
            
            // Attempt to reconnect if under max retries
            if (this.retryCount < this.maxRetries) {
                this.retryCount++;
                setTimeout(() => {
                    console.log(`Attempting to reconnect (${this.retryCount}/${this.maxRetries})...`);
                    this.connectSSE();
                }, this.retryDelay);
            } else {
                this.showError("GPU monitoring failed. Please refresh the page to try again.");
            }
        };
    }

    showError(message) {
        const gpuCard = document.querySelector('.gpu-stat').closest('.card');
        const existingAlert = gpuCard.querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }

        const alert = document.createElement('div');
        alert.className = 'alert alert-warning mx-3 mb-3';
        alert.textContent = message;
        gpuCard.querySelector('.card-body').insertBefore(alert, gpuCard.querySelector('.row'));
    }

    updateStats(stats) {
        // Clear any previous error messages
        const existingAlert = document.querySelector('.gpu-stat').closest('.card').querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }

        if (stats.status === 'no_gpu') {
            this.showNoGPU(stats.message);
            return;
        }

        if (stats.status === 'error' || stats.status === 'timeout') {
            this.showError(stats.message);
            this.showNoData();
            return;
        }

        document.getElementById('gpu-utilization').textContent = 
            `${stats.gpu_utilization.toFixed(1)}%`;
        document.getElementById('memory-usage').textContent = 
            `${stats.memory_used.toFixed(0)} / ${stats.memory_total.toFixed(0)} MB`;
        document.getElementById('gpu-temp').textContent = 
            `${stats.temperature.toFixed(1)}°C`;
    }

    showNoGPU(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-info mx-3 mb-3';
        alert.textContent = message;
        const gpuCard = document.querySelector('.gpu-stat').closest('.card');
        gpuCard.querySelector('.card-body').insertBefore(alert, gpuCard.querySelector('.row'));
        this.showNoData();
    }

    showNoData() {
        document.getElementById('gpu-utilization').textContent = '---%';
        document.getElementById('memory-usage').textContent = '--- / --- MB';
        document.getElementById('gpu-temp').textContent = '---°C';
    }
}
