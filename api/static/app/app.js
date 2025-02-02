import { api } from './lib/api-client.js';
import { store } from './lib/store.js';

// Dynamically set API base URL based on current location
const API_BASE = `${window.location.origin}/api/v1`;
const authToken = localStorage.getItem('authToken');

class App {
    constructor() {
        this.currentController = null;
        this.currentReader = null;
        this.setupEventListeners();
        this.checkAuth();
        this.initializeFileEditor();
    }

    initializeFileEditor() {
        // Create file editor modal if it doesn't exist
        if (!document.getElementById('file-editor-modal')) {
            const modal = document.createElement('div');
            modal.id = 'file-editor-modal';
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 w-3/4 max-w-4xl max-h-[90vh] overflow-y-auto">
                    <div class="flex justify-between items-center mb-4">
                        <h2 id="file-editor-title" class="text-xl font-semibold">Edit File</h2>
                        <button id="close-file-editor" class="text-gray-500 hover:text-gray-700">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    <textarea id="file-editor" class="w-full h-96 p-4 border rounded font-mono text-sm"></textarea>
                    <div class="flex justify-end mt-4 space-x-2">
                        <button id="save-file-button" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                            Save
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Add close button handler
            document.getElementById('close-file-editor').onclick = () => {
                modal.classList.add('hidden');
            };
        }
    }

    async checkAuth() {
        try {
            // Try JWT token first
            const token = localStorage.getItem('authToken');
            if (token) {
                await api.verifyAuth();
                store.dispatch('auth/login', { token });
                this.initializeApp();
                return;
            }

            // Fallback to basic auth
            const basicAuth = localStorage.getItem('basicAuth');
            if (basicAuth) {
                const [username, password] = atob(basicAuth).split(':');
                try {
                    await api.verifyAuth();
                    store.dispatch('auth/login', { username });
                    this.initializeApp();
                    return;
                } catch {
                    localStorage.removeItem('basicAuth');
                }
            }

            this.showLoginForm();
        } catch {
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
            const email = e.target.email?.value;
            
            try {
                // Try to register first (will fail if user exists)
                try {
                    await api.register(username, password, email || `${username}@example.com`);
                } catch {
                    // Ignore registration errors
                }

                // Then try to login
                const data = await api.login(username, password);
                store.dispatch('auth/login', { token: data.access_token });
                this.initializeApp();
            } catch (error) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'Login failed'
                });
            }
        });

        // Message input
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const cancelButton = document.getElementById('cancel-button');

        messageInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        sendButton?.addEventListener('click', () => this.sendMessage());
        cancelButton?.addEventListener('click', () => this.cancelMessage());

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
            if (messageInput && sendButton && cancelButton) {
                messageInput.disabled = streaming;
                sendButton.disabled = streaming;
                cancelButton.style.display = streaming ? 'inline-block' : 'none';
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
                    // Get currently selected advisor
                    const currentAdvisorId = store.getState('advisors.selected');
                    // Load advisors and then select the current one
                    await this.loadAdvisors();
                    if (currentAdvisorId) {
                        const advisorEditSelect = document.getElementById('advisor-edit-select');
                        if (advisorEditSelect) {
                            advisorEditSelect.value = currentAdvisorId;
                            // Trigger change event to load advisor details
                            advisorEditSelect.dispatchEvent(new Event('change'));
                        }
                    }
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
            
            const advisorData = {
                name: formData.get('advisor-name'),
                model: formData.get('advisor-model'),
                temperature: parseFloat(formData.get('advisor-temperature')),
                gateway: formData.get('advisor-gateway'),
                tools: formData.get('advisor-tools')?.split(',').map(t => t.trim()).filter(t => t) || [],
                messages: [{
                    role: 'system',
                    content: formData.get('advisor-prompt')
                }]
            };

            try {
                await this.saveAdvisor(advisorData);
                store.dispatch('ui/addSuccess', {
                    id: Date.now(),
                    message: 'Advisor saved successfully'
                });
                await this.loadAdvisors();
            } catch (error) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'Failed to save advisor'
                });
            }
        });

        // Advisor selection
        document.getElementById('advisor-select')?.addEventListener('change', async (e) => {
            const advisorId = e.target.value;
            store.setState('advisors.selected', advisorId);
            if (advisorId) {
                await this.loadChatHistory(advisorId);
            } else {
                store.setState('chat.history', []);
                store.setState('chat.currentId', null);
                store.setState('chat.messages', []);
                this.renderChatHistory();
                this.renderMessages();
            }
        });

        // System Message Editor
        const systemMessageModal = document.getElementById('system-message-modal');
        const systemMessageEditor = document.getElementById('system-message-editor');
        const closeSystemMessageModal = document.getElementById('close-system-message-modal');
        const previewSystemMessage = document.getElementById('preview-system-message');
        const saveSystemMessage = document.getElementById('save-system-message');
        const previewModal = document.getElementById('preview-modal');
        const closePreviewModal = document.getElementById('close-preview-modal');
        const previewContent = document.getElementById('preview-content');

        // Add edit button next to the system prompt textarea
        const promptTextarea = document.querySelector('[name="advisor-prompt"]');
        if (promptTextarea) {
            const editButton = document.createElement('button');
            editButton.type = 'button';
            editButton.className = 'mt-2 text-blue-500 hover:text-blue-600';
            editButton.textContent = 'Edit in Full Screen';
            editButton.onclick = () => {
                systemMessageEditor.value = promptTextarea.value;
                systemMessageModal.classList.remove('hidden');
            };
            promptTextarea.parentNode.appendChild(editButton);
        }

        // Close system message modal
        closeSystemMessageModal?.addEventListener('click', () => {
            systemMessageModal.classList.add('hidden');
        });

        // Preview system message
        previewSystemMessage?.addEventListener('click', () => {
            previewContent.innerHTML = marked.parse(systemMessageEditor.value);
            previewModal.classList.remove('hidden');
        });

        // Close preview modal
        closePreviewModal?.addEventListener('click', () => {
            previewModal.classList.add('hidden');
        });

        // Save system message
        saveSystemMessage?.addEventListener('click', () => {
            if (promptTextarea) {
                promptTextarea.value = systemMessageEditor.value;
            }
            systemMessageModal.classList.add('hidden');
        });

        // Tab switching
        const advisorsTab = document.getElementById('advisors-tab');
        const filesTab = document.getElementById('files-tab');
        const advisorsPanel = document.getElementById('advisors-panel');
        const filesPanel = document.getElementById('files-panel');

        advisorsTab?.addEventListener('click', () => {
            advisorsTab.classList.add('bg-blue-50', 'text-blue-700');
            advisorsTab.classList.remove('text-gray-500');
            filesTab.classList.remove('bg-blue-50', 'text-blue-700');
            filesTab.classList.add('text-gray-500');
            advisorsPanel.classList.remove('hidden');
            filesPanel.classList.add('hidden');
        });

        filesTab?.addEventListener('click', () => {
            filesTab.classList.add('bg-blue-50', 'text-blue-700');
            filesTab.classList.remove('text-gray-500');
            advisorsTab.classList.remove('bg-blue-50', 'text-blue-700');
            advisorsTab.classList.add('text-gray-500');
            filesPanel.classList.remove('hidden');
            advisorsPanel.classList.add('hidden');
        });
    }

    async initializeApp() {
        document.getElementById('login-container')?.classList.add('hidden');
        document.getElementById('app-container')?.classList.remove('hidden');
        
        try {
            await Promise.all([
                this.loadAdvisors(),
                this.loadFiles()
            ]);
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to initialize app'
            });
        }
    }

    async loadAdvisors() {
        try {
            const advisors = await api.getAdvisors();
            store.setState('advisors.list', advisors);
            this.renderAdvisors();
            this.renderAdvisorSelectors(advisors);
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load advisors'
            });
        }
    }

    async loadFiles() {
        try {
            const files = await api.getFiles();
            store.setState('files.list', files);
            this.renderFiles();
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load files'
            });
        }
    }

    async loadChatHistory(advisorId) {
        try {
            const chats = await api.getChatHistory(advisorId);
            store.setState('chat.history', chats);
            this.renderChatHistory();
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load chat history'
            });
        }
    }

    async loadChat(chatId) {
        try {
            const messages = await api.getMessages(chatId);
            store.setState('chat.currentId', chatId);
            store.setState('chat.messages', messages);
            this.renderMessages();
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load chat'
            });
        }
    }

    async deleteChat(chatId) {
        try {
            await api.deleteChat(chatId);
            const currentId = store.getState('chat.currentId');
            if (currentId === chatId) {
                store.setState('chat.currentId', null);
                store.setState('chat.messages', []);
                this.renderMessages();
            }
            const advisorId = store.getState('advisors.selected');
            await this.loadChatHistory(advisorId);
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to delete chat'
            });
        }
    }

    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput?.value.trim();
        if (!message) return;

        const chatId = store.getState('chat.currentId');
        if (!chatId) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'No active chat'
            });
            return;
        }

        try {
            // Create AbortController for cancellation
            this.currentController = new AbortController();
            store.setState('chat.isStreaming', true);

            // Add user message immediately
            const messages = store.getState('chat.messages') || [];
            const userMessage = { role: 'user', content: message };
            store.setState('chat.messages', [...messages, userMessage]);
            this.renderMessages();
            messageInput.value = '';

            // Create placeholder for assistant message
            const assistantMessage = { role: 'assistant', content: '' };
            store.setState('chat.messages', [...messages, userMessage, assistantMessage]);
            this.renderMessages();

            // Send message and handle streaming response
            const response = await api.sendMessage(chatId, message, this.currentController.signal);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim() || !line.startsWith('data: ')) continue;

                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.message?.content) {
                            assistantMessage.content += data.message.content;
                            const currentMessages = store.getState('chat.messages');
                            store.setState('chat.messages', [
                                ...currentMessages.slice(0, -1),
                                assistantMessage
                            ]);
                            this.renderMessages();
                        }
                    } catch (error) {
                        console.error('Error parsing chunk:', error);
                    }
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                store.dispatch('ui/addSuccess', {
                    id: Date.now(),
                    message: 'Message cancelled'
                });
            } else {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: 'Failed to send message'
                });
            }
        } finally {
            store.setState('chat.isStreaming', false);
            this.currentController = null;
        }
    }

    async cancelMessage() {
        const chatId = store.getState('chat.currentId');
        if (!chatId || !this.currentController) return;

        try {
            this.currentController.abort();
            await api.cancelMessage(chatId);
        } catch (error) {
            console.error('Error cancelling message:', error);
        }
    }

    async handleFiles(files) {
        for (const file of files) {
            try {
                store.dispatch('files/setUploading', {
                    name: file.name,
                    progress: 0
                });

                await api.uploadFile(file.name, file);

                store.dispatch('ui/addSuccess', {
                    id: Date.now(),
                    message: `Uploaded ${file.name}`
                });

                await this.loadFiles();
            } catch (error) {
                store.dispatch('ui/addError', {
                    id: Date.now(),
                    message: `Failed to upload ${file.name}`
                });
            } finally {
                store.dispatch('files/setUploading', null);
            }
        }
    }

    async loadAdvisorForEditing(advisorId) {
        try {
            const advisor = await api.getAdvisor(advisorId);
            const form = document.getElementById('advisor-edit-form');
            if (!form) return;

            form.querySelector('[name="advisor-name"]').value = advisor.name;
            form.querySelector('[name="advisor-model"]').value = advisor.model || '';
            form.querySelector('[name="advisor-temperature"]').value = advisor.temperature || 1.0;
            form.querySelector('[name="advisor-gateway"]').value = advisor.gateway || 'openrouter';
            form.querySelector('[name="advisor-tools"]').value = advisor.tools?.join(', ') || '';
            form.querySelector('[name="advisor-prompt"]').value = 
                advisor.messages?.find(m => m.role === 'system')?.content || '';
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to load advisor'
            });
        }
    }

    async saveAdvisor(advisorData) {
        const advisorId = store.getState('advisors.editing');
        if (advisorId) {
            await api.updateAdvisor(advisorId, advisorData);
        } else {
            await api.createAdvisor(advisorData);
        }
    }

    renderAdvisors() {
        const advisors = store.getState('advisors.list') || [];
        const container = document.getElementById('advisor-list');
        if (!container) return;

        container.innerHTML = '';
        advisors.forEach(advisor => {
            const div = document.createElement('div');
            div.className = 'p-4 bg-white rounded shadow mb-4';
            div.innerHTML = `
                <div class="flex justify-between items-center">
                    <h3 class="text-lg font-semibold">${advisor.name}</h3>
                    <div class="space-x-2">
                        <button class="text-blue-500 hover:text-blue-700" onclick="app.editAdvisor('${advisor.id}')">
                            Edit
                        </button>
                        <button class="text-red-500 hover:text-red-700" onclick="app.deleteAdvisor('${advisor.id}')">
                            Delete
                        </button>
                    </div>
                </div>
                <div class="mt-2 text-sm text-gray-600">
                    <div>Model: ${advisor.model || 'default'}</div>
                    <div>Temperature: ${advisor.temperature || 1.0}</div>
                    <div>Tools: ${advisor.tools?.join(', ') || 'none'}</div>
                </div>
            `;
            container.appendChild(div);
        });
    }

    renderAdvisorSelectors(advisors) {
        const selectors = [
            document.getElementById('advisor-select'),
            document.getElementById('advisor-edit-select')
        ];

        selectors.forEach(select => {
            if (!select) return;

            select.innerHTML = '<option value="">Select an advisor...</option>';
            if (select.id === 'advisor-edit-select') {
                select.innerHTML += '<option value="new">Create New Advisor</option>';
            }

            advisors.forEach(advisor => {
                const option = document.createElement('option');
                option.value = advisor.id;
                option.textContent = advisor.name;
                select.appendChild(option);
            });
        });
    }

    renderChatHistory() {
        const chats = store.getState('chat.history') || [];
        const container = document.getElementById('chat-history');
        if (!container) return;

        container.innerHTML = '';
        chats.forEach(chat => {
            const div = document.createElement('div');
            div.className = 'p-4 bg-white rounded shadow mb-4 cursor-pointer hover:bg-gray-50';
            div.onclick = () => this.loadChat(chat.id);
            div.innerHTML = `
                <div class="flex justify-between items-center">
                    <div class="text-sm text-gray-600">
                        ${this.formatDate(chat.created_at)}
                    </div>
                    <button class="text-red-500 hover:text-red-700" onclick="event.stopPropagation(); app.deleteChat('${chat.id}')">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
                <div class="mt-2">
                    ${chat.message_count} messages
                </div>
            `;
            container.appendChild(div);
        });
    }

    renderMessages() {
        const messages = store.getState('chat.messages') || [];
        const container = document.getElementById('message-list');
        if (!container) return;

        container.innerHTML = '';
        messages.forEach(message => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `group w-full text-gray-800 dark:text-gray-100 border-b border-black/10 dark:border-gray-900/50 ${message.role === 'assistant' ? 'bg-gray-50' : 'bg-white'}`;
            
            const contentWrapper = document.createElement('div');
            contentWrapper.className = 'text-base gap-4 md:gap-6 md:max-w-2xl lg:max-w-[38rem] xl:max-w-3xl p-4 md:py-6 lg:px-0 m-auto flex';
            
            // Avatar
            const avatar = document.createElement('div');
            avatar.className = 'w-[30px] h-[30px] flex flex-col relative items-end';
            avatar.innerHTML = message.role === 'assistant' ? 
                '<div class="relative h-7 w-7 p-1 rounded-sm bg-blue-500 text-white flex items-center justify-center text-xs font-bold">AI</div>' :
                '<div class="relative h-7 w-7 p-1 rounded-sm bg-gray-800 text-white flex items-center justify-center text-xs font-bold">U</div>';
            
            // Message content
            const contentContainer = document.createElement('div');
            contentContainer.className = 'relative flex w-[calc(100%-50px)] flex-col gap-1 md:gap-3 lg:w-[calc(100%-115px)]';
            
            const content = document.createElement('div');
            content.className = 'flex flex-grow flex-col gap-3';
            content.innerHTML = marked.parse(message.content);

            // Save snippet button for assistant messages
            if (message.role === 'assistant') {
                const saveButton = document.createElement('button');
                saveButton.className = 'absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200';
                saveButton.title = 'Save as snippet';
                saveButton.innerHTML = `
                    <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 text-gray-500 hover:text-gray-700" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg">
                        <path d="M5 13l4 4L19 7"></path>
                    </svg>
                `;
                saveButton.onclick = () => this.saveSnippet(message.content);
                contentContainer.appendChild(saveButton);
            }

            contentContainer.appendChild(content);
            contentWrapper.appendChild(avatar);
            contentWrapper.appendChild(contentContainer);
            messageDiv.appendChild(contentWrapper);
            container.appendChild(messageDiv);
        });

        this.scrollToBottom();
    }

    async saveSnippet(content) {
        try {
            const advisor = document.getElementById('chatAdvisorSelect')?.selectedOptions[0]?.text || 'Unknown Advisor';
            await api.createSnippet({
                source_type: 'advisor',
                source_name: advisor,
                content: content,
                tags: ['chat'],
                snippet_metadata: {
                    conversation_id: store.getState('chat.currentId'),
                    advisor_id: store.getState('chat.advisorId')
                }
            });
            store.dispatch('ui/addSuccess', {
                id: Date.now(),
                message: 'Snippet saved successfully'
            });
        } catch (error) {
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: 'Failed to save snippet'
            });
        }
    }

    renderFiles() {
        const files = store.getState('files.list') || [];
        const container = document.getElementById('file-list');
        if (!container) return;

        container.innerHTML = '';
        files.forEach(file => {
            // Clean up the path - remove leading/trailing slashes and multiple slashes
            const cleanPath = this.cleanPath(file.file_path);
            // Remove 'files/' prefix if it exists
            const displayPath = cleanPath.replace(/^files\//, '');

            const div = document.createElement('div');
            div.className = 'p-4 bg-white rounded shadow mb-4';
            div.innerHTML = `
                <div class="flex justify-between items-center">
                    <div class="text-sm">
                        <div class="font-semibold">${displayPath}</div>
                        <div class="text-gray-600">${this.formatFileSize(file.size_bytes)}</div>
                    </div>
                    <div class="space-x-2">
                        <button class="text-blue-500 hover:text-blue-700" onclick="app.editFile('${displayPath}')">
                            Edit
                        </button>
                        <button class="text-red-500 hover:text-red-700" onclick="app.deleteFile('${displayPath}')">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>
                </div>
            `;
            container.appendChild(div);
        });
    }

    async editFile(path) {
        try {
            const cleanedPath = this.cleanPath(path);
            
            // Get file content with proper auth headers
            const response = await fetch(`${API_BASE}/files/${cleanedPath}/content`, {
                headers: {
                    'Authorization': `Bearer ${store.getState('auth.token')}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to fetch file content: ${response.status}`);
            }
            
            // Get the raw text content
            const content = await response.text();
            
            // Try to parse as JSON to see if the content is JSON-encoded
            try {
                const parsed = JSON.parse(content);
                // If it's a string wrapped in JSON, unwrap it
                this.showFileEditor(cleanedPath, typeof parsed === 'string' ? parsed : content);
            } catch (e) {
                // If it's not JSON, use the raw content
                this.showFileEditor(cleanedPath, content);
            }
        } catch (error) {
            console.error('Error editing file:', error);
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: `Failed to edit file: ${error.message}`
            });
        }
    }

    showFileEditor(path, content) {
        const modal = document.getElementById('file-editor-modal');
        const editor = document.getElementById('file-editor');
        const title = document.getElementById('file-editor-title');
        
        if (!modal || !editor || !title) {
            console.error('File editor elements not found');
            return;
        }
        
        title.textContent = `Editing: ${path}`;
        editor.value = content;
        modal.classList.remove('hidden');
        
        // Store the current file path for save operation
        this.currentEditingFile = path;

        // Add event listener for save button if not already added
        const saveButton = document.getElementById('save-file-button');
        if (saveButton) {
            saveButton.onclick = () => this.saveFile();
        }
    }

    async saveFile() {
        try {
            const content = document.getElementById('file-editor').value;
            if (!this.currentEditingFile) {
                throw new Error('No file selected for saving');
            }
            
            // Create FormData and append file
            const formData = new FormData();
            const file = new File([content], this.currentEditingFile.split('/').pop(), {
                type: 'text/plain'
            });
            formData.append('file', file);
            
            const response = await fetch(`${API_BASE}/files/${this.cleanPath(this.currentEditingFile)}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${store.getState('auth.token')}`
                },
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save file');
            }
            
            await this.loadFiles();
            store.dispatch('ui/addSuccess', {
                id: Date.now(),
                message: 'File saved successfully'
            });
            
            // Close the editor modal
            document.getElementById('file-editor-modal')?.classList.add('hidden');
        } catch (error) {
            console.error('Error saving file:', error);
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: `Failed to save file: ${error.message}`
            });
        }
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleString();
    }

    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    }

    scrollToBottom() {
        const container = document.getElementById('message-list');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    showLoginForm() {
        document.getElementById('login-container')?.classList.remove('hidden');
        document.getElementById('app-container')?.classList.add('hidden');
    }

    // Clean up file path - remove leading/trailing slashes and multiple slashes
    cleanPath(path) {
        // Remove leading/trailing slashes and multiple slashes
        let cleaned = path.replace(/^\/+|\/+$/g, '').replace(/\/+/g, '/');
        // Remove 'files/' prefix if it exists
        cleaned = cleaned.replace(/^files\//, '');
        return cleaned;
    }

    async deleteFile(path) {
        if (!confirm(`Are you sure you want to delete ${path}?`)) {
            return;
        }

        try {
            const cleanedPath = this.cleanPath(path);
            
            const response = await fetch(`${API_BASE}/files/${cleanedPath}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${store.getState('auth.token')}`
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to delete file');
            }
            
            await this.loadFiles();
            store.dispatch('ui/addSuccess', {
                id: Date.now(),
                message: 'File deleted successfully'
            });
        } catch (error) {
            console.error('Error deleting file:', error);
            store.dispatch('ui/addError', {
                id: Date.now(),
                message: `Failed to delete file: ${error.message}`
            });
        }
    }
}

// Initialize app
const app = new App();
window.app = app; // Export for global access
