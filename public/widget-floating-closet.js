(function () {
  const CONFIG = {
    LOGIN_URL: "/login?returnUrl=/_secure/account#/closet",
    CLOSET_URL: "/_secure/account#/closet",
    BTN_ID: "ml-floating-closet-btn"
  };

  function getEmail() {
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
    if (document.getElementById("ml-floating-closet-style")) return;

    const style = document.createElement("style");
    style.id = "ml-floating-closet-style";
    style.innerHTML = `
      #${CONFIG.BTN_ID} {
        position: fixed;
        right: 24px;
        bottom: 110px;
        width: 64px;
        height: 64px;
        border-radius: 999px;
        background: #b7a36b;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        box-shadow: 0 10px 24px rgba(0,0,0,0.18);
        text-decoration: none;
        font-size: 12px;
        font-weight: 700;
        text-align: center;
        line-height: 1.1;
      }
    `;
    document.head.appendChild(style);
  }

  function createButton() {
    if (document.getElementById(CONFIG.BTN_ID)) return;

    const btn = document.createElement("a");
    btn.id = CONFIG.BTN_ID;
    btn.innerHTML = "Meu<br>Closet";

    const email = getEmail();
    btn.href = email ? CONFIG.CLOSET_URL : CONFIG.LOGIN_URL;

    document.body.appendChild(btn);
  }

  function init() {
    injectStyles();
    createButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();