class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
        this.credentials = null;
    }

    setCredentials(username, password) {
        this.credentials = btoa(`${username}:${password}`);
    }

    clearCredentials() {
        this.credentials = null;
    }

    async request(endpoint, options = {}) {
        if (!this.credentials) {
            throw new ApiError('Authentication required', 401);
        }

        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Authorization': `Basic ${this.credentials}`,
            ...options.headers
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new ApiError(error.detail || `HTTP error ${response.status}`, response.status);
            }

            // Handle streaming responses
            const contentType = response.headers.get('Content-Type');
            if (contentType && contentType.includes('text/event-stream')) {
                return response;
            }

            // Parse JSON response
            return await response.json();
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError(error.message, 500);
        }
    }

    // Auth endpoints
    async verifyAuth(username, password) {
        this.setCredentials(username, password);
        try {
            await this.request('/auth/verify');
            return true;
        } catch (error) {
            this.clearCredentials();
            throw error;
        }
    }

    // Advisor endpoints
    async listAdvisors() {
        return this.request('/advisors');
    }

    async getAdvisor(name) {
        return this.request(`/advisors/${name}`);
    }

    async createAdvisor(data) {
        return this.request('/advisors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    }

    async updateAdvisor(name, data) {
        // Ensure gateway is included in advisor data if specified
        return this.request(`/advisors/${name}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    }

    // Chat endpoints
    async listChats(advisorId) {
        return this.request(`/chat/advisor/${advisorId}/history`);
    }

    async getChat(chatId) {
        return this.request(`/chat/${chatId}`);
    }

    async getArchivedChats() {
        return this.request('/chat/archived');
    }

    async getArchivedChat(chatId) {
        return this.request(`/chat/archived/${chatId}`);
    }

    async getChatHistory(advisorId) {
        return this.request(`/chat/advisor/${advisorId}/history`);
    }

    async deleteChat(chatId) {
        return this.request(`/chat/${chatId}`, {
            method: 'DELETE'
        });
    }

    async createChat(advisorId) {
        return this.request(`/chat/advisor/${advisorId}/new`, {
            method: 'POST'
        });
    }

    async sendMessage(chatId, message, gateway = null) {
        const body = { message };
        if (gateway) {
            body.gateway = gateway;
        }
        
        return this.request(`/chat/${chatId}/message`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify(body)
        });
    }

    async cancelStream(chatId) {
        return this.request(`/chat/${chatId}/cancel`, {
            method: 'POST'
        });
    }

    // File endpoints
    async listFiles() {
        return this.request('/files');
    }

    async uploadFile(file, path = '') {
        const formData = new FormData();
        formData.append('file', file);
        
        return this.request(`/files/${path}`, {
            method: 'POST',
            body: formData
        });
    }

    async createDirectory(path) {
        return this.request(`/files/${path}`, {
            method: 'POST'
        });
    }

    async getFile(path) {
        return this.request(`/files/${path}`);
    }

    async updateFile(path, content) {
        return this.request(`/files/${path}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
    }

    async deleteFile(path) {
        return this.request(`/files/${path}`, {
            method: 'DELETE'
        });
    }
}

// Export singleton instance
export const api = new ApiClient();
