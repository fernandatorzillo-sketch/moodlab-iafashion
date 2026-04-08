(function () {
  const API_BASE = "https://SEU-ENDERECO-DO-BACKEND";
  const TEST_EMAIL = "shirleyanastacio8@gmail.com";
  const REQUEST_TIMEOUT_MS = 15000;

  const BRAND = {
    accent: "#b7a56a",
    accentDark: "#9f8e58",
    border: "#e9e1d2",
    bgSoft: "#fbf8f1",
    text: "#2b2b2b",
    textSoft: "#6f6558",
    error: "#b94a48",
    white: "#ffffff",
    shadow: "0 12px 32px rgba(0,0,0,0.10)",
    radius: "16px",
  };

  function log(...args) {
    console.log("[MoodLab Widget]", ...args);
  }

  function normalizeText(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function getLoggedEmail() {
    try {
      const checkoutEmail =
        window.vtexjs &&
        window.vtexjs.checkout &&
        window.vtexjs.checkout.orderForm &&
        window.vtexjs.checkout.orderForm.clientProfileData &&
        window.vtexjs.checkout.orderForm.clientProfileData.email;

      if (checkoutEmail) return String(checkoutEmail).trim().toLowerCase();

      const sessionEmail =
        window.__RUNTIME__ &&
        window.__RUNTIME__.session &&
        window.__RUNTIME__.session.email;

      if (sessionEmail) return String(sessionEmail).trim().toLowerCase();
    } catch (e) {
      console.error("Erro ao capturar email logado:", e);
    }

    return TEST_EMAIL;
  }

  function fetchWithTimeout(url, options = {}, timeout = REQUEST_TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    return fetch(url, {
      ...options,
      signal: controller.signal,
    }).finally(() => clearTimeout(timer));
  }

  async function apiGet(path) {
    const response = await fetchWithTimeout(`${API_BASE}${path}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
      },
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Erro ${response.status}`);
    }

    return response.json();
  }

  async function apiPost(path, payload) {
    const response = await fetchWithTimeout(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Erro ${response.status}`);
    }

    return response.json();
  }

  function ensureRoot() {
    let root = document.getElementById("moodlab-widget-root");
    if (root) return root;

    root = document.createElement("div");
    root.id = "moodlab-widget-root";
    document.body.appendChild(root);
    return root;
  }

  function createStyles() {
    if (document.getElementById("moodlab-widget-styles")) return;

    const style = document.createElement("style");
    style.id = "moodlab-widget-styles";
    style.innerHTML = `
      #moodlab-widget-root {
        font-family: Arial, Helvetica, sans-serif;
      }

      .mlw-floating {
        position: fixed;
        right: 20px;
        bottom: 110px;
        z-index: 999999;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .mlw-btn {
        appearance: none;
        border: none;
        cursor: pointer;
        transition: all .2s ease;
      }

      .mlw-fab-btn {
        background: ${BRAND.accent};
        color: ${BRAND.white};
        border-radius: 999px;
        padding: 14px 20px;
        font-size: 15px;
        font-weight: 600;
        box-shadow: ${BRAND.shadow};
        min-width: 220px;
      }

      .mlw-fab-btn:hover {
        background: ${BRAND.accentDark};
        transform: translateY(-1px);
      }

      .mlw-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,.28);
        z-index: 999998;
        opacity: 0;
        pointer-events: none;
        transition: opacity .2s ease;
      }

      .mlw-overlay.open {
        opacity: 1;
        pointer-events: auto;
      }

      .mlw-drawer {
        position: fixed;
        top: 0;
        right: 0;
        width: min(460px, 92vw);
        height: 100vh;
        background: ${BRAND.white};
        z-index: 999999;
        box-shadow: -10px 0 30px rgba(0,0,0,.12);
        transform: translateX(100%);
        transition: transform .25s ease;
        display: flex;
        flex-direction: column;
      }

      .mlw-drawer.open {
        transform: translateX(0);
      }

      .mlw-header {
        padding: 24px 24px 16px;
        border-bottom: 1px solid ${BRAND.border};
      }

      .mlw-title {
        font-size: 20px;
        font-weight: 700;
        color: ${BRAND.text};
        margin: 0 0 10px 0;
      }

      .mlw-close {
        background: transparent;
        color: ${BRAND.textSoft};
        font-size: 15px;
        padding: 0;
      }

      .mlw-close:hover {
        color: ${BRAND.text};
      }

      .mlw-body {
        padding: 20px 24px 28px;
        overflow-y: auto;
        flex: 1;
        background: ${BRAND.white};
      }

      .mlw-loading,
      .mlw-empty,
      .mlw-error {
        font-size: 16px;
        line-height: 1.5;
        padding: 8px 0;
      }

      .mlw-loading,
      .mlw-empty {
        color: ${BRAND.textSoft};
      }

      .mlw-error {
        color: ${BRAND.error};
        white-space: pre-wrap;
      }

      .mlw-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 18px;
      }

      .mlw-card {
        border: 1px solid ${BRAND.border};
        border-radius: ${BRAND.radius};
        overflow: hidden;
        background: ${BRAND.white};
      }

      .mlw-card-image {
        width: 100%;
        aspect-ratio: 3 / 4;
        background: ${BRAND.bgSoft};
        overflow: hidden;
      }

      .mlw-card-image img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }

      .mlw-card-no-image {
        width: 100%;
        height: 100%;
        min-height: 240px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: ${BRAND.textSoft};
        font-size: 14px;
      }

      .mlw-card-content {
        padding: 14px 14px 16px;
      }

      .mlw-chip {
        display: inline-block;
        margin-bottom: 8px;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: .04em;
        color: ${BRAND.accentDark};
      }

      .mlw-card-name {
        font-size: 18px;
        font-weight: 700;
        line-height: 1.35;
        color: ${BRAND.text};
        margin-bottom: 8px;
      }

      .mlw-card-reason {
        font-size: 14px;
        color: ${BRAND.textSoft};
        line-height: 1.45;
        margin-bottom: 12px;
      }

      .mlw-card-price {
        font-size: 15px;
        font-weight: 700;
        color: ${BRAND.text};
        margin-bottom: 12px;
      }

      .mlw-link-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: ${BRAND.accent};
        color: ${BRAND.white};
        text-decoration: none;
        border-radius: 12px;
        padding: 11px 16px;
        font-weight: 600;
        font-size: 14px;
      }

      .mlw-link-btn:hover {
        background: ${BRAND.accentDark};
      }

      .mlw-form {
        display: grid;
        gap: 18px;
      }

      .mlw-field label {
        display: block;
        font-size: 15px;
        font-weight: 600;
        color: ${BRAND.text};
        margin-bottom: 8px;
      }

      .mlw-field select {
        width: 100%;
        height: 56px;
        border-radius: 12px;
        border: 1px solid ${BRAND.border};
        background: ${BRAND.white};
        padding: 0 14px;
        font-size: 16px;
        color: ${BRAND.text};
        outline: none;
      }

      .mlw-primary {
        height: 54px;
        border-radius: 12px;
        background: ${BRAND.accent};
        color: ${BRAND.white};
        font-size: 17px;
        font-weight: 700;
      }

      .mlw-primary:hover {
        background: ${BRAND.accentDark};
      }

      .mlw-primary[disabled] {
        opacity: .65;
        cursor: not-allowed;
      }

      .mlw-subtitle {
        font-size: 15px;
        color: ${BRAND.textSoft};
        line-height: 1.5;
        margin-bottom: 18px;
      }

      .mlw-section-title {
        font-size: 16px;
        font-weight: 700;
        color: ${BRAND.text};
        margin: 0 0 14px 0;
      }

      .mlw-back {
        margin-bottom: 16px;
        background: transparent;
        color: ${BRAND.accentDark};
        font-weight: 600;
        padding: 0;
      }

      @media (max-width: 768px) {
        .mlw-floating {
          right: 14px;
          bottom: 92px;
        }

        .mlw-fab-btn {
          min-width: 200px;
          font-size: 14px;
          padding: 13px 18px;
        }

        .mlw-header {
          padding: 20px 18px 14px;
        }

        .mlw-body {
          padding: 18px 18px 24px;
        }

        .mlw-card-name {
          font-size: 17px;
        }
      }
    `;
    document.head.appendChild(style);
  }

  const state = {
    drawerMode: null,
    drawerOpen: false,
    email: null,
    questions: null,
    mounted: false,
  };

  function currency(value) {
    const number = Number(value || 0);
    if (!number) return "";
    try {
      return number.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
      });
    } catch {
      return `R$ ${number.toFixed(2)}`;
    }
  }

  function createElement(tag, className, html) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (html !== undefined) el.innerHTML = html;
    return el;
  }

  function getOrCreateOverlay(root) {
    let overlay = root.querySelector(".mlw-overlay");
    if (overlay) return overlay;

    overlay = createElement("div", "mlw-overlay");
    overlay.addEventListener("click", closeDrawer);
    root.appendChild(overlay);
    return overlay;
  }

  function getOrCreateDrawer(root) {
    let drawer = root.querySelector(".mlw-drawer");
    if (drawer) return drawer;

    drawer = createElement("div", "mlw-drawer");

    const header = createElement("div", "mlw-header");
    const title = createElement("h2", "mlw-title");
    title.id = "mlw-drawer-title";

    const close = createElement("button", "mlw-btn mlw-close", "Fechar");
    close.type = "button";
    close.addEventListener("click", closeDrawer);

    header.appendChild(title);
    header.appendChild(close);

    const body = createElement("div", "mlw-body");
    body.id = "mlw-drawer-body";

    drawer.appendChild(header);
    drawer.appendChild(body);
    root.appendChild(drawer);
    return drawer;
  }

  function setDrawerTitle(text) {
    const title = document.getElementById("mlw-drawer-title");
    if (title) title.textContent = text;
  }

  function setDrawerContent(node) {
    const body = document.getElementById("mlw-drawer-body");
    if (!body) return;
    body.innerHTML = "";
    body.appendChild(node);
  }

  function openDrawer(mode) {
    state.drawerMode = mode;
    state.drawerOpen = true;

    const root = ensureRoot();
    const overlay = getOrCreateOverlay(root);
    const drawer = getOrCreateDrawer(root);

    overlay.classList.add("open");
    drawer.classList.add("open");
  }

  function closeDrawer() {
    state.drawerOpen = false;

    const root = ensureRoot();
    const overlay = root.querySelector(".mlw-overlay");
    const drawer = root.querySelector(".mlw-drawer");

    if (overlay) overlay.classList.remove("open");
    if (drawer) drawer.classList.remove("open");
  }

  function ensureFloatingButtons(root) {
    let floating = root.querySelector(".mlw-floating");
    if (floating) return floating;

    floating = createElement("div", "mlw-floating");

    const purchasesBtn = createElement(
      "button",
      "mlw-btn mlw-fab-btn",
      "Com base nas suas compras"
    );
    purchasesBtn.type = "button";
    purchasesBtn.addEventListener("click", handleOpenPurchases);

    const lookBtn = createElement(
      "button",
      "mlw-btn mlw-fab-btn",
      "Monte seu look"
    );
    lookBtn.type = "button";
    lookBtn.addEventListener("click", handleOpenLookBuilder);

    floating.appendChild(purchasesBtn);
    floating.appendChild(lookBtn);
    root.appendChild(floating);

    return floating;
  }

  function buildLoading(message = "Carregando...") {
    return createElement("div", "mlw-loading", message);
  }

  function buildError(message) {
    return createElement("div", "mlw-error", message);
  }

  function buildEmpty(message) {
    return createElement("div", "mlw-empty", message);
  }

  function recommendationCard(item) {
    const card = createElement("div", "mlw-card");

    const imageWrap = createElement("div", "mlw-card-image");
    const imgUrl = item.imagem_url || item.image_url || "";
    if (imgUrl) {
      const img = document.createElement("img");
      img.src = imgUrl;
      img.alt = item.nome || "Produto";
      imageWrap.appendChild(img);
    } else {
      imageWrap.appendChild(
        createElement("div", "mlw-card-no-image", "Sem imagem")
      );
    }

    const content = createElement("div", "mlw-card-content");
    const chip = createElement(
      "div",
      "mlw-chip",
      (item.categoria || item.departamento || "Sugestão").replaceAll("_", " ")
    );
    const name = createElement("div", "mlw-card-name", item.nome || "Produto");
    const reason = createElement(
      "div",
      "mlw-card-reason",
      item.motivo || "Selecionado para você"
    );
    const priceText = currency(item.price);
    const price = priceText
      ? createElement("div", "mlw-card-price", priceText)
      : null;

    const link = document.createElement("a");
    link.className = "mlw-link-btn";
    link.href = item.link_produto || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Ver produto";

    content.appendChild(chip);
    content.appendChild(name);
    content.appendChild(reason);
    if (price) content.appendChild(price);
    content.appendChild(link);

    card.appendChild(imageWrap);
    card.appendChild(content);
    return card;
  }

  function renderRecommendationsView(title, recommendations, subtitleText) {
    setDrawerTitle(title);

    const container = document.createElement("div");

    if (subtitleText) {
      const subtitle = createElement("div", "mlw-subtitle", subtitleText);
      container.appendChild(subtitle);
    }

    if (!recommendations || !recommendations.length) {
      container.appendChild(
        buildEmpty("Nenhuma recomendação encontrada para esse perfil.")
      );
      setDrawerContent(container);
      return;
    }

    const grid = createElement("div", "mlw-grid");
    recommendations.forEach((item) => {
      grid.appendChild(recommendationCard(item));
    });

    container.appendChild(grid);
    setDrawerContent(container);
  }

  async function handleOpenPurchases() {
    try {
      const email = getLoggedEmail();
      state.email = email;

      openDrawer("purchases");
      setDrawerTitle("Com base nas suas compras");
      setDrawerContent(buildLoading("Buscando sugestões personalizadas..."));

      const data = await apiPost("/api/v1/customer-closet/recommendations", {
        email,
        answers: {
          ocasiao: "praia",
          objetivo: "completar_look",
          estilo: "elegante",
        },
        limit: 8,
      });

      log("Recommendations purchases:", data);

      renderRecommendationsView(
        "Com base nas suas compras",
        data.recommendations || [],
        "Sugestões compatíveis com o seu histórico e com o seu perfil de compra."
      );
    } catch (e) {
      console.error("Erro ao carregar recomendações por compras:", e);
      setDrawerTitle("Com base nas suas compras");
      setDrawerContent(
        buildError(
          `Não foi possível carregar recomendações.\n\n${
            e && e.message ? e.message : String(e)
          }`
        )
      );
    }
  }

  function buildQuestionsForm(questions) {
    const wrapper = document.createElement("div");

    const subtitle = createElement(
      "div",
      "mlw-subtitle",
      "Responda rapidamente e eu sugiro peças mais alinhadas com a ocasião e seu objetivo."
    );
    wrapper.appendChild(subtitle);

    const form = createElement("div", "mlw-form");

    questions.forEach((question) => {
      const field = createElement("div", "mlw-field");
      const label = document.createElement("label");
      label.textContent = question.label || question.id;

      const select = document.createElement("select");
      select.name = question.id;

      (question.options || []).forEach((option) => {
        const el = document.createElement("option");
        el.value = option.value;
        el.textContent = option.label;
        select.appendChild(el);
      });

      field.appendChild(label);
      field.appendChild(select);
      form.appendChild(field);
    });

    const submit = createElement("button", "mlw-btn mlw-primary", "Ver sugestões");
    submit.type = "button";

    submit.addEventListener("click", async () => {
      try {
        submit.disabled = true;
        submit.textContent = "Montando sugestões...";

        const answers = {};
        form.querySelectorAll("select").forEach((select) => {
          answers[select.name] = select.value;
        });

        setDrawerTitle("Monte seu look");
        setDrawerContent(buildLoading("Montando sugestões..."));

        const email = getLoggedEmail();
        state.email = email;

        const data = await apiPost("/api/v1/customer-closet/recommendations", {
          email,
          answers,
          limit: 8,
        });

        log("Recommendations look builder:", data);

        renderRecommendationsView(
          "Monte seu look",
          data.recommendations || [],
          "Sugestões com base na ocasião, objetivo e estilo que você escolheu."
        );
      } catch (e) {
        console.error("Erro ao montar look:", e);
        setDrawerTitle("Monte seu look");
        setDrawerContent(
          buildError(
            `Não foi possível carregar recomendações.\n\n${
              e && e.message ? e.message : String(e)
            }`
          )
        );
      }
    });

    wrapper.appendChild(form);
    wrapper.appendChild(submit);
    return wrapper;
  }

  async function handleOpenLookBuilder() {
    try {
      openDrawer("look-builder");
      setDrawerTitle("Monte seu look");
      setDrawerContent(buildLoading("Carregando perguntas..."));

      let questions = state.questions;
      if (!questions) {
        const response = await apiGet("/api/v1/customer-closet/questions");
        questions = response.questions || [];
        state.questions = questions;
      }

      setDrawerTitle("Monte seu look");
      setDrawerContent(buildQuestionsForm(questions));
    } catch (e) {
      console.error("Erro ao carregar formulário do look:", e);
      setDrawerTitle("Monte seu look");
      setDrawerContent(
        buildError(
          `Não foi possível carregar as perguntas.\n\n${
            e && e.message ? e.message : String(e)
          }`
        )
      );
    }
  }

  function mount() {
    if (state.mounted) return;
    state.mounted = true;

    const root = ensureRoot();
    createStyles();
    ensureFloatingButtons(root);
    getOrCreateOverlay(root);
    getOrCreateDrawer(root);

    log("Widget iniciado");
  }

  function waitForBody(maxAttempts = 40, delay = 500) {
    let attempts = 0;

    const interval = setInterval(() => {
      attempts += 1;

      if (document.body) {
        clearInterval(interval);
        mount();
        return;
      }

      if (attempts >= maxAttempts) {
        clearInterval(interval);
      }
    }, delay);
  }

  waitForBody();
})();