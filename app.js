const state = {
  all: [],
  search: "",
  relevantOnly: false,
  freshOnly: false,
};

const tbodyEl = document.getElementById("listings-body");
const emptyStateEl = document.getElementById("empty-state");
const resultCountEl = document.getElementById("result-count");
const updatedLineEl = document.getElementById("updated-line");
const searchEl = document.getElementById("search");
const freshToggleEl = document.getElementById("fresh-toggle");
const relevantToggleEl = document.getElementById("relevant-toggle");

function parseDate(dateValue) {
  if (!dateValue) return null;
  const d = new Date(dateValue);
  return isNaN(d) ? null : d;
}

function isWithinLast24Hrs(dateValue) {
  const d = parseDate(dateValue);
  if (!d) return false;
  return Date.now() - d.getTime() <= 24 * 60 * 60 * 1000;
}

function postedLabel(dateValue) {
  const d = parseDate(dateValue);
  if (!d) {
    return dateValue ? dateValue.toLowerCase() : "date unknown";
  }
  const days = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (days <= 0) return "today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  return `${Math.floor(days / 30)} mo ago`;
}

function formatUpdatedLine(isoString) {
  if (!isoString) return "Waiting on the first automated scrape to run.";
  const dt = new Date(isoString);
  return `Listings last refreshed: ${dt.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}`;
}

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

function matchScore(tagCount) {
  return Math.min(100, tagCount * 30);
}

function render() {
  const q = state.search.trim().toLowerCase();

  const filtered = state.all.filter((item) => {
    if (state.relevantOnly && item.tags.length === 0) return false;
    if (state.freshOnly && !isWithinLast24Hrs(item.posted_at)) return false;
    if (!q) return true;
    const haystack = `${item.company} ${item.title} ${item.location}`.toLowerCase();
    return haystack.includes(q);
  });

  resultCountEl.textContent = `${filtered.length} of ${state.all.length} internship postings`;
  tbodyEl.innerHTML = "";
  emptyStateEl.hidden = filtered.length !== 0;

  for (const item of filtered) {
    const tr = document.createElement("tr");

    const companyTd = document.createElement("td");
    companyTd.className = "col-company";
    const companyCell = document.createElement("div");
    companyCell.className = "company-cell";
    const avatar = document.createElement("div");
    avatar.className = "company-avatar";
    avatar.textContent = initials(item.company);
    const companyName = document.createElement("span");
    companyName.className = "company-name";
    companyName.textContent = item.company;
    companyCell.appendChild(avatar);
    companyCell.appendChild(companyName);
    companyTd.appendChild(companyCell);

    const roleTd = document.createElement("td");
    roleTd.className = "col-role";
    const link = document.createElement("a");
    link.className = "role-title";
    link.href = item.url || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = item.title;
    roleTd.appendChild(link);
    if (isWithinLast24Hrs(item.posted_at)) {
      const badge = document.createElement("span");
      badge.className = "fresh-badge";
      badge.textContent = "NEW";
      roleTd.appendChild(badge);
    }

    const locationTd = document.createElement("td");
    locationTd.className = "col-location";
    const locSpan = document.createElement("span");
    locSpan.className = "location-text";
    locSpan.textContent = item.location;
    locationTd.appendChild(locSpan);

    const postedTd = document.createElement("td");
    postedTd.className = "col-posted";
    const postedSpan = document.createElement("span");
    postedSpan.className = "posted-text";
    postedSpan.textContent = postedLabel(item.posted_at);
    postedTd.appendChild(postedSpan);

    const matchTd = document.createElement("td");
    matchTd.className = "col-match";
    const score = matchScore(item.tags.length);
    const scoreSpan = document.createElement("span");
    scoreSpan.className = "match-score" + (score === 0 ? " low" : "");
    scoreSpan.textContent = score === 0 ? "—" : `${score}%`;
    if (item.tags.length > 0) {
      scoreSpan.title = item.tags.join(", ");
    }
    matchTd.appendChild(scoreSpan);

    tr.appendChild(companyTd);
    tr.appendChild(roleTd);
    tr.appendChild(locationTd);
    tr.appendChild(postedTd);
    tr.appendChild(matchTd);
    tbodyEl.appendChild(tr);
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

freshToggleEl.addEventListener("click", () => {
  state.freshOnly = !state.freshOnly;
  freshToggleEl.setAttribute("aria-pressed", String(state.freshOnly));
  render();
});

relevantToggleEl.addEventListener("click", () => {
  state.relevantOnly = !state.relevantOnly;
  relevantToggleEl.setAttribute("aria-pressed", String(state.relevantOnly));
  render();
});

init();
