// Meta-PyTorch cross-project search powered by Lunr.js
(function () {
  var index = null;
  var docs = {};       // id → flat doc object
  var projects = {};   // projectId → project object

  function init() {
    var url = window.__searchIndexURL || "_static/search-index.json";
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        projects = {};
        data.forEach(function (p) { projects[p.id] = p; });

        // Build a flat list: one entry per project + one per sub-page
        var entries = [];
        data.forEach(function (p) {
          entries.push({
            id: p.id,
            title: p.title,
            body: p.description + " " + p.keywords,
            category: p.category,
            url: p.url,
            project: p.id
          });
          (p.pages || []).forEach(function (pg, i) {
            var pid = p.id + "-page-" + i;
            entries.push({
              id: pid,
              title: pg.title,
              body: pg.content + " " + p.keywords,
              category: p.category,
              url: pg.url,
              project: p.id
            });
          });
        });

        entries.forEach(function (e) { docs[e.id] = e; });

        index = lunr(function () {
          this.ref("id");
          this.field("title", { boost: 10 });
          this.field("body");
          this.field("category", { boost: 2 });

          entries.forEach(function (e) { this.add(e); }, this);
        });
      })
      .catch(function (err) {
        console.warn("[search] Could not load search index:", err);
      });
  }

  function search(query) {
    if (!index || !query.trim()) return [];

    var results;
    try {
      // First try wildcard search for partial matches
      results = index.search(query.trim() + "*");
      // Also add exact matches (union, deduplicated)
      var exact = index.search(query.trim());
      var seen = {};
      results.forEach(function (r) { seen[r.ref] = true; });
      exact.forEach(function (r) {
        if (!seen[r.ref]) results.push(r);
      });
    } catch (e) {
      // If lunr chokes on special chars, try plain search
      try { results = index.search(query.trim()); } catch (e2) { results = []; }
    }

    // Deduplicate by URL and limit
    var seen_urls = {};
    var out = [];
    results.forEach(function (r) {
      var doc = docs[r.ref];
      if (!doc || seen_urls[doc.url]) return;
      seen_urls[doc.url] = true;
      out.push(doc);
    });
    return out.slice(0, 10);
  }

  // Render dropdown results
  function renderResults(container, results, query) {
    container.innerHTML = "";
    if (!results.length) {
      container.innerHTML =
        '<div class="search-no-results">No results found</div>' +
        '<a class="search-google-fallback" href="https://www.google.com/search?q=' +
        encodeURIComponent(query + " (site:github.com/meta-pytorch OR site:meta-pytorch.org)") +
        '" target="_blank" rel="noopener">' +
        '<i class="fa-brands fa-google"></i> Search Google instead</a>';
      return;
    }

    results.forEach(function (doc) {
      var proj = projects[doc.project] || {};
      var item = document.createElement("a");
      item.className = "search-result-item";
      item.href = doc.url;
      item.target = "_blank";
      item.rel = "noopener";
      var displayUrl = doc.url.replace(/^https?:\/\//, "");
      item.innerHTML =
        '<span class="search-result-icon"><i class="fa-solid fa-file-lines"></i></span>' +
        '<span class="search-result-body">' +
          '<span class="search-result-title">' + escapeHtml(doc.title) + '</span>' +
          '<span class="search-result-url">' + escapeHtml(displayUrl) + '</span>' +
        '</span>';
      container.appendChild(item);
    });

    // Always add Google fallback at the bottom
    var fallback = document.createElement("a");
    fallback.className = "search-google-fallback";
    fallback.href = "https://www.google.com/search?q=" +
      encodeURIComponent(query + " (site:github.com/meta-pytorch OR site:meta-pytorch.org)");
    fallback.target = "_blank";
    fallback.rel = "noopener";
    fallback.innerHTML = '<i class="fa-brands fa-google"></i> More results on Google';
    container.appendChild(fallback);
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // Wire up all search forms on the page
  function wireUpSearch() {
    document.querySelectorAll("form.bd-search").forEach(function (form) {
      var input = form.querySelector("input[type='search']");
      if (!input) return;

      // Create dropdown container
      var dropdown = document.createElement("div");
      dropdown.className = "search-dropdown";
      form.style.position = "relative";
      form.appendChild(dropdown);

      var debounceTimer = null;

      input.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        var q = input.value;
        if (!q.trim()) {
          dropdown.classList.remove("show");
          return;
        }
        debounceTimer = setTimeout(function () {
          var results = search(q);
          renderResults(dropdown, results, q);
          dropdown.classList.add("show");
        }, 150);
      });

      input.addEventListener("focus", function () {
        if (input.value.trim() && dropdown.children.length) {
          dropdown.classList.add("show");
        }
      });

      // Close dropdown on outside click
      document.addEventListener("click", function (e) {
        if (!form.contains(e.target)) {
          dropdown.classList.remove("show");
        }
      });

      // Close on Escape
      input.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
          dropdown.classList.remove("show");
          input.blur();
        }
      });

      // Prevent form submission (no need to navigate away)
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var q = input.value.trim();
        if (!q) return;
        var results = search(q);
        if (results.length) {
          window.open(results[0].url, "_blank", "noopener");
        } else {
          window.open(
            "https://www.google.com/search?q=" +
              encodeURIComponent(q + " (site:github.com/meta-pytorch OR site:meta-pytorch.org)"),
            "_blank", "noopener"
          );
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    init();
    wireUpSearch();
  });
})();
