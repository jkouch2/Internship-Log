const state = {
  all: [],
  search: "",
  relevantOnly: false,
};

const listingsEl = document.getElementById("listings");
const emptyStateEl = document.getElementById("empty-state");
const resultCountEl = document.getElementById("result-count");
const updatedLineEl = document.getElementById("updated-line");
const searchEl = document.getElementById("search");
const relevantToggleEl = document.getElementById("relevant-only");

function timeAgo(isoString) {
  if (!isoString) return "date unknown";
  const then = new Date(isoString);
  if (isNaN(then)) return "date unknown";
  const diffMs = Date.now() - then.getTime();
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days <= 0) return "posted today";
  if (days === 1) return "posted 1 day ago";
  if (days < 30) return `posted ${days} days ago`;
  const months = Math.floor(days / 30);
  return `posted ${months} mo ago`;
}

function formatUpdatedLine(isoString) {
  if (!isoString) return "Waiting on the first automated scrape to run.";
  const dt = new Date(isoString);
  const formatted = dt.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  return `Listings last refreshed: ${formatted}`;
}

function render() {
  const q = state.search.trim().toLowerCase();

  const filtered = state.all.filter((item) => {
    if (state.relevantOnly && item.tags.length === 0) return false;
    if (!q) return true;
    const haystack = `${item.company} ${item.title} ${item.location}`.toLowerCase();
    return haystack.includes(q);
  });

  resultCountEl.textContent = `${filtered.length} of ${state.all.length} internship postings`;

  listingsEl.innerHTML = "";
  emptyStateEl.hidden = filtered.length !== 0;

  for (const item of filtered) {
    const card = document.createElement("article");
    card.className = "listing-card" + (item.tags.length > 0 ? " is-relevant" : "");

    const title = document.createElement("h2");
    title.className = "listing-title";
    const link = document.createElement("a");
    link.href = item.url || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = item.title;
    title.appendChild(link);

    const freshness = document.createElement("span");
    freshness.className = "freshness";
    freshness.textContent = timeAgo(item.posted_at);

    const meta = document.createElement("p");
    meta.className = "listing-meta";
    const companySpan = document.createElement("span");
    companySpan.className = "company";
    companySpan.textContent = item.company;
    meta.appendChild(companySpan);
    meta.appendChild(document.createTextNode(` — ${item.location}`));

    card.appendChild(title);
    card.appendChild(freshness);
    card.appendChild(meta);

    if (item.tags.length > 0) {
      const tagsWrap = document.createElement("div");
      tagsWrap.className = "tags";
      for (const tag of item.tags) {
        const chip = document.createElement("span");
        chip.className = "tag";
        chip.textContent = tag;
        tagsWrap.appendChild(chip);
      }
      card.appendChild(tagsWrap);
    }

    listingsEl.appendChild(card);
  }
}

async function init() {
  try {
    const res = await fetch("data/listings.json", { cache: "no-store" });
    const data = await res.json();
    state.all = data.listings || [];
    updatedLineEl.textContent = formatUpdatedLine(data.generated_at);
  } catch (err) {
    updatedLineEl.textContent = "Couldn't load listings data.";
    console.error(err);
  }
  render();
}

searchEl.addEventListener("input", (e) => {
  state.search = e.target.value;
  render();
});

relevantToggleEl.addEventListener("change", (e) => {
  state.relevantOnly = e.target.checked;
  render();
});

init();
