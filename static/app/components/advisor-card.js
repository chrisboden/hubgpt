import { store } from '../lib/store.js';

class AdvisorCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['name', 'model', 'last-used', 'active'];
    }

    connectedCallback() {
        this.render();
        this.addEventListeners();

        // Subscribe to store changes
        this._unsubscribe = store.subscribe('advisors.selected', (selected) => {
            this.toggleAttribute('active', selected === this.getAttribute('name'));
        });
    }

    disconnectedCallback() {
        this._unsubscribe?.();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue) {
            this.render();
        }
    }

    addEventListeners() {
        this.shadowRoot.querySelector('.advisor-card').addEventListener('click', () => {
            const name = this.getAttribute('name');
            store.dispatch('advisors/select', name);
        });
    }

    render() {
        const name = this.getAttribute('name') || '';
        const model = this.getAttribute('model') || '';
        const lastUsed = this.getAttribute('last-used') || '';
        const active = this.hasAttribute('active');

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                }

                .advisor-card {
                    padding: 0.75rem;
                    border-radius: 0.5rem;
                    border: 1px solid hsl(var(--border));
                    background-color: hsl(var(--background));
                    cursor: pointer;
                    transition: all 150ms ease;
                }

                :host([active]) .advisor-card {
                    border-color: hsl(var(--primary));
                    background-color: hsl(var(--accent));
                }

                .advisor-card:hover {
                    background-color: hsl(var(--accent));
                }

                .name {
                    font-weight: 500;
                    color: hsl(var(--foreground));
                    margin-bottom: 0.25rem;
                }

                .model {
                    font-size: 0.875rem;
                    color: hsl(var(--muted-foreground));
                }

                .last-used {
                    font-size: 0.75rem;
                    color: hsl(var(--muted-foreground));
                    margin-top: 0.25rem;
                }

                /* Dark mode adjustments */
                @media (prefers-color-scheme: dark) {
                    .advisor-card {
                        background-color: hsl(var(--background));
                    }
                }
            </style>

            <div class="advisor-card">
                <div class="name">${name}</div>
                ${model ? `<div class="model">${model}</div>` : ''}
                ${lastUsed ? `<div class="last-used">Last used: ${lastUsed}</div>` : ''}
            </div>
        `;
    }
}

customElements.define('advisor-card', AdvisorCard);
