// Build project cards and star counts from projects.json
(function () {
  function formatStars(count) {
    if (count >= 1000) {
      return (count / 1000).toFixed(1).replace(/\.0$/, "") + "k";
    }
    return String(count);
  }

  function fetchStarCountsAndSort(grid, cards) {
    var pending = cards.length;
    var starData = {}; // repo → count

    cards.forEach(function (card) {
      var repo = card.getAttribute("data-repo");
      if (!repo) {
        pending--;
        return;
      }

      fetch("https://api.github.com/repos/meta-pytorch/" + repo)
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (data) {
          if (data && typeof data.stargazers_count === "number") {
            starData[repo] = data.stargazers_count;
            var h3 = card.querySelector("h3");
            if (h3) {
              var badge = document.createElement("span");
              badge.className = "star-count";
              badge.innerHTML =
                '<i class="fa-solid fa-star"></i> ' + formatStars(data.stargazers_count);
              h3.appendChild(badge);
            }
          }
        })
        .catch(function () {})
        .finally(function () {
          pending--;
          if (pending <= 0) {
            sortCardsByStars(grid, starData);
          }
        });
    });

    // If no cards had repos, nothing to sort
    if (cards.length === 0) return;
  }

  function sortCardsByStars(grid, starData) {
    var cards = Array.prototype.slice.call(grid.querySelectorAll(".project-card"));
    cards.sort(function (a, b) {
      var starsA = starData[a.getAttribute("data-repo")] || 0;
      var starsB = starData[b.getAttribute("data-repo")] || 0;
      return starsB - starsA;
    });
    cards.forEach(function (card) {
      grid.appendChild(card);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var grid = document.getElementById("project-grid");
    if (!grid) return;

    var url = window.__projectsURL || "_static/projects.json";
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (projects) {
        projects.forEach(function (p) {
          var card = document.createElement("div");
          card.className = "project-card";
          card.setAttribute("data-repo", p.repo);

          // Category tag
          var tag = document.createElement("span");
          tag.className = "category-tag";
          tag.textContent = p.category;
          card.appendChild(tag);

          // Title
          var h3 = document.createElement("h3");
          h3.textContent = p.title;
          card.appendChild(h3);

          // Description
          var desc = document.createElement("p");
          desc.textContent = p.description;
          card.appendChild(desc);

          // Links
          var links = document.createElement("div");
          links.className = "project-links";
          links.innerHTML =
            '<a href="' + p.github + '" title="GitHub" target="_blank" rel="noopener">' +
            '<i class="fa-brands fa-github"></i> GitHub</a>' +
            '<a href="' + p.docs + '" title="Docs" target="_blank" rel="noopener">' +
            '<i class="fa-solid fa-book"></i> Docs</a>';
          card.appendChild(links);

          grid.appendChild(card);
        });

        // Fetch star counts, then sort by stars descending
        fetchStarCountsAndSort(grid, grid.querySelectorAll(".project-card[data-repo]"));
      })
      .catch(function (err) {
        console.warn("[project-cards] Could not load projects.json:", err);
      });
  });
})();
