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

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            if (result.status === 'connected') {
                localStorage.setItem('ollamaServerUrl', serverUrl);
                this.serverUrl = serverUrl;
                this.updateConnectionStatus('success', 'Connexion établie avec succès');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.updateConnectionStatus('error', result.message || 'Échec de la connexion au serveur');
            }
        } catch (error) {
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

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.updateConnectionStatus(
                result.status === 'connected' ? 'success' : 'error',
                result.message || (result.status === 'connected' ? 'Connecté' : 'Déconnecté')
            );
        } catch (error) {
            this.updateConnectionStatus('error', `Erreur de vérification: ${error.message}`);
        }
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
