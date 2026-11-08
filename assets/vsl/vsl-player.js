/* vsl-player.js — LumiVelle /vsl page behaviour on the Vimeo player.

   Adapted from the H&W vsl-pitch.js (stage, pitch reveal, fit lines), with the
   VTurb player replaced by the official Vimeo player.js SDK:

     1. the order button opens when the viewer's PLAYBACK reaches the pitch
        second (data-vdelay on #video = 2834 = 47:14). Never wall-clock time,
        never a query-string shortcut, never as an error fallback: pausing
        stops progress toward it, and the button only appears from a
        timeupdate/seeked payload (or a resume position) read through the SDK.
     2. stage — real sound on (Vimeo getMuted/getVolume): headline shrinks,
        player grows and pins until the pitch (Escape steps out)
     3. reveal — body.is-revealed, announcement, "fit" scroll
     4. SDK/iframe failure — a visible status with a reload link, nothing else
     5. tracking params carried onto the checkout link without touching hid/affid */
(function () {
  "use strict";

  var video = document.getElementById("video");
  var status = document.getElementById("player-status");
  var offers = Array.prototype.slice.call(document.querySelectorAll(".esconder"));

  var UNLOCK_SECONDS = video ? Number(video.getAttribute("data-vdelay")) || 0 : 0;
  var VIDEO_ID = video ? video.getAttribute("data-video-id") || "" : "";
  var STORAGE_KEY = "lumivelle-vsl-unlock:" + VIDEO_ID + ":" + UNLOCK_SECONDS;
  var READY_TIMEOUT_MS = 20000;

  var lessMotion = function () {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  };

  /* [data-fit-line] text shrinks until it fits its box on one line, 11px
     floor; below that it wraps. */
  var shrinkToFit = function (text) {
    var box = text.parentNode;
    if (!box) return;
    text.style.fontSize = "";
    text.style.whiteSpace = "";
    var cs = window.getComputedStyle(box);
    var available = box.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
    if (!available || !text.scrollWidth || text.scrollWidth <= available) return;

    var base = parseFloat(window.getComputedStyle(text).fontSize) || 20;
    var size = Math.max(11, Math.floor((base * available) / text.scrollWidth));
    text.style.fontSize = size + "px";
    for (var pass = 0; text.scrollWidth > available && size > 11 && pass < 6; pass++) {
      size = Math.max(11, Math.floor((size * available) / text.scrollWidth));
      text.style.fontSize = size + "px";
    }
    text.style.whiteSpace = text.scrollWidth > available ? "normal" : "";
  };

  var fitLines = function () {
    Array.prototype.forEach.call(document.querySelectorAll("[data-fit-line]"), shrinkToFit);
  };

  /* ---- Checkout tracking -------------------------------------------------- */

  /* Only these fields travel, and only when the checkout link does not
     already carry them: hid and affid (and anything else) are never touched. */
  var TRACKING = /^(utm_(source|medium|campaign|term|content)|fbclid|gclid|ttclid|click_id|clickid|sub[1-5]|src|sck)$/;

  var carryTracking = function () {
    var incoming;
    try {
      incoming = new URLSearchParams(window.location.search);
    } catch (e) {
      return;
    }
    var extra = [];
    Array.prototype.forEach.call(document.querySelectorAll("a.buylink"), function (link) {
      var href = link.href || "";
      var query = href.indexOf("?") === -1 ? "" : href.slice(href.indexOf("?") + 1);
      var present = new URLSearchParams(query);
      extra = [];
      incoming.forEach(function (value, key) {
        if (!TRACKING.test(key) || present.has(key) || !value || value.length > 200) return;
        extra.push(encodeURIComponent(key) + "=" + encodeURIComponent(value));
      });
      if (extra.length) link.href = href + (query ? "&" : "?") + extra.join("&");
    });
  };

  /* ---- Session memory of an earned reveal ---------------------------------- */

  var readRevealed = function () {
    try {
      return window.sessionStorage.getItem(STORAGE_KEY) === "1";
    } catch (e) {
      return false;
    }
  };

  var saveRevealed = function () {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, "1");
    } catch (e) {
      /* storage denied: the reveal still happens, it just is not remembered */
    }
  };

  /* ---- Stage -------------------------------------------------------------- */

  var revealed = false;
  var stageActive = false;
  var stageDone = false;

  var measureSticky = function () {
    var pinned = document.querySelector(".vsl-video");
    var height = pinned && document.body.classList.contains("is-stripped") ? pinned.offsetHeight : 0;
    document.body.style.setProperty("--sticky-h", height + "px");
  };

  var enterStage = function () {
    if (stageActive || stageDone || revealed) return;
    stageActive = true;
    /* The stage never makes the player narrower than it is now. */
    if (video) video.style.setProperty("--vsl-rest-w", video.offsetWidth + "px");
    document.body.classList.add("is-stage", "is-stripped");
    window.setTimeout(measureSticky, 600); /* after the transition */
  };

  var exitStage = function () {
    if (!stageActive) return;
    stageActive = false;
    stageDone = true;
    document.body.classList.remove("is-stage");
  };

  /* Sound counts as on only when Vimeo says it is: not muted and volume > 0.
     If the player cannot be asked, the page stays out of the stage. */
  var checkSound = function (player) {
    Promise.all([player.getMuted(), player.getVolume()]).then(
      function (state) {
        if (state[0] === false && state[1] > 0) enterStage();
      },
      function () {}
    );
  };

  if (video && video.hasAttribute("data-stage")) {
    document.addEventListener("keydown", function (e) {
      if (stageActive && (e.key === "Escape" || e.key === "Esc")) exitStage();
    });
  }

  /* ---- Reveal ------------------------------------------------------------- */

  var scrollOnReveal = function (offer) {
    var mode = offer.getAttribute("data-reveal-scroll");
    if (mode !== "fit") return;
    var behavior = lessMotion() ? "auto" : "smooth";
    var wait = Number(offer.getAttribute("data-reveal-scroll-delay")) || 0;
    window.setTimeout(function () {
      var overflow = offer.getBoundingClientRect().bottom - window.innerHeight;
      if (overflow > 0) window.scrollBy({ top: overflow + 16, behavior: behavior });
    }, wait);
  };

  /* An endless pulse off screen is wasted paint. */
  var pauseWhenOffscreen = function (offer) {
    if (!window.IntersectionObserver) return;
    var target = offer.querySelector(".vsl-cta") || offer;
    new window.IntersectionObserver(function (entries) {
      document.body.classList.toggle("cta-offscreen", !entries[entries.length - 1].isIntersecting);
    }).observe(target);
  };

  var reveal = function (restored) {
    if (revealed) return;
    revealed = true;
    offers.forEach(function (offer) {
      offer.style.display = "block";
    });
    document.body.classList.add("is-revealed");
    exitStage();
    fitLines();
    offers.forEach(function (offer) {
      pauseWhenOffscreen(offer);
      /* screen readers hear that the button arrived */
      var notice = offer.querySelector("[data-offer-notice]");
      if (notice) notice.textContent = notice.getAttribute("data-offer-notice");
      if (!restored) scrollOnReveal(offer);
    });
    if (!restored) saveRevealed();
  };

  /* A position unlocks the offer only if it is a real, finite number of
     seconds at or past the pitch second. */
  var handlePosition = function (seconds) {
    if (typeof seconds !== "number" || !isFinite(seconds)) return;
    if (UNLOCK_SECONDS > 0 && seconds >= UNLOCK_SECONDS) reveal(false);
  };

  var secondsOf = function (payload) {
    return payload && typeof payload === "object" && !Array.isArray(payload) ? payload.seconds : undefined;
  };

  /* ---- Player status ------------------------------------------------------ */

  var showStatus = function (message) {
    if (!status) return;
    status.innerHTML = message + ' <a href="/vsl">Reload this page</a> to try again.';
    status.hidden = false;
  };

  var hideStatus = function () {
    if (status) status.hidden = true;
  };

  /* ---- Boot --------------------------------------------------------------- */

  var boot = function () {
    carryTracking();
    if (readRevealed()) reveal(true);

    var iframe = document.querySelector("#video iframe");
    if (!iframe) return showStatus("The video could not be found.");
    if (!window.Vimeo || typeof window.Vimeo.Player !== "function") {
      return showStatus("The video player could not load.");
    }

    var player;
    try {
      player = new window.Vimeo.Player(iframe);
    } catch (e) {
      return showStatus("The video player could not start.");
    }

    var ready = false;
    var timeout = window.setTimeout(function () {
      if (!ready) showStatus("The video player is taking too long to load.");
    }, READY_TIMEOUT_MS);

    player.on("timeupdate", function (data) {
      handlePosition(secondsOf(data));
    });
    player.on("seeked", function (data) {
      handlePosition(secondsOf(data));
    });
    player.on("play", function () {
      checkSound(player);
    });
    player.on("volumechange", function () {
      checkSound(player);
    });

    player.ready().then(
      function () {
        ready = true;
        window.clearTimeout(timeout);
        hideStatus();
        /* resume: the viewer may already be past the pitch */
        return player.getCurrentTime().then(handlePosition, function () {});
      },
      function () {
        window.clearTimeout(timeout);
        showStatus("The video player could not load.");
      }
    );
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  fitLines();
  var lastWidth = window.innerWidth;
  var resizeTimer = null;
  window.addEventListener("resize", function () {
    if (window.innerWidth === lastWidth) return; /* mobile URL bar show/hide */
    lastWidth = window.innerWidth;
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      fitLines();
      measureSticky();
    }, 150);
  });
})();
