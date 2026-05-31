let token = localStorage.getItem("admin_token");
let currentCompany = null;
let currentBotConfig = null;
let currentSection = "dashboard";

const sectionTitles = {
  dashboard: "Dashboard",
  companies: "Empresas",
  "bot-config": "Configuración del bot",
  conversations: "Conversaciones",
  analytics: "Analíticas",
};

function setActiveSection(section) {
  document.querySelectorAll(".nav-item[data-section]").forEach((item) => {
    item.classList.toggle("active", item.dataset.section === section);
  });
}

function toggleShell(showDashboard) {
  document.getElementById("loginScreen").classList.toggle("hidden", showDashboard);
  document.getElementById("dashboardShell").classList.toggle("hidden", !showDashboard);
}

function showError(message) {
  const errorEl = document.getElementById("loginError");
  if (errorEl) {
    errorEl.textContent = message;
  }
}

function showCompanyBadge() {
  const badge = document.getElementById("selectedCompanyBadge");
  badge.textContent = currentCompany ? currentCompany.name : "Selecciona una empresa";
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

function showCompanySelector() {
  document.getElementById("companyModal").classList.remove("hidden");
}

async function fetchWithAuth(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    logout();
    throw new Error("Sesión expirada");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Error en la solicitud");
  }

  return response.json();
}

async function doLogin() {
  const email = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;

  try {
    const response = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Credenciales incorrectas");
    }

    token = payload.access_token;
    localStorage.setItem("admin_token", token);
    toggleShell(true);
    showError("");
    await loadCompanies();
    await loadSection("dashboard");
  } catch (error) {
    showError(error.message);
  }
}

function logout() {
  localStorage.removeItem("admin_token");
  token = null;
  currentCompany = null;
  currentBotConfig = null;
  toggleShell(false);
  showCompanyBadge();
  document.getElementById("contentArea").innerHTML = "";
}

async function loadCompanies() {
  if (!token) {
    return;
  }

  const data = await fetchWithAuth("/api/admin/companies?limit=100");
  const select = document.getElementById("companySelect");
  select.innerHTML = "";

  if (!data.data || data.data.length === 0) {
    select.innerHTML = '<option value="">No hay empresas disponibles</option>';
    currentCompany = null;
    showCompanyBadge();
    return;
  }

  data.data.forEach((company) => {
    const option = document.createElement("option");
    option.value = company.id;
    option.textContent = `${company.name} (${company.plan})`;
    select.appendChild(option);
  });

  if (!currentCompany) {
    currentCompany = data.data[0];
  }

  showCompanyBadge();
}

function selectCompany() {
  const select = document.getElementById("companySelect");
  const selectedId = Number(select.value);
  if (!selectedId) {
    return;
  }

  currentCompany = {
    id: selectedId,
    name: select.options[select.selectedIndex].text,
  };

  showCompanyBadge();
  closeModal("companyModal");
  loadSection(currentSection);
}

async function loadSection(section, button) {
  currentSection = section;
  setActiveSection(section);
  document.getElementById("sectionTitle").textContent = sectionTitles[section];

  if (!token) {
    return;
  }

  switch (section) {
    case "dashboard":
      await renderDashboard();
      break;
    case "companies":
      await renderCompanies();
      break;
    case "bot-config":
      await renderBotConfig();
      break;
    case "conversations":
      await renderConversations();
      break;
    case "analytics":
      await renderAnalytics();
      break;
  }
}

function renderCard(title, value) {
  return `
    <div class="stat-card">
      <h3>${title}</h3>
      <div class="stat-number">${value}</div>
    </div>
  `;
}

async function renderDashboard() {
  if (!currentCompany) {
    document.getElementById("contentArea").innerHTML = '<div class="panel-card"><h3>Selecciona una empresa</h3><p>Para ver métricas del dashboard, elige una empresa del selector.</p></div>';
    return;
  }

  const [stats, companyStats] = await Promise.all([
    fetchWithAuth("/api/admin/stats/dashboard"),
    fetchWithAuth(`/api/admin/stats/companies/${currentCompany.id}`),
  ]);

  document.getElementById("contentArea").innerHTML = `
    <div class="stats-grid">
      ${renderCard("Empresas totales", stats.total_companies)}
      ${renderCard("Empresas activas", stats.active_companies)}
      ${renderCard("Conversaciones", companyStats.total_conversations)}
      ${renderCard("Mensajes", companyStats.total_messages)}
      ${renderCard("Última semana", companyStats.messages_last_7_days)}
      ${renderCard("Activas", companyStats.active_conversations)}
    </div>
    <div class="panel-card">
      <h3>Canales de comunicación</h3>
      <table>
        <thead>
          <tr><th>Canal</th><th>Conversaciones</th></tr>
        </thead>
        <tbody>
          <tr><td>🌐 Web Chat</td><td>${stats.messages_by_channel.web}</td></tr>
          <tr><td>📱 WhatsApp</td><td>${stats.messages_by_channel.whatsapp}</td></tr>
        </tbody>
      </table>
    </div>
  `;
}

async function renderCompanies() {
  const data = await fetchWithAuth("/api/admin/companies?limit=100");
  document.getElementById("contentArea").innerHTML = `
    <div class="panel-card">
      <div class="panel-header">
        <div>
          <h3>Gestión de empresas</h3>
          <p>Administra el ciclo completo de tus clientes.</p>
        </div>
        <button class="btn btn-primary" onclick="createCompanyFlow()">➕ Nueva empresa</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Plan</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          ${data.data.map((company) => `
            <tr>
              <td>${company.id}</td>
              <td>${company.name}</td>
              <td>${company.plan}</td>
              <td><span class="badge ${company.is_active ? "badge-active" : "badge-inactive"}">${company.is_active ? "Activo" : "Inactivo"}</span></td>
              <td>
                <button class="btn btn-secondary" onclick="editCompany(${company.id})">Editar</button>
                <button class="btn btn-primary" onclick="toggleCompanyStatus(${company.id}, ${!company.is_active})">${company.is_active ? "Desactivar" : "Activar"}</button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function createCompanyFlow() {
  const name = window.prompt("Nombre de la empresa");
  if (!name) return;

  const plan = window.prompt("Plan (free, starter, pro)", "free");
  if (!plan) return;

  await fetchWithAuth("/api/admin/companies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, plan }),
  });

  await renderCompanies();
}

async function editCompany(companyId) {
  const name = window.prompt("Nuevo nombre de la empresa");
  if (name === null) return;

  const plan = window.prompt("Nuevo plan", "free");
  if (plan === null) return;

  await fetchWithAuth(`/api/admin/companies/${companyId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, plan }),
  });

  await renderCompanies();
}

async function toggleCompanyStatus(companyId, nextStatus) {
  await fetchWithAuth(`/api/admin/companies/${companyId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: nextStatus }),
  });

  await renderCompanies();
}

async function renderBotConfig() {
  if (!currentCompany) {
    document.getElementById("contentArea").innerHTML = '<div class="panel-card"><h3>Selecciona una empresa</h3><p>Debes escoger una empresa para editar su configuración del bot.</p></div>';
    return;
  }

  currentBotConfig = await fetchWithAuth(`/api/admin/companies/${currentCompany.id}/bot-config`);

  document.getElementById("contentArea").innerHTML = `
    <div class="panel-card">
      <div class="panel-header">
        <div>
          <h3>Configuración del bot</h3>
          <p>${currentCompany.name}</p>
        </div>
        <button class="btn btn-primary" onclick="toggleBotStatus()">${currentBotConfig.is_running ? "Detener bot" : "Iniciar bot"}</button>
      </div>
      <div class="kv-grid">
        <div class="stat-card">
          <h3>Prompt del sistema</h3>
          <p>${currentBotConfig.system_prompt}</p>
          <button class="btn btn-secondary" onclick="editBotField('system_prompt')">Editar</button>
        </div>
        <div class="stat-card">
          <h3>Modelo</h3>
          <div class="stat-number">${currentBotConfig.model}</div>
          <button class="btn btn-secondary" onclick="editBotField('model')">Editar</button>
        </div>
        <div class="stat-card">
          <h3>Temperatura</h3>
          <div class="stat-number">${currentBotConfig.temperature}</div>
          <button class="btn btn-secondary" onclick="editBotField('temperature')">Editar</button>
        </div>
        <div class="stat-card">
          <h3>Mensajes de contexto</h3>
          <div class="stat-number">${currentBotConfig.max_context_messages}</div>
          <button class="btn btn-secondary" onclick="editBotField('max_context_messages')">Editar</button>
        </div>
        <div class="stat-card">
          <h3>Límite por usuario</h3>
          <div class="stat-number">${currentBotConfig.rate_limit_per_user}</div>
          <button class="btn btn-secondary" onclick="editBotField('rate_limit_per_user')">Editar</button>
        </div>
        <div class="stat-card">
          <h3>Mensaje de bienvenida</h3>
          <p>${currentBotConfig.welcome_message}</p>
          <button class="btn btn-secondary" onclick="editBotField('welcome_message')">Editar</button>
        </div>
      </div>
    </div>
  `;
}

async function editBotField(field) {
  if (!currentCompany) return;

  const currentValue = currentBotConfig[field];
  const value = window.prompt(`Editar ${field}`, currentValue);
  if (value === null) return;

  const payload = {};
  if (["temperature"].includes(field)) {
    payload[field] = Number(value);
  } else if (["max_context_messages", "rate_limit_per_user"].includes(field)) {
    payload[field] = Number(value);
  } else {
    payload[field] = value;
  }

  await fetchWithAuth(`/api/admin/companies/${currentCompany.id}/bot-config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  await renderBotConfig();
}

async function toggleBotStatus() {
  if (!currentCompany) return;

  await fetchWithAuth(`/api/admin/companies/${currentCompany.id}/bot-config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_running: !currentBotConfig.is_running }),
  });

  await renderBotConfig();
}

async function renderConversations() {
  if (!currentCompany) {
    document.getElementById("contentArea").innerHTML = '<div class="panel-card"><h3>Selecciona una empresa</h3><p>Elige una empresa para revisar sus conversaciones recientes.</p></div>';
    return;
  }

  const data = await fetchWithAuth(`/api/admin/companies/${currentCompany.id}/conversations`);

  document.getElementById("contentArea").innerHTML = `
    <div class="panel-card">
      <h3>Conversaciones recientes</h3>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Canal</th>
            <th>Última actividad</th>
            <th>Mensajes</th>
            <th>Acción</th>
          </tr>
        </thead>
        <tbody>
          ${data.data.map((conversation) => `
            <tr>
              <td>${conversation.id}</td>
              <td>${conversation.channel === "web" ? "🌐 Web" : "📱 WhatsApp"}</td>
              <td>${conversation.last_activity || conversation.started_at}</td>
              <td>${conversation.message_count}</td>
              <td><button class="btn btn-secondary" onclick="viewConversation(${conversation.id})">Ver mensajes</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function viewConversation(conversationId) {
  const messages = await fetchWithAuth(`/api/admin/conversations/${conversationId}/messages`);
  const content = messages.map((item) => `${item.role === "user" ? "👤" : "🤖"} ${item.content}`).join("\n\n");
  window.alert(content || "No hay mensajes disponibles.");
}

async function renderAnalytics() {
  if (!currentCompany) {
    document.getElementById("contentArea").innerHTML = '<div class="panel-card"><h3>Selecciona una empresa</h3><p>Debes escoger una empresa para analizar sus métricas.</p></div>';
    return;
  }

  const stats = await fetchWithAuth(`/api/admin/stats/companies/${currentCompany.id}`);

  document.getElementById("contentArea").innerHTML = `
    <div class="stats-grid">
      ${renderCard("Conversaciones", stats.total_conversations)}
      ${renderCard("Mensajes", stats.total_messages)}
      ${renderCard("Última semana", stats.messages_last_7_days)}
      ${renderCard("Activas", stats.active_conversations)}
    </div>
    <div class="panel-card">
      <h3>Recomendaciones</h3>
      <ul class="list">
        ${stats.active_conversations === 0 ? "<li>⚠️ No hay conversaciones activas. Revisa el canal o promueve tu bot.</li>" : "<li>✅ Hay conversaciones activas en este momento.</li>"}
        ${stats.messages_last_7_days < 10 ? "<li>⚠️ El volumen de mensajes es bajo. Considera revisar la conectividad y la experiencia del bot.</li>" : "<li>📈 El crecimiento de mensajes es saludable.</li>"}
        <li>💡 Mantén el prompt del sistema alineado con la personalidad de tu marca.</li>
      </ul>
    </div>
  `;
}

if (token) {
  toggleShell(true);
  loadCompanies().then(() => loadSection("dashboard"));
}
