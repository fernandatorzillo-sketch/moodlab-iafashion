(function () {
  const CONFIG = {
    API_BASE:
      (window.MOODLAB_CLOSET_CONFIG && window.MOODLAB_CLOSET_CONFIG.API_BASE) ||
      "https://closet-moodlab.onrender.com",
    ROOT_ID: "moodlab-account-closet-root",
    TITLE: "Seu Closet",
    SUBTITLE: "Suas peças, combinações e sugestões em um só lugar.",
  };

  function safeText(value) {
    return value == null ? "" : String(value);
  }

  function escapeHtml(str) {
    return safeText(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function injectStyles() {
    if (document.getElementById("moodlab-account-closet-styles")) return;

    const style = document.createElement("style");
    style.id = "moodlab-account-closet-styles";
    style.innerHTML = `
      #${CONFIG.ROOT_ID} {
        max-width: 1280px;
        margin: 32px auto;
        padding: 0 16px;
        font-family: Arial, sans-serif;
      }

      .ml-closet-shell {
        background: #fff;
        border: 1px solid #e9dfcf;
        border-radius: 18px;
        padding: 28px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.04);
      }

      .ml-closet-header h1 {
        margin: 0 0 8px 0;
        font-size: 34px;
        line-height: 1.1;
        color: #2f2a24;
      }

      .ml-closet-header p {
        margin: 0;
        color: #7a6f63;
        font-size: 15px;
      }

      .ml-closet-stats {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin: 24px 0 28px;
      }

      .ml-stat {
        min-width: 150px;
        background: #faf7f2;
        border: 1px solid #eadfce;
        border-radius: 14px;
        padding: 14px 16px;
      }

      .ml-stat-label {
        font-size: 12px;
        text-transform: uppercase;
        color: #9a8f83;
        margin-bottom: 6px;
      }

      .ml-stat-value {
        font-size: 22px;
        color: #2f2a24;
        font-weight: 700;
      }

      .ml-section {
        margin-top: 32px;
      }

      .ml-section h2 {
        margin: 0 0 14px;
        font-size: 24px;
        color: #2f2a24;
      }

      .ml-filters {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 18px;
      }

      .ml-filter-btn {
        background: #fff;
        border: 1px solid #d8c8af;
        color: #7c6c52;
        border-radius: 999px;
        padding: 10px 16px;
        font-size: 14px;
        cursor: pointer;
      }

      .ml-filter-btn.active {
        background: #b7a36b;
        color: #fff;
        border-color: #b7a36b;
      }

      .ml-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 18px;
      }

      .ml-card {
        background: #fff;
        border: 1px solid #eadfce;
        border-radius: 16px;
        overflow: hidden;
      }

      .ml-card-image {
        width: 100%;
        aspect-ratio: 3 / 4;
        background: #f8f3ec;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
      }

      .ml-card-image img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }

      .ml-card-body {
        padding: 14px;
      }

      .ml-card-category {
        font-size: 11px;
        text-transform: uppercase;
        color: #9a8f83;
        margin-bottom: 6px;
      }

      .ml-card-title {
        font-size: 16px;
        line-height: 1.35;
        color: #2f2a24;
        min-height: 44px;
        margin-bottom: 8px;
      }

      .ml-card-reason {
        font-size: 13px;
        color: #7a6f63;
        line-height: 1.4;
        margin-bottom: 12px;
      }

      .ml-card-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }

      .ml-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        padding: 10px 14px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
      }

      .ml-btn-primary {
        background: #b7a36b;
        color: #fff;
        border: 1px solid #b7a36b;
      }

      .ml-btn-secondary {
        background: #fff;
        color: #7c6c52;
        border: 1px solid #d8c8af;
      }

      .ml-look-box {
        border: 1px solid #eadfce;
        border-radius: 16px;
        padding: 18px;
        background: #fcfaf7;
      }

      .ml-look-title {
        margin: 0 0 14px;
        font-size: 18px;
        color: #2f2a24;
      }

      .ml-empty,
      .ml-loading,
      .ml-error {
        border-radius: 16px;
        padding: 18px;
        background: #faf7f2;
        border: 1px solid #eadfce;
        color: #7a6f63;
      }

      .ml-error {
        color: #a04f4f;
        background: #fff6f6;
        border-color: #efcaca;
      }
    `;
    document.head.appendChild(style);
  }

  function getRoot() {
    let root = document.getElementById(CONFIG.ROOT_ID);
    if (!root) {
      root = document.createElement("div");
      root.id = CONFIG.ROOT_ID;
      const target =
        document.querySelector(".account__container.container") ||
        document.querySelector(".account__main") ||
        document.querySelector(".account") ||
        document.querySelector(".container") ||
        document.body;
      target.appendChild(root);
    }
    return root;
  }

  function renderLoading(root) {
    root.innerHTML = `
      <div class="ml-closet-shell">
        <div class="ml-loading">Carregando seu closet...</div>
      </div>
    `;
  }

  function renderError(root, message) {
    root.innerHTML = `
      <div class="ml-closet-shell">
        <div class="ml-error">
          <strong>Não foi possível carregar seu closet.</strong><br />
          ${escapeHtml(message || "Tente novamente em instantes.")}
        </div>
      </div>
    `;
  }

  function getLoggedEmail() {
    try {
      const fromCheckout =
        window.vtexjs &&
        window.vtexjs.checkout &&
        window.vtexjs.checkout.orderForm &&
        window.vtexjs.checkout.orderForm.clientProfileData &&
        window.vtexjs.checkout.orderForm.clientProfileData.email;

      if (fromCheckout) return String(fromCheckout).trim();

      const pageText = document.body ? document.body.innerText : "";
      const match = pageText.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
      if (match && match[0]) return match[0].trim();

      const mailto = document.querySelector('a[href^="mailto:"]');
      if (mailto) {
        const href = mailto.getAttribute("href") || "";
        const email = href.replace(/^mailto:/i, "").trim();
        if (email) return email;
      }

      return "";
    } catch (e) {
      return "";
    }
  }

  async function waitForEmail(maxAttempts, delayMs) {
    for (let i = 0; i < maxAttempts; i++) {
      const email = getLoggedEmail();
      if (email) return email;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    return "";
  }

  async function fetchClosetData(email) {
    const response = await fetch(
      `${CONFIG.API_BASE}/api/v1/customer-closet/lookup`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ email: email }),
      }
    );

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }

    return response.json();
  }

  function buildStats(data) {
    const closetCount = Array.isArray(data.closet) ? data.closet.length : 0;
    const looksCount = Array.isArray(data.looks) ? data.looks.length : 0;
    const recsCount = Array.isArray(data.recommendations) ? data.recommendations.length : 0;
    const categories = new Set((data.closet || []).map((i) => safeText(i.category)).filter(Boolean));

    return `
      <div class="ml-closet-stats">
        <div class="ml-stat"><div class="ml-stat-label">Peças</div><div class="ml-stat-value">${closetCount}</div></div>
        <div class="ml-stat"><div class="ml-stat-label">Categorias</div><div class="ml-stat-value">${categories.size}</div></div>
        <div class="ml-stat"><div class="ml-stat-label">Looks</div><div class="ml-stat-value">${looksCount}</div></div>
        <div class="ml-stat"><div class="ml-stat-label">Sugestões</div><div class="ml-stat-value">${recsCount}</div></div>
      </div>
    `;
  }

  function buildCard(item, showReason) {
    const category = escapeHtml(item.category || item.department || "");
    const title = escapeHtml(item.name || "Produto");
    const reason = escapeHtml(item.reason || "");
    const image = item.image_url
      ? `<img src="${escapeHtml(item.image_url)}" alt="${title}" />`
      : `<div>Sem imagem</div>`;
    const url = item.url || "#";

    return `
      <div class="ml-card">
        <div class="ml-card-image">${image}</div>
        <div class="ml-card-body">
          <div class="ml-card-category">${category}</div>
          <div class="ml-card-title">${title}</div>
          ${showReason ? `<div class="ml-card-reason">${reason}</div>` : ""}
          <div class="ml-card-actions">
            <a class="ml-btn ml-btn-primary" href="${escapeHtml(url)}">Ver produto</a>
          </div>
        </div>
      </div>
    `;
  }

  function buildClosetSection(closet) {
    const items = Array.isArray(closet) ? closet : [];
    const categories = ["Todos"].concat(
      Array.from(new Set(items.map((item) => safeText(item.category)).filter(Boolean)))
    );

    return `
      <div class="ml-section" id="ml-closet-section">
        <h2>Meu Closet</h2>
        <div class="ml-filters" id="ml-closet-filters">
          ${categories
            .map(
              (category, index) => `
                <button class="ml-filter-btn ${index === 0 ? "active" : ""}" data-category="${escapeHtml(category)}" type="button">
                  ${escapeHtml(category)}
                </button>`
            )
            .join("")}
        </div>
        <div class="ml-grid" id="ml-closet-grid">
          ${
            items.length
              ? items
                  .map(
                    (item) => `
                    <div class="ml-closet-item" data-category="${escapeHtml(item.category || "")}">
                      ${buildCard(item, false)}
                    </div>`
                  )
                  .join("")
              : `<div class="ml-empty">Nenhuma peça encontrada no closet.</div>`
          }
        </div>
      </div>
    `;
  }

  function buildLooksSection(looks) {
    const list = Array.isArray(looks) ? looks : [];
    if (!list.length) {
      return `<div class="ml-section"><h2>Looks sugeridos</h2><div class="ml-empty">Ainda não encontramos combinações suficientes para montar looks.</div></div>`;
    }

    return `
      <div class="ml-section">
        <h2>Looks sugeridos</h2>
        ${list
          .map(
            (look) => `
            <div class="ml-look-box" style="margin-bottom:16px;">
              <h3 class="ml-look-title">${escapeHtml(look.title || "Look sugerido")}</h3>
              <div class="ml-grid">
                ${(look.items || []).map((item) => buildCard(item, false)).join("")}
              </div>
            </div>`
          )
          .join("")}
      </div>
    `;
  }

  function buildRecommendationsSection(recommendations) {
    const items = Array.isArray(recommendations) ? recommendations : [];

    return `
      <div class="ml-section">
        <h2>Recomendações para você</h2>
        ${
          items.length
            ? `<div class="ml-grid">${items.map((item) => buildCard(item, true)).join("")}</div>`
            : `<div class="ml-empty">Sem recomendações no momento.</div>`
        }
      </div>
    `;
  }

  function attachClosetFilters(root) {
    const filterWrap = root.querySelector("#ml-closet-filters");
    const grid = root.querySelector("#ml-closet-grid");
    if (!filterWrap || !grid) return;

    filterWrap.addEventListener("click", function (event) {
      const btn = event.target.closest(".ml-filter-btn");
      if (!btn) return;

      const category = btn.getAttribute("data-category") || "Todos";

      filterWrap.querySelectorAll(".ml-filter-btn").forEach((node) => node.classList.remove("active"));
      btn.classList.add("active");

      grid.querySelectorAll(".ml-closet-item").forEach((item) => {
        const itemCategory = item.getAttribute("data-category") || "";
        const show = category === "Todos" || itemCategory === category;
        item.style.display = show ? "" : "none";
      });
    });
  }

  function renderAccountCloset(root, data) {
    const customerName = safeText(data.customer && data.customer.name) || "Cliente";

    root.innerHTML = `
      <div class="ml-closet-shell">
        <div class="ml-closet-header">
          <h1>${CONFIG.TITLE}</h1>
          <p>${CONFIG.SUBTITLE}</p>
          <p style="margin-top:8px;"><strong>${escapeHtml(customerName)}</strong></p>
        </div>
        ${buildStats(data)}
        ${buildClosetSection(data.closet)}
        ${buildLooksSection(data.looks)}
        ${buildRecommendationsSection(data.recommendations)}
      </div>
    `;

    attachClosetFilters(root);
  }

  async function bootstrap() {
    injectStyles();
    const root = getRoot();
    renderLoading(root);

    try {
      const email = await waitForEmail(20, 1000);
      if (!email) {
        renderError(root, "Não foi possível identificar o cliente logado.");
        return;
      }

      const data = await fetchClosetData(email);
      renderAccountCloset(root, data);
    } catch (error) {
      renderError(root, error && error.message ? error.message : "Erro inesperado.");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();