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
        max-width: 1440px;
        margin: 8px auto 32px;
        padding: 0 24px;
        font-family: Arial, sans-serif;
      }

      .ml-closet-shell {
        background: #fff;
        border: 1px solid #e9dfcf;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.03);
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

      @media (max-width: 768px) {
        #${CONFIG.ROOT_ID} {
          padding: 0 16px;
          margin: 8px auto 24px;
        }

        .ml-closet-shell {
          padding: 18px;
        }

        .ml-closet-header h1 {
          font-size: 28px;
        }

        .ml-grid {
          grid-template-columns: 1fr 1fr;
        }
      }

      @media (max-width: 540px) {
        .ml-grid {
          grid-template-columns: 1fr;
        }
      }

      .ml-card-price {
        font-size: 15px;
        font-weight: 600;
        color: #5a4a3a;
        margin: 4px 0 8px;
      }
      .ml-look-box {
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #e8e0d8;
      }
      .ml-look-title {
        font-size: 16px;
        font-weight: 600;
        color: #3a2e24;
        margin: 0 0 12px;
      }
      .ml-shopper-intro { color: #6a5a4a; margin-bottom: 20px; font-size: 14px; }
      .ml-shopper-question { margin-bottom: 20px; }
      .ml-shopper-question label { display: block; font-weight: 600; font-size: 14px; color: #3a2e24; margin-bottom: 10px; }
      .ml-shopper-options { display: flex; flex-wrap: wrap; gap: 8px; }
      .ml-option-btn {
        padding: 8px 16px; border: 1.5px solid #c8b89a; border-radius: 20px;
        background: #fff; color: #5a4a3a; font-size: 13px; cursor: pointer; transition: all 0.2s;
      }
      .ml-option-btn:hover { background: #f5ece0; }
      .ml-option-btn.selected { background: #8a6a3a; border-color: #8a6a3a; color: #fff; }
      .ml-shopper-submit { margin-top: 8px; width: 100%; max-width: 280px; }
      .ml-shopper-submit:disabled { opacity: 0.4; cursor: not-allowed; }
      .ml-shopper-result { margin-top: 24px; }
      .ml-shopper-perfil {
        background: #f5ece0; border-left: 3px solid #8a6a3a;
        padding: 12px 16px; border-radius: 6px; font-size: 14px; color: #3a2e24; margin-bottom: 16px;
      }
      .ml-shopper-dicas { font-size: 13px; color: #6a5a4a; margin: 0 0 16px 16px; }
      .ml-shopper-dicas li { margin-bottom: 4px; }
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
        document.querySelector(".account-main") ||
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

  function isValidEmail(str) {
    return typeof str === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str.trim());
  }

  function getLoggedEmailSync() {
    try {
      const fromCheckout =
        window.vtexjs &&
        window.vtexjs.checkout &&
        window.vtexjs.checkout.orderForm &&
        window.vtexjs.checkout.orderForm.clientProfileData &&
        window.vtexjs.checkout.orderForm.clientProfileData.email;
      if (isValidEmail(fromCheckout)) return String(fromCheckout).trim();

      const fromTheme =
        window.aguadecoco &&
        (window.aguadecoco.userEmail || window.aguadecoco.email ||
         (window.aguadecoco.user && window.aguadecoco.user.email));
      if (isValidEmail(fromTheme)) return String(fromTheme).trim();

      if (isValidEmail(window.janus_app_user_email)) return String(window.janus_app_user_email).trim();

      const metaEmail = document.querySelector('meta[name="user-email"], [data-user-email]');
      if (metaEmail) {
        const val = metaEmail.getAttribute("content") || metaEmail.getAttribute("data-user-email");
        if (isValidEmail(val)) return val.trim();
      }

      const pageText = document.body ? document.body.innerText : "";
      const emailRegex = /\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b/gi;
      let m;
      while ((m = emailRegex.exec(pageText)) !== null) {
        const candidate = m[0].trim().toLowerCase();
        if (
          !candidate.includes("vtex.com.br") &&
          !candidate.includes("@aguadecoco.com.br") &&
          !candidate.includes("@sentry") &&
          !candidate.includes("@facebook") &&
          !candidate.includes("@google") &&
          !candidate.includes("@pinterest") &&
          isValidEmail(candidate)
        ) {
          return candidate;
        }
      }

      return "";
    } catch (e) {
      return "";
    }
  }

  async function getEmailFromSession() {
    try {
      const res = await fetch("/api/sessions?items=profile.email", {
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (!res.ok) return "";
      const data = await res.json();
      const email =
        data &&
        data.namespaces &&
        data.namespaces.profile &&
        data.namespaces.profile.email &&
        data.namespaces.profile.email.value;
      if (isValidEmail(email)) return String(email).trim();
      return "";
    } catch (e) {
      return "";
    }
  }

  async function waitForEmail(maxAttempts, delayMs) {
    const sessionEmail = await getEmailFromSession();
    if (sessionEmail) return sessionEmail;

    for (let i = 0; i < maxAttempts; i++) {
      const email = getLoggedEmailSync();
      if (email) return email;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    return "";
  }

  async function fetchClosetData(email) {
    const response = await fetch(`${CONFIG.API_BASE}/api/v1/customer-closet/lookup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ email: email }),
    });

    const text = await response.text();

    if (!response.ok) {
      throw new Error(text || `HTTP ${response.status}`);
    }

    try {
      return JSON.parse(text);
    } catch (e) {
      throw new Error("Resposta inválida da API.");
    }
  }

  function normalizeApiData(raw) {
    const customer =
      raw.customer ||
      (raw.cliente
        ? {
            name: raw.cliente.nome || raw.cliente.name || "Cliente",
            email: raw.cliente.email || "",
          }
        : {
            name: "Cliente",
            email: "",
          });

    const closet = raw.closet || raw.closet_products || [];
    const looks = raw.looks || [];
    const recommendations = raw.recommendations || [];

    return {
      customer: customer,
      closet: Array.isArray(closet) ? closet : [],
      looks: Array.isArray(looks) ? looks : [],
      recommendations: Array.isArray(recommendations) ? recommendations : [],
      found: raw.found,
      debug: raw.debug || {},
    };
  }

  function buildStats(data) {
    const closetCount = Array.isArray(data.closet) ? data.closet.length : 0;
    const looksCount = Array.isArray(data.looks) ? data.looks.length : 0;
    const recsCount = Array.isArray(data.recommendations) ? data.recommendations.length : 0;

    const categories = new Set(
      (data.closet || [])
        .map((i) => safeText(i.category || i.categoria || i.department))
        .filter(Boolean)
    );

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
    const category = escapeHtml(item.category || item.categoria || item.department || "");
    const title = escapeHtml(item.name || item.nome || "Produto");
    const reason = escapeHtml(item.motivo || item.reason || "");
    const rawImageUrl = item.image_url || item.imagem_url || "";
    const imageUrl = rawImageUrl
      .replace(/\/arquivos\/ids\/(\d+)(?:-\d+-\d+)?(\/[^?#]*)/, "/arquivos/ids/$1-500-500$2");
    const isVtexImage = imageUrl && (
      imageUrl.includes("lojaaguadecoco.vteximg.com.br") ||
      imageUrl.includes("aguadecoco.vteximg.com.br") ||
      imageUrl.includes("vtexassets.com")
    );
    const finalImageUrl = isVtexImage
      ? `${CONFIG.API_BASE}/api/v1/image-proxy?url=${encodeURIComponent(imageUrl)}`
      : imageUrl;

    // Não mostra recomendação sem imagem
    if (showReason && !finalImageUrl) return "";

    const placeholderSvg = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='267' viewBox='0 0 200 267'%3E%3Crect width='200' height='267' fill='%23f3ede4'/%3E%3Ctext x='100' y='140' font-family='Arial' font-size='12' fill='%23b0a090' text-anchor='middle'%3ESem imagem%3C/text%3E%3C/svg%3E`;
    const image = finalImageUrl
      ? `<img src="${finalImageUrl}" alt="${escapeHtml(title)}" loading="lazy" onerror="this.onerror=null;this.src='${placeholderSvg}';" />`
      : `<img src="${placeholderSvg}" alt="Sem imagem" />`;

    const url = item.url || item.link_produto || item.product_url || "#";
    const rawPrice = item.price || item.preco || 0;
    const priceHtml = rawPrice > 0
      ? `<div class="ml-card-price">${Number(rawPrice).toLocaleString("pt-BR", {style:"currency", currency:"BRL"})}</div>`
      : "";

    return `
      <div class="ml-card">
        <div class="ml-card-image">${image}</div>
        <div class="ml-card-body">
          <div class="ml-card-category">${category}</div>
          <div class="ml-card-title">${title}</div>
          ${priceHtml}
          ${showReason && reason ? `<div class="ml-card-reason">${reason}</div>` : ""}
          <div class="ml-card-actions">
            <a class="ml-btn ml-btn-primary" href="${url}" target="_blank" rel="noopener">Ver produto</a>
          </div>
        </div>
      </div>
    `;
  }


  function buildClosetSection(closet) {
    const items = Array.isArray(closet) ? closet : [];
    const categories = ["Todos"].concat(
      Array.from(
        new Set(
          items
            .map((item) => safeText(item.category || item.categoria || item.department))
            .filter(Boolean)
        )
      )
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
                    <div class="ml-closet-item" data-category="${escapeHtml(item.category || item.categoria || item.department || "")}">
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

  function generateLooksFromCloset(closet, recommendations) {
    // Monta looks combinando peças do closet por categoria/departamento
    const pieces = Array.isArray(closet) ? closet.filter(i => i.image_url || i.imagem_url) : [];
    const recs   = Array.isArray(recommendations) ? recommendations.filter(i => i.image_url || i.imagem_url) : [];

    const byType = {};
    pieces.forEach(item => {
      const key = (item.category || item.categoria || item.department || "outros").toLowerCase();
      if (!byType[key]) byType[key] = [];
      byType[key].push({...item, _source: "closet"});
    });
    recs.forEach(item => {
      const key = (item.category || item.categoria || item.department || "outros").toLowerCase();
      if (!byType[key]) byType[key] = [];
      byType[key].push({...item, _source: "rec"});
    });

    const LOOK_RECIPES = [
      {title: "Look Praia", keys: ["beachwear", "maio", "biquini", "saida_praia", "saida de praia"], min: 2},
      {title: "Look Casual",  keys: ["vestido", "blusa", "calca", "short", "saia", "camisa", "camiseta"], min: 2},
      {title: "Look Completo", keys: [], min: 2},
    ];

    const looks = [];
    for (const recipe of LOOK_RECIPES) {
      const pool = [];
      if (recipe.keys.length) {
        recipe.keys.forEach(k => { if (byType[k]) pool.push(...byType[k]); });
      } else {
        Object.values(byType).forEach(arr => pool.push(...arr));
      }
      // Deduplica por sku_id
      const seen = new Set();
      const unique = pool.filter(i => {
        const id = i.sku_id || i.id || i.name;
        if (seen.has(id)) return false;
        seen.add(id);
        return true;
      });
      if (unique.length >= recipe.min) {
        looks.push({title: recipe.title, items: unique.slice(0, 4)});
      }
      if (looks.length >= 2) break;
    }
    return looks;
  }

  function buildLooksSection(looks, closet, recommendations) {
    const generated = (Array.isArray(looks) && looks.length)
      ? looks
      : generateLooksFromCloset(closet, recommendations);

    if (!generated.length) {
      return `<div class="ml-section"><h2>Looks sugeridos</h2><div class="ml-empty">Adicione mais peças ao seu closet para vermos combinações.</div></div>`;
    }

    return `
      <div class="ml-section">
        <h2>Looks sugeridos</h2>
        ${generated.map(look => `
          <div class="ml-look-box">
            <h3 class="ml-look-title">${escapeHtml(look.title || "Look sugerido")}</h3>
            <div class="ml-grid">
              ${(look.items || []).map(item => buildCard(item, false)).join("")}
            </div>
          </div>`).join("")}
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

  function buildPersonalShopperSection(email) {
    return `
      <div class="ml-section" id="ml-shopper-section">
        <h2>✨ Personal Shopper</h2>
        <p class="ml-shopper-intro">Responda algumas perguntas e monte um look completo com suas peças + sugestões personalizadas.</p>
        <form class="ml-shopper-form" id="ml-shopper-form">
          <div class="ml-shopper-question">
            <label>Para qual ocasião você precisa de um look?</label>
            <div class="ml-shopper-options" data-field="occasion">
              <button type="button" class="ml-option-btn" data-value="praia">🏖️ Praia</button>
              <button type="button" class="ml-option-btn" data-value="resort">🌴 Resort</button>
              <button type="button" class="ml-option-btn" data-value="jantar">🍷 Jantar</button>
              <button type="button" class="ml-option-btn" data-value="viagem">✈️ Viagem</button>
              <button type="button" class="ml-option-btn" data-value="dia_a_dia">☀️ Dia a dia</button>
            </div>
          </div>
          <div class="ml-shopper-question">
            <label>O que você quer encontrar?</label>
            <div class="ml-shopper-options" data-field="goal">
              <button type="button" class="ml-option-btn" data-value="cross_sell">🔀 Complementar meus looks</button>
              <button type="button" class="ml-option-btn" data-value="up_sell">⬆️ Peças mais sofisticadas</button>
              <button type="button" class="ml-option-btn" data-value="novidades">🆕 Novidades para meu estilo</button>
            </div>
          </div>
          <div class="ml-shopper-question">
            <label>Qual vibe você quer hoje?</label>
            <div class="ml-shopper-options" data-field="style">
              <button type="button" class="ml-option-btn" data-value="elegante">💎 Elegante</button>
              <button type="button" class="ml-option-btn" data-value="casual">😎 Casual</button>
              <button type="button" class="ml-option-btn" data-value="leve">🌊 Leve</button>
            </div>
          </div>
          <button type="submit" class="ml-btn ml-btn-primary ml-shopper-submit" disabled>Montar meu look →</button>
        </form>
        <div id="ml-shopper-result" class="ml-shopper-result" style="display:none;"></div>
      </div>
    `;
  }

  function attachPersonalShopper(root, email) {
    const form = root.querySelector("#ml-shopper-form");
    if (!form) return;
    const answers = {};

    form.querySelectorAll(".ml-shopper-options").forEach(group => {
      group.addEventListener("click", e => {
        const btn = e.target.closest(".ml-option-btn");
        if (!btn) return;
        group.querySelectorAll(".ml-option-btn").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        answers[group.dataset.field] = btn.dataset.value;
        // Enable submit when all 3 questions answered
        const submitBtn = form.querySelector(".ml-shopper-submit");
        if (Object.keys(answers).length >= 3) submitBtn.removeAttribute("disabled");
      });
    });

    form.addEventListener("submit", async e => {
      e.preventDefault();
      const resultEl = root.querySelector("#ml-shopper-result");
      resultEl.style.display = "block";
      resultEl.innerHTML = `<div class="ml-loading"><div class="ml-spinner"></div><p>Montando seu look personalizado…</p></div>`;

      try {
        const resp = await fetch(`${CONFIG.API_BASE}/api/v1/customer-closet/recommendations`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({email, answers, limit: 8}),
        });
        const data = await resp.json();
        const recs = (data.recommendations || []).filter(i => i.image_url || i.imagem_url);
        const perfil = data.perfil_estilo || "";
        const dicas = Array.isArray(data.dicas_estilo) ? data.dicas_estilo : [];

        if (!recs.length) {
          resultEl.innerHTML = `<div class="ml-empty">Não encontramos sugestões para essa combinação. Tente outra ocasião!</div>`;
          return;
        }

        resultEl.innerHTML = `
          ${perfil ? `<p class="ml-shopper-perfil">${escapeHtml(perfil)}</p>` : ""}
          ${dicas.length ? `<ul class="ml-shopper-dicas">${dicas.map(d => `<li>${escapeHtml(d)}</li>`).join("")}</ul>` : ""}
          <h3>Sugestões para você</h3>
          <div class="ml-grid">${recs.map(i => buildCard(i, true)).join("")}</div>
        `;
      } catch (err) {
        resultEl.innerHTML = `<div class="ml-empty">Erro ao buscar sugestões. Tente novamente.</div>`;
      }
    });
  }

  function renderAccountCloset(root, rawData) {
    const data = normalizeApiData(rawData);
    const customerName = safeText(data.customer && data.customer.name) || "Cliente";
    const email = (data.customer && data.customer.email) || "";

    root.innerHTML = `
      <div class="ml-closet-shell">
        <div class="ml-closet-header">
          <h1>${CONFIG.TITLE}</h1>
          <p>${CONFIG.SUBTITLE}</p>
          <p style="margin-top:8px;"><strong>${escapeHtml(customerName)}</strong></p>
        </div>
        ${buildStats(data)}
        ${buildClosetSection(data.closet)}
        ${buildLooksSection(data.looks, data.closet, data.recommendations)}
        ${buildRecommendationsSection(data.recommendations)}
        ${buildPersonalShopperSection(email)}
      </div>
    `;

    attachClosetFilters(root);
    attachPersonalShopper(root, email);
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