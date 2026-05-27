/**
 * MoodLab — Personal Shopper Widget
 * Botão flutuante + chat com IA na lateral direita
 * Para injetar nas páginas de categoria e produto VTEX Legacy
 *
 * Uso: <script src="https://closet-moodlab.onrender.com/public/widget-stylist-chat.js"></script>
 */
(function () {
  "use strict";

  const API_BASE = "https://closet-moodlab.onrender.com";
  const BRAND = {
    gold: "#b7a56a",
    goldDark: "#9a8a52",
    goldLight: "#f5efe0",
    bg: "#fdfaf5",
    text: "#2b2520",
    textSoft: "#7a6e63",
    border: "#e8dece",
    white: "#ffffff",
    radius: "16px",
    shadow: "0 8px 40px rgba(0,0,0,0.14)",
  };

  // ── Evita duplicação ────────────────────────────────────────────────────────
  if (window.__moodlabStylistChat) return;
  window.__moodlabStylistChat = true;

  // ── Detecta email logado VTEX ───────────────────────────────────────────────
  function getLoggedEmail() {
    try {
      const vtex =
        window.vtexjs?.checkout?.orderForm?.clientProfileData?.email ||
        window.__RUNTIME__?.session?.email ||
        window.vtex?.session?.email;
      if (vtex) return String(vtex).trim().toLowerCase();
    } catch (_) {}
    return "";
  }

  // ── Detecta contexto da página ──────────────────────────────────────────────
  function getPageContext() {
    const path = window.location.pathname;
    if (path.includes("/p")) return "produto:" + document.title.split("|")[0].trim();
    return "categoria:" + document.title.split("|")[0].trim();
  }

  // ── Estilos injetados ───────────────────────────────────────────────────────
  function injectStyles() {
    const css = `
      #ml-chat-fab {
        position: fixed;
        bottom: ${window.MOODLAB_WIDGET_BOTTOM || 28}px;
        right: 28px;
        z-index: 99999;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: ${BRAND.gold};
        border: none;
        cursor: pointer;
        box-shadow: ${BRAND.shadow};
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s, background 0.2s;
        outline: none;
      }
      #ml-chat-fab:hover { background: ${BRAND.goldDark}; transform: scale(1.07); }
      #ml-chat-fab svg { width: 26px; height: 26px; fill: none; stroke: #fff; stroke-width: 2; }

      #ml-chat-badge {
        position: absolute;
        top: -4px;
        right: -4px;
        background: #e05c3a;
        color: #fff;
        font-size: 11px;
        font-weight: 700;
        border-radius: 99px;
        padding: 2px 6px;
        display: none;
        font-family: Arial, sans-serif;
      }

      #ml-chat-panel {
        position: fixed;
        bottom: ${(window.MOODLAB_WIDGET_BOTTOM || 28) + 72}px;
        right: 28px;
        z-index: 99998;
        width: 380px;
        max-width: calc(100vw - 40px);
        max-height: 80vh;
        background: ${BRAND.bg};
        border: 1px solid ${BRAND.border};
        border-radius: ${BRAND.radius};
        box-shadow: ${BRAND.shadow};
        display: flex;
        flex-direction: column;
        overflow: hidden;
        font-family: 'Georgia', serif;
        transform: translateY(20px) scale(0.97);
        opacity: 0;
        pointer-events: none;
        transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
      }
      #ml-chat-panel.ml-open {
        transform: translateY(0) scale(1);
        opacity: 1;
        pointer-events: all;
      }

      #ml-panel-header {
        background: ${BRAND.gold};
        color: ${BRAND.white};
        padding: 14px 16px;
        display: flex;
        align-items: center;
        gap: 10px;
        flex-shrink: 0;
      }
      #ml-panel-header .ml-logo {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
      }
      #ml-panel-header .ml-subtitle {
        font-size: 11px;
        opacity: 0.85;
        font-style: italic;
        font-family: 'Georgia', serif;
      }
      #ml-close-btn {
        margin-left: auto;
        background: none;
        border: none;
        color: #fff;
        cursor: pointer;
        font-size: 20px;
        line-height: 1;
        padding: 0 4px;
        opacity: 0.8;
      }
      #ml-close-btn:hover { opacity: 1; }

      #ml-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        scroll-behavior: smooth;
      }

      .ml-msg {
        max-width: 90%;
        padding: 10px 14px;
        border-radius: 12px;
        font-size: 14px;
        line-height: 1.5;
        color: ${BRAND.text};
      }
      .ml-msg.ml-bot {
        background: ${BRAND.white};
        border: 1px solid ${BRAND.border};
        align-self: flex-start;
        border-bottom-left-radius: 4px;
      }
      .ml-msg.ml-user {
        background: ${BRAND.gold};
        color: #fff;
        align-self: flex-end;
        border-bottom-right-radius: 4px;
      }
      .ml-msg.ml-typing {
        background: ${BRAND.white};
        border: 1px solid ${BRAND.border};
        align-self: flex-start;
        color: ${BRAND.textSoft};
        font-style: italic;
        font-size: 13px;
      }

      /* Carrossel */
      .ml-carousel-wrap {
        width: 100%;
        overflow-x: auto;
        padding: 4px 0 8px;
        scrollbar-width: thin;
        -webkit-overflow-scrolling: touch;
      }
      .ml-carousel {
        display: flex;
        gap: 10px;
        width: max-content;
      }
      .ml-card {
        width: 140px;
        background: ${BRAND.white};
        border: 1px solid ${BRAND.border};
        border-radius: 12px;
        overflow: hidden;
        flex-shrink: 0;
        cursor: pointer;
        transition: box-shadow 0.15s, transform 0.15s;
        text-decoration: none;
      }
      .ml-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.12); transform: translateY(-2px); }
      .ml-card img {
        width: 100%;
        height: 110px;
        object-fit: cover;
        display: block;
      }
      .ml-card-body { padding: 8px 10px; }
      .ml-card-name {
        font-size: 12px;
        color: ${BRAND.text};
        font-weight: 600;
        line-height: 1.3;
        margin-bottom: 3px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .ml-card-price {
        font-size: 12px;
        color: ${BRAND.gold};
        font-weight: 700;
      }
      .ml-card-btn {
        display: block;
        margin: 6px 10px 8px;
        padding: 5px 0;
        background: ${BRAND.gold};
        color: #fff;
        text-align: center;
        font-size: 11px;
        font-weight: 700;
        border-radius: 99px;
        text-decoration: none;
        letter-spacing: 0.5px;
        transition: background 0.15s;
      }
      .ml-card-btn:hover { background: ${BRAND.goldDark}; }

      /* Email gate */
      #ml-email-gate {
        padding: 20px 16px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      #ml-email-gate p {
        font-size: 14px;
        color: ${BRAND.textSoft};
        margin: 0;
        line-height: 1.5;
        font-style: italic;
      }
      .ml-input {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid ${BRAND.border};
        border-radius: 99px;
        font-size: 14px;
        font-family: 'Georgia', serif;
        color: ${BRAND.text};
        background: ${BRAND.white};
        outline: none;
        box-sizing: border-box;
        transition: border-color 0.15s;
      }
      .ml-input:focus { border-color: ${BRAND.gold}; }
      .ml-btn-gold {
        padding: 10px 0;
        background: ${BRAND.gold};
        color: #fff;
        border: none;
        border-radius: 99px;
        font-size: 14px;
        font-weight: 700;
        cursor: pointer;
        font-family: 'Georgia', serif;
        transition: background 0.15s;
        letter-spacing: 0.3px;
      }
      .ml-btn-gold:hover { background: ${BRAND.goldDark}; }
      .ml-btn-gold:disabled { background: #ccc; cursor: not-allowed; }

      /* Input bar */
      #ml-input-bar {
        padding: 10px 12px;
        border-top: 1px solid ${BRAND.border};
        display: flex;
        gap: 8px;
        flex-shrink: 0;
        background: ${BRAND.white};
      }
      #ml-text-input {
        flex: 1;
        padding: 9px 14px;
        border: 1px solid ${BRAND.border};
        border-radius: 99px;
        font-size: 13px;
        font-family: 'Georgia', serif;
        color: ${BRAND.text};
        background: ${BRAND.bg};
        outline: none;
        resize: none;
        height: 38px;
        transition: border-color 0.15s;
      }
      #ml-text-input:focus { border-color: ${BRAND.gold}; }
      #ml-send-btn {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: ${BRAND.gold};
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        transition: background 0.15s;
      }
      #ml-send-btn:hover { background: ${BRAND.goldDark}; }
      #ml-send-btn:disabled { background: #ccc; cursor: not-allowed; }
      #ml-send-btn svg { width: 16px; height: 16px; fill: #fff; }

      @media (max-width: 480px) {
        #ml-chat-panel { right: 12px; bottom: 90px; width: calc(100vw - 24px); }
        #ml-chat-fab { right: 16px; bottom: ${window.MOODLAB_WIDGET_BOTTOM || 20}px; }
      }
    `;
    const style = document.createElement("style");
    style.id = "ml-stylist-chat-styles";
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ── Estado ──────────────────────────────────────────────────────────────────
  let state = {
    open: false,
    email: getLoggedEmail(),
    emailConfirmed: !!getLoggedEmail(),
    loading: false,
  };

  // ── Cria DOM ────────────────────────────────────────────────────────────────
  function buildUI() {
    // FAB
    const fab = document.createElement("button");
    fab.id = "ml-chat-fab";
    fab.setAttribute("aria-label", "Personal Shopper MoodLab");
    fab.innerHTML = `
      <svg viewBox="0 0 24 24">
        <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 2.98.97 4.29L2 22l5.71-.97C9.02 21.64 10.46 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2z"/>
        <path d="M8 10h8M8 14h5" stroke-linecap="round"/>
      </svg>
      <span id="ml-chat-badge">1</span>
    `;

    // Panel
    const panel = document.createElement("div");
    panel.id = "ml-chat-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Personal Shopper");
    panel.innerHTML = `
      <div id="ml-panel-header">
        <div>
          <div class="ml-logo">✦ Personal Shopper</div>
          <div class="ml-subtitle">Água de Coco · IA</div>
        </div>
        <button id="ml-close-btn" aria-label="Fechar">×</button>
      </div>
      <div id="ml-messages"></div>
      <div id="ml-email-gate" style="display:none">
        <p>Para personalizar suas sugestões, informe seu e-mail:</p>
        <input class="ml-input" id="ml-email-input" type="email" placeholder="seu@email.com" autocomplete="email"/>
        <button class="ml-btn-gold" id="ml-email-confirm-btn">Continuar</button>
      </div>
      <div id="ml-input-bar" style="display:none">
        <input id="ml-text-input" placeholder="O que você está procurando?" autocomplete="off"/>
        <button id="ml-send-btn" aria-label="Enviar">
          <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
        </button>
      </div>
    `;

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    // Events
    fab.addEventListener("click", togglePanel);
    panel.querySelector("#ml-close-btn").addEventListener("click", closePanel);
    panel.querySelector("#ml-email-confirm-btn").addEventListener("click", confirmEmail);
    panel.querySelector("#ml-email-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") confirmEmail();
    });

    const sendBtn = panel.querySelector("#ml-send-btn");
    const textInput = panel.querySelector("#ml-text-input");
    sendBtn.addEventListener("click", sendMessage);
    textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });

    return { fab, panel };
  }

  // ── Toggle ──────────────────────────────────────────────────────────────────
  function togglePanel() { state.open ? closePanel() : openPanel(); }

  function openPanel() {
    state.open = true;
    const panel = document.getElementById("ml-chat-panel");
    const badge = document.getElementById("ml-chat-badge");
    panel.classList.add("ml-open");
    if (badge) badge.style.display = "none";

    const messages = document.getElementById("ml-messages");
    if (!messages.children.length) {
      if (state.emailConfirmed) {
        showInputBar();
        addBotMessage("Olá! 👋 Sou sua personal shopper. Me conta o que você está procurando — posso sugerir peças do seu estilo, completar um look ou apresentar as novidades.");
      } else {
        showEmailGate();
        addBotMessage("Olá! Sou sua personal shopper da Água de Coco. ✨\nVou usar seu histórico para sugerir peças perfeitas para você.");
      }
    }
  }

  function closePanel() {
    state.open = false;
    document.getElementById("ml-chat-panel").classList.remove("ml-open");
  }

  function showEmailGate() {
    document.getElementById("ml-email-gate").style.display = "flex";
    document.getElementById("ml-input-bar").style.display = "none";
  }

  function showInputBar() {
    document.getElementById("ml-email-gate").style.display = "none";
    document.getElementById("ml-input-bar").style.display = "flex";
    setTimeout(() => document.getElementById("ml-text-input")?.focus(), 100);
  }

  // ── Email confirm ───────────────────────────────────────────────────────────
  function confirmEmail() {
    const input = document.getElementById("ml-email-input");
    const email = (input?.value || "").trim().toLowerCase();
    if (!email || !email.includes("@")) {
      input.style.borderColor = "#e05c3a";
      return;
    }
    state.email = email;
    state.emailConfirmed = true;
    showInputBar();
    addBotMessage(`Ótimo, ${email.split("@")[0]}! Agora me conta o que você está procurando. 🌿`);
  }

  // ── Mensagens ───────────────────────────────────────────────────────────────
  function addBotMessage(text) {
    const div = document.createElement("div");
    div.className = "ml-msg ml-bot";
    div.textContent = text;
    appendMessage(div);
  }

  function addUserMessage(text) {
    const div = document.createElement("div");
    div.className = "ml-msg ml-user";
    div.textContent = text;
    appendMessage(div);
  }

  function addTyping() {
    const div = document.createElement("div");
    div.className = "ml-msg ml-typing";
    div.id = "ml-typing-indicator";
    div.textContent = "Consultando seu estilo…";
    appendMessage(div);
    return div;
  }

  function removeTyping() {
    document.getElementById("ml-typing-indicator")?.remove();
  }

  function appendMessage(el) {
    const messages = document.getElementById("ml-messages");
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  // ── Carrossel de produtos ───────────────────────────────────────────────────
  function addProductCarousel(products) {
    if (!products || !products.length) return;

    const wrapper = document.createElement("div");
    wrapper.className = "ml-msg ml-bot";
    wrapper.style.padding = "8px 0";
    wrapper.style.maxWidth = "100%";

    const scrollWrap = document.createElement("div");
    scrollWrap.className = "ml-carousel-wrap";

    const carousel = document.createElement("div");
    carousel.className = "ml-carousel";

    products.forEach((p) => {
      const card = document.createElement("a");
      card.className = "ml-card";
      card.href = p.url || "#";
      card.target = "_top";
      card.rel = "noopener";

      const img = document.createElement("img");
      img.src = p.image_url || "";
      img.alt = p.name || "";
      img.onerror = function () {
        this.style.display = "none";
        this.parentElement.style.paddingTop = "10px";
      };

      const body = document.createElement("div");
      body.className = "ml-card-body";
      body.innerHTML = `
        <div class="ml-card-name">${p.name || ""}</div>
        <div class="ml-card-price">${p.price || ""}</div>
      `;

      const btn = document.createElement("a");
      btn.className = "ml-card-btn";
      btn.href = p.url || "#";
      btn.target = "_top";
      btn.textContent = "Ver produto";

      // Registra clique
      card.addEventListener("click", () => trackClick(p.id, p.name));
      btn.addEventListener("click", (e) => { e.stopPropagation(); trackClick(p.id, p.name); });

      card.appendChild(img);
      card.appendChild(body);
      card.appendChild(btn);
      carousel.appendChild(card);
    });

    scrollWrap.appendChild(carousel);
    wrapper.appendChild(scrollWrap);
    appendMessage(wrapper);
  }

  // ── Track clique ────────────────────────────────────────────────────────────
  function trackClick(productId, productName) {
    try {
      fetch(`${API_BASE}/api/v1/customer-closet/track-click`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: state.email,
          product_id: String(productId || ""),
          source: "widget_stylist_chat",
          occasion: productName || "",
        }),
        keepalive: true,
      }).catch(() => {});
    } catch (_) {}
  }

  // ── Envio de mensagem ───────────────────────────────────────────────────────
  async function sendMessage() {
    if (state.loading) return;

    const input = document.getElementById("ml-text-input");
    const message = (input?.value || "").trim();
    if (!message) return;

    input.value = "";
    input.disabled = true;
    document.getElementById("ml-send-btn").disabled = true;
    state.loading = true;

    addUserMessage(message);
    const typing = addTyping();

    try {
      const res = await fetch(`${API_BASE}/api/v1/customer-closet/stylist-chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: state.email,
          message,
          page_context: getPageContext(),
          limit: 6,
        }),
      });

      removeTyping();

      if (!res.ok) throw new Error("Erro " + res.status);

      const data = await res.json();
      if (data.message) addBotMessage(data.message);
      if (data.products?.length) {
        addProductCarousel(data.products);
      } else {
        addBotMessage("Não encontrei produtos disponíveis para esse pedido agora. Que tal tentar com outras palavras?");
      }
    } catch (err) {
      removeTyping();
      addBotMessage("Ops, tive um problema ao buscar sugestões. Tente novamente em instantes.");
      console.error("[MoodLab Stylist]", err);
    } finally {
      state.loading = false;
      if (input) { input.disabled = false; input.focus(); }
      document.getElementById("ml-send-btn").disabled = false;
    }
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  function init() {
    injectStyles();
    buildUI();

    // Mostra badge após 3s para chamar atenção
    setTimeout(() => {
      if (!state.open) {
        const badge = document.getElementById("ml-chat-badge");
        if (badge) badge.style.display = "block";
      }
    }, 3000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
