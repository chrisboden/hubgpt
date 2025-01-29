class Store {
    constructor() {
        this._state = {
            auth: {
                isAuthenticated: false,
                username: null
            },
            advisors: {
                list: [],
                selected: null
            },
            chat: {
                currentId: null,
                messages: [],
                isStreaming: false
            },
            files: {
                list: [],
                uploading: false,
                dragActive: false
            },
            ui: {
                darkMode: window.matchMedia('(prefers-color-scheme: dark)').matches,
                errors: [],
                successes: []
            }
        };

        this._subscribers = new Map();
        this._computedCache = new Map();

        // Initialize dark mode listener
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            this.setState('ui.darkMode', e.matches);
        });
    }

    // State management
    getState(path = '') {
        if (!path) return { ...this._state };
        return path.split('.').reduce((obj, key) => obj?.[key], this._state);
    }

    setState(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((obj, key) => obj[key], this._state);
        
        if (target[lastKey] === value) return; // No change
        
        target[lastKey] = value;
        this._notifySubscribers(path);
        
        // Clear computed cache for affected paths
        this._computedCache.clear();
        
        // Update document class for dark mode
        if (path === 'ui.darkMode') {
            document.documentElement.classList.toggle('dark', value);
        }
    }

    // Pub/Sub
    subscribe(path, callback) {
        if (!this._subscribers.has(path)) {
            this._subscribers.set(path, new Set());
        }
        this._subscribers.get(path).add(callback);
        
        // Initial call with current state
        callback(this.getState(path));
        
        // Return unsubscribe function
        return () => this._subscribers.get(path).delete(callback);
    }

    _notifySubscribers(path) {
        const value = this.getState(path);
        
        // Notify direct subscribers
        if (this._subscribers.has(path)) {
            this._subscribers.get(path).forEach(callback => callback(value));
        }
        
        // Notify parent path subscribers
        const parts = path.split('.');
        while (parts.length > 1) {
            parts.pop();
            const parentPath = parts.join('.');
            if (this._subscribers.has(parentPath)) {
                const parentValue = this.getState(parentPath);
                this._subscribers.get(parentPath).forEach(callback => callback(parentValue));
            }
        }
    }

    // Computed properties
    computed(key, deps, fn) {
        const compute = () => {
            const values = deps.map(dep => this.getState(dep));
            return fn(...values);
        };

        // Initial computation
        this._computedCache.set(key, compute());

        // Subscribe to dependencies
        deps.forEach(dep => {
            this.subscribe(dep, () => {
                this._computedCache.set(key, compute());
                this._notifySubscribers(key);
            });
        });

        return key;
    }

    // Actions
    dispatch(action, payload) {
        switch (action) {
            case 'auth/login':
                this.setState('auth.isAuthenticated', true);
                this.setState('auth.username', payload.username);
                break;

            case 'auth/logout':
                this.setState('auth.isAuthenticated', false);
                this.setState('auth.username', null);
                this.setState('advisors.selected', null);
                this.setState('chat.currentId', null);
                this.setState('chat.messages', []);
                break;

            case 'advisors/select':
                this.setState('advisors.selected', payload);
                break;

            case 'chat/setMessages':
                this.setState('chat.messages', payload);
                break;

            case 'chat/addMessage':
                this.setState('chat.messages', [...this.getState('chat.messages'), payload]);
                break;

            case 'chat/setStreaming':
                this.setState('chat.isStreaming', payload);
                break;

            case 'files/setDragActive':
                this.setState('files.dragActive', payload);
                break;

            case 'ui/toggleSidebar':
                this.setState('ui.sidebarOpen', !this.getState('ui.sidebarOpen'));
                break;

            case 'ui/toggleDarkMode':
                this.setState('ui.darkMode', !this.getState('ui.darkMode'));
                break;

            case 'ui/addError':
                this.setState('ui.errors', [...this.getState('ui.errors'), payload]);
                break;

            case 'ui/clearError':
                this.setState('ui.errors', this.getState('ui.errors').filter(e => e.id !== payload));
                break;

            case 'ui/addSuccess':
                this.setState('ui.successes', [...this.getState('ui.successes'), payload]);
                break;

            case 'ui/clearSuccess':
                this.setState('ui.successes', this.getState('ui.successes').filter(s => s.id !== payload));
                break;

            default:
                console.warn(`Unknown action: ${action}`);
        }
    }
}

// Export singleton instance
export const store = new Store();
