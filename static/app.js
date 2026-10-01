(function () {
    "use strict";

    const documentElement = document.documentElement;
    documentElement.classList.add("js-ready");

    const skeleton = document.querySelector("[data-page-skeleton]");
    const main = document.querySelector("main");
    let openDeleteConfirmation = null;
    let activeModalElement = null;
    let modalBackgroundState = new Map();
    let modalScrollState = null;

    function showLoadingState() {
        if (skeleton) {
            skeleton.hidden = false;
            skeleton.setAttribute("aria-hidden", "false");
        }
        if (main) {
            main.setAttribute("aria-busy", "true");
        }
    }

    function setSubmitState(form, submitter) {
        if (form.dataset.loadingStarted === "true") {
            return false;
        }
        form.dataset.loadingStarted = "true";
        const submitButtons = form.querySelectorAll("button[type=submit]");
        submitButtons.forEach(function (button) {
            button.disabled = true;
            const label = button.dataset.loadingLabel;
            if (label && (button === submitter || submitButtons.length === 1)) {
                button.textContent = label;
            }
        });
        showLoadingState();
        return true;
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
        if (destination.origin === window.location.origin) {
            showLoadingState();
        }
    });

    document.addEventListener("submit", function (event) {
        const form = event.target.closest("form[data-loading-form]");
        if (!form || event.defaultPrevented) {
            return;
        }

        if (form.matches("[data-delete-form]") && form.dataset.confirmed !== "true") {
            event.preventDefault();
            if (openDeleteConfirmation) {
                openDeleteConfirmation(form);
            }
            return;
        }

        if (!setSubmitState(form, event.submitter)) {
            event.preventDefault();
        }
    });

    const passwordInput = document.querySelector("[data-password-input]");
    const passwordToggle = document.querySelector("[data-password-toggle]");
    if (passwordInput && passwordToggle) {
        passwordToggle.addEventListener("click", function () {
            const isPassword = passwordInput.type === "password";
            passwordInput.type = isPassword ? "text" : "password";
            passwordToggle.textContent = isPassword ? "Hide" : "Show";
            passwordToggle.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
        });
    }

    function syncRange(input, output) {
        if (input && output) {
            output.textContent = input.value;
            input.addEventListener("input", function () {
                output.textContent = input.value;
            });
        }
    }

    syncRange(document.getElementById("rating"), document.getElementById("rating-val"));
    syncRange(document.getElementById("modal-rating"), document.getElementById("modal-rating-val"));

    function setupReveal() {
        const revealItems = document.querySelectorAll("[data-reveal]");
        const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (reduceMotion || !("IntersectionObserver" in window)) {
            revealItems.forEach(function (item) { item.classList.add("is-visible"); });
            return;
        }
        const revealObserver = new IntersectionObserver(function (items, observer) {
            items.forEach(function (item) {
                if (item.isIntersecting) {
                    item.target.classList.add("is-visible");
                    observer.unobserve(item.target);
                }
            });
        }, { threshold: 0.08 });
        revealItems.forEach(function (item) {
            revealObserver.observe(item);
        });
    }

    function setupPointerGlow() {
        if (!(window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches)
            || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        document.querySelectorAll("[data-pointer-glow]").forEach(function (card) {
            card.addEventListener("pointermove", function (event) {
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
    }

    function renderPosterPlaceholder(container) {
        container.replaceChildren();
        const mark = document.createElement("span");
        mark.className = "poster-mark";
        mark.textContent = "SW";
        const label = document.createElement("span");
        label.textContent = "Artwork unavailable";
        container.append(mark, label);
    }

    function setupImageFallbacks() {
        document.querySelectorAll(".card-media img").forEach(function (image) {
            const showFallback = function () {
                image.hidden = true;
                const fallback = image.parentElement.querySelector(".poster-placeholder");
                if (fallback) {
                    fallback.hidden = false;
                    fallback.setAttribute("aria-hidden", "false");
                }
            };
            image.addEventListener("error", showFallback);
            if (image.complete && image.naturalWidth === 0) {
                showFallback();
            }
        });
    }

    function setupLibraryFilters() {
        const cards = Array.from(document.querySelectorAll("[data-entry-card]"));
        const sections = Array.from(document.querySelectorAll("[data-library-section]"));
        const searchInput = document.getElementById("library-search");
        const typeFilter = document.getElementById("filter-type");
        const statusFilter = document.getElementById("filter-status");
        const ratingFilter = document.getElementById("filter-rating");
        const sortControl = document.getElementById("sort-library");
        const summary = document.getElementById("filter-summary");
        const reset = document.getElementById("filter-reset");
        const filterEmpty = document.querySelector("[data-filter-empty]");
        if (!searchInput || !typeFilter || !statusFilter || !ratingFilter || !sortControl || !summary || !reset) {
            return;
        }

        function numeric(value) {
            const parsed = Number(value);
            return Number.isFinite(parsed) ? parsed : 0;
        }

        function compareCards(left, right, mode) {
            if (mode === "title-asc" || mode === "title-desc") {
                const result = (left.dataset.entryTitle || "").localeCompare(right.dataset.entryTitle || "", undefined, { sensitivity: "base" });
                return mode === "title-desc" ? -result : result;
            }
            if (mode === "rating-asc" || mode === "rating-desc") {
                const result = numeric(left.dataset.entryRating) - numeric(right.dataset.entryRating);
                return mode === "rating-desc" ? -result : result;
            }
            const leftDate = Date.parse(left.dataset.entryAdded || "") || 0;
            const rightDate = Date.parse(right.dataset.entryAdded || "") || 0;
            return mode === "added-asc" ? leftDate - rightDate : rightDate - leftDate;
        }

        function applyFilters() {
            const searchText = searchInput.value.trim();
            const normalizedQuery = searchText.toLocaleLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
            const type = typeFilter.value;
            const status = statusFilter.value;
            const minimumRating = ratingFilter.value === "all" ? 0 : numeric(ratingFilter.value);
            const sort = sortControl.value;
            const hasFilterCriteria = Boolean(normalizedQuery) || type !== "all" || status !== "all" || minimumRating > 0;
            const hasActiveCriteria = hasFilterCriteria || sort !== "added-desc";
            let visibleTotal = 0;

            sections.forEach(function (section) {
                const sectionCards = cards.filter(function (card) {
                    return card.closest("[data-library-section]") === section;
                });
                const visibleCards = sectionCards.filter(function (card) {
                    const normalizedTitle = (card.dataset.entryTitle || "").toLocaleLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
                    const visible = (type === "all" || card.dataset.entryType === type) &&
                        (status === "all" || card.dataset.entryStatus === status) &&
                        numeric(card.dataset.entryRating) >= minimumRating &&
                        (!normalizedQuery || normalizedTitle.includes(normalizedQuery));
                    card.hidden = !visible;
                    return visible;
                }).sort(function (left, right) { return compareCards(left, right, sort); });
                const grid = section.querySelector("[data-card-grid]");
                const count = section.querySelector("[data-section-count]");
                if (grid) {
                    visibleCards.forEach(function (card) { grid.appendChild(card); });
                    grid.hidden = visibleCards.length === 0;
                }
                section.hidden = visibleCards.length === 0;
                if (count) {
                    count.textContent = visibleCards.length === sectionCards.length
                        ? `${sectionCards.length} titles`
                        : `${visibleCards.length} of ${sectionCards.length} titles`;
                }
                visibleTotal += visibleCards.length;
            });
            const summaryParts = [`Showing ${visibleTotal} of ${cards.length} titles`];
            if (normalizedQuery) {
                summaryParts.push(`Search “${searchText}”`);
            }
            if (type !== "all") {
                summaryParts.push(typeFilter.selectedOptions[0].textContent.trim());
            }
            if (status !== "all") {
                summaryParts.push(statusFilter.selectedOptions[0].textContent.trim());
            }
            if (minimumRating > 0) {
                summaryParts.push(ratingFilter.selectedOptions[0].textContent.trim());
            }
            if (sort !== "added-desc") {
                summaryParts.push(`Sorted: ${sortControl.selectedOptions[0].textContent.trim()}`);
            }
            summary.textContent = summaryParts.join(" · ");
            reset.hidden = !hasActiveCriteria;
            if (filterEmpty) {
                filterEmpty.hidden = !(cards.length > 0 && visibleTotal === 0 && hasFilterCriteria);
            }
        }

        [typeFilter, statusFilter, ratingFilter, sortControl].forEach(function (control) {
            control.addEventListener("change", applyFilters);
        });
        searchInput.addEventListener("input", applyFilters);
        if (reset) {
            reset.addEventListener("click", function () {
                searchInput.value = "";
                typeFilter.value = "all";
                statusFilter.value = "all";
                ratingFilter.value = "all";
                sortControl.value = "added-desc";
                applyFilters();
            });
        }
        applyFilters();
    }

    function focusableIn(modal) {
        return Array.from(modal.querySelectorAll(
            "button:not([disabled]):not([hidden]), select:not([disabled]):not([hidden]), input:not([type=\"hidden\"]):not([disabled]):not([hidden]), textarea:not([disabled]):not([hidden]), [href]:not([hidden]), [contenteditable=\"true\"]:not([hidden]), [tabindex]:not([tabindex=\"-1\"]):not([hidden])"
        )).filter(function (element) {
            return element.getClientRects().length > 0 && element.getAttribute("aria-hidden") !== "true";
        });
    }

    function isolatePageForModal(modal) {
        modalBackgroundState = new Map();
        Array.from(document.body.children).forEach(function (region) {
            if (region === modal || region.contains(modal)) {
                return;
            }
            modalBackgroundState.set(region, {
                inert: region.inert,
                ariaHidden: region.getAttribute("aria-hidden"),
            });
            region.inert = true;
            region.setAttribute("aria-hidden", "true");
        });
    }

    function restorePageAfterModal() {
        modalBackgroundState.forEach(function (state, region) {
            region.inert = state.inert;
            if (state.ariaHidden === null) {
                region.removeAttribute("aria-hidden");
            } else {
                region.setAttribute("aria-hidden", state.ariaHidden);
            }
        });
        modalBackgroundState.clear();
    }

    function lockPageScroll() {
        if (modalScrollState) {
            return;
        }
        const body = document.body;
        const root = document.documentElement;
        const scrollY = window.scrollY || root.scrollTop || 0;
        const scrollbarWidth = Math.max(0, window.innerWidth - root.clientWidth);
        const currentPadding = Number.parseFloat(window.getComputedStyle(body).paddingRight) || 0;
        modalScrollState = {
            scrollY: scrollY,
            bodyStyle: body.getAttribute("style"),
            rootStyle: root.getAttribute("style"),
        };
        root.style.overflow = "hidden";
        body.style.position = "fixed";
        body.style.top = `-${scrollY}px`;
        body.style.left = "0";
        body.style.right = "0";
        body.style.width = "100%";
        body.style.overflow = "hidden";
        if (scrollbarWidth > 0) {
            body.style.paddingRight = `${currentPadding + scrollbarWidth}px`;
        }
    }

    function unlockPageScroll() {
        if (!modalScrollState) {
            return;
        }
        const state = modalScrollState;
        modalScrollState = null;
        if (state.bodyStyle === null) {
            document.body.removeAttribute("style");
        } else {
            document.body.setAttribute("style", state.bodyStyle);
        }
        if (state.rootStyle === null) {
            document.documentElement.removeAttribute("style");
        } else {
            document.documentElement.setAttribute("style", state.rootStyle);
        }
        window.scrollTo(0, state.scrollY);
    }

    function setupModal(modal, closeButton, initialFocus) {
        if (!modal || !closeButton) {
            return { open: function () {}, close: function () {} };
        }
        let lastFocusedElement = null;
        const focusOptions = { preventScroll: true };
        function close() {
            if (!modal.classList.contains("active")) {
                return;
            }
            const returnFocus = lastFocusedElement;
            modal.classList.remove("active");
            modal.setAttribute("aria-hidden", "true");
            document.removeEventListener("focusin", keepFocusInside, true);
            if (activeModalElement === modal) {
                activeModalElement = null;
                restorePageAfterModal();
                unlockPageScroll();
            }
            if (returnFocus && returnFocus.isConnected) {
                returnFocus.focus(focusOptions);
            }
        }
        function open(trigger) {
            if (activeModalElement && activeModalElement !== modal) {
                return;
            }
            lastFocusedElement = trigger;
            activeModalElement = modal;
            isolatePageForModal(modal);
            lockPageScroll();
            modal.classList.add("active");
            modal.setAttribute("aria-hidden", "false");
            document.addEventListener("focusin", keepFocusInside, true);
            (initialFocus || closeButton).focus(focusOptions);
        }
        function keepFocusInside(event) {
            if (activeModalElement === modal && !modal.contains(event.target)) {
                (initialFocus || closeButton).focus(focusOptions);
            }
        }
        closeButton.addEventListener("click", close);
        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                close();
            }
        });
        modal.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                event.preventDefault();
                close();
                return;
            }
            if (event.key !== "Tab") {
                return;
            }
            const focusable = focusableIn(modal);
            if (!focusable.length) {
                return;
            }
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            const activeIndex = focusable.indexOf(document.activeElement);
            if (!focusable.length) {
                event.preventDefault();
                modal.focus(focusOptions);
            } else if (event.shiftKey && activeIndex <= 0) {
                event.preventDefault();
                last.focus(focusOptions);
            } else if (!event.shiftKey && (activeIndex === -1 || activeIndex === focusable.length - 1)) {
                event.preventDefault();
                first.focus(focusOptions);
            }
        });
        return { open: open, close: close };
    }

    function setupEditModal() {
        const modal = document.getElementById("edit-modal");
        if (!modal) {
            return;
        }
        const status = document.getElementById("modal-status");
        const rating = document.getElementById("modal-rating");
        const title = document.getElementById("edit-modal-title-text");
        const controller = setupModal(modal, document.getElementById("modal-close"), status);
        document.querySelectorAll(".card-edit-js").forEach(function (button) {
            button.addEventListener("click", function () {
                document.getElementById("edit-form").action = `/edit/${button.dataset.id}`;
                status.value = button.dataset.status;
                rating.value = button.dataset.rating;
                document.getElementById("modal-rating-val").textContent = button.dataset.rating;
                title.textContent = `Edit ${button.dataset.title}`;
                controller.open(button);
            });
        });
    }

    function setupDetailModal() {
        const modal = document.getElementById("detail-modal");
        if (!modal) {
            return;
        }
        const title = document.getElementById("detail-modal-title");
        const poster = document.getElementById("detail-poster");
        const controller = setupModal(modal, document.getElementById("detail-close"), null);
        document.querySelectorAll("[data-detail-trigger]").forEach(function (button) {
            button.addEventListener("click", function () {
                title.textContent = button.dataset.detailTitle;
                document.getElementById("detail-type").textContent = button.dataset.detailType;
                document.getElementById("detail-status").textContent = button.dataset.detailStatus;
                document.getElementById("detail-rating").textContent = `${button.dataset.detailRating}/10 · ${button.dataset.detailRatingContext}`;
                document.getElementById("detail-release").textContent = button.dataset.detailRelease;
                document.getElementById("detail-added").textContent = button.dataset.detailAdded;
                document.getElementById("detail-source").textContent = button.dataset.detailSource;
                document.getElementById("detail-metadata-state").textContent = button.dataset.detailMetadataState;
                document.getElementById("detail-synopsis").textContent = button.dataset.detailSynopsis || "No synopsis supplied.";
                poster.replaceChildren();
                if (button.dataset.detailPoster) {
                    const image = document.createElement("img");
                    image.src = button.dataset.detailPoster;
                    image.alt = "";
                    image.addEventListener("error", function () { renderPosterPlaceholder(poster); });
                    poster.appendChild(image);
                } else {
                    renderPosterPlaceholder(poster);
                }
                controller.open(button);
            });
        });
    }

    function setupDeleteModal() {
        const modal = document.getElementById("delete-modal");
        const confirmForm = document.getElementById("delete-confirm-form");
        const title = document.getElementById("delete-modal-title");
        if (!modal || !confirmForm || !title) {
            return;
        }
        const controller = setupModal(modal, document.getElementById("delete-cancel"), document.getElementById("delete-cancel"));
        openDeleteConfirmation = function (form) {
            confirmForm.action = form.action;
            title.textContent = `Delete ${form.dataset.deleteTitle}?`;
            controller.open(form.querySelector("button[type=submit]"));
        };
    }

    function setupManagementMode() {
        const mainRegion = document.querySelector("main[data-management-mode]");
        const toggle = document.querySelector("[data-manage-toggle]");
        const workspace = document.querySelector("[data-management-workspace]");
        if (!mainRegion || !toggle || !workspace) {
            return;
        }

        function setMode(active, focusWorkspace) {
            mainRegion.dataset.managementMode = active ? "active" : "inactive";
            toggle.setAttribute("aria-expanded", String(active));
            toggle.textContent = active ? "Done" : "Manage";
            toggle.setAttribute("aria-label", active ? "Finish managing archive" : "Manage archive");
            if (active && focusWorkspace) {
                workspace.scrollIntoView({ block: "start" });
                const titleInput = workspace.querySelector("#title");
                if (titleInput) {
                    titleInput.focus({ preventScroll: true });
                }
            } else if (!active && focusWorkspace) {
                toggle.focus({ preventScroll: true });
            }
        }

        function handleManagementLink(event, toggleMode) {
            if (
                event.defaultPrevented || event.button !== 0 || event.metaKey ||
                event.ctrlKey || event.shiftKey || event.altKey
            ) {
                return;
            }
            event.preventDefault();
            const currentMode = mainRegion.dataset.managementMode === "active";
            setMode(toggleMode ? !currentMode : true, true);
        }

        toggle.addEventListener("click", function (event) {
            handleManagementLink(event, true);
        });
        document.querySelectorAll("[data-management-trigger]").forEach(function (link) {
            link.addEventListener("click", function (event) {
                handleManagementLink(event, false);
            });
        });
        toggle.setAttribute("aria-expanded", String(mainRegion.dataset.managementMode === "active"));
        toggle.textContent = mainRegion.dataset.managementMode === "active" ? "Done" : "Manage";
        if (window.location.hash === "#management-workspace" || window.location.hash === "#add-form") {
            setMode(true, false);
        }
    }

    function setupTitleSearch() {
        const input = document.getElementById("title");
        const feedback = document.getElementById("title-search-feedback");
        const results = document.getElementById("title-search-results");
        if (!input || !feedback || !results) {
            return;
        }
        let timer = null;
        let controller = null;
        let searchSequence = 0;
        input.addEventListener("input", function () {
            const requestSequence = ++searchSequence;
            window.clearTimeout(timer);
            if (controller) {
                controller.abort();
            }
            results.replaceChildren();
            results.hidden = true;
            const query = input.value.trim();
            if (query.length < 2) {
                feedback.hidden = true;
                return;
            }
            feedback.hidden = false;
            feedback.textContent = "Checking TMDB match...";
            timer = window.setTimeout(async function () {
                controller = new AbortController();
                try {
                    const response = await fetch(`/search?q=${encodeURIComponent(query)}`, { signal: controller.signal });
                    const payload = await response.json();
                    if (requestSequence !== searchSequence) {
                        return;
                    }
                    if (!response.ok || payload.error) {
                        throw new Error(payload.error || "Search unavailable.");
                    }
                    if (!payload.result) {
                        feedback.textContent = "No TMDB match found. You can save this title manually.";
                        return;
                    }
                    feedback.textContent = "TMDB match found. Review it or save manually.";
                    const suggestion = document.createElement("button");
                    suggestion.type = "button";
                    suggestion.className = "search-suggestion";
                    suggestion.textContent = `Use “${payload.result.full_title}”`;
                    suggestion.addEventListener("click", function () {
                        input.value = payload.result.full_title;
                        feedback.textContent = "TMDB match selected.";
                        results.hidden = true;
                    });
                    results.appendChild(suggestion);
                    results.hidden = false;
                } catch (error) {
                    if (requestSequence === searchSequence && error.name !== "AbortError") {
                        feedback.textContent = "TMDB search is unavailable. You can save this title manually.";
                    }
                }
            }, 260);
        });
    }

    setupReveal();
    setupPointerGlow();
    setupImageFallbacks();
    setupLibraryFilters();
    setupEditModal();
    setupDetailModal();
    setupDeleteModal();
    setupManagementMode();
    setupTitleSearch();
}());
