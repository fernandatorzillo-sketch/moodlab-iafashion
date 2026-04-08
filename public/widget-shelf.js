(function () {
  const CONFIG = {
    API_BASE:
      (window.MOODLAB_CLOSET_CONFIG && window.MOODLAB_CLOSET_CONFIG.API_BASE) ||
      "https://SEU-DOMINIO-API.com",
  };

  function injectStyles() {
    if (document.getElementById("moodlab-shelf-styles")) return;

    const style = document.createElement("style");
    style.id = "moodlab-shelf-styles";
    style.innerHTML = `
      .ml-shelf-floating {
        position: fixed;
        right: 16px;
        bottom: 24px;
        z-index: 999999;
      }

      .ml-shelf-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 13px 18px;
        border-radius: 999px;
        border: 1px solid #b7a36b;
        background: #b7a36b;
        color: #fff;
        cursor: pointer;
        font-size: 14px;
        font-weight: 700;
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      }

      .ml-shelf-modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,.35);
        z-index: 999998;
        display: none;
      }

      .ml-shelf-modal-overlay.open {
        display: block;
      }

      .ml-shelf-modal {
        position: fixed;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        width: min(560px, 92vw);
        background: #fff;
        border-radius: 18px;
        z-index: 999999;
        box-shadow: 0 18px 40px rgba(0,0,0,.12);
        padding: 24px;
        display: none;
      }

      .ml-shelf-modal.open {
        display: block;
      }

      .ml-shelf-modal h3 {
        margin: 0 0 10px;
        color: #2f2a24;
      }

      .ml-shelf-modal p {
        margin: 0 0 18px;
        color: #7a6f63;
      }

      .ml-shelf-actions {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }

      .ml-shelf-action-btn {
        border-radius: 999px;
        padding: 11px 16px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
      }

      .ml-shelf-action-primary {
        border: 1px solid #b7a36b;
        background: #b7a36b;
        color: #fff;
      }

      .ml-shelf-action-secondary {
        border: 1px solid #d8c8af;
        background: #fff;
        color: #7c6c52;
      }
    `;
    document.head.appendChild(style);
  }

  function ensureModal() {
    let overlay = document.getElementById("ml-shelf-modal-overlay");
    let modal = document.getElementById("ml-shelf-modal");

    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "ml-shelf-modal-overlay";
      overlay.className = "ml-shelf-modal-overlay";
      overlay.addEventListener("click", closeModal);
      document.body.appendChild(overlay);
    }

    if (!modal) {
      modal = document.createElement("div");
      modal.id = "ml-shelf-modal";
      modal.className = "ml-shelf-modal";
      modal.innerHTML = `
        <h3>Closet Omnichannel</h3>
        <p>Quer ver sugestões com base no seu histórico ou montar um look?</p>
        <div class="ml-shelf-actions">
          <button id="ml-shelf-open-purchases" class="ml-shelf-action-btn ml-shelf-action-primary" type="button">
            Com base nas suas compras
          </button>
          <button id="ml-shelf-open-look" class="ml-shelf-action-btn ml-shelf-action-secondary" type="button">
            Monte seu look
          </button>
        </div>
      `;
      document.body.appendChild(modal);
    }

    const btnPurchases = document.getElementById("ml-shelf-open-purchases");
    const btnLook = document.getElementById("ml-shelf-open-look");

    if (btnPurchases && !btnPurchases.dataset.bound) {
      btnPurchases.dataset.bound = "true";
      btnPurchases.addEventListener("click", function () {
        closeModal();
        if (window.MoodLabPDPDrawer && typeof window.MoodLabPDPDrawer.openPurchases === "function") {
          window.MoodLabPDPDrawer.openPurchases();
        } else {
          window.location.href = "/account";
        }
      });
    }

    if (btnLook && !btnLook.dataset.bound) {
      btnLook.dataset.bound = "true";
      btnLook.addEventListener("click", function () {
        closeModal();
        if (window.MoodLabPDPDrawer && typeof window.MoodLabPDPDrawer.openLookBuilder === "function") {
          window.MoodLabPDPDrawer.openLookBuilder();
        } else {
          window.location.href = "/account";
        }
      });
    }
  }

  function openModal() {
    ensureModal();
    document.getElementById("ml-shelf-modal-overlay").classList.add("open");
    document.getElementById("ml-shelf-modal").classList.add("open");
  }

  function closeModal() {
    const overlay = document.getElementById("ml-shelf-modal-overlay");
    const modal = document.getElementById("ml-shelf-modal");
    if (overlay) overlay.classList.remove("open");
    if (modal) modal.classList.remove("open");
  }

  function mount() {
    injectStyles();
    if (document.getElementById("ml-shelf-floating")) return;

    const wrap = document.createElement("div");
    wrap.id = "ml-shelf-floating";
    wrap.className = "ml-shelf-floating";

    const btn = document.createElement("button");
    btn.className = "ml-shelf-btn";
    btn.type = "button";
    btn.textContent = "Closet Omnichannel";
    btn.addEventListener("click", openModal);

    wrap.appendChild(btn);
    document.body.appendChild(wrap);

    ensureModal();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();