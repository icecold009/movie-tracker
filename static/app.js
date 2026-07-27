(function () {
    "use strict";

    document.documentElement.classList.add("js-ready");

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

    const revealItems = document.querySelectorAll("[data-reveal]");
    if ("IntersectionObserver" in window) {
        const revealObserver = new IntersectionObserver(function (items, observer) {
            items.forEach(function (item) {
                if (item.isIntersecting) {
                    item.target.classList.add("is-visible");
                    observer.unobserve(item.target);
                }
            });
        }, { threshold: 0.08 });

        revealItems.forEach(function (item, index) {
            item.style.setProperty("--reveal-delay", `${Math.min(index * 55, 440)}ms`);
            revealObserver.observe(item);
        });
    } else {
        revealItems.forEach(function (item) {
            item.classList.add("is-visible");
        });
    }

    document.querySelectorAll("[data-pointer-glow]").forEach(function (card) {
        card.addEventListener("pointermove", function (event) {
            if (event.pointerType === "touch") {
                return;
            }
            const bounds = card.getBoundingClientRect();
            const x = ((event.clientX - bounds.left) / bounds.width) * 100;
            const y = ((event.clientY - bounds.top) / bounds.height) * 100;
            card.style.setProperty("--pointer-x", `${x}%`);
            card.style.setProperty("--pointer-y", `${y}%`);
        });
        card.addEventListener("pointerleave", function () {
            card.style.removeProperty("--pointer-x");
            card.style.removeProperty("--pointer-y");
        });
    });
}());
