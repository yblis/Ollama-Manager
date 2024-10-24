class BenchmarkManager {
    constructor() {
        this.activeBenchmarks = new Set();
        this.refreshBenchmarks();
        // Refresh benchmark results every 5 seconds
        setInterval(() => this.refreshBenchmarks(), 5000);
    }

    showError(message, targetElement) {
        const container = targetElement.closest('.table-responsive');
        const existingAlert = container.previousElementSibling;
        if (existingAlert && existingAlert.classList.contains('alert')) {
            existingAlert.remove();
        }

        const alert = document.createElement('div');
        alert.className = 'alert alert-danger mb-3';
        alert.textContent = message;
        container.parentNode.insertBefore(alert, container);
        
        // Auto-hide after 5 seconds
        setTimeout(() => alert.remove(), 5000);
    }

    async startBenchmark(modelName) {
        if (this.activeBenchmarks.has(modelName)) {
            this.showError(`Un benchmark est déjà en cours pour le modèle ${modelName}`, document.getElementById('benchmark-results-list'));
            return;
        }

        try {
            const response = await fetch(`/api/models/benchmark/${modelName}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`Erreur serveur: ${response.status}`);
            }
            
            const result = await response.json();
            if (result.error) {
                throw new Error(result.error);
            }
            
            this.activeBenchmarks.add(modelName);
            this.refreshBenchmarks();
        } catch (error) {
            console.error('Failed to start benchmark:', error);
            this.showError(`Impossible de démarrer le benchmark pour ${modelName}: ${error.message}`, document.getElementById('benchmark-results-list'));
        }
    }

    async refreshBenchmarks() {
        try {
            const response = await fetch('/api/models/benchmark/results');
            if (!response.ok) {
                throw new Error(`Erreur serveur: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.updateBenchmarksList(data.results || [], data.active_benchmarks || []);
        } catch (error) {
            console.error('Failed to fetch benchmark results:', error);
            this.showError(`Impossible de récupérer les résultats: ${error.message}`, document.getElementById('benchmark-results-list'));
        }
    }

    calculateAverageMetrics(metrics) {
        if (!Array.isArray(metrics) || metrics.length === 0) return { cpu: 0, memory: 0 };
        
        const sum = metrics.reduce((acc, metric) => ({
            cpu: acc.cpu + (metric.cpu_percent || 0),
            memory: acc.memory + (metric.memory_percent || 0)
        }), { cpu: 0, memory: 0 });
        
        return {
            cpu: (sum.cpu / metrics.length).toFixed(1),
            memory: (sum.memory / metrics.length).toFixed(1)
        };
    }

    updateBenchmarksList(results, activeBenchmarks) {
        const tbody = document.getElementById('benchmark-results-list');
        if (!tbody) return;
        
        tbody.innerHTML = '';

        if (!Array.isArray(results) || !Array.isArray(activeBenchmarks) || 
            (results.length === 0 && activeBenchmarks.length === 0)) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="6" class="text-center text-muted">Aucun résultat de benchmark disponible</td>';
            tbody.appendChild(row);
            return;
        }

        // Add active benchmarks
        activeBenchmarks.forEach(modelName => {
            if (typeof modelName !== 'string') return;
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${modelName}</td>
                <td colspan="3" class="text-center">
                    <div class="spinner-border spinner-border-sm text-secondary" role="status">
                        <span class="visually-hidden">Benchmark en cours...</span>
                    </div>
                </td>
                <td><span class="badge bg-warning">En cours</span></td>
                <td>-</td>
            `;
            tbody.appendChild(row);
        });

        // Add completed benchmarks
        results.forEach(result => {
            if (!result || typeof result !== 'object') return;
            
            const avgMetrics = this.calculateAverageMetrics(result.metrics || []);
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${result.model || 'Unknown'}</td>
                <td>${(result.elapsed_time || 0).toFixed(2)}s</td>
                <td>${avgMetrics.cpu}%</td>
                <td>${avgMetrics.memory}%</td>
                <td>
                    <span class="badge ${result.success ? 'bg-success' : 'bg-danger'}">
                        ${result.success ? 'Succès' : 'Échec'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="benchmarkManager.startBenchmark('${result.model}')">
                        Relancer
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }
}
