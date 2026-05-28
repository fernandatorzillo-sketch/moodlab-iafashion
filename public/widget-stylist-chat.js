/**
 * MoodLab — Personal Shopper Widget v3
 * Botão lateral empilhado com "AJUDA" (MyCatwalk)
 * Com imagens de produto, tracking de conversão e chat IA
 *
 * Uso: <script src="https://closet-moodlab.onrender.com/public/widget-stylist-chat.js"></script>
 */
(function () {
  "use strict";

  const API_BASE =
    (window.MOODLAB_CLOSET_CONFIG && window.MOODLAB_CLOSET_CONFIG.API_BASE) ||
    "https://closet-moodlab.onrender.com";

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

  if (window.__moodlabStylistChat) return;
  window.__moodlabStylistChat = true;

  // ── Detecta email VTEX ──────────────────────────────────────────────────────
  function getLoggedEmail() {
    try {
      return (
        window.vtexjs?.checkout?.orderForm?.clientProfileData?.email ||
        window.__RUNTIME__?.session?.email ||
        window.vtex?.session?.email ||
        ""
      );
    } catch (_) { return ""; }
  }

  // ── Contexto da página ──────────────────────────────────────────────────────
  function getPageContext() {
    const h1 = document.querySelector("h1");
    const title = h1 ? h1.textContent.trim().substring(0, 80) : document.title.split("|")[0].trim();
    const path = window.location.pathname;
    if (path.endsWith("/p") || path.endsWith("/p/")) return "produto: " + title;
    return "categoria: " + title;
  }

  // ── CSS ─────────────────────────────────────────────────────────────────────
  function injectStyles() {
    const css = `
      /* ── Botão lateral empilhado (estilo AJUDA do MyCatwalk) ── */
      #ml-fab-sidebar {
        position: fixed;
        right: 0;
        bottom: 230px; /* acima do botão AJUDA do MyCatwalk */
        z-index: 99997;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
      }

      #ml-fab-btn {
        writing-mode: vertical-rl;
        text-orientation: mixed;
        transform: rotate(180deg);
        background: ${BRAND.gold};
        color: ${BRAND.white};
        border: none;
        border-radius: 6px 0 0 6px;
        padding: 14px 8px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        cursor: pointer;
        font-family: 'Arial', sans-serif;
        box-shadow: -2px 2px 12px rgba(0,0,0,0.15);
        transition: background 0.2s, padding 0.2s;
        display: flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
        line-height: 1;
      }
      #ml-fab-btn:hover { background: ${BRAND.goldDark}; padding: 14px 10px; }
      #ml-fab-btn .ml-fab-icon {
        width: 14px;
        height: 14px;
        fill: none;
        stroke: #fff;
        stroke-width: 2;
        flex-shrink: 0;
      }
      #ml-fab-badge {
        position: absolute;
        top: -6px;
        right: 8px;
        background: #e05c3a;
        color: #fff;
        font-size: 10px;
        font-weight: 700;
        border-radius: 99px;
        padding: 2px 5px;
        display: none;
        font-family: Arial, sans-serif;
        writing-mode: horizontal-tb;
        transform: none;
      }

      /* ── Painel de chat ── */
      #ml-chat-panel {
        position: fixed;
        top: 80px;
        right: 44px;
        z-index: 99998;
        width: 420px;
        max-width: calc(100vw - 52px);
        max-height: calc(100vh - 100px);
        background: ${BRAND.bg};
        border: 1px solid ${BRAND.border};
        border-radius: ${BRAND.radius};
        box-shadow: ${BRAND.shadow};
        display: flex;
        flex-direction: column;
        overflow: hidden;
        font-family: 'Georgia', serif;
        transform: translateX(30px);
        opacity: 0;
        pointer-events: none;
        transition: all 0.22s ease;
      }
      /* Mobile: tela cheia com input sempre visível */
      @media (max-width: 600px) {
        #ml-chat-panel {
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          right: 0 !important;
          bottom: 0 !important;
          width: 100% !important;
          max-width: 100% !important;
          max-height: 100% !important;
          border-radius: 0 !important;
          transform: translateY(100%) !important;
        }
        #ml-chat-panel.ml-open {
          transform: translateY(0) !important;
        }
        #ml-messages {
          flex: 1;
          overflow-y: auto;
          -webkit-overflow-scrolling: touch;
          padding-bottom: 8px !important;
        }
        #ml-input-bar {
          position: sticky !important;
          bottom: 0 !important;
          background: ${BRAND.white} !important;
          border-top: 1px solid ${BRAND.border} !important;
          padding: 10px 12px env(safe-area-inset-bottom, 8px) !important;
          flex-shrink: 0 !important;
          z-index: 10 !important;
        }
        #ml-email-gate {
          padding-bottom: env(safe-area-inset-bottom, 16px) !important;
        }
      }
      #ml-chat-panel.ml-open {
        transform: translateX(0);
        opacity: 1;
        pointer-events: all;
      }

      /* ── Header ── */
      #ml-panel-header {
        background: ${BRAND.gold};
        color: ${BRAND.white};
        padding: 13px 16px;
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
        font-family: 'Arial', sans-serif;
      }
      #ml-panel-header .ml-subtitle {
        font-size: 11px;
        opacity: 0.85;
        font-style: italic;
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
        font-family: Arial, sans-serif;
      }
      #ml-close-btn:hover { opacity: 1; }

      /* ── Mensagens ── */
      #ml-messages {
        flex: 1;
        overflow-y: auto;
        padding: 14px 14px 8px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        scroll-behavior: smooth;
      }
      .ml-msg {
        max-width: 92%;
        padding: 10px 14px;
        border-radius: 12px;
        font-size: 14px;
        line-height: 1.55;
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

      /* ── Carrossel de produtos com imagens ── */
      .ml-carousel-wrap {
        width: 100%;
        overflow-x: auto;
        padding: 4px 0 8px;
        scrollbar-width: thin;
        scrollbar-color: ${BRAND.border} transparent;
        -webkit-overflow-scrolling: touch;
        cursor: grab;
        user-select: none;
      }
      .ml-carousel-wrap::-webkit-scrollbar { height: 4px; }
      .ml-carousel-wrap::-webkit-scrollbar-track { background: transparent; }
      .ml-carousel-wrap::-webkit-scrollbar-thumb { background: ${BRAND.border}; border-radius: 99px; }

      .ml-carousel { display: flex; gap: 10px; width: max-content; padding: 2px; }

      .ml-card {
        width: 160px;
        background: ${BRAND.white};
        border: 1px solid ${BRAND.border};
        border-radius: 12px;
        overflow: hidden;
        flex-shrink: 0;
        text-decoration: none;
        display: block;
        transition: box-shadow 0.15s, transform 0.15s;
      }
      .ml-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,0.13); transform: translateY(-2px); }

      .ml-card-img {
        width: 100%;
        height: 140px;
        object-fit: cover;
        display: block;
        background: #f5f0ea;
      }
      .ml-card-img-placeholder {
        width: 100%;
        height: 140px;
        background: linear-gradient(135deg, #f5efe0 0%, #e8dece 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
      }
      .ml-card-body { padding: 8px 10px 4px; }
      .ml-card-name {
        font-size: 12px;
        color: ${BRAND.text};
        font-weight: 600;
        line-height: 1.35;
        margin-bottom: 3px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        font-family: 'Georgia', serif;
      }
      .ml-card-price {
        font-size: 13px;
        color: ${BRAND.gold};
        font-weight: 700;
        font-family: 'Arial', sans-serif;
      }
      .ml-card-price-de {
        font-size: 11px;
        color: ${BRAND.textSoft};
        font-family: 'Arial', sans-serif;
        margin-bottom: 1px;
      }
      .ml-card-price-de s {
        text-decoration: line-through;
        color: #aaa;
      }
      .ml-card-price-sale {
        color: #c0392b !important;
      }
      .ml-card-complement {
        font-size: 10px;
        color: ${BRAND.gold};
        font-weight: 700;
        text-align: center;
        padding: 3px 8px 0;
        font-family: 'Arial', sans-serif;
        letter-spacing: 0.3px;
      }
      .ml-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        padding: 4px 0 8px;
        max-width: 100%;
      }
      .ml-chip {
        background: ${BRAND.white};
        border: 1.5px solid ${BRAND.gold};
        color: ${BRAND.goldDark || "#9a8a52"};
        border-radius: 99px;
        padding: 5px 12px;
        font-size: 12px;
        font-family: 'Arial', sans-serif;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s;
        white-space: nowrap;
      }
      .ml-chip:hover {
        background: ${BRAND.gold};
        color: #fff;
      }
      .ml-card-btn {
        display: block;
        margin: 6px 8px 8px;
        padding: 6px 0;
        background: ${BRAND.gold};
        color: #fff;
        text-align: center;
        font-size: 11px;
        font-weight: 700;
        border-radius: 99px;
        text-decoration: none;
        letter-spacing: 0.5px;
        font-family: 'Arial', sans-serif;
        transition: background 0.15s;
      }
      .ml-card-btn:hover { background: ${BRAND.goldDark}; }

      /* ── Email gate ── */
      #ml-email-gate {
        padding: 18px 16px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        flex-shrink: 0;
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
        padding: 10px 14px;
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
        font-family: 'Arial', sans-serif;
        transition: background 0.15s;
        letter-spacing: 0.3px;
        width: 100%;
      }
      .ml-btn-gold:hover { background: ${BRAND.goldDark}; }
      .ml-btn-gold:disabled { background: #ccc; cursor: not-allowed; }

      /* ── Input bar ── */
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
        height: 38px;
        transition: border-color 0.15s;
        box-sizing: border-box;
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
      #ml-send-btn svg { width: 15px; height: 15px; fill: #fff; }

      /* ── Mobile ── */
      @media (max-width: 480px) {
        #ml-chat-panel {
          right: 40px;
          top: 60px;
          width: calc(100vw - 52px);
          max-height: calc(100vh - 80px);
        }
        #ml-fab-btn { font-size: 10px; padding: 12px 7px; }
      }
    `;
    const style = document.createElement("style");
    style.id = "ml-stylist-chat-styles";
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ── Estado persistente via sessionStorage ────────────────────────────────
  // ── Persistência leve por sessão de navegação ──────────────────────────
  // Usa sessionStorage com chave fixa — conversa persiste entre páginas
  // mas não entre sessões diferentes do browser (privacidade OK)
  const STORAGE_KEY = "ml_ps_conv";

  function _storageSave(email, emailConfirmed, messages) {
    try {
      // Salva só texto + referência mínima de produtos (sem imagens pesadas)
      const lightMsgs = messages.slice(-8).map(m => {
        if (m.type !== "products") return m;
        return {
          type: "products",
          products: (m.products || []).slice(0, 4).map(p => ({
            id: p.id, name: p.name, price: p.price,
            url: p.url, image_url: p.image_url,
            category: p.category,
          }))
        };
      });
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        email, emailConfirmed, messages: lightMsgs
      }));
    } catch (_) {}
  }

  function _storageLoad() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (_) { return null; }
  }

  function saveState(s) {
    _storageSave(s.email, s.emailConfirmed, s.messages);
  }

  // Carrega conversa salva
  const _saved = _storageLoad();
  const _loggedEmail = getLoggedEmail();

  // Se email logado mudou em relação ao salvo, descarta conversa antiga
  const _savedIsValid = _saved && (
    !_loggedEmail || !_saved.email || _saved.email === _loggedEmail
  );

  const state = {
    open: false,
    email: _loggedEmail || (_savedIsValid && _saved.email) || "",
    emailConfirmed: !!(_loggedEmail || (_savedIsValid && _saved.emailConfirmed)),
    loading: false,
    messages: (_savedIsValid && _saved.messages) || [],
  };

  // ── Cria DOM ────────────────────────────────────────────────────────────────
  function buildUI() {
    // Wrapper lateral
    const sidebar = document.createElement("div");
    sidebar.id = "ml-fab-sidebar";

    // Botão lateral
    const fabBtn = document.createElement("button");
    fabBtn.id = "ml-fab-btn";
    fabBtn.setAttribute("aria-label", "Personal Shopper MoodLab");
    fabBtn.innerHTML = `
      <svg class="ml-fab-icon" viewBox="0 0 24 24">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
        <path d="M7 9h10M7 13h7" stroke-linecap="round" stroke="#fff"/>
      </svg>
      PERSONAL SHOPPER
      <span id="ml-fab-badge">1</span>
    `;
    sidebar.appendChild(fabBtn);

    // Painel
    const panel = document.createElement("div");
    panel.id = "ml-chat-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Personal Shopper Água de Coco");
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
        <button class="ml-btn-gold" id="ml-email-confirm-btn">Continuar →</button>
      </div>
      <div id="ml-input-bar" style="display:none">
        <input id="ml-text-input" placeholder="O que você está procurando?" autocomplete="off"/>
        <button id="ml-send-btn" aria-label="Enviar">
          <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
        </button>
      </div>
    `;

    document.body.appendChild(sidebar);
    document.body.appendChild(panel);

    // Eventos
    fabBtn.addEventListener("click", togglePanel);
    panel.querySelector("#ml-close-btn").addEventListener("click", closePanel);
    panel.querySelector("#ml-email-confirm-btn").addEventListener("click", confirmEmail);
    panel.querySelector("#ml-email-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") confirmEmail();
    });
    panel.querySelector("#ml-send-btn").addEventListener("click", sendMessage);
    panel.querySelector("#ml-text-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
  }

  // ── Toggle ──────────────────────────────────────────────────────────────────
  function togglePanel() { state.open ? closePanel() : openPanel(); }

  function isMobile() { return window.innerWidth <= 600; }

  function openPanel() {
    state.open = true;
    const panel = document.getElementById("ml-chat-panel");
    const badge = document.getElementById("ml-fab-badge");
    panel.classList.add("ml-open");
    if (badge) badge.style.display = "none";
    // No mobile, previne scroll do body e mantém input visível
    if (isMobile()) {
      document.body.style.overflow = "hidden";
      document.body.style.position = "fixed";
      document.body.style.width = "100%";
    }

    const messages = document.getElementById("ml-messages");
    if (!messages.children.length) {
      // Restaura conversa anterior se existir
      if (state.messages && state.messages.length > 0) {
        restoreMessages();
        if (state.emailConfirmed) showInputBar();
        else showEmailGate();
      } else if (state.emailConfirmed) {
        showInputBar();
        addBotMessage("Olá! ✨ Sou sua personal shopper da Água de Coco. Me conta o que você procura — posso sugerir peças do seu estilo, completar um look ou mostrar as novidades.");
      } else {
        showEmailGate();
        addBotMessage("Olá! Sou sua personal shopper da Água de Coco. ✨\nVou usar seu histórico para sugerir peças perfeitas para você.");
      }
    }
    setTimeout(() => {
      const input = document.getElementById("ml-text-input");
      if (input && state.emailConfirmed) input.focus();
    }, 300);
  }

  function restoreMessages() {
    const messages = document.getElementById("ml-messages");
    messages.innerHTML = "";
    // Restaura async para não bloquear o thread principal
    const msgs = state.messages.slice(-8); // só últimas 8
    let i = 0;
    function restoreNext() {
      if (i >= msgs.length) {
        setTimeout(() => { messages.scrollTop = messages.scrollHeight; }, 50);
        return;
      }
      const msg = msgs[i++];
      if (msg.type === "bot") addBotMessage(msg.text, false);
      else if (msg.type === "user") addUserMessage(msg.text, false);
      else if (msg.type === "products" && msg.products) addProductCarousel(msg.products);
      setTimeout(restoreNext, 0); // yield para não travar
    }
    restoreNext();
  }

  function closePanel() {
    state.open = false;
    document.getElementById("ml-chat-panel").classList.remove("ml-open");
    // Restaura scroll do body no mobile
    document.body.style.overflow = "";
    document.body.style.position = "";
    document.body.style.width = "";
  }

  function showEmailGate() {
    document.getElementById("ml-email-gate").style.display = "flex";
    document.getElementById("ml-input-bar").style.display = "none";
  }

  function showInputBar() {
    document.getElementById("ml-email-gate").style.display = "none";
    document.getElementById("ml-input-bar").style.display = "flex";
  }

  // ── Email ───────────────────────────────────────────────────────────────────
  function confirmEmail() {
    const input = document.getElementById("ml-email-input");
    const email = (input?.value || "").trim().toLowerCase();
    if (!email || !email.includes("@")) {
      if (input) input.style.borderColor = "#e05c3a";
      return;
    }
    // Se email mudou, limpa conversa anterior
    if (state.email && state.email !== email) {
      state.messages = [];
      try { document.getElementById("ml-messages").innerHTML = ""; } catch(_) {}
    }
    state.email = email;
    state.emailConfirmed = true;
    saveState(state);
    showInputBar();
    addBotMessage(`Ótimo, ${email.split("@")[0]}! Me conta o que você está procurando. 🌿`);
    setTimeout(() => document.getElementById("ml-text-input")?.focus(), 100);
  }

  // ── Mensagens ───────────────────────────────────────────────────────────────
  function addBotMessage(text, save = true) {
    const div = document.createElement("div");
    div.className = "ml-msg ml-bot";
    div.textContent = text;
    appendMsg(div);
    if (save) {
      state.messages.push({ type: "bot", text });
      saveState(state);
    }
  }

  function addUserMessage(text, save = true) {
    const div = document.createElement("div");
    div.className = "ml-msg ml-user";
    div.textContent = text;
    appendMsg(div);
    if (save) {
      state.messages.push({ type: "user", text });
      saveState(state);
    }
  }

  function addTyping() {
    const div = document.createElement("div");
    div.className = "ml-msg ml-typing";
    div.id = "ml-typing-indicator";
    div.textContent = "Consultando seu estilo…";
    appendMsg(div);
  }

  function removeTyping() {
    document.getElementById("ml-typing-indicator")?.remove();
  }

  function appendMsg(el) {
    const messages = document.getElementById("ml-messages");
    messages.appendChild(el);
    // Scroll to bottom - important on mobile
    requestAnimationFrame(() => {
      messages.scrollTop = messages.scrollHeight;
      // Extra scroll after images load
      setTimeout(() => { messages.scrollTop = messages.scrollHeight; }, 300);
    });
  }

  // ── Carrossel com imagens ───────────────────────────────────────────────────
  function addProductCarousel(products) {
    if (!products?.length) return;

    const wrapper = document.createElement("div");
    wrapper.className = "ml-msg ml-bot";
    wrapper.style.cssText = "padding:8px 0 4px;max-width:100%;background:transparent;border:none;";

    const scrollWrap = document.createElement("div");
    scrollWrap.className = "ml-carousel-wrap";

    const carousel = document.createElement("div");
    carousel.className = "ml-carousel";

    products.forEach((p) => {
      // Sanitize URL — fix common AI mistakes like aguadecocobr.com
      function fixUrl(u) {
        if (!u) return "#";
        u = String(u).trim();
        // Fix missing dot: aguadecocobr.com → aguadecoco.com.br
        u = u.replace(/aguadecocobr\.com/g, "aguadecoco.com.br");
        // Ensure https
        if (u.startsWith("//")) u = "https:" + u;
        if (!u.startsWith("http") && u.startsWith("/")) u = "https://www.aguadecoco.com.br" + u;
        return u;
      }

      const card = document.createElement("a");
      card.className = "ml-card";
      card.href = fixUrl(p.url);
      card.target = "_self";
      card.rel = "noopener";

      // Imagem do produto
      if (p.image_url && p.image_url.startsWith("http")) {
        const img = document.createElement("img");
        img.className = "ml-card-img";
        img.src = p.image_url;
        img.alt = p.name || "";
        img.loading = "lazy";
        img.decoding = "async";
        img.onerror = function () {
          const ph = document.createElement("div");
          ph.className = "ml-card-img-placeholder";
          ph.textContent = "👗";
          this.parentNode.replaceChild(ph, this);
        };
        card.appendChild(img);
      } else {
        const ph = document.createElement("div");
        ph.className = "ml-card-img-placeholder";
        ph.textContent = "👗";
        card.appendChild(ph);
      }

      // Info
      const body = document.createElement("div");
      body.className = "ml-card-body";
      const hasDiscount = p.list_price && p.list_price !== p.price && p.list_price !== "";
      const priceHtml = p.price
        ? (hasDiscount
            ? `<div class="ml-card-price-de">De: <s>${p.list_price}</s></div>
               <div class="ml-card-price ml-card-price-sale">Por: ${p.price}</div>`
            : `<div class="ml-card-price">${p.price}</div>`)
        : "";
      body.innerHTML = `
        <div class="ml-card-name">${p.name || ""}</div>
        ${priceHtml}
      `;
      card.appendChild(body);

      // Badge complemento
      if (p.is_complement) {
        const badge = document.createElement("div");
        badge.className = "ml-card-complement";
        badge.textContent = "✦ Completa seu look";
        card.appendChild(badge);
      }

      // Botão
      const btn = document.createElement("a");
      btn.className = "ml-card-btn";
      btn.href = fixUrl(p.url);
      btn.target = "_self";
      btn.textContent = "Ver produto";
      card.appendChild(btn);

      // Tracking ao clicar
      card.addEventListener("click", () => trackConversion(p));
      btn.addEventListener("click", (e) => { e.stopPropagation(); trackConversion(p); });

      carousel.appendChild(card);
    });

    scrollWrap.appendChild(carousel);
    wrapper.appendChild(scrollWrap);
    appendMsg(wrapper);
    // Salva apenas referência leve dos produtos (não as imagens)
    state.messages.push({ 
      type: "products", 
      products: products.map(p => ({
        id: p.id,
        name: p.name,
        price: p.price,
        url: p.url,
        image_url: p.image_url,
        category: p.category,
        is_complement: p.is_complement,
      })).slice(0, 6) // máximo 6 produtos salvos
    });
    saveState(state);
  }

  // ── Tracking de conversão ───────────────────────────────────────────────────
  function trackConversion(product) {
    try {
      fetch(`${API_BASE}/api/v1/customer-closet/track-click`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: state.email || "anonimo",
          product_id: String(product.id || product.product_id || ""),
          occasion: product.name || "",
          source: "widget_stylist_chat",
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
    addTyping();

    try {
      const res = await fetch(`${API_BASE}/api/v1/customer-closet/stylist-chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: state.email || "anonimo@aguadecoco.com.br",
          message,
          page_context: getPageContext(),
          limit: 6,
        }),
      });

      removeTyping();

      if (!res.ok) throw new Error("HTTP " + res.status);

      const data = await res.json();

      if (data.message) addBotMessage(data.message);

      if (data.products?.length) {
        addProductCarousel(data.products);
        maybeShowChips(message, data.products);
      } else {
        addBotMessage("Não encontrei produtos disponíveis para esse pedido agora. Tente com outras palavras?");
        addRefinementChips(["🔄 Tentar novamente", "🎨 Mudar a ocasião", "🌊 Ver looks de praia", "💃 Ver looks de festa"]);
      }
    } catch (err) {
      removeTyping();
      addBotMessage("Ops, tive um problema ao buscar sugestões. Tente novamente em instantes.");
      console.error("[MoodLab]", err);
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

    // Badge após 4s
    setTimeout(() => {
      if (!state.open) {
        const badge = document.getElementById("ml-fab-badge");
        if (badge) badge.style.display = "block";
      }
    }, 4000);
  }

  // Inicia com pequeno delay para não bloquear carregamento da página
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(init, 300));
  } else {
    setTimeout(init, 300);
  }
})();
