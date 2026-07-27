(function () {
    "use strict";

    const skeleton = document.querySelector("[data-page-skeleton]");
    if (!skeleton) {
        return;
    }

    const main = document.querySelector("main");

    function showLoadingState() {
        skeleton.hidden = false;
        skeleton.setAttribute("aria-hidden", "false");
        if (main) {
            main.setAttribute("aria-busy", "true");
        }
    }

    document.addEventListener("click", function (event) {
        if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
        ) {
            return;
        }

        const link = event.target.closest("a[data-loading-link]");
        if (!link || link.target === "_blank" || link.hasAttribute("download")) {
            return;
        }

        const destination = new URL(link.href, window.location.href);
        if (destination.origin !== window.location.origin) {
            return;
        }

        showLoadingState();
    });

    document.addEventListener("submit", function (event) {
        const form = event.target.closest("form[data-loading-form]");
        if (form && !event.defaultPrevented) {
            showLoadingState();
        }
    });
}());
