// Simple state management store
class Store {
    constructor() {
        this.state = {
            auth: {
                token: null,
                username: null,
                isAuthenticated: false
            },
            advisors: {
                list: [],
                selected: null,
                editing: null
            },
            chat: {
                currentId: null,
                messages: [],
                history: [],
                isStreaming: false
            },
            files: {
                list: [],
                uploading: null,
                dragActive: false
            },
            ui: {
                errors: [],
                successes: []
            }
        };
        this.subscribers = new Map();
    }

    // Get state by path (e.g., 'auth.token')
    getState(path) {
        return path.split('.').reduce((obj, key) => obj?.[key], this.state);
    }

    // Set state by path
    setState(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((obj, key) => {
            if (!obj[key]) obj[key] = {};
            return obj[key];
        }, this.state);
        target[lastKey] = value;

        // Notify subscribers
        this.notify(path);
    }

    // Subscribe to state changes
    subscribe(path, callback) {
        if (!this.subscribers.has(path)) {
            this.subscribers.set(path, new Set());
        }
        this.subscribers.get(path).add(callback);

        // Initial call with current state
        callback(this.getState(path));

        // Return unsubscribe function
        return () => {
            this.subscribers.get(path)?.delete(callback);
        };
    }

    // Notify subscribers of state change
    notify(path) {
        const value = this.getState(path);
        this.subscribers.get(path)?.forEach(callback => callback(value));
    }

    // Dispatch actions
    dispatch(action, payload) {
        const [namespace, type] = action.split('/');
        
        switch (`${namespace}/${type}`) {
            case 'auth/login':
                if (payload.token) {
                    this.setState('auth.token', payload.token);
                    this.setState('auth.isAuthenticated', true);
                } else if (payload.username) {
                    this.setState('auth.username', payload.username);
                    this.setState('auth.isAuthenticated', true);
                }
                break;

            case 'auth/logout':
                this.setState('auth.token', null);
                this.setState('auth.username', null);
                this.setState('auth.isAuthenticated', false);
                break;

            case 'advisors/select':
                this.setState('advisors.selected', payload);
                break;

            case 'advisors/edit':
                this.setState('advisors.editing', payload);
                break;

            case 'chat/setMessages':
                this.setState('chat.messages', payload);
                break;

            case 'chat/addMessage':
                const messages = this.getState('chat.messages') || [];
                this.setState('chat.messages', [...messages, payload]);
                break;

            case 'files/setUploading':
                this.setState('files.uploading', payload);
                break;

            case 'files/setDragActive':
                this.setState('files.dragActive', payload);
                break;

            case 'ui/addError':
                const errors = this.getState('ui.errors');
                this.setState('ui.errors', [...errors, payload]);
                break;

            case 'ui/clearError':
                this.setState('ui.errors', 
                    this.getState('ui.errors').filter(error => error.id !== payload)
                );
                break;

            case 'ui/addSuccess':
                const successes = this.getState('ui.successes');
                this.setState('ui.successes', [...successes, payload]);
                break;

            case 'ui/clearSuccess':
                this.setState('ui.successes',
                    this.getState('ui.successes').filter(success => success.id !== payload)
                );
                break;

            default:
                console.warn(`Unknown action: ${action}`);
        }
    }
}

export const store = new Store(); 