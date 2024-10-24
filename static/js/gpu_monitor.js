class GPUMonitor {
    constructor() {
        this.eventSource = new EventSource('/api/gpu/stats');
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.eventSource.onmessage = (event) => {
            const stats = JSON.parse(event.data);
            this.updateStats(stats);
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
            this.eventSource.close();
        };
    }

    updateStats(stats) {
        if (stats.error) {
            console.error('GPU Stats Error:', stats.error);
            return;
        }

        document.getElementById('gpu-utilization').textContent = 
            `${stats.gpu_utilization.toFixed(1)}%`;
        document.getElementById('memory-usage').textContent = 
            `${stats.memory_used.toFixed(0)} / ${stats.memory_total.toFixed(0)} MB`;
        document.getElementById('gpu-temp').textContent = 
            `${stats.temperature.toFixed(1)}°C`;
    }
}
