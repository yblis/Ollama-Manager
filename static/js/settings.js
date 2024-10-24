class SettingsManager {
    constructor() {
        this.serverUrl = localStorage.getItem('ollamaServerUrl') || 'http://localhost:11434';
        this.setupEventListeners();
        this.loadSettings();
    }

    setupEventListeners() {
        document.getElementById('settingsModal').addEventListener('show.bs.modal', () => {
            this.loadSettings();
        });

        document.getElementById('saveSettings').addEventListener('click', () => {
            this.saveSettings();
        });

        document.getElementById('serverUrl').addEventListener('input', () => {
            this.checkConnection();
        });
    }

    loadSettings() {
        document.getElementById('serverUrl').value = this.serverUrl;
        this.checkConnection();
    }

    async saveSettings() {
        const serverUrl = document.getElementById('serverUrl').value.trim();
        if (!serverUrl) {
            this.updateConnectionStatus('error', 'L\'URL du serveur ne peut pas être vide');
            return;
        }

        try {
            const response = await fetch('/api/settings/server', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: serverUrl })
            });

            let result;
            try {
                result = await response.json();
            } catch (e) {
                throw new Error('Format de réponse invalide');
            }

            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Service non disponible');
                }
                throw new Error(result.error?.message || `Erreur ${response.status}`);
            }

            if (result.error) {
                this.updateConnectionStatus('error', result.error.message);
                if (result.error.code === "INSTALLATION_ERROR") {
                    this.showInstallationInstructions();
                    return;
                }
                return;
            }

            if (result.status === 'connected') {
                localStorage.setItem('ollamaServerUrl', serverUrl);
                this.serverUrl = serverUrl;
                this.updateConnectionStatus('success', 'Connexion établie avec succès');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.updateConnectionStatus('error', result.error?.message || 'Échec de la connexion au serveur');
            }
        } catch (error) {
            console.error('Settings update failed:', error);
            this.updateConnectionStatus('error', `Erreur: ${error.message}`);
        }
    }

    async checkConnection() {
        const serverUrl = document.getElementById('serverUrl').value.trim();
        if (!serverUrl) {
            this.updateConnectionStatus('warning', 'Veuillez saisir l\'URL du serveur');
            return;
        }

        try {
            const response = await fetch('/api/settings/check', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: serverUrl })
            });

            let result;
            try {
                result = await response.json();
            } catch (e) {
                throw new Error('Format de réponse invalide');
            }

            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Service de vérification non disponible');
                }
                throw new Error(result.error?.message || `Erreur ${response.status}`);
            }

            if (result.error) {
                this.updateConnectionStatus('error', result.error.message);
                if (result.error.code === "INSTALLATION_ERROR") {
                    this.showInstallationInstructions();
                    return;
                }
                return;
            }

            this.updateConnectionStatus(
                result.status === 'connected' ? 'success' : 'error',
                result.status === 'connected' ? 
                    `Connecté au serveur ${result.version || ''}` : 
                    result.error?.message || 'Échec de la connexion'
            );
        } catch (error) {
            console.error('Connection check failed:', error);
            this.updateConnectionStatus('error', `Erreur: ${error.message}`);
        }
    }

    showInstallationInstructions() {
        const statusDiv = document.getElementById('connectionStatus');
        statusDiv.className = 'alert alert-warning';
        statusDiv.innerHTML = `
            <h5 class="alert-heading">Installation d'Ollama requise</h5>
            <p>Le service Ollama n'est pas installé sur le système.</p>
            <hr>
            <p class="mb-0">
                Pour installer Ollama, suivez les instructions sur 
                <a href="https://ollama.ai/download" target="_blank" class="alert-link">
                    le site officiel d'Ollama
                </a>
            </p>
        `;
    }

    updateConnectionStatus(type, message) {
        const statusDiv = document.getElementById('connectionStatus');
        statusDiv.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'warning'}`;
        statusDiv.textContent = message;
    }
}

// Initialize settings manager
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
});
