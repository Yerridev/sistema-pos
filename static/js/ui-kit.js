(function () {
  function _getCsrfToken() {
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function apiFetch(url, options) {
    options = options || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    var csrfToken = _getCsrfToken();
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    var fetchOpts = Object.assign({}, options, { headers: headers });
    if (options.body) fetchOpts.body = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
    return fetch(url, fetchOpts).then(function (res) {
      return res.json().then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function showToast(message, type) {
    type = type || 'success';
    var container = document.createElement('div');
    container.className = 'fixed top-5 right-5 z-[200] flex items-center gap-sm px-lg py-md rounded-xl shadow-lg text-white text-sm font-medium transition-all';
    container.style.backgroundColor = type === 'success' ? '#25D366' : '#EA0038';
    var icon = document.createElement('span');
    icon.className = 'material-symbols-outlined text-[18px]';
    icon.textContent = type === 'success' ? 'check_circle' : 'error';
    var msg = document.createElement('span');
    msg.textContent = message;
    container.appendChild(icon);
    container.appendChild(msg);
    document.body.appendChild(container);
    setTimeout(function () {
      container.remove();
    }, 3000);
  }

  function setLoading(element, isLoading) {
    if (!element) return;
    element.disabled = isLoading;
    var txtEl = element.querySelector('[data-loading-text]');
    if (txtEl) txtEl.textContent = isLoading ? 'Guardando...' : 'Guardar';
    var icoEl = element.querySelector('[data-loading-icon]');
    var spinnerEl = element.querySelector('[data-spinner]');
    if (icoEl) icoEl.classList.toggle('hidden', isLoading);
    if (spinnerEl) spinnerEl.classList.toggle('hidden', !isLoading);
  }

  function openModal(id) {
    var modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    var focusable = modal.querySelector('input, textarea, select, button');
    if (focusable) focusable.focus();
  }

  function closeModal(id) {
    var modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }

  window.UIKit = {
    apiFetch: apiFetch,
    showToast: showToast,
    setLoading: setLoading,
    openModal: openModal,
    closeModal: closeModal,
  };
})();