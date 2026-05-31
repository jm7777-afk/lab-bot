class AIChatWidget extends HTMLElement {
    constructor() {
        super();
        this.companyUuid = this.getAttribute("company-uuid") || "";
        this.sessionId = localStorage.getItem("chat_session_id") || this.generateUUID();
        localStorage.setItem("chat_session_id", this.sessionId);
        this.attachShadow({ mode: "open" });
    }

    connectedCallback() {
        this.render();
        this.bindEvents();
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host { position: fixed; right: 20px; bottom: 20px; z-index: 9999; font-family: Inter, Arial, sans-serif; }
                .chat-button { width: 60px; height: 60px; border-radius: 999px; background: #2563eb; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 28px; cursor: pointer; box-shadow: 0 12px 30px rgba(37, 99, 235, 0.25); }
                .chat-window { display: none; width: 380px; height: 500px; background: #fff; border-radius: 18px; box-shadow: 0 18px 40px rgba(15, 23, 42, 0.25); overflow: hidden; flex-direction: column; margin-bottom: 12px; }
                .chat-window.open { display: flex; }
                .chat-header { background: linear-gradient(135deg, #1d4ed8, #2563eb); color: #fff; padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
                .close-btn { cursor: pointer; font-size: 18px; }
                .messages { flex: 1; padding: 16px; overflow-y: auto; background: #f8fafc; }
                .message { margin-bottom: 12px; padding: 10px 12px; border-radius: 12px; max-width: 85%; line-height: 1.4; white-space: pre-wrap; }
                .message.user { background: #2563eb; color: #fff; margin-left: auto; }
                .message.assistant { background: #fff; border: 1px solid #e2e8f0; color: #0f172a; }
                .input-row { display: flex; border-top: 1px solid #e2e8f0; padding: 12px; gap: 8px; background: #fff; }
                .input-row input { flex: 1; border: 1px solid #cbd5e1; border-radius: 10px; padding: 10px 12px; outline: none; }
                .input-row button { border: 0; border-radius: 10px; background: #2563eb; color: #fff; padding: 10px 16px; font-weight: 700; cursor: pointer; }
                .typing { color: #64748b; font-style: italic; padding: 8px 12px; }
            </style>
            <div class="chat-window" id="window">
                <div class="chat-header">
                    <span>Asistente IA</span>
                    <span class="close-btn" id="close">✕</span>
                </div>
                <div class="messages" id="messages"></div>
                <div class="input-row">
                    <input id="input" type="text" placeholder="Escribe tu mensaje..." />
                    <button id="send">Enviar</button>
                </div>
            </div>
            <div class="chat-button" id="toggle">💬</div>
        `;
    }

    bindEvents() {
        const toggle = this.shadowRoot.getElementById("toggle");
        const close = this.shadowRoot.getElementById("close");
        const send = this.shadowRoot.getElementById("send");
        const input = this.shadowRoot.getElementById("input");

        toggle.onclick = () => this.shadowRoot.getElementById("window").classList.toggle("open");
        close.onclick = () => this.shadowRoot.getElementById("window").classList.remove("open");
        send.onclick = () => this.sendMessage();
        input.onkeydown = (event) => {
            if (event.key === "Enter") {
                this.sendMessage();
            }
        };
    }

    addMessage(text, role) {
        const container = this.shadowRoot.getElementById("messages");
        const node = document.createElement("div");
        node.className = `message ${role}`;
        node.textContent = text;
        container.appendChild(node);
        container.scrollTop = container.scrollHeight;
    }

    showTyping() {
        const container = this.shadowRoot.getElementById("messages");
        const node = document.createElement("div");
        node.className = "typing";
        node.textContent = "Escribiendo...";
        container.appendChild(node);
        container.scrollTop = container.scrollHeight;
        return node;
    }

    async sendMessage() {
        const input = this.shadowRoot.getElementById("input");
        const message = input.value.trim();
        if (!message) {
            return;
        }

        this.addMessage(message, "user");
        input.value = "";
        const indicator = this.showTyping();

        try {
            const response = await fetch("/chat/web/send", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    company_uuid: this.companyUuid,
                    session_id: this.sessionId,
                    message,
                    channel: "web",
                }),
            });

            const data = await response.json();
            indicator.remove();
            if (!response.ok) {
                this.addMessage(data.detail || "Ocurrió un error al procesar el mensaje.", "assistant");
                return;
            }

            this.addMessage(data.response, "assistant");
        } catch (error) {
            indicator.remove();
            this.addMessage("No se pudo conectar con el servidor. Reintenta en unos segundos.", "assistant");
        }
    }

    generateUUID() {
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
            const random = (Math.random() * 16) | 0;
            const value = char === "x" ? random : (random & 0x3) | 0x8;
            return value.toString(16);
        });
    }
}

customElements.define("ai-chat-widget", AIChatWidget);
