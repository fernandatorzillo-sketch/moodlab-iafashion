(function () {
  const CONFIG = {
    LOGIN_URL: "/login?returnUrl=/secure/account#/closet",
    CLOSET_URL: "/secure/account#/closet"
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
      .ml-floating-closet-btn {
        position: fixed;
        right: 24px;
        bottom: 110px;
        width: 58px;
        height: 58px;
        border-radius: 999px;
        background: #b7a36b;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        box-shadow: 0 10px 24px rgba(0,0,0,0.18);
        cursor: pointer;
        text-decoration: none;
        font-size: 13px;
        font-weight: 700;
      }
    `;
    document.head.appendChild(style);
  }

  function createButton() {
    const btn = document.createElement("a");
    btn.className = "ml-floating-closet-btn";
    btn.innerText = "Closet";

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