(function () {
  const config = JSON.parse(document.getElementById("app-config").dataset.config);
  const searchUrl = config.searchUrl;

  const cart = new Map();
  const searchInput = document.getElementById("product-search");
  const searchButton = document.getElementById("search-button");
  const searchResults = document.getElementById("search-results");
  const searchHint = document.getElementById("search-hint");
  const scanBanner = document.getElementById("scan-banner");
  const scanBannerIcon = document.getElementById("scan-banner-icon");
  const resultsCount = document.getElementById("results-count");
  const cartLines = document.getElementById("cart-lines");
  const cartItemsInput = document.getElementById("cart-items");
  const discountInput = document.getElementById("descuento");
  const discountLabel = document.getElementById("discount-label");
  const confirmButton = document.getElementById("confirm-button");
  const confirmIcon = document.getElementById("confirm-icon");
  const confirmLabel = document.getElementById("confirm-label");
  const clearCartButton = document.getElementById("clear-cart");
  const cartCount = document.getElementById("cart-count");
  const subtotalLabel = document.getElementById("subtotal-label");
  const igvLabel = document.getElementById("igv-label");
  const totalLabel = document.getElementById("total-label");
  const efectivoWrapper = document.getElementById("efectivo-wrapper");
  const efectivoInput = document.getElementById("efectivo-recibido");
  const vueltoLabel = document.getElementById("vuelto-label");
  const vueltoCaption = document.getElementById("vuelto-caption");
  const saleForm = document.getElementById("sale-form");
  let lastResults = new Map();
  let currentTotal = 0;
  let scanBannerTimeout = null;

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[char]));
  }

  function money(value) {
    return `S/. ${Number(value).toFixed(2)}`;
  }

  function isEfectivoSelected() {
    const checked = document.querySelector('input[name="metodo_pago"]:checked');
    return !checked || checked.value === "EFECTIVO";
  }

  function setScanStatus(type, message) {
    const styles = {
      neutral: { classes: "bg-slate-50 dark:bg-white/5 text-text-secondary", icon: "info" },
      success: { classes: "bg-success/10 text-success", icon: "check_circle" },
      warning: { classes: "bg-amber-50 dark:bg-amber-500/10 text-warning", icon: "priority_high" },
      error: { classes: "bg-red-50 dark:bg-red-500/10 text-error", icon: "error" },
    };
    const style = styles[type] || styles.neutral;
    scanBanner.className = `mt-sm flex items-center gap-xs rounded-lg px-md py-sm text-sm font-medium transition-colors ${style.classes}`;
    scanBannerIcon.textContent = style.icon;
    searchHint.textContent = message;

    if (scanBannerTimeout) clearTimeout(scanBannerTimeout);
    if (type === "success") {
      scanBannerTimeout = setTimeout(() => {
        setScanStatus("neutral", "Listo para el siguiente escaneo o busqueda.");
      }, 2500);
    }
  }

  function emptyResults(message, icon = "manage_search") {
    searchResults.innerHTML = `
      <div class="px-lg py-sm text-center">
        <span class="material-symbols-outlined text-[28px] text-text-secondary" aria-hidden="true">${icon}</span>
        <p class="text-sm text-text-secondary mt-xs">${escapeHtml(message)}</p>
      </div>
    `;
  }

  function renderResults(products) {
    lastResults = new Map(products.map(product => [String(product.id), product]));
    resultsCount.textContent = products.length ? `${products.length} resultado(s)` : "Sin resultados";

    if (!products.length) {
      emptyResults("No se encontraron productos con stock disponible.", "search_off");
      return;
    }

    searchResults.innerHTML = products.map(product => `
      <div class="px-lg py-md flex flex-col md:flex-row md:items-center md:justify-between gap-md hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
        <div class="min-w-0">
          <p class="font-semibold text-text-primary dark:text-[#E8E9EC] truncate">${escapeHtml(product.nombre)}</p>
          <p class="text-sm text-text-secondary">${escapeHtml(product.codigo_barra || "Sin codigo")} - ${escapeHtml(product.categoria)}</p>
          <p class="text-caption-xs text-text-secondary mt-xs">Stock disponible: ${product.stock_actual} ${escapeHtml(product.unidad)}</p>
        </div>
        <div class="flex items-center justify-between md:justify-end gap-md">
          <span class="font-mono text-lg font-bold text-text-primary dark:text-[#E8E9EC]">${money(product.precio_venta)}</span>
          <button type="button" class="add-product inline-flex min-h-[44px] items-center gap-xs rounded-lg bg-primary px-md py-sm text-sm font-semibold text-white hover:bg-primary-hover focus:ring-4 focus:ring-primary/20 transition-colors"
                  data-id="${product.id}">
            <span class="material-symbols-outlined text-[18px]" aria-hidden="true">add_shopping_cart</span>
            Agregar
          </button>
        </div>
      </div>
    `).join("");
  }

  async function searchProducts(autoAdd = false) {
    const query = searchInput.value.trim();
    if (!query) {
      lastResults = new Map();
      resultsCount.textContent = "Sin busqueda activa";
      emptyResults("Busca un producto para agregarlo al carrito.");
      setScanStatus("neutral", "Con lector de barras: apunta al campo y escanea. Si el codigo coincide, se agrega con Enter.");
      return;
    }

    searchButton.disabled = true;
    setScanStatus("neutral", "Buscando producto...");
    try {
      const response = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}`, {
        headers: {"X-Requested-With": "XMLHttpRequest"},
      });
      const data = await response.json();

      if (autoAdd && data.match_type === "barcode" && data.results.length === 1) {
        addToCart(data.results[0]);
        searchInput.value = "";
        lastResults = new Map();
        resultsCount.textContent = "Agregado por codigo";
        emptyResults("Producto agregado. Puedes escanear el siguiente.", "task_alt");
        setScanStatus("success", `${data.results[0].nombre} agregado al carrito.`);
        searchInput.focus();
        return;
      }

      renderResults(data.results);
      if (!data.results.length) {
        setScanStatus("warning", "No se encontro ningun producto con ese codigo o nombre.");
      } else {
        setScanStatus("neutral", data.match_type === "barcode"
          ? "Codigo encontrado. Presiona Agregar o Enter para sumar otra unidad."
          : "Selecciona un resultado para agregarlo al carrito.");
      }
    } catch (error) {
      emptyResults("No se pudo realizar la busqueda. Intenta nuevamente.", "error");
      setScanStatus("error", "Error de busqueda. Revisa tu conexion e intenta de nuevo.");
    } finally {
      searchButton.disabled = false;
    }
  }

  function addToCart(product) {
    const id = String(product.id);
    const current = cart.get(id);
    if (current) {
      if (current.cantidad < current.stock_actual) {
        current.cantidad += 1;
        setScanStatus("success", `${current.nombre}: cantidad ${current.cantidad}.`);
      } else {
        setScanStatus("warning", `${current.nombre} ya alcanzo el stock disponible.`);
      }
    } else {
      cart.set(id, {...product, cantidad: 1});
      setScanStatus("success", `${product.nombre} agregado al carrito.`);
    }
    renderCart();
  }

  function changeQuantity(id, delta) {
    const item = cart.get(String(id));
    if (!item) return;
    item.cantidad = Math.max(1, Math.min(item.cantidad + delta, item.stock_actual));
    renderCart();
  }

  function updateEfectivoUI() {
    const efectivoActivo = isEfectivoSelected();
    efectivoWrapper.classList.toggle("hidden", !efectivoActivo);
    if (!efectivoActivo) return;

    const recibido = Number(efectivoInput.value || 0);
    const vuelto = recibido - currentTotal;
    const shortfall = currentTotal - recibido;

    vueltoLabel.classList.remove("text-success", "text-error", "text-text-primary", "dark:text-[#E8E9EC]");
    vueltoCaption.classList.remove("text-success", "text-error");

    if (!efectivoInput.value || recibido === 0) {
      vueltoLabel.textContent = money(0);
      vueltoLabel.classList.add("text-text-primary", "dark:text-[#E8E9EC]");
      vueltoCaption.textContent = "Vuelto";
    } else if (recibido >= currentTotal) {
      vueltoLabel.textContent = money(vuelto);
      vueltoLabel.classList.add("text-success");
      vueltoCaption.textContent = "Vuelto: " + money(vuelto);
      vueltoCaption.classList.add("text-success");
    } else {
      vueltoLabel.textContent = money(recibido);
      vueltoLabel.classList.add("text-error");
      vueltoCaption.textContent = "Falta " + money(shortfall);
      vueltoCaption.classList.add("text-error");
    }
  }

  function canConfirm(itemsCount) {
    const hasCaja = Boolean(document.querySelector('input[name="caja"]:checked'));
    if (itemsCount === 0 || !hasCaja) return false;
    if (isEfectivoSelected()) {
      const recibido = Number(efectivoInput.value || 0);
      return recibido >= currentTotal;
    }
    return true;
  }

  function renderCart() {
    const items = Array.from(cart.values());
    if (!items.length) {
      cartLines.innerHTML = '<div class="px-md py-lg text-center text-sm text-text-secondary">El carrito esta vacio.</div>';
    } else {
      cartLines.innerHTML = items.map(item => `
        <div class="px-md py-sm flex flex-col gap-sm">
          <div class="flex items-start justify-between gap-sm">
            <div class="min-w-0">
              <p class="text-sm font-semibold text-text-primary dark:text-[#E8E9EC] truncate">${escapeHtml(item.nombre)}</p>
              <p class="text-caption-xs text-text-secondary">${escapeHtml(item.codigo_barra || "Sin codigo")} - Stock ${item.stock_actual}</p>
            </div>
            <button type="button" class="remove-product rounded-lg p-xs min-h-[44px] min-w-[44px] flex items-center justify-center text-text-secondary hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-error" data-id="${item.id}" aria-label="Quitar ${escapeHtml(item.nombre)}">
              <span class="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
            </button>
          </div>
          <div class="flex items-center justify-between gap-sm">
            <div class="inline-flex items-center rounded-lg border border-border-subtle dark:border-white/10 overflow-hidden">
              <button type="button" class="qty-minus min-h-[44px] min-w-[44px] flex items-center justify-center text-text-secondary hover:bg-slate-50 dark:hover:bg-white/5" data-id="${item.id}" aria-label="Restar unidad">
                <span class="material-symbols-outlined text-[20px]" aria-hidden="true">remove</span>
              </button>
              <input type="number" min="1" max="${item.stock_actual}" value="${item.cantidad}" data-id="${item.id}" aria-label="Cantidad de ${escapeHtml(item.nombre)}"
                     class="cart-qty w-14 min-h-[44px] border-0 px-xs py-xs text-base font-mono text-center focus:ring-0 dark:bg-[#15171C] dark:text-[#E8E9EC]">
              <button type="button" class="qty-plus min-h-[44px] min-w-[44px] flex items-center justify-center text-text-secondary hover:bg-slate-50 dark:hover:bg-white/5" data-id="${item.id}" aria-label="Sumar unidad">
                <span class="material-symbols-outlined text-[20px]" aria-hidden="true">add</span>
              </button>
            </div>
            <div class="text-right">
              <p class="font-mono text-sm font-bold text-text-primary dark:text-[#E8E9EC]">${money(Number(item.precio_venta) * item.cantidad)}</p>
              <p class="text-caption-xs text-text-secondary">${money(item.precio_venta)} c/u</p>
            </div>
          </div>
        </div>
      `).join("");
    }

    const importe = items.reduce((sum, item) => sum + Number(item.precio_venta) * item.cantidad, 0);
    const discount = Math.max(Number(discountInput.value || 0), 0);
    const total = Math.max(importe - discount, 0);
    const subtotal = total / 1.18;
    const igv = total - subtotal;
    const totalUnits = items.reduce((sum, item) => sum + item.cantidad, 0);
    currentTotal = total;

    subtotalLabel.textContent = money(subtotal);
    igvLabel.textContent = money(igv);
    discountLabel.textContent = money(discount);
    totalLabel.textContent = money(total);
    cartCount.textContent = `${items.length} producto(s), ${totalUnits} unidad(es)`;
    cartItemsInput.value = JSON.stringify(items.map(item => ({
      producto_id: item.id,
      cantidad: item.cantidad,
    })));

    updateEfectivoUI();
    confirmButton.disabled = !canConfirm(items.length);
    clearCartButton.disabled = items.length === 0;
  }

  function init() {
    searchButton.addEventListener("click", () => searchProducts(false));
    searchInput.addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        searchProducts(true);
      }
    });
    searchResults.addEventListener("click", event => {
      const button = event.target.closest(".add-product");
      if (!button) return;
      const product = lastResults.get(String(button.dataset.id));
      if (product) addToCart(product);
    });
    cartLines.addEventListener("input", event => {
      if (!event.target.classList.contains("cart-qty")) return;
      const item = cart.get(String(event.target.dataset.id));
      if (!item) return;
      item.cantidad = Math.max(1, Math.min(Number(event.target.value || 1), item.stock_actual));
      event.target.value = item.cantidad;
      renderCart();
    });
    cartLines.addEventListener("click", event => {
      const removeButton = event.target.closest(".remove-product");
      const minusButton = event.target.closest(".qty-minus");
      const plusButton = event.target.closest(".qty-plus");
      if (removeButton) {
        cart.delete(String(removeButton.dataset.id));
        renderCart();
      }
      if (minusButton) changeQuantity(minusButton.dataset.id, -1);
      if (plusButton) changeQuantity(plusButton.dataset.id, 1);
    });
    clearCartButton.addEventListener("click", () => {
      cart.clear();
      renderCart();
      searchInput.focus();
    });
    discountInput.addEventListener("input", renderCart);
    efectivoInput.addEventListener("input", () => {
      updateEfectivoUI();
      confirmButton.disabled = !canConfirm(cart.size);
    });
    document.querySelectorAll('input[name="caja"]').forEach(input => input.addEventListener("change", renderCart));
    document.querySelectorAll('.metodo-pago-input').forEach(input => input.addEventListener("change", renderCart));

    saleForm.addEventListener("submit", event => {
      if (!cart.size) {
        event.preventDefault();
        setScanStatus("error", "Agrega productos al carrito antes de confirmar.");
        searchInput.focus();
        return;
      }
      if (!canConfirm(cart.size)) {
        event.preventDefault();
        setScanStatus("error", "Verifica el efectivo recibido: debe cubrir el total de la venta.");
        efectivoInput.focus();
        return;
      }
      confirmButton.disabled = true;
      confirmIcon.textContent = "progress_activity";
      confirmIcon.classList.add("animate-spin");
      confirmLabel.textContent = "Procesando venta...";
    });

    document.addEventListener("keydown", event => {
      if (event.key === "F2") {
        event.preventDefault();
        searchInput.focus();
        searchInput.select();
        return;
      }
      if (event.key === "F9") {
        event.preventDefault();
        if (!confirmButton.disabled) saleForm.requestSubmit(confirmButton);
        return;
      }
      if (event.key === "Escape") {
        if (document.activeElement === searchInput || searchInput.value) {
          event.preventDefault();
          searchInput.value = "";
          searchProducts(false);
          searchInput.focus();
        }
      }
    });

    searchInput.focus();
    renderCart();
  }

  window.NuevaVenta = { init };
})();