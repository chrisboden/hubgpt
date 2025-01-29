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

        // Success toast handling
        store.subscribe('ui.successes', (successes) => {
            const toastContainer = document.getElementById('success-toast');
            if (!toastContainer) return;

            toastContainer.innerHTML = '';
            successes.forEach(success => {
                const toast = document.createElement('div');
                toast.className = 'bg-green-500 text-white px-4 py-2 rounded shadow-lg mb-2 flex items-center justify-between';
                toast.innerHTML = `
                    <span>${success.message}</span>
                    <button class="ml-4 text-sm opacity-70 hover:opacity-100">&times;</button>
                `;

                toast.querySelector('button').onclick = () => {
                    store.dispatch('ui/clearSuccess', success.id);
                };

                toastContainer.appendChild(toast);

                // Auto-dismiss after 3 seconds
                setTimeout(() => {
                    store.dispatch('ui/clearSuccess', success.id);
                }, 3000);
            });
        });

        // Settings sidebar toggle
        const settingsToggle = document.getElementById('settings-toggle');
        const settingsSidebar = document.getElementById('settings-sidebar');
        const closeSettings = document.getElementById('close-settings');

        if (settingsToggle) {
            settingsToggle.addEventListener('click', async () => {
                if (settingsSidebar) {
                    settingsSidebar.classList.remove('translate-x-full');
                    // Reload advisors when opening settings
                    await this.loadAdvisors();
                }
            });
        }

        if (closeSettings) {
            closeSettings.addEventListener('click', () => {
                if (settingsSidebar) {
                    settingsSidebar.classList.add('translate-x-full');
                    // Clear form when closing
                    const advisorEditForm = document.getElementById('advisor-edit-form');
                    const advisorEditSelect = document.getElementById('advisor-edit-select');
                    if (advisorEditForm && advisorEditSelect) {
                        advisorEditForm.classList.add('hidden');
                        advisorEditSelect.value = '';
                    }
                }
            });
        }

        // Advisor editing
        const advisorEditSelect = document.getElementById('advisor-edit-select');
        const advisorEditForm = document.getElementById('advisor-edit-form');
        const createNewAdvisorBtn = document.getElementById('create-new-advisor');

        advisorEditSelect?.addEventListener('change', async () => {
            const advisorId = advisorEditSelect.value;
            if (!advisorId) {
                advisorEditForm?.classList.add('hidden');
                return;
            }
            
            advisorEditForm?.classList.remove('hidden');
            if (advisorId === 'new') {
                this.clearAdvisorForm();
            } else {
                await this.loadAdvisorForEditing(advisorId);
            }
        });

        advisorEditForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            // Safely get form values with null checks
            const name = formData.get('advisor-name');
            const model = formData.get('advisor-model');
            const temperature = formData.get('advisor-temperature');
            const gateway = formData.get('advisor-gateway');
            const tools = formData.get('advisor-tools');
            const systemPrompt = formData.get('advisor-prompt');

            // Validate required fields
            if (!name) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'Advisor name is required'
                });
                return;
            }

            if (!model) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'Model is required'
                });
                return;
            }

            if (!systemPrompt) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'System prompt is required'
                });
                return;
            }

            const advisorData = {
                name: name.trim(),
                model: model.trim(),
                temperature: parseFloat(temperature || '0.7'),
                gateway: gateway ? gateway.trim() : 'openrouter',
                tools: tools ? tools.trim() : '',
                system_prompt: systemPrompt.trim()
            };

            try {
                await this.saveAdvisor(advisorData);
                store.dispatch('ui/addSuccess', {
                    id: Date.now(),
                    message: 'Advisor saved successfully'
                });
                await this.loadAdvisors();
                
                // Close the sidebar after successful save
                settingsSidebar?.classList.add('translate-x-full');
            } catch (error) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: `Failed to save advisor: ${error.message}`
                });
            }
        });

        createNewAdvisorBtn?.addEventListener('click', () => {
            advisorEditSelect.value = 'new';
            this.clearAdvisorForm();
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
            // First try to load from current chats
            let chat = await api.getChat(chatId).catch(() => null);
            
            // If not found in current chats, try archived chats
            if (!chat) {
                const archivedChats = await api.getArchivedChats();
                const archivedChatId = archivedChats.find(c => c.startsWith(chatId));
                if (archivedChatId) {
                    chat = await api.getArchivedChat(archivedChatId);
                }
            }

            if (!chat) {
                throw new Error('Chat not found');
            }

            store.setState('chat.currentId', chat.id);
            store.setState('chat.messages', chat.messages || []);
            
            // Update UI
            this.renderMessages();
            this.scrollToBottom();
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: `Failed to load chat: ${error.message}`
            });
        }
    }

    renderMessages() {
        const container = document.getElementById('messages-container');
        if (!container) return;

        const messages = store.getState('chat.messages');
        
        // If container is empty or number of bubbles doesn't match messages, do a full render
        if (container.children.length !== messages.length) {
            container.innerHTML = '';
            messages.forEach(message => {
                const bubble = document.createElement('chat-bubble');
                bubble.setAttribute('role', message.role);
                bubble.setAttribute('timestamp', this.formatDate(message.timestamp));
                bubble.content = message.content;
                container.appendChild(bubble);
            });
        } else {
            // Otherwise just update the last message's content
            const lastBubble = container.lastElementChild;
            if (lastBubble) {
                lastBubble.content = messages[messages.length - 1].content;
            }
        }

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
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        if (!message) return;

        const chatId = store.getState('chat.currentId');
        const advisor = store.getState('advisors.selected');
        if (!chatId || !advisor) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'No active chat or advisor selected'
            });
            return;
        }

        // Get advisor data to check for gateway configuration
        const advisorData = await api.getAdvisor(advisor);
        const gateway = advisorData.gateway || 'openrouter';  // Default to openrouter if not specified

        messageInput.value = '';
        messageInput.style.height = 'auto';

        // Add user message to UI immediately
        const userMessage = { role: 'user', content: message };
        store.dispatch('chat/addMessage', userMessage);
        this.renderMessages();

        try {
            // Send message with gateway configuration
            const response = await api.sendMessage(chatId, message, gateway);
            
            if (response.ok) {
                const reader = response.body.getReader();
                this.currentReader = reader;
                
                let assistantMessage = { role: 'assistant', content: '' };
                store.dispatch('chat/addMessage', assistantMessage);
                this.renderMessages(); // Initial render of empty assistant message

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const text = new TextDecoder().decode(value);
                    const lines = text.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') continue;

                            try {
                                const parsed = JSON.parse(data);
                                if (parsed.message && parsed.message.content) {
                                    assistantMessage.content += parsed.message.content;
                                    this.renderMessages();
                                }
                            } catch (e) {
                                console.error('Error parsing SSE data:', e);
                            }
                        }
                    }
                }
            }
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to send message'
            });
        } finally {
            this.currentReader = null;
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

    async loadAdvisors() {
        try {
            const advisors = await api.listAdvisors();
            store.setState('advisors.list', advisors);
            
            // Update both advisor selectors
            this.renderAdvisorSelectors(advisors);
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load advisors'
            });
        }
    }

    renderAdvisorSelectors(advisors) {
        // Main advisor selector
        const advisorSelect = document.getElementById('advisor-select');
        if (advisorSelect) {
            advisorSelect.innerHTML = `
                <option value="">Select an advisor</option>
                ${advisors.map(advisor => `
                    <option value="${advisor.name}">${advisor.name}</option>
                `).join('')}
            `;
        }

        // Edit advisor selector
        const advisorEditSelect = document.getElementById('advisor-edit-select');
        if (advisorEditSelect) {
            advisorEditSelect.innerHTML = `
                <option value="">Select an advisor to edit</option>
                <option value="new">Create New Advisor</option>
                ${advisors.map(advisor => `
                    <option value="${advisor.name}">${advisor.name}</option>
                `).join('')}
            `;
        }
    }

    async loadAdvisorForEditing(advisorId) {
        if (advisorId === 'new') {
            this.clearAdvisorForm();
            return;
        }

        try {
            const advisor = await api.getAdvisor(advisorId);
            console.log('Loaded advisor:', advisor);  // Debug log
            
            if (!advisor) {
                throw new Error('Invalid advisor data received');
            }

            // Set form values directly from the advisor object
            document.getElementById('advisor-name').value = advisor.name || '';
            document.getElementById('advisor-model').value = advisor.model || '';
            document.getElementById('advisor-temperature').value = advisor.temperature || 0.7;
            document.getElementById('advisor-gateway').value = advisor.gateway || '';
            document.getElementById('advisor-tools').value = Array.isArray(advisor.tools) ? advisor.tools.join(', ') : '';
            
            // Get the system prompt - everything after the YAML front matter
            let systemPrompt = '';
            if (advisor.messages && advisor.messages.length > 0) {
                systemPrompt = advisor.messages[0].content;
            }
            document.getElementById('advisor-prompt').value = systemPrompt;

            // Show the form
            document.getElementById('advisor-edit-form').classList.remove('hidden');
        } catch (error) {
            console.error('Error loading advisor:', error);  // Debug log
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: `Failed to load advisor: ${error.message}`
            });
            // Hide the form on error
            document.getElementById('advisor-edit-form').classList.add('hidden');
        }
    }

    clearAdvisorForm() {
        document.getElementById('advisor-name').value = '';
        document.getElementById('advisor-model').value = 'gpt-4';
        document.getElementById('advisor-temperature').value = '0.7';
        document.getElementById('advisor-gateway').value = '';
        document.getElementById('advisor-tools').value = '';
        document.getElementById('advisor-prompt').value = '';
    }

    async saveAdvisor(advisorData) {
        if (!advisorData.name) {
            throw new Error('Advisor name is required');
        }

        // Create the advisor data structure
        const data = {
            name: advisorData.name,
            model: advisorData.model,
            temperature: parseFloat(advisorData.temperature),
            gateway: advisorData.gateway || 'openrouter',
            stream: true
        };

        // Add tools if specified
        if (advisorData.tools && advisorData.tools.length > 0) {
            const toolsArray = advisorData.tools.split(',').map(t => t.trim()).filter(Boolean);
            if (toolsArray.length > 0) {
                data.tools = toolsArray;
            }
        }

        // Add the system prompt as the first message
        if (advisorData.system_prompt) {
            data.messages = [{
                role: 'system',
                content: advisorData.system_prompt
            }];
        }

        const advisorId = advisorData.name;
        return api.updateAdvisor(advisorId, data);
    }

    scrollToBottom() {
        const container = document.getElementById('messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
}

// Initialize app
window.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
