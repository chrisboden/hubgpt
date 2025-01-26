import { api } from './lib/api-client.js';
import { store } from './lib/store.js';

class App {
    constructor() {
        this.currentController = null;
        this.currentReader = null;
        this.setupEventListeners();
        this.checkAuth();
    }

    async checkAuth() {
        const credentials = localStorage.getItem('auth');
        if (credentials) {
            const [username, password] = atob(credentials).split(':');
            try {
                await api.verifyAuth(username, password);
                store.dispatch('auth/login', { username });
                this.initializeApp();
            } catch {
                this.showLoginForm();
            }
        } else {
            this.showLoginForm();
        }
    }

    setupEventListeners() {
        // New Chat button
        document.getElementById('new-chat-btn')?.addEventListener('click', async () => {
            const advisorId = store.getState('advisors.selected');
            if (!advisorId) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'Please select an advisor first'
                });
                return;
            }
            try {
                const chat = await api.createChat(advisorId);
                store.setState('chat.currentId', chat.id);
                store.setState('chat.messages', []);
                this.renderMessages();
                await this.loadChatHistory(advisorId);
            } catch (error) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'Failed to create new chat'
                });
            }
        });

        // Auth form
        document.getElementById('login-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = e.target.username.value;
            const password = e.target.password.value;
            
            try {
                await api.verifyAuth(username, password);
                localStorage.setItem('auth', btoa(`${username}:${password}`));
                store.dispatch('auth/login', { username });
                this.initializeApp();
            } catch (error) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'Invalid credentials'
                });
            }
        });

        // Message input
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');

        messageInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        sendButton?.addEventListener('click', () => this.sendMessage());

        // File dropzone
        const dropzone = document.getElementById('file-dropzone');
        const fileInput = document.getElementById('file-input');

        dropzone?.addEventListener('dragover', (e) => {
            e.preventDefault();
            store.dispatch('files/setDragActive', true);
        });

        dropzone?.addEventListener('dragleave', () => {
            store.dispatch('files/setDragActive', false);
        });

        dropzone?.addEventListener('drop', async (e) => {
            e.preventDefault();
            store.dispatch('files/setDragActive', false);
            await this.handleFiles(Array.from(e.dataTransfer.files));
        });

        dropzone?.addEventListener('click', () => {
            fileInput?.click();
        });

        fileInput?.addEventListener('change', async () => {
            if (fileInput.files.length) {
                await this.handleFiles(Array.from(fileInput.files));
                fileInput.value = ''; // Reset for future uploads
            }
        });

        // Subscribe to store changes
        store.subscribe('files.dragActive', (active) => {
            dropzone?.classList.toggle('active', active);
        });

        store.subscribe('chat.isStreaming', (streaming) => {
            if (messageInput && sendButton) {
                messageInput.disabled = streaming;
                sendButton.disabled = streaming;
            }
        });

        // Error toast handling
        store.subscribe('ui.errors', (errors) => {
            const toastContainer = document.getElementById('error-toast');
            if (!toastContainer) return;

            toastContainer.innerHTML = '';
            errors.forEach(error => {
                const toast = document.createElement('div');
                toast.className = 'bg-destructive text-destructive-foreground px-4 py-2 rounded shadow-lg mb-2 flex items-center justify-between';
                toast.innerHTML = `
                    <span>${error.message}</span>
                    <button class="ml-4 text-sm opacity-70 hover:opacity-100">&times;</button>
                `;

                toast.querySelector('button').onclick = () => {
                    store.dispatch('ui/clearError', error.id);
                };

                toastContainer.appendChild(toast);

                // Auto-dismiss after 5 seconds
                setTimeout(() => {
                    store.dispatch('ui/clearError', error.id);
                }, 5000);
            });
        });
    }

    async initializeApp() {
        document.getElementById('login-form')?.classList.add('hidden');
        document.getElementById('app')?.classList.remove('hidden');

        // Load advisors
        try {
            const advisors = await api.listAdvisors();
            store.setState('advisors.list', advisors);
            this.renderAdvisors();
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load advisors'
            });
        }

        // Load files
        try {
            const files = await api.listFiles();
            store.setState('files.list', files.files || []);
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load files'
            });
        }
    }

    renderAdvisors() {
        const select = document.getElementById('advisor-select');
        if (!select) return;

        const advisors = store.getState('advisors.list');
        const currentValue = select.value;

        // Clear all options except the placeholder
        while (select.options.length > 1) {
            select.remove(1);
        }

        advisors.forEach(advisor => {
            const option = document.createElement('option');
            option.value = advisor.name;
            option.textContent = `${advisor.name} (${advisor.model})`;
            select.appendChild(option);
        });

        // Restore selection if it exists in new list
        if (currentValue && advisors.some(a => a.name === currentValue)) {
            select.value = currentValue;
        }

        // Add change handler if not already added
        if (!select.dataset.hasChangeHandler) {
            select.addEventListener('change', async () => {
                const advisorId = select.value;
                if (advisorId) {
                    store.dispatch('advisors/select', advisorId);
                    await this.loadChatHistory(advisorId);
                }
            });
            select.dataset.hasChangeHandler = 'true';
        }
    }

    async loadChatHistory(advisorId) {
        const historyContainer = document.getElementById('chat-history');
        if (!historyContainer) return;

        try {
            const chats = await api.listChats(advisorId);
            historyContainer.innerHTML = '';

            chats.forEach(chat => {
                const chatItem = document.createElement('div');
                chatItem.className = 'p-2 bg-muted/10 rounded hover:bg-muted/20 cursor-pointer flex justify-between items-center';
                
                const info = document.createElement('span');
                info.className = 'flex-1';
                info.textContent = `${this.formatDate(chat.updated_at)} (${chat.message_count} msgs)`;
                
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'ml-2 text-destructive hover:text-destructive/80';
                deleteBtn.textContent = '×';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    if (confirm('Delete this chat?')) {
                        this.deleteChat(chat.id);
                    }
                };

                chatItem.appendChild(info);
                chatItem.appendChild(deleteBtn);
                
                chatItem.onclick = () => this.loadChat(chat.id);
                historyContainer.appendChild(chatItem);
            });

            // If no current chat is selected and we have chats, load the most recent one
            if (!store.getState('chat.currentId') && chats.length > 0) {
                await this.loadChat(chats[0].id);
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load chat history'
            });
        }
    }

    async deleteChat(chatId) {
        try {
            await api.request(`/chat/${chatId}`, { method: 'DELETE' });
            const advisorId = store.getState('advisors.selected');
            if (advisorId) {
                await this.loadChatHistory(advisorId);
            }
        } catch (error) {
            console.error('Error deleting chat:', error);
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to delete chat'
            });
        }
    }

    async loadChat(chatId) {
        try {
            const chat = await api.getChat(chatId);
            store.setState('chat.currentId', chat.id);
            store.setState('chat.messages', chat.messages || []);
            this.renderMessages();
        } catch (error) {
            console.error('Error loading chat:', error);
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load chat'
            });
        }
    }

    renderMessages() {
        const container = document.getElementById('messages-container');
        if (!container) return;

        container.innerHTML = '';
        const messages = store.getState('chat.messages');

        messages.forEach(message => {
            const bubble = document.createElement('chat-bubble');
            bubble.setAttribute('role', message.role);
            bubble.setAttribute('timestamp', this.formatDate(message.timestamp));
            bubble.content = message.content;
            container.appendChild(bubble);
        });

        container.scrollTop = container.scrollHeight;
    }

    async handleFiles(files) {
        store.setState('files.uploading', true);
        const errors = [];

        for (const file of files) {
            try {
                await api.uploadFile(file);
            } catch (error) {
                errors.push(`Failed to upload ${file.name}: ${error.message}`);
            }
        }

        if (errors.length) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: errors.join('\n')
            });
        }

        // Refresh file list
        try {
            const response = await api.listFiles();
            store.setState('files.list', response.files || []);
        } catch (error) {
            console.error('Failed to refresh file list:', error);
        }

        store.setState('files.uploading', false);
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input?.value.trim();
        
        if (!message || !store.getState('chat.currentId')) return;

        // Clear input and disable
        input.value = '';
        store.dispatch('chat/setStreaming', true);

        // Add user message
        const userMessage = {
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
        };
        store.dispatch('chat/addMessage', userMessage);

        // Create assistant message placeholder
        const assistantBubble = document.createElement('chat-bubble');
        assistantBubble.setAttribute('role', 'assistant');
        assistantBubble.setAttribute('status', 'streaming');
        document.getElementById('messages-container')?.appendChild(assistantBubble);

        try {
            // Send message and handle streaming response
            const chatId = store.getState('chat.currentId');
            const response = await api.sendMessage(chatId, message);

            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let fullResponse = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.message?.content) {
                                const chunk = data.message.content;
                                fullResponse += chunk;
                                assistantBubble.content = fullResponse;
                            }
                        } catch (error) {
                            console.error('Error parsing chunk:', error);
                        }
                    }
                }
            }

            // Update final message
            assistantBubble.removeAttribute('status');
            store.dispatch('chat/addMessage', {
                role: 'assistant',
                content: fullResponse,
                timestamp: new Date().toISOString()
            });

        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: `Failed to send message: ${error.message}`
            });
            assistantBubble.remove();
        } finally {
            store.dispatch('chat/setStreaming', false);
            input?.focus();
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        } else if (diff < 86400000) { // Less than 1 day
            const hours = Math.floor(diff / 3600000);
            return `${hours}h ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    showLoginForm() {
        document.getElementById('app')?.classList.add('hidden');
        document.getElementById('login-form')?.classList.remove('hidden');
        document.getElementById('login-error')?.classList.add('hidden');
        
        // Clear any stored credentials
        localStorage.removeItem('auth');
        store.dispatch('auth/logout');
    }
}

// Initialize app
window.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
