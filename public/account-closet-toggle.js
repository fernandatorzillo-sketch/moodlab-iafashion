(function () {
  function applyMaxLength() {
    try {
      var input = $('.vtex-address-form__number .vtex-address-form-3-x-input');
      if (input.length) {
        input.attr('maxlength', '6');
      }
    } catch (e) {}
  }

  function isClosetHash() {
    return window.location.href.indexOf("#closet") > -1;
  }

  function showClosetMode() {
    var wrapper = document.getElementById("moodlab-account-closet-wrapper");
    var defaultContent = document.getElementById("moodlab-account-default");
    if (!wrapper || !defaultContent) return;

    wrapper.style.display = "block";
    defaultContent.style.display = "none";
  }

  function showDefaultMode() {
    var wrapper = document.getElementById("moodlab-account-closet-wrapper");
    var defaultContent = document.getElementById("moodlab-account-default");
    if (!wrapper || !defaultContent) return;

    wrapper.style.display = "none";
    defaultContent.style.display = "block";
  }

  function closetRendered() {
    var root = document.getElementById("moodlab-account-closet-root");
    if (!root) return false;
    return !!(root.innerHTML && root.innerHTML.replace(/\s/g, "").length > 0);
  }

  function toggleMoodlabClosetSafe() {
    if (!isClosetHash()) {
      showDefaultMode();
      return;
    }

    var root = document.getElementById("moodlab-account-closet-root");
    if (!root) {
      showDefaultMode();
      return;
    }

    root.style.minHeight = "300px";

    setTimeout(function () {
      if (closetRendered()) {
        showClosetMode();
      } else {
        showDefaultMode();
      }
    }, 1200);
  }

  function initMoodlabAccountCloset() {
    applyMaxLength();
    toggleMoodlabClosetSafe();

    try {
      $(window).on("orderFormUpdated.vtex", function () {
        applyMaxLength();
      });
    } catch (e) {}

    try {
      var observer = new MutationObserver(function () {
        applyMaxLength();
        toggleMoodlabClosetSafe();
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: false
      });
    } catch (e) {}

    window.addEventListener("hashchange", function () {
      applyMaxLength();
      toggleMoodlabClosetSafe();
    });

    window.addEventListener("load", function () {
      toggleMoodlabClosetSafe();
      setTimeout(toggleMoodlabClosetSafe, 500);
      setTimeout(toggleMoodlabClosetSafe, 1500);
      setTimeout(toggleMoodlabClosetSafe, 3000);
    });

    document.addEventListener("DOMContentLoaded", function () {
      toggleMoodlabClosetSafe();
      setTimeout(toggleMoodlabClosetSafe, 500);
      setTimeout(toggleMoodlabClosetSafe, 1500);
    });
  }

  initMoodlabAccountCloset();
})();