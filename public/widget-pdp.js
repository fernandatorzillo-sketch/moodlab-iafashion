(function () {
  const CONFIG = {
    API_BASE:
      (window.MOODLAB_CLOSET_CONFIG && window.MOODLAB_CLOSET_CONFIG.API_BASE) ||
      "https://SEU-DOMINIO-API.com",
  };

  function getLoggedEmail() {
    try {
      return (
        window.vtexjs &&
        window.vtexjs.checkout &&
        window.vtexjs.checkout.orderForm &&
        window.vtexjs.checkout.orderForm.clientProfileData &&
        window.vtexjs.checkout.orderForm.clientProfileData.email
      ) || "";
    } catch (e) {
      return "";
    }
  }

  function injectStyles() {
    if (document.getElementById("moodlab-pdp-styles")) return;

    const style = document.createElement("style");
    style.id = "moodlab-pdp-styles";
    style.innerHTML = `
      .ml-pdp-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 12px 18px;
        border-radius: 999px;
        border: 1px solid #d8c8af;
        background: #fff;
        color: #7c6c52;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        margin-top: 12px;
      }

      .ml-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.4);
        z-index: 999998;
        display: none;
      }

      .ml-overlay.open {
        display: block;
      }

      .ml-drawer {
        position: fixed;
        top: 0;
        right: 0;
        width: min(430px, 95vw);
        height: 100vh;
        background: #fff;
        z-index: 999999;
        box-shadow: -10px 0 30px rgba(0,0,0,0.10);
        transform: translateX(100%);
        transition: transform .2s ease;
        display: flex;
        flex-direction: column;
      }

      .ml-drawer.open {
        transform: translateX(0);
      }

      .ml-drawer-header {
        padding: 20px;
        border-bottom: 1px solid #eadfce;
      }

      .ml-drawer-title {
        margin: 0 0 8px;
        font-size: 22px;
        color: #2f2a24;
      }

      .ml-drawer-close {
        background: none;
        border: none;
        color: #7c6c52;
        cursor: pointer;
        padding: 0;
      }

      .ml-drawer-body {
        padding: 20px;
        overflow-y: auto;
        flex: 1;
      }

      .ml-pdp-grid {
        display: grid;
        gap: 16px;
      }

      .ml-pdp-card {
        border: 1px solid #eadfce;
        border-radius: 16px;
        overflow: hidden;
        background: #fff;
      }

      .ml-pdp-card img {
        width: 100%;
        aspect-ratio: 3/4;
        object-fit: cover;
        display: block;
        background: #f8f3ec;
      }

      .ml-pdp-card-body {
        padding: 14px;
      }

      .ml-pdp-card-category {
        font-size: 11px;
        text-transform: uppercase;
        color: #9a8f83;
        margin-bottom: 6px;
      }

      .ml-pdp-card-title {
        font-size: 16px;
        color: #2f2a24;
        margin-bottom: 8px;
      }

      .ml-pdp-card-reason {
        font-size: 13px;
        color: #7a6f63;
        margin-bottom: 12px;
      }

      .ml-pdp-link {
        display: inline-flex;
        padding: 10px 14px;
        border-radius: 999px;
        text-decoration: none;
        background: #b7a36b;
        color: #fff;
        font-weight: 600;
        font-size: 13px;
      }
    `;
    document.head.appendChild(style);
  }

  function ensureDrawer() {
    let overlay = document.getElementById("ml-pdp-overlay");
    let drawer = document.getElementById("ml-pdp-drawer");

    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "ml-pdp-overlay";
      overlay.className = "ml-overlay";
      overlay.addEventListener("click", closeDrawer);
      document.body.appendChild(overlay);
    }

    if (!drawer) {
      drawer = document.createElement("div");
      drawer.id = "ml-pdp-drawer";
      drawer.className = "ml-drawer";
      drawer.innerHTML = `
        <div class="ml-drawer-header">
          <h2 class="ml-drawer-title">Combina com seu closet</h2>
          <button class="ml-drawer-close" type="button">Fechar</button>
        </div>
        <div class="ml-drawer-body" id="ml-pdp-drawer-body">Carregando...</div>
      `;
      drawer.querySelector(".ml-drawer-close").addEventListener("click", closeDrawer);
      document.body.appendChild(drawer);
    }

    return { overlay, drawer };
  }

  function openDrawer() {
    const { overlay, drawer } = ensureDrawer();
    overlay.classList.add("open");
    drawer.classList.add("open");
  }

  function closeDrawer() {
    const overlay = document.getElementById("ml-pdp-overlay");
    const drawer = document.getElementById("ml-pdp-drawer");
    if (overlay) overlay.classList.remove("open");
    if (drawer) drawer.classList.remove("open");
  }

  async function fetchRecommendations(email) {
    const response = await fetch(`${CONFIG.API_BASE}/api/v1/customer-closet/recommendations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: email,
        answers: {
          objetivo: "completar_look",
          ocasiao: "praia",
          estilo: "elegante"
        },
        limit: 6
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }

    return response.json();
  }

  function renderRecommendations(data) {
    const body = document.getElementById("ml-pdp-drawer-body");
    if (!body) return;

    const items = Array.isArray(data.recommendations) ? data.recommendations : [];
    if (!items.length) {
      body.innerHTML = `<div>Sem recomendações no momento.</div>`;
      return;
    }

    body.innerHTML = `
      <div class="ml-pdp-grid">
        ${items
          .map(
            (item) => `
            <div class="ml-pdp-card">
              ${
                item.imagem_url
                  ? `<img src="${item.imagem_url}" alt="${item.nome || "Produto"}" />`
                  : `<div style="aspect-ratio:3/4;background:#f8f3ec;"></div>`
              }
              <div class="ml-pdp-card-body">
                <div class="ml-pdp-card-category">${item.categoria || ""}</div>
                <div class="ml-pdp-card-title">${item.nome || "Produto"}</div>
                <div class="ml-pdp-card-reason">${item.motivo || ""}</div>
                <a class="ml-pdp-link" href="${item.link_produto || "#"}">Ver produto</a>
              </div>
            </div>`
          )
          .join("")}
      </div>
    `;
  }

  async function handleClick() {
    openDrawer();
    const body = document.getElementById("ml-pdp-drawer-body");
    body.innerHTML = "Carregando recomendações...";

    try {
      const email = getLoggedEmail();
      if (!email) {
        body.innerHTML = "Não foi possível identificar o cliente logado.";
        return;
      }

      const data = await fetchRecommendations(email);
      renderRecommendations(data);
    } catch (e) {
      body.innerHTML = `Erro ao carregar recomendações: ${e.message || e}`;
    }
  }

  function mount() {
    injectStyles();

    const target =
      document.querySelector(".product-info") ||
      document.querySelector(".product-details") ||
      document.querySelector(".buy-button-box") ||
      document.querySelector(".descricao-preco") ||
      null;

    if (!target || document.getElementById("ml-pdp-btn")) return;

    const btn = document.createElement("button");
    btn.id = "ml-pdp-btn";
    btn.className = "ml-pdp-btn";
    btn.type = "button";
    btn.textContent = "Combina com seu closet";
    btn.addEventListener("click", handleClick);

    target.appendChild(btn);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();