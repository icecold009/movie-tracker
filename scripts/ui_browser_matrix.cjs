"use strict";

const assert = require("node:assert/strict");
const { execFileSync, spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { chromium } = require("playwright");

const repo = path.resolve(__dirname, "..");
const port = Number(process.env.UI_FIXTURE_PORT || 5069);
const origin = "http://127.0.0.1:" + port;
const branch = execFileSync(
  "git",
  ["-c", "safe.directory=*", "rev-parse", "--abbrev-ref", "HEAD"],
  { cwd: repo },
).toString().trim();
const commit = execFileSync(
  "git",
  ["-c", "safe.directory=*", "rev-parse", "HEAD"],
  { cwd: repo },
).toString().trim();
const worktree = execFileSync(
  "git",
  ["-c", "safe.directory=*", "status", "--porcelain"],
  { cwd: repo },
).toString().trim();
assert.equal(worktree, "", "Capture baselines only from a clean committed worktree.");

const safeBranch = branch.replace(/[^a-z0-9-]+/gi, "-");
const output = path.resolve(
  process.env.UI_EVIDENCE_DIR ||
    path.join(os.tmpdir(), "movie-tracker-ui-evidence", safeBranch + "-" + commit.slice(0, 8)),
);
const viewports = [
  { name: "390x844", width: 390, height: 844 },
  { name: "768x1024", width: 768, height: 1024 },
  { name: "1024x900", width: 1024, height: 900 },
  { name: "1440x1000", width: 1440, height: 1000 },
];
const report = {
  capturedAt: new Date().toISOString(),
  repository: "movie-tracker",
  branch,
  commit,
  origin,
  fixtureOnly: true,
  pythonVersion: null,
  nodeVersion: process.version,
  browserVersion: null,
  viewports: [],
  states: [],
  accessibility: [],
  interactions: [],
  screenshots: [],
  requests: [],
  externalRequests: [],
  postPaths: [],
  consoleErrors: [],
  expectedServiceErrors: [],
  pageErrors: [],
};
let fixtureServer;
let browser;

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function startFixtureServer() {
  const python = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
  const serverScript = path.join(repo, "scripts", "ui_fixture_server.py");
  fixtureServer = spawn(
    python,
    [serverScript, "--host", "127.0.0.1", "--port", String(port)],
    {
      cwd: repo,
      env: { ...process.env },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );

  let startupOutput = "";
  fixtureServer.stdout.on("data", (chunk) => {
    startupOutput += chunk.toString();
    startupOutput = startupOutput.slice(-3000);
  });
  fixtureServer.stderr.on("data", (chunk) => {
    startupOutput += chunk.toString();
    startupOutput = startupOutput.slice(-3000);
  });

  let exitInfo = null;
  fixtureServer.once("exit", (code, signal) => {
    exitInfo = { code, signal };
  });

  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (exitInfo) {
      throw new Error(
        "Local fixture server exited before readiness: " +
          JSON.stringify(exitInfo) +
          " " +
          startupOutput,
      );
    }
    try {
      const response = await fetch(origin + "/_ui_fixture/health");
      if (response.ok && response.headers.get("x-movie-tracker-ui-fixture") === "synthetic") {
        const body = await response.json();
        assert.equal(body.fixture_only, true);
        report.pythonVersion = body.python_version;
        return;
      }
    } catch {
      // Wait for the child process to bind its requested loopback port.
    }
    await delay(200);
  }
  throw new Error(
    "The loopback fixture server did not become ready on " + origin + ". " + startupOutput,
  );
}

async function stopFixtureServer() {
  if (!fixtureServer || fixtureServer.exitCode !== null) {
    return;
  }
  fixtureServer.kill();
  await Promise.race([
    new Promise((resolve) => fixtureServer.once("close", resolve)),
    delay(3000),
  ]);
}

function observe(page, label) {
  page.on("pageerror", (error) => {
    report.pageErrors.push({ label, message: error.message });
  });
  page.on("console", (message) => {
    if (message.type() !== "error") {
      return;
    }
    const item = { label, message: message.text() };
    if (/503|service unavailable/i.test(item.message) && /error|failure/i.test(label)) {
      report.expectedServiceErrors.push(item);
    } else {
      report.consoleErrors.push(item);
    }
  });
  page.on("request", (request) => {
    const url = request.url();
    report.requests.push({ label, method: request.method(), url });
    if (request.method() === "POST") {
      report.postPaths.push(new URL(url).pathname);
    }
  });
}

async function newPage(contextOptions, label) {
  const context = await browser.newContext(contextOptions);
  await context.route("**/*", async (route) => {
    const requestUrl = route.request().url();
    if (new URL(requestUrl).origin === origin) {
      await route.continue();
    } else {
      report.externalRequests.push({ label, url: requestUrl });
      await route.abort();
    }
  });
  const page = await context.newPage();
  observe(page, label);
  return { context, page };
}

async function screenshot(page, label) {
  const filename = label.replace(/[^a-z0-9-]+/gi, "-").toLowerCase() + ".png";
  const filepath = path.join(output, filename);
  await page.screenshot({
    path: filepath,
    fullPage: true,
    animations: "disabled",
  });
  report.screenshots.push(filepath);
  return filepath;
}

async function auditPage(page, label, viewport) {
  const audit = await page.evaluate(() => {
    function visible(element) {
      const style = getComputedStyle(element);
      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        Number.parseFloat(style.opacity || "1") > 0 &&
        element.getClientRects().length > 0 &&
        !element.closest("[hidden], [inert], [aria-hidden='true']")
      );
    }

    function accessibleName(element) {
      const labelledBy = (element.getAttribute("aria-labelledby") || "")
        .split(/\s+/)
        .filter(Boolean)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map((node) => node.innerText || node.textContent || "")
        .join(" ")
        .trim();
      const labels = element.labels
        ? Array.from(element.labels).map((node) => node.innerText || node.textContent || "").join(" ").trim()
        : "";
      return (
        element.getAttribute("aria-label") ||
        labelledBy ||
        labels ||
        element.innerText?.trim() ||
        element.getAttribute("title") ||
        element.getAttribute("alt") ||
        element.getAttribute("value") ||
        ""
      ).trim();
    }

    const namedControls = Array.from(
      document.querySelectorAll(
        "a[href], button, input:not([type='hidden']), select, textarea, summary, [role='button']",
      ),
    )
      .filter(visible)
      .filter((element) => !accessibleName(element))
      .map((element) => element.outerHTML.slice(0, 180));

    const missingImageAlternatives = Array.from(document.querySelectorAll("img"))
      .filter((image) => !image.hasAttribute("alt"))
      .map((image) => image.outerHTML.slice(0, 180));

    const brokenIdRefs = [];
    for (const element of document.querySelectorAll(
      "[aria-labelledby], [aria-describedby]",
    )) {
      for (const attribute of ["aria-labelledby", "aria-describedby"]) {
        const value = element.getAttribute(attribute);
        if (!value) {
          continue;
        }
        for (const id of value.split(/\s+/).filter(Boolean)) {
          if (!document.getElementById(id)) {
            brokenIdRefs.push({ attribute, id, tag: element.tagName });
          }
        }
      }
    }

    const smallTargets = Array.from(
      document.querySelectorAll(
        "a[href], button, input:not([type='hidden']), select, textarea, summary",
      ),
    )
      .filter(visible)
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          name: accessibleName(element),
          tag: element.tagName,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      })
      .filter((target) => target.width < 44 || target.height < 44);

    const viewportWidth = document.documentElement.clientWidth;
    const documentWidth = document.documentElement.scrollWidth;
    const mains = document.querySelectorAll("main").length;
    const overlays = Array.from(
      document.querySelectorAll(
        "vite-error-overlay, #webpack-dev-server-client-overlay, [data-nextjs-dialog]",
      ),
    ).length;
    return {
      title: document.title,
      mains,
      viewportWidth,
      documentWidth,
      horizontalOverflow: documentWidth > viewportWidth,
      namedControls,
      missingImageAlternatives,
      brokenIdRefs,
      smallTargets,
      overlays,
    };
  });

  assert.equal(audit.mains, 1, label + " has one main landmark.");
  assert.equal(audit.namedControls.length, 0, label + " has named visible controls: " + JSON.stringify(audit.namedControls));
  assert.equal(audit.missingImageAlternatives.length, 0, label + " gives every image an alt attribute.");
  assert.equal(audit.brokenIdRefs.length, 0, label + " has valid ARIA ID references.");
  assert.equal(audit.overlays, 0, label + " has no framework/error overlay.");
  assert.equal(audit.horizontalOverflow, false, label + " has no horizontal overflow: " + JSON.stringify(audit));
  if (viewport.width <= 768) {
    assert.equal(
      audit.smallTargets.length,
      0,
      label + " has >=44px visible touch targets: " + JSON.stringify(audit.smallTargets),
    );
  }

  report.accessibility.push({ label, viewport: viewport.name, result: audit });
  return audit;
}

async function navigate(page, pathname, label, expectedStatus, viewport) {
  const response = await page.goto(origin + pathname, { waitUntil: "networkidle" });
  assert.ok(response, label + " receives a document response.");
  assert.equal(response.status(), expectedStatus, label + " response status.");
  assert.equal(
    response.headers()["x-movie-tracker-ui-fixture"],
    "synthetic",
    label + " is served by the local fixture harness.",
  );
  const audit = await auditPage(page, label, viewport);
  return { response, audit };
}

async function captureState(name, pathname, expectedStatus, assertion) {
  const viewport = { name: "390x844", width: 390, height: 844 };
  const { context, page } = await newPage(
    { viewport: { width: viewport.width, height: viewport.height } },
    name,
  );
  try {
    const result = await navigate(page, pathname, name, expectedStatus, viewport);
    if (assertion) {
      await assertion(page, result.response);
    }
    await screenshot(page, name + "-" + viewport.name);
    report.states.push({
      name,
      path: pathname,
      status: result.response.status(),
      viewport: viewport.name,
      screenshot: report.screenshots[report.screenshots.length - 1],
    });
  } finally {
    await context.close();
  }
}

async function verifyKeyboardAndDialog() {
  const viewport = { name: "1440x1000", width: 1440, height: 1000 };
  const { context, page } = await newPage(
    { viewport: { width: viewport.width, height: viewport.height } },
    "keyboard-and-dialog",
  );
  try {
    await navigate(page, "/?fixture=admin", "keyboard-and-dialog", 200, viewport);

    const expectedFocusOrder = await page.evaluate(() => {
      function visible(element) {
        const style = getComputedStyle(element);
        return (
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          element.getClientRects().length > 0 &&
          !element.closest("[hidden], [inert], [aria-hidden='true']")
        );
      }
      function key(element) {
        return [
          element.tagName.toLowerCase(),
          element.id || "",
          (element.getAttribute("aria-label") || element.innerText || element.textContent || "")
            .trim()
            .replace(/\s+/g, " "),
        ].join("|");
      }
      return Array.from(
        document.querySelectorAll(
          "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex='-1'])",
        ),
      )
        .filter((element) => visible(element) && element.tabIndex >= 0)
        .map(key)
        .slice(0, 6);
    });

    const actualFocusOrder = [];
    for (let index = 0; index < expectedFocusOrder.length; index += 1) {
      await page.keyboard.press("Tab");
      const active = await page.evaluate(() => {
        const element = document.activeElement;
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return {
          key: [
            element.tagName.toLowerCase(),
            element.id || "",
            (element.getAttribute("aria-label") || element.innerText || element.textContent || "")
              .trim()
              .replace(/\s+/g, " "),
          ].join("|"),
          focusVisible: element.matches(":focus-visible"),
          visibleRing:
            (style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) > 0) ||
            style.boxShadow !== "none",
          inViewport:
            rect.bottom >= 0 &&
            rect.top <= innerHeight &&
            rect.right >= 0 &&
            rect.left <= innerWidth,
        };
      });
      actualFocusOrder.push(active.key);
      if (index === 0) {
        assert.equal(active.focusVisible, true, "Keyboard focus uses :focus-visible.");
        assert.equal(active.visibleRing, true, "Keyboard focus has a visible outline or shadow.");
        assert.equal(active.inViewport, true, "Keyboard focus remains in the viewport.");
      }
    }
    assert.deepEqual(actualFocusOrder, expectedFocusOrder, "Tab follows visible DOM order.");
    report.interactions.push({
      name: "keyboard-order-and-visible-focus",
      sequence: actualFocusOrder,
    });

    const trigger = page.locator("[data-detail-trigger]").first();
    await trigger.focus();
    await page.keyboard.press("Enter");
    const dialog = page.locator("#detail-modal");
    assert.equal(await dialog.getAttribute("aria-hidden"), "false");
    assert.equal(await dialog.getAttribute("aria-modal"), "true");
    const backgroundState = await page.locator("main").evaluate((main) => ({
      inert: main.inert,
      ariaHidden: main.getAttribute("aria-hidden"),
    }));
    assert.deepEqual(backgroundState, { inert: true, ariaHidden: "true" });

    await page.keyboard.press("Shift+Tab");
    assert.equal(
      await dialog.evaluate((element) => element.contains(document.activeElement)),
      true,
      "Reverse Tab remains inside the dialog.",
    );
    await page.keyboard.press("Tab");
    assert.equal(
      await dialog.evaluate((element) => element.contains(document.activeElement)),
      true,
      "Forward Tab remains inside the dialog.",
    );
    await page.keyboard.press("Escape");
    assert.equal(await dialog.getAttribute("aria-hidden"), "true");
    assert.equal(
      await trigger.evaluate((element) => document.activeElement === element),
      true,
      "Escape returns focus to the dialog trigger.",
    );
    const restoredBackground = await page.locator("main").evaluate((main) => ({
      inert: main.inert,
      ariaHidden: main.getAttribute("aria-hidden"),
    }));
    assert.deepEqual(restoredBackground, { inert: false, ariaHidden: null });
    await screenshot(page, "dialog-closed-desktop");
    report.interactions.push({
      name: "dialog-isolation-focus-trap-escape-return",
      passed: true,
    });
  } finally {
    await context.close();
  }
}

async function verifyLoadingSkeleton() {
  const viewport = { name: "390x844", width: 390, height: 844 };
  const { context, page } = await newPage(
    { viewport: { width: viewport.width, height: viewport.height } },
    "loading-skeleton",
  );
  try {
    await navigate(page, "/?fixture=loading-skeleton", "loading-skeleton", 200, viewport);
    await page.evaluate(() => {
      const link = document.querySelector("a[data-loading-link]");
      window.addEventListener(
        "click",
        (event) => {
          if (event.target.closest("a[data-loading-link]")) {
            event.preventDefault();
          }
        },
        { once: true },
      );
      link.click();
    });
    const state = await page.evaluate(() => ({
      skeletonVisible: !document.querySelector("[data-page-skeleton]").hidden,
      skeletonAriaHidden: document
        .querySelector("[data-page-skeleton]")
        .getAttribute("aria-hidden"),
      mainBusy: document.querySelector("main").getAttribute("aria-busy"),
    }));
    assert.deepEqual(state, {
      skeletonVisible: true,
      skeletonAriaHidden: "false",
      mainBusy: "true",
    });
    await screenshot(page, "loading-skeleton-mobile");
    report.states.push({ name: "loading-skeleton", viewport: viewport.name, passed: true });
  } finally {
    await context.close();
  }
}

async function verifyZeroSearch() {
  const viewport = { name: "390x844", width: 390, height: 844 };
  const { context, page } = await newPage(
    { viewport: { width: viewport.width, height: viewport.height } },
    "zero-search-results",
  );
  try {
    await navigate(page, "/?fixture=zero-search-results", "zero-search-results", 200, viewport);
    await page.locator("#library-search").fill("No matching fixture title");
    assert.equal(await page.locator("[data-filter-empty]").isVisible(), true);
    assert.equal(
      await page.locator("[data-entry-card]:visible").count(),
      0,
      "Zero-result search hides all cards.",
    );
    await screenshot(page, "zero-search-results-mobile");
    report.states.push({ name: "zero-search-results", viewport: viewport.name, passed: true });
  } finally {
    await context.close();
  }
}

async function verifyProviderRecovery() {
  const viewport = { name: "390x844", width: 390, height: 844 };
  const { context, page } = await newPage(
    { viewport: { width: viewport.width, height: viewport.height } },
    "tmdb-error-recovery",
  );
  try {
    await navigate(page, "/?fixture=admin-tmdb-error", "tmdb-error-recovery", 200, viewport);
    await page.getByRole("link", { name: "Manage archive" }).click();
    await page.locator("#title").fill("Synthetic provider failure");
    const button = page.getByRole("button", { name: "Search TMDB and add" });
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle" }),
      button.click(),
    ]);
    assert.equal(await page.locator(".add-recovery").getAttribute("role"), "alert");
    assert.match(await page.locator(".add-recovery").innerText(), /Synthetic TMDB outage/);
    assert.equal(await page.locator("#title").inputValue(), "Synthetic provider failure");
    await screenshot(page, "tmdb-error-recovery-mobile");
    report.states.push({ name: "tmdb-error-recovery", viewport: viewport.name, passed: true });
  } finally {
    await context.close();
  }
}

async function verifyManualFallbackAndNoJs() {
  const viewport = { name: "390x844", width: 390, height: 844 };
  const { context, page } = await newPage(
    { viewport: { width: viewport.width, height: viewport.height } },
    "manual-metadata-fallback",
  );
  try {
    await navigate(page, "/?fixture=manual-fallback", "manual-metadata-fallback", 200, viewport);
    await page.getByRole("link", { name: "Manage archive" }).click();
    assert.equal(await page.locator(".add-recovery").getAttribute("role"), "alert");
    assert.equal(await page.locator("#title").inputValue(), "Preserved fixture title");
    await screenshot(page, "manual-metadata-fallback-mobile");

    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle" }),
      page.getByRole("button", { name: "Save without metadata" }).click(),
    ]);
    assert.equal(
      await page.getByRole("heading", { name: "Preserved fixture title" }).count(),
      1,
      "Manual fallback saves through the in-memory fixture store.",
    );
    report.states.push({
      name: "manual-metadata-fallback",
      viewport: viewport.name,
      submitted: true,
    });
  } finally {
    await context.close();
  }

  const noJs = await newPage(
    {
      viewport: { width: viewport.width, height: viewport.height },
      javaScriptEnabled: false,
    },
    "no-js-form-submission",
  );
  try {
    await navigate(noJs.page, "/?fixture=admin-empty", "no-js-form-submission", 200, viewport);
    assert.equal(await noJs.page.locator("#add-form").isVisible(), true);
    assert.equal(await noJs.page.locator("#title").isVisible(), true);
    await noJs.page.locator("#title").fill("Fixture-only no-JS title");
    await Promise.all([
      noJs.page.waitForNavigation({ waitUntil: "networkidle" }),
      noJs.page.getByRole("button", { name: "Save without metadata" }).click(),
    ]);
    assert.equal(
      await noJs.page.getByRole("heading", { name: "Fixture-only no-JS title" }).count(),
      1,
      "The server-rendered no-JS manual form submits successfully.",
    );
    report.interactions.push({
      name: "no-js-server-rendered-manual-form",
      passed: true,
    });
  } finally {
    await noJs.context.close();
  }
}

async function verifyPointerAndReducedMotion() {
  const viewport = { name: "390x844", width: 390, height: 844 };
  const coarse = await newPage(
    {
      viewport: { width: viewport.width, height: viewport.height },
      isMobile: true,
      hasTouch: true,
      reducedMotion: "no-preference",
    },
    "coarse-pointer",
  );
  try {
    await navigate(coarse.page, "/?fixture=results", "coarse-pointer", 200, viewport);
    const mode = await coarse.page.evaluate(() => ({
      fine: matchMedia("(hover: hover) and (pointer: fine)").matches,
      coarse: matchMedia("(pointer: coarse)").matches,
    }));
    assert.deepEqual(mode, { fine: false, coarse: true });
    const card = coarse.page.locator("[data-pointer-glow]").first();
    await card.evaluate((element) => {
      element.dispatchEvent(
        new PointerEvent("pointermove", {
          bubbles: true,
          pointerType: "touch",
          clientX: 30,
          clientY: 30,
        }),
      );
    });
    assert.equal(await card.evaluate((element) => element.style.getPropertyValue("--pointer-x")), "");
    await screenshot(coarse.page, "coarse-pointer-mobile");
    report.interactions.push({ name: "coarse-pointer-no-hover-glow", mode, passed: true });
  } finally {
    await coarse.context.close();
  }

  const reduced = await newPage(
    {
      viewport: { width: viewport.width, height: viewport.height },
      reducedMotion: "reduce",
    },
    "reduced-motion",
  );
  try {
    await navigate(reduced.page, "/?fixture=results", "reduced-motion", 200, viewport);
    const state = await reduced.page.evaluate(() => ({
      requested: matchMedia("(prefers-reduced-motion: reduce)").matches,
      revealItems: Array.from(document.querySelectorAll("[data-reveal]")).map((element) => ({
        opacity: getComputedStyle(element).opacity,
        transform: getComputedStyle(element).transform,
      })),
      transition: getComputedStyle(document.querySelector(".card")).transitionDuration,
      skeletonAnimation: getComputedStyle(document.querySelector(".skeleton-block")).animationName,
    }));
    assert.equal(state.requested, true);
    assert.ok(state.revealItems.length > 0);
    assert.ok(
      state.revealItems.every((item) => item.opacity === "1" && item.transform === "none"),
      "Reduced-motion reveals are visible immediately.",
    );
    assert.equal(state.transition, "0s");
    assert.equal(state.skeletonAnimation, "none");
    await screenshot(reduced.page, "reduced-motion-mobile");
    report.interactions.push({ name: "reduced-motion", passed: true, ...state });
  } finally {
    await reduced.context.close();
  }
}

async function run() {
  fs.mkdirSync(output, { recursive: true });
  await startFixtureServer();
  browser = await chromium.launch({ headless: true });
  report.browserVersion = browser.version();

  for (const viewport of viewports) {
    for (const route of [
      { label: "library-results", path: "/?fixture=results" },
      {
        label: "recommendation-results",
        path: "/recommendations?fixture=recommendation-results",
      },
      { label: "login", path: "/login" },
    ]) {
      const { context, page } = await newPage(
        { viewport: { width: viewport.width, height: viewport.height } },
        route.label + "-" + viewport.name,
      );
      try {
        const result = await navigate(page, route.path, route.label + "-" + viewport.name, 200, viewport);
        if (route.label === "library-results") {
          assert.equal(await page.locator("[data-entry-card]").count(), 3);
        } else if (route.label === "recommendation-results") {
          assert.equal(await page.getByRole("heading", { name: "New Mystery" }).count(), 1);
        } else {
          assert.equal(await page.getByRole("heading", { name: "Welcome back." }).count(), 1);
          const toggle = page.locator("[data-password-toggle]");
          assert.equal(await toggle.getAttribute("aria-label"), "Show password");
        }
        if (route.label === "login") {
          assert.ok(
            result.audit.documentWidth <= viewport.width,
            "Login fits without horizontal overflow at " + viewport.name,
          );
          assert.ok(
            result.audit.smallTargets.length === 0,
            "Login touch targets meet 44px at " + viewport.name,
          );
        }
        await screenshot(page, route.label + "-" + viewport.name);
        report.viewports.push({
          route: route.label,
          name: viewport.name,
          ...result.audit,
        });
      } finally {
        await context.close();
      }
    }
  }

  await captureState("empty-library", "/?fixture=empty-library", 200, async (page) => {
    assert.equal(await page.getByRole("heading", { name: "No titles yet." }).count(), 1);
  });
  await captureState("database-error", "/?fixture=database-error", 503, async (page) => {
    assert.equal(await page.getByRole("alert").count(), 1);
  });
  await captureState("recommendation-empty", "/recommendations?fixture=recommendation-empty", 200, async (page) => {
    assert.match(await page.locator(".state-kicker").innerText(), /No results to show/i);
    assert.equal(await page.locator(".recommendation-card").count(), 0);
  });
  await captureState(
    "recommendation-provider-error",
    "/recommendations?fixture=recommendation-provider-error",
    503,
    async (page) => {
      assert.equal(await page.getByRole("alert").count(), 1);
      assert.equal(await page.getByRole("link", { name: "Retry recommendations" }).count(), 1);
    },
  );
  await captureState(
    "recommendation-database-error",
    "/recommendations?fixture=recommendation-database-error",
    503,
    async (page) => {
      assert.equal(await page.getByRole("alert").count(), 1);
      assert.equal(await page.getByRole("link", { name: "Retry recommendations" }).count(), 1);
    },
  );
  await captureState("stale-metadata", "/?fixture=stale-metadata", 200, async (page) => {
    assert.equal(
      await page.locator('[data-detail-metadata-state="Stale"]').count(),
      1,
    );
  });
  await captureState("undo-recovery", "/?fixture=undo-recovery", 200, async (page) => {
    assert.equal(await page.getByRole("button", { name: "Undo delete" }).count(), 1);
  });
  await captureState("authenticated-admin", "/?fixture=admin", 200, async (page) => {
    assert.equal(await page.locator('main[data-management-mode="inactive"]').count(), 1);
    assert.equal(await page.getByRole("link", { name: "Manage archive" }).count(), 1);
    await page.getByRole("link", { name: "Manage archive" }).click();
    assert.equal(await page.locator('main[data-management-mode="active"]').count(), 1);
    assert.equal(await page.getByRole("link", { name: "Finish managing archive" }).count(), 1);
    assert.equal(await page.locator("#title").isVisible(), true);
    await page.locator("#manage-toggle").click();
    assert.equal(await page.locator('main[data-management-mode="inactive"]').count(), 1);
    assert.equal(await page.getByRole("link", { name: "Manage archive" }).count(), 1);
  });

  await verifyZeroSearch();
  await verifyLoadingSkeleton();
  await verifyProviderRecovery();
  await verifyManualFallbackAndNoJs();
  await verifyKeyboardAndDialog();
  await verifyPointerAndReducedMotion();

  assert.equal(report.externalRequests.length, 0, "No requests left the local fixture origin.");
  assert.equal(report.consoleErrors.length, 0, "No unexplained browser console errors occurred.");
  assert.equal(report.pageErrors.length, 0, "No uncaught browser errors occurred.");
  assert.ok(
    report.requests.every((request) => new URL(request.url).origin === origin),
    "Every browser request stays on the fixture origin.",
  );
  assert.ok(
    report.postPaths.every((pathname) => pathname === "/add"),
    "The only browser POST actions are fixture-only add forms.",
  );

  report.evidenceScope = {
    pythonCi: "Reported separately by pytest/Ruff/compileall/pip-check runs.",
    browser: "Local synthetic Flask fixture server only; no provider/database network access.",
    accessibility: "Targeted DOM naming/ARIA checks and keyboard focus/dialog checks; not axe and not a screen-reader pass.",
    preview: "Not represented by this local browser report.",
    production: "Not represented by this local browser report.",
  };
  const reportPath = path.join(output, "verification-report.json");
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
  console.log(
    JSON.stringify(
      {
        branch,
        commit,
        browserVersion: report.browserVersion,
        pythonVersion: report.pythonVersion,
        viewports: report.viewports.length,
        states: report.states.map((state) => state.name),
        accessibilityChecks: report.accessibility.length,
        interactions: report.interactions.map((item) => item.name),
        postPaths: report.postPaths,
        screenshots: report.screenshots,
        report: reportPath,
      },
      null,
      2,
    ),
  );
}

run()
  .catch((error) => {
    console.error(error.stack || error);
    process.exitCode = 1;
  })
  .finally(async () => {
    if (browser) {
      await browser.close();
    }
    await stopFixtureServer();
  });
