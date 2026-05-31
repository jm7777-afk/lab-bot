// components.js - pequeños componentes reutilizables
export function showToast(message, type = 'success') {
  const containerId = 'toastContainer';
  let container = document.getElementById(containerId);
  if (!container) {
    container = document.createElement('div');
    container.id = containerId;
    container.style.position = 'fixed';
    container.style.right = '20px';
    container.style.bottom = '20px';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}
