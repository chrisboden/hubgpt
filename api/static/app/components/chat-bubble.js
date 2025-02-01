class ChatBubble extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['role', 'timestamp', 'status'];
    }

    connectedCallback() {
        this.render();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue) {
            this.render();
        }
    }

    get content() {
        return this._content || '';
    }

    set content(value) {
        this._content = value;
        this.updateContent();
    }

    appendContent(chunk) {
        this._content = (this._content || '') + chunk;
        this.updateContent();
    }

    updateContent() {
        const contentElement = this.shadowRoot.querySelector('.content');
        if (contentElement) {
            if (this.getAttribute('role') === 'assistant') {
                contentElement.innerHTML = marked.parse(this.content);
            } else {
                contentElement.textContent = this.content;
            }
        }
    }

    render() {
        const role = this.getAttribute('role') || 'user';
        const timestamp = this.getAttribute('timestamp');
        const status = this.getAttribute('status');

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    margin-bottom: 1rem;
                    max-width: 80%;
                    animation: fade-in 0.2s ease-out;
                }

                @keyframes fade-in {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                :host([role="user"]) {
                    margin-left: auto;
                }

                :host([role="assistant"]) {
                    margin-right: auto;
                }

                .bubble {
                    position: relative;
                }

                .role {
                    font-size: 0.875rem;
                    color: hsl(var(--muted-foreground));
                    margin-bottom: 0.25rem;
                }

                .content {
                    border-radius: 0.5rem;
                    padding: 0.75rem 1rem;
                    overflow-wrap: break-word;
                }

                :host([role="user"]) .content {
                    background-color: hsl(var(--primary));
                    color: hsl(var(--primary-foreground));
                }

                :host([role="assistant"]) .content {
                    background-color: hsl(var(--secondary));
                    color: hsl(var(--secondary-foreground));
                }

                .timestamp {
                    font-size: 0.75rem;
                    color: hsl(var(--muted-foreground));
                    margin-top: 0.25rem;
                }

                .loading {
                    display: inline-flex;
                    gap: 0.25rem;
                }

                .loading::after {
                    content: '...';
                    animation: loading-dots 1.5s steps(4, jump-none) infinite;
                }

                @keyframes loading-dots {
                    0%, 20% { content: '.'; }
                    40% { content: '..'; }
                    60% { content: '...'; }
                    80%, 100% { content: ''; }
                }

                /* Markdown Styles */
                .content :first-child {
                    margin-top: 0;
                }

                .content :last-child {
                    margin-bottom: 0;
                }

                .content p {
                    margin: 0.5rem 0;
                }

                .content pre {
                    background-color: hsl(var(--muted));
                    padding: 0.75rem;
                    border-radius: 0.375rem;
                    overflow-x: auto;
                }

                .content code {
                    font-family: monospace;
                    font-size: 0.875em;
                }

                .content p code {
                    background-color: hsl(var(--muted));
                    padding: 0.125rem 0.25rem;
                    border-radius: 0.25rem;
                }

                .content ul, .content ol {
                    margin: 0.5rem 0;
                    padding-left: 1.5rem;
                }

                .content li {
                    margin: 0.25rem 0;
                }

                .content blockquote {
                    border-left: 3px solid hsl(var(--border));
                    margin: 0.5rem 0;
                    padding-left: 1rem;
                    color: hsl(var(--muted-foreground));
                }
            </style>

            <div class="bubble">
                <div class="role">${role === 'user' ? 'You' : 'Advisor'}</div>
                <div class="content">
                    ${status === 'streaming' ? 
                        `<div class="loading">Thinking</div>` : 
                        (role === 'assistant' ? marked.parse(this.content || '') : (this.content || ''))}
                </div>
                ${timestamp ? `<div class="timestamp">${timestamp}</div>` : ''}
            </div>
        `;
    }
}

customElements.define('chat-bubble', ChatBubble);
