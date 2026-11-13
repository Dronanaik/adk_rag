/**
 * Synchronizes the MkDocs Material GitHub repository version badge
 * (.md-source__fact--version) with the latest semantic version across
 * GitHub Tags (/tags) and GitHub Releases (/releases/latest), and refreshes
 * stale sessionStorage (__source) entries.
 */
(function () {
  var REPO = "Dronanaik/adk_rag";
  var FALLBACK_VERSION = "v2.4.0";

  function parseSemver(tag) {
    if (!tag || typeof tag !== "string") return [0, 0, 0];
    var m = tag.trim().replace(/^v/i, "").match(/^(\d+)\.(\d+)\.(\d+)/);
    if (!m) return [0, 0, 0];
    return [parseInt(m[1], 10), parseInt(m[2], 10), parseInt(m[3], 10)];
  }

  function compareSemver(a, b) {
    var pa = parseSemver(a);
    var pb = parseSemver(b);
    for (var i = 0; i < 3; i++) {
      if (pa[i] !== pb[i]) return pa[i] - pb[i];
    }
    return 0;
  }

  function pickHighestVersion(candidates) {
    var best = FALLBACK_VERSION;
    for (var i = 0; i < candidates.length; i++) {
      var c = candidates[i];
      if (c && compareSemver(c, best) > 0) {
        best = c;
      }
    }
    return best;
  }

  function updateSessionStorageVersion(version) {
    try {
      for (var i = 0; i < sessionStorage.length; i++) {
        var key = sessionStorage.key(i);
        if (key && key.indexOf("__source") !== -1) {
          var raw = sessionStorage.getItem(key);
          if (raw) {
            var parsed = JSON.parse(raw);
            if (parsed && typeof parsed === "object") {
              parsed.version = version;
              sessionStorage.setItem(key, JSON.stringify(parsed));
            }
          }
        }
      }
    } catch (e) {
      void e;
    }
  }

  function applyVersionToDom(version) {
    var versionNodes = document.querySelectorAll(".md-source__fact--version");
    if (versionNodes.length > 0) {
      versionNodes.forEach(function (node) {
        if (node.textContent !== version) {
          node.textContent = version;
        }
      });
      return;
    }

    var factsLists = document.querySelectorAll(".md-source__facts");
    factsLists.forEach(function (ul) {
      if (!ul.querySelector(".md-source__fact--version")) {
        var li = document.createElement("li");
        li.className = "md-source__fact md-source__fact--version";
        li.textContent = version;
        ul.insertBefore(li, ul.firstChild);
      }
    });
  }

  async function resolveLatestVersion() {
    var candidates = [FALLBACK_VERSION];
    try {
      var responses = await Promise.allSettled([
        fetch("https://api.github.com/repos/" + REPO + "/tags?per_page=15", {
          cache: "no-store",
        }),
        fetch("https://api.github.com/repos/" + REPO + "/releases/latest", {
          cache: "no-store",
        }),
      ]);

      if (responses[0].status === "fulfilled" && responses[0].value.ok) {
        var tags = await responses[0].value.json();
        if (Array.isArray(tags)) {
          tags.forEach(function (t) {
            if (t && t.name) candidates.push(t.name);
          });
        }
      }

      if (responses[1].status === "fulfilled" && responses[1].value.ok) {
        var rel = await responses[1].value.json();
        if (rel && rel.tag_name) {
          candidates.push(rel.tag_name);
        }
      }
    } catch (e) {
      void e;
    }

    var latest = pickHighestVersion(candidates);
    updateSessionStorageVersion(latest);
    applyVersionToDom(latest);

    // Observe the repository widget in case MkDocs Material renders facts asynchronously after load
    var repos = document.querySelectorAll(".md-source__repository");
    repos.forEach(function (repoEl) {
      var observer = new MutationObserver(function () {
        applyVersionToDom(latest);
      });
      observer.observe(repoEl, { childList: true, subtree: true });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", resolveLatestVersion);
  } else {
    resolveLatestVersion();
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(function () {
      resolveLatestVersion();
    });
  }
})();
