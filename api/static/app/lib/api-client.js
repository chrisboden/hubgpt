// API Client for HubGPT
const API_BASE = '/api/v1';

class ApiClient {
    constructor() {
        this.authToken = localStorage.getItem('authToken');
    }

    // Helper to get auth headers
    getHeaders(additionalHeaders = {}) {
        const headers = {
            ...additionalHeaders
        };

        // Add JWT token if available
        if (this.authToken) {
            headers.Authorization = `Bearer ${this.authToken}`;
        } else {
            // Fallback to basic auth if stored
            const basicAuth = localStorage.getItem('basicAuth');
            if (basicAuth) {
                headers.Authorization = `Basic ${basicAuth}`;
            }
        }

        return headers;
    }

    // Auth Methods
    async register(username, password, email) {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password, email })
        });

        if (!response.ok) {
            throw new Error('Registration failed');
        }

        return response.json();
    }

    async login(username, password) {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            throw new Error('Login failed');
        }

        const data = await response.json();
        this.authToken = data.access_token;
        localStorage.setItem('authToken', this.authToken);
        return data;
    }

    async logout() {
        const response = await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Logout failed');
        }

        this.authToken = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('basicAuth');
    }

    async verifyAuth() {
        const response = await fetch(`${API_BASE}/verify`, {
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Auth verification failed');
        }

        return response.json();
    }

    // Advisor Methods
    async getAdvisors() {
        const response = await fetch(`${API_BASE}/advisors`, {
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to fetch advisors');
        }

        return response.json();
    }

    async getAdvisor(advisorId) {
        const response = await fetch(`${API_BASE}/advisors/${advisorId}`, {
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to fetch advisor');
        }

        return response.json();
    }

    async createAdvisor(advisorData) {
        const response = await fetch(`${API_BASE}/advisors`, {
            method: 'POST',
            headers: this.getHeaders({
                'Content-Type': 'application/json'
            }),
            body: JSON.stringify(advisorData)
        });

        if (!response.ok) {
            throw new Error('Failed to create advisor');
        }

        return response.json();
    }

    async updateAdvisor(advisorId, advisorData) {
        const response = await fetch(`${API_BASE}/advisors/${advisorId}`, {
            method: 'PUT',
            headers: this.getHeaders({
                'Content-Type': 'application/json'
            }),
            body: JSON.stringify(advisorData)
        });

        if (!response.ok) {
            throw new Error('Failed to update advisor');
        }

        return response.json();
    }

    async deleteAdvisor(advisorId) {
        const response = await fetch(`${API_BASE}/advisors/${advisorId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to delete advisor');
        }
    }

    // Chat Methods
    async createChat(advisorId) {
        const response = await fetch(`${API_BASE}/chat/advisor/${advisorId}/new`, {
            method: 'POST',
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to create chat');
        }

        return response.json();
    }

    async getChatHistory(advisorId) {
        const response = await fetch(`${API_BASE}/chat/advisor/${advisorId}/history`, {
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to fetch chat history');
        }

        return response.json();
    }

    async getMessages(chatId) {
        const response = await fetch(`${API_BASE}/chat/messages/${chatId}`, {
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to fetch messages');
        }

        return response.json();
    }

    async sendMessage(chatId, message, signal) {
        const response = await fetch(`${API_BASE}/chat/${chatId}/message`, {
            method: 'POST',
            headers: this.getHeaders({
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            }),
            body: JSON.stringify({ message }),
            signal
        });

        if (!response.ok) {
            throw new Error('Failed to send message');
        }

        return response;
    }

    async cancelMessage(chatId) {
        const response = await fetch(`${API_BASE}/chat/${chatId}/cancel`, {
            method: 'POST',
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to cancel message');
        }
    }

    async deleteChat(chatId) {
        const response = await fetch(`${API_BASE}/chat/${chatId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to delete chat');
        }
    }

    // File Methods
    async getFiles() {
        const response = await fetch(`${API_BASE}/files`, {
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to fetch files');
        }

        return response.json();
    }

    async uploadFile(path, file, isPublic = false) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('is_public', isPublic);

        const response = await fetch(`${API_BASE}/files/${path}`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: formData
        });

        if (!response.ok) {
            throw new Error('Failed to upload file');
        }

        return response.json();
    }

    async getFileContent(path) {
        const response = await fetch(`${API_BASE}/files/${path}/content`, {
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to fetch file content');
        }

        return response.text();
    }

    async deleteFile(path) {
        const response = await fetch(`${API_BASE}/files/${path}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });

        if (!response.ok) {
            throw new Error('Failed to delete file');
        }
    }

    async shareFile(path, userId, permissions) {
        const response = await fetch(`${API_BASE}/files/${path}/share`, {
            method: 'POST',
            headers: this.getHeaders({
                'Content-Type': 'application/json'
            }),
            body: JSON.stringify({
                shared_with_id: userId,
                permissions
            })
        });

        if (!response.ok) {
            throw new Error('Failed to share file');
        }

        return response.json();
    }

    // Snippet Methods
    async createSnippet(snippetData) {
        const response = await fetch(`${API_BASE}/snippets`, {
            method: 'POST',
            headers: this.getHeaders({
                'Content-Type': 'application/json'
            }),
            body: JSON.stringify(snippetData)
        });

        if (!response.ok) {
            throw new Error('Failed to create snippet');
        }

        return response.json();
    }
}

export const api = new ApiClient(); 