(function () {
  "use strict";

  const CONFIG = {
    API_BASE:
      (window.MOODLAB_CLOSET_CONFIG && window.MOODLAB_CLOSET_CONFIG.API_BASE) ||
      "https://closet-moodlab.onrender.com",
    BRAND_COLOR: "#8a6a3a",
    BRAND_LIGHT: "#f5ece0",
  };

  // ── Detecta contexto da página ────────────────────────────────────────────
  function getPageContext() {
    const url = window.location.href;
    const path = window.location.pathname;
    // PDP: URL termina em /p
    if (path.endsWith("/p") || path.endsWith("/p/")) return "pdp";
    // Categoria: tem segmento de categoria sem /p
    if (path.split("/").length >= 2 && !path.includes("account") && !path.includes("checkout")) return "category";
    return "other";
  }

  function getProductContext() {
    try {
      // Tenta pegar nome do produto da página PDP
      const h1 = document.querySelector("h1");
      return h1 ? h1.textContent.trim().substring(0, 60) : "";
    } catch (e) { return ""; }
  }

  // ── Rastreia clique no backend ────────────────────────────────────────────
  async function trackClick(email, productId, occasion, source) {
    try {
      await fetch(`${CONFIG.API_BASE}/api/v1/customer-closet/track-click`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, product_id: productId, occasion, source }),
      });
    } catch (e) {}
  }

  // ── Obtém email do cliente logado ─────────────────────────────────────────
  async function getEmail() {
    try {
      const res = await fetch("/api/sessions?items=profile.email", {
        credentials: "include", headers: { Accept: "application/json" }
      });
      if (res.ok) {
        const d = await res.json();
        const email = d?.namespaces?.profile?.email?.value;
        if (email && email.includes("@")) return email.trim().toLowerCase();
      }
    } catch (e) {}
    try {
      const e = window.vtexjs?.checkout?.orderForm?.clientProfileData?.email;
      if (e && e.includes("@")) return e.trim().toLowerCase();
    } catch (e) {}
    return "";
  }

  // ── Estilos ───────────────────────────────────────────────────────────────
  function injectStyles() {
    if (document.getElementById("ml-stylist-widget-styles")) return;
    const s = document.createElement("style");
    s.id = "ml-stylist-widget-styles";
    s.innerHTML = `
      #ml-stylist-fab {
        position: fixed;
        right: 20px;
        bottom: 28px;
        z-index: 999990;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 8px;
      }

      .ml-stylist-fab-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        background: ${CONFIG.BRAND_COLOR};
        color: #fff;
        border: none;
        border-radius: 999px;
        padding: 13px 20px;
        font-size: 14px;
        font-weight: 700;
        cursor: pointer;
        box-shadow: 0 6px 24px rgba(0,0,0,0.18);
        font-family: Arial, sans-serif;
        white-space: nowrap;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }

      .ml-stylist-fab-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.22);
      }

      .ml-stylist-fab-badge {
        background: #e8c87a;
        color: #5a3a10;
        font-size: 11px;
        font-weight: 700;
        border-radius: 999px;
        padding: 3px 10px;
        font-family: Arial, sans-serif;
        text-align: center;
      }

      /* Drawer */
      #ml-stylist-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,.38);
        z-index: 999991;
        display: none;
      }
      #ml-stylist-overlay.open { display: block; }

      #ml-stylist-drawer {
        position: fixed;
        top: 0;
        right: 0;
        width: min(420px, 96vw);
        height: 100vh;
        background: #fff;
        z-index: 999992;
        box-shadow: -12px 0 40px rgba(0,0,0,.12);
        transform: translateX(100%);
        transition: transform .22s ease;
        display: flex;
        flex-direction: column;
        font-family: Arial, sans-serif;
      }
      #ml-stylist-drawer.open { transform: translateX(0); }

      .ml-stylist-header {
        padding: 20px 20px 16px;
        border-bottom: 1px solid #eadfce;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .ml-stylist-header h2 {
        margin: 0;
        font-size: 20px;
        color: #2f2a24;
      }
      .ml-stylist-header p {
        margin: 4px 0 0;
        font-size: 13px;
        color: #9a8f83;
      }
      .ml-stylist-close {
        background: none;
        border: none;
        font-size: 22px;
        color: #9a8f83;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 6px;
      }
      .ml-stylist-close:hover { background: #f5f0e8; }

      .ml-stylist-body {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
      }

      /* Perguntas */
      .ml-q { margin-bottom: 20px; }
      .ml-q label {
        display: block;
        font-size: 14px;
        font-weight: 700;
        color: #3a2e24;
        margin-bottom: 10px;
      }
      .ml-opts { display: flex; flex-wrap: wrap; gap: 8px; }
      .ml-opt {
        padding: 9px 16px;
        border: 1.5px solid #c8b89a;
        border-radius: 999px;
        background: #fff;
        color: #5a4a3a;
        font-size: 13px;
        cursor: pointer;
        font-family: Arial, sans-serif;
        transition: all .15s;
      }
      .ml-opt:hover { background: #f5ece0; }
      .ml-opt.selected { background: ${CONFIG.BRAND_COLOR}; border-color: ${CONFIG.BRAND_COLOR}; color: #fff; }

      .ml-stylist-submit {
        width: 100%;
        padding: 13px;
        background: ${CONFIG.BRAND_COLOR};
        color: #fff;
        border: none;
        border-radius: 999px;
        font-size: 15px;
        font-weight: 700;
        cursor: pointer;
        margin-top: 8px;
        font-family: Arial, sans-serif;
        transition: opacity .15s;
      }
      .ml-stylist-submit:disabled { opacity: .45; cursor: not-allowed; }

      /* Cards de resultado */
      .ml-stylist-result { margin-top: 20px; }
      .ml-stylist-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-top: 14px;
      }
      .ml-stylist-card {
        border: 1px solid #eadfce;
        border-radius: 14px;
        overflow: hidden;
        background: #fff;
      }
      .ml-stylist-card img {
        width: 100%;
        aspect-ratio: 3/4;
        object-fit: cover;
        display: block;
        background: #f8f3ec;
      }
      .ml-stylist-card-body { padding: 10px 12px 12px; }
      .ml-stylist-card-cat {
        font-size: 10px;
        text-transform: uppercase;
        color: #9a8f83;
        margin-bottom: 4px;
      }
      .ml-stylist-card-name {
        font-size: 13px;
        color: #2f2a24;
        font-weight: 600;
        margin-bottom: 6px;
        line-height: 1.3;
      }
      .ml-stylist-card-price {
        font-size: 14px;
        font-weight: 700;
        color: #7a4a1a;
        margin-bottom: 8px;
      }
      .ml-stylist-card-de {
        font-size: 11px;
        color: #9a8f83;
        text-decoration: line-through;
        display: block;
        margin-bottom: 2px;
      }
      .ml-stylist-card-reason {
        font-size: 11px;
        color: #7a6f63;
        margin-bottom: 8px;
        line-height: 1.4;
      }
      .ml-stylist-card-btn {
        display: block;
        text-align: center;
        padding: 8px;
        border-radius: 999px;
        background: ${CONFIG.BRAND_COLOR};
        color: #fff;
        text-decoration: none;
        font-size: 12px;
        font-weight: 700;
        font-family: Arial, sans-serif;
      }
      .ml-stylist-empty {
        text-align: center;
        padding: 32px 16px;
        color: #9a8f83;
        font-size: 14px;
      }
      .ml-stylist-loading {
        text-align: center;
        padding: 40px 16px;
        color: #9a8f83;
        font-size: 14px;
      }
      .ml-stylist-perfil {
        background: #f5ece0;
        border-left: 3px solid ${CONFIG.BRAND_COLOR};
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 13px;
        color: #3a2e24;
        margin-bottom: 14px;
      }
      .ml-stylist-back {
        display: flex;
        align-items: center;
        gap: 6px;
        background: none;
        border: none;
        color: ${CONFIG.BRAND_COLOR};
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        padding: 0;
        margin-bottom: 16px;
        font-family: Arial, sans-serif;
      }
      @media (max-width: 480px) {
        .ml-stylist-grid { grid-template-columns: 1fr; }
      }
    `;
    document.head.appendChild(s);
  }

  // ── Markup do drawer ──────────────────────────────────────────────────────
  function ensureDrawer() {
    if (document.getElementById("ml-stylist-drawer")) return;

    const overlay = document.createElement("div");
    overlay.id = "ml-stylist-overlay";
    overlay.addEventListener("click", closeDrawer);
    document.body.appendChild(overlay);

    const drawer = document.createElement("div");
    drawer.id = "ml-stylist-drawer";
    drawer.innerHTML = `
      <div class="ml-stylist-header">
        <div>
          <h2>✨ Personal Stylist</h2>
          <p>Monte um look completo com sugestões para você</p>
        </div>
        <button class="ml-stylist-close" type="button" aria-label="Fechar">✕</button>
      </div>
      <div class="ml-stylist-body" id="ml-stylist-body">
        ${buildQuestionsHTML()}
      </div>
    `;
    drawer.querySelector(".ml-stylist-close").addEventListener("click", closeDrawer);
    document.body.appendChild(drawer);
    attachQuestionListeners();
  }

  function buildQuestionsHTML() {
    return `
      <form id="ml-stylist-form">
        <div class="ml-q">
          <label>Para qual ocasião você precisa de um look?</label>
          <div class="ml-opts" data-field="occasion">
            <button type="button" class="ml-opt" data-value="praia">🏖️ Praia</button>
            <button type="button" class="ml-opt" data-value="resort">🌴 Resort</button>
            <button type="button" class="ml-opt" data-value="jantar">🍷 Jantar</button>
            <button type="button" class="ml-opt" data-value="viagem">✈️ Viagem</button>
            <button type="button" class="ml-opt" data-value="dia_a_dia">☀️ Dia a dia</button>
          </div>
        </div>
        <div class="ml-q">
          <label>O que você quer encontrar?</label>
          <div class="ml-opts" data-field="goal">
            <button type="button" class="ml-opt" data-value="cross_sell">🔀 Complementar meus looks</button>
            <button type="button" class="ml-opt" data-value="up_sell">⬆️ Peças mais sofisticadas</button>
            <button type="button" class="ml-opt" data-value="novidades">🆕 Novidades para meu estilo</button>
          </div>
        </div>
        <div class="ml-q">
          <label>Qual vibe você quer hoje?</label>
          <div class="ml-opts" data-field="style">
            <button type="button" class="ml-opt" data-value="elegante">💎 Elegante</button>
            <button type="button" class="ml-opt" data-value="casual">😎 Casual</button>
            <button type="button" class="ml-opt" data-value="leve">🌊 Leve</button>
          </div>
        </div>
        <button type="submit" class="ml-stylist-submit" disabled>Montar meu look →</button>
      </form>
    `;
  }

  const answers = {};

  function attachQuestionListeners() {
    const form = document.getElementById("ml-stylist-form");
    if (!form) return;
    form.querySelectorAll(".ml-opts").forEach(group => {
      group.addEventListener("click", e => {
        const btn = e.target.closest(".ml-opt");
        if (!btn) return;
        group.querySelectorAll(".ml-opt").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        answers[group.dataset.field] = btn.dataset.value;
        const submit = form.querySelector(".ml-stylist-submit");
        if (Object.keys(answers).length >= 3) submit.removeAttribute("disabled");
      });
    });
    form.addEventListener("submit", handleSubmit);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const body = document.getElementById("ml-stylist-body");
    body.innerHTML = `<div class="ml-stylist-loading">⏳ Montando seu look personalizado…</div>`;

    const email = await getEmail();
    const source = getPageContext() === "pdp" ? "widget_pdp" : "widget_category";
    const productCtx = getProductContext();

    try {
      const resp = await fetch(`${CONFIG.API_BASE}/api/v1/customer-closet/recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email || "",
          answers,
          limit: 8,
          source,
          product_context: productCtx,
        }),
      });
      const data = await resp.json();
      const recs = (data.recommendations || []).filter(i => i.image_url || i.imagem_url);
      renderResults(body, recs, data.perfil_estilo || "", answers.occasion, email, source);
    } catch (err) {
      body.innerHTML = `<div class="ml-stylist-empty">Erro ao buscar sugestões. Tente novamente.</div>`;
    }
  }

  function proxyImg(url) {
    if (!url) return "";
    const clean = url.split("?")[0].replace(/\/arquivos\/ids\/(\d+)-\d+-\d+(\/[^?#]+)/, "/arquivos/ids/$1-500-500$2");
    const isVtex = clean.includes("vteximg.com.br") || clean.includes("vtexassets.com");
    return isVtex ? `${CONFIG.API_BASE}/api/v1/image-proxy?url=${encodeURIComponent(clean)}` : clean;
  }

  function renderResults(body, recs, perfil, occasion, email, source) {
    if (!recs.length) {
      body.innerHTML = `
        <button class="ml-stylist-back" id="ml-back-btn">← Tentar outra combinação</button>
        <div class="ml-stylist-empty">Não encontramos sugestões para essa combinação. Tente outra ocasião!</div>
      `;
      document.getElementById("ml-back-btn").addEventListener("click", resetForm);
      return;
    }

    body.innerHTML = `
      <button class="ml-stylist-back" id="ml-back-btn">← Tentar outra combinação</button>
      ${perfil ? `<div class="ml-stylist-perfil">${escH(perfil)}</div>` : ""}
      <div class="ml-stylist-grid">
        ${recs.map(item => {
          const img = proxyImg(item.image_url || item.imagem_url || "");
          const sale = parseFloat(item.price || item.preco || 0);
          const list = parseFloat(item.list_price || 0);
          const hasDisc = list > 0 && list > sale + 0.01;
          const fmt = v => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
          const priceHTML = sale > 0
            ? (hasDisc ? `<span class="ml-stylist-card-de">De ${fmt(list)}</span><div class="ml-stylist-card-price">Por ${fmt(sale)}</div>`
                       : `<div class="ml-stylist-card-price">${fmt(sale)}</div>`)
            : "";
          return `
            <div class="ml-stylist-card">
              ${img ? `<img src="${img}" alt="${escH(item.name || item.nome || "")}" loading="lazy" />` : ""}
              <div class="ml-stylist-card-body">
                <div class="ml-stylist-card-cat">${escH(item.category || item.categoria || "")}</div>
                <div class="ml-stylist-card-name">${escH(item.name || item.nome || "Produto")}</div>
                ${priceHTML}
                ${item.reason || item.motivo ? `<div class="ml-stylist-card-reason">${escH(item.reason || item.motivo)}</div>` : ""}
                <a class="ml-stylist-card-btn"
                   href="${item.product_url || item.link_produto || "#"}"
                   target="_blank" rel="noopener"
                   onclick="window._mlTrackClick && window._mlTrackClick('${escH(email)}','${escH(item.product_id || item.sku_id || "")}','${escH(occasion)}','${escH(source)}')">
                  Ver produto
                </a>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;
    document.getElementById("ml-back-btn").addEventListener("click", resetForm);

    // Expõe função de tracking global
    window._mlTrackClick = (em, pid, occ, src) => trackClick(em, pid, occ, src);
  }

  function resetForm() {
    Object.keys(answers).forEach(k => delete answers[k]);
    const body = document.getElementById("ml-stylist-body");
    if (body) {
      body.innerHTML = buildQuestionsHTML();
      attachQuestionListeners();
    }
  }

  function escH(str) {
    return String(str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }

  function openDrawer() {
    ensureDrawer();
    document.getElementById("ml-stylist-overlay").classList.add("open");
    document.getElementById("ml-stylist-drawer").classList.add("open");
  }

  function closeDrawer() {
    const o = document.getElementById("ml-stylist-overlay");
    const d = document.getElementById("ml-stylist-drawer");
    if (o) o.classList.remove("open");
    if (d) d.classList.remove("open");
  }

  // ── FAB button ────────────────────────────────────────────────────────────
  function mount() {
    const ctx = getPageContext();
    if (ctx === "other") return;
    if (document.getElementById("ml-stylist-fab")) return;

    injectStyles();

    const fab = document.createElement("div");
    fab.id = "ml-stylist-fab";

    const label = ctx === "pdp"
      ? "Como usar essa peça?"
      : "Monte seu look";

    fab.innerHTML = `
      <div class="ml-stylist-fab-badge">✨ Personal Stylist</div>
      <button class="ml-stylist-fab-btn" type="button">${label}</button>
    `;
    fab.querySelector("button").addEventListener("click", openDrawer);
    document.body.appendChild(fab);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }

  // Re-mount em navegações SPA da VTEX
  window.addEventListener("hashchange", mount);
  window.addEventListener("popstate", mount);
})();
