"use strict";

/* ═══════════════════════════════════════════════════════════════════════════
   Job Radar — Frontend
   ═══════════════════════════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────────────────
const S = {
  jobs:          {},       // raw dict from /api/jobs, keyed by job_id
  group:         "new",   // currently selected left-rail group
  expandedId:    null,    // job currently expanded in center column
  selectedId:    null,    // job selected for right-rail panel
  lastRefresh:   null,    // Date | null
  nextRefreshAt: null,    // Date | null
  hourlyTimer:   null,    // setInterval handle
  notesTimer:    null,    // debounce handle
};

// ── Group Config ──────────────────────────────────────────────────────────
const GROUPS = [
  { id: "new",      label: "New",           status: "new",      dot: "dot-new"      },
  { id: "saved",    label: "Saved / On-Hold",status: "saved",    dot: "dot-saved"    },
  { id: "applied",  label: "Applied",       status: "applied",  dot: "dot-applied"  },
  { id: "rejected", label: "Rejected",      status: "rejected", dot: "dot-rejected" },
  { id: "expired",  label: "Expired",       status: "expired",  dot: "dot-expired"  },
];

const EMPTY_MESSAGES = {
  new:      "No new postings — click ↻ to fetch feeds",
  saved:    "No saved postings\nStar any posting to save it here",
  applied:  "No active applications",
  rejected: "No rejected postings",
  expired:  "No expired postings",
};

// ── Quick Search Config ───────────────────────────────────────────────────
// These buttons appear in the left rail under "Quick Search."
// Each one opens a Google Jobs search in a new tab for manual browsing.
//
// HOW TO CUSTOMIZE:
//   1. Replace the label with your target job title (shown on the button).
//   2. Replace the URL with a Google Jobs search for that title.
//      Template — swap YOUR+TITLE+HERE for your search terms:
//        https://www.google.com/search?q=%22YOUR+TITLE+HERE%22+remote&ibp=htl;jobs
//      Tip: wrap exact phrases in %22...%22 (URL-encoded double quotes).
//      Tip: do NOT add -intern or -contract — they break Google Jobs results.
//   3. Add as many entries as you like following the same { label, url } pattern.
//
// NOTE: Quick Search is for manual browsing only. To have Job Radar automatically
// pull postings into your dashboard, add Google Alert RSS feeds to config.json.

// Location clause: remote-first, but open to Bay Area onsite/hybrid
const _LOC = "remote+OR+%22San+Francisco%22+OR+%22Bay+Area%22";

const QUICK_SEARCHES = [
  {
    label: "Senior Product Manager",
    url: `https://www.google.com/search?q=%22senior+product+manager%22+${_LOC}&ibp=htl;jobs`,
  },
  {
    label: "Customer Success Manager",
    url: `https://www.google.com/search?q=%22customer+success+manager%22+${_LOC}&ibp=htl;jobs`,
  },
  {
    label: "Technical Program Manager",
    url: `https://www.google.com/search?q=%22technical+program+manager%22+${_LOC}&ibp=htl;jobs`,
  },
  {
    label: "Enterprise CSM",
    url: `https://www.google.com/search?q=%22enterprise+customer+success+manager%22+${_LOC}&ibp=htl;jobs`,
  },
  {
    label: "Implementation Manager",
    url: `https://www.google.com/search?q=%22implementation+manager%22+SaaS+${_LOC}&ibp=htl;jobs`,
  },
  {
    label: "Strategic Account Manager",
    url: `https://www.google.com/search?q=%22strategic+account+manager%22+SaaS+${_LOC}&ibp=htl;jobs`,
  },
  {
    label: "Partner Success Manager",
    url: `https://www.google.com/search?q=%22partner+success+manager%22+${_LOC}&ibp=htl;jobs`,
  },
  {
    label: "Solutions Consultant",
    url: `https://www.google.com/search?q=%22solutions+consultant%22+SaaS+${_LOC}&ibp=htl;jobs`,
  },
  {
    label: "Marketplace PM",
    url: `https://www.google.com/search?q=%22product+manager%22+marketplace+${_LOC}&ibp=htl;jobs`,
  },
];

// ── API Layer ─────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${msg}`);
  }
  return res.json();
}

async function loadJobs() {
  S.jobs = await apiFetch("/api/jobs");
}

async function apiUpdateStatus(jobId, status) {
  const updated = await apiFetch(`/api/jobs/${jobId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  S.jobs[jobId] = updated;
}

async function apiSaveNotes(jobId, notes) {
  await apiFetch(`/api/jobs/${jobId}/notes`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
  });
  if (S.jobs[jobId]) S.jobs[jobId].notes = notes;
}

async function apiDeleteJob(jobId) {
  await apiFetch(`/api/jobs/${jobId}`, { method: "DELETE" });
  delete S.jobs[jobId];
}

async function apiSaveUrl(jobId, url) {
  await apiFetch(`/api/jobs/${jobId}/url`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (S.jobs[jobId]) S.jobs[jobId].url = url;
}

async function apiFetchRecommendations(jobId) {
  // Return cached value if already generated
  if (S.jobs[jobId]?.recommendations) return S.jobs[jobId].recommendations;
  const data = await apiFetch(`/api/jobs/${jobId}/recommendations`);
  if (S.jobs[jobId]) S.jobs[jobId].recommendations = data.recommendations;
  return data.recommendations;
}

// ── Refresh ───────────────────────────────────────────────────────────────
async function runRefresh() {
  const btn = document.getElementById("refreshBtn");
  btn.classList.add("spinning");
  btn.disabled = true;

  try {
    const result = await apiFetch("/api/refresh", { method: "POST" });
    await loadJobs();
    S.lastRefresh = new Date();

    const parts = [];
    if (result.added > 0)   parts.push(`${result.added} new`);
    if (result.expired > 0) parts.push(`${result.expired} expired`);
    if (result.skipped > 0) parts.push(`${result.skipped} filtered`);
    const summary = parts.length ? parts.join(", ") : "No new postings";
    showToast(`↻ ${summary}`);
  } catch (err) {
    console.error("[Job Radar] Refresh failed:", err);
    showToast("Refresh failed — check the terminal for errors");
  } finally {
    btn.classList.remove("spinning");
    btn.disabled = false;
    renderAll();
    updateRefreshMeta();
  }
}

// ── Auto-Refresh — top of each hour ──────────────────────────────────────
function scheduleHourlyRefresh() {
  const now = new Date();
  const next = new Date(now);
  next.setHours(next.getHours() + 1, 0, 0, 0);
  const msToNext = next - now;

  S.nextRefreshAt = next;
  updateRefreshMeta();

  // Fire once at the top of the next hour, then every 60 min after
  setTimeout(() => {
    runRefresh();

    const nextNext = new Date(next.getTime() + 3_600_000);
    S.nextRefreshAt = nextNext;
    updateRefreshMeta();

    S.hourlyTimer = setInterval(() => {
      runRefresh();
      S.nextRefreshAt = new Date(Date.now() + 3_600_000);
      updateRefreshMeta();
    }, 3_600_000);
  }, msToNext);
}

// ── Sorting ───────────────────────────────────────────────────────────────
function getGroupJobs(groupId) {
  let jobs;

  if (groupId === "applied") {
    // Include legacy "waiting" status jobs so nothing gets orphaned
    jobs = Object.values(S.jobs).filter(j => j.status === "applied" || j.status === "waiting");
  } else {
    const status = GROUPS.find(g => g.id === groupId)?.status;
    jobs = Object.values(S.jobs).filter(j => j.status === status);
  }

  switch (groupId) {
    case "new":
      return jobs.sort((a, b) => {
        if (a.gold && !b.gold) return -1;
        if (!a.gold && b.gold) return 1;
        return b.fit_score - a.fit_score;
      });
    case "saved":
      return jobs.sort((a, b) =>
        (b.date_status_changed || "").localeCompare(a.date_status_changed || ""));
    case "applied":
      // Most recently applied first
      return jobs.sort((a, b) => {
        const ad = a.date_applied || a.date_status_changed || "";
        const bd = b.date_applied || b.date_status_changed || "";
        return bd.localeCompare(ad);
      });
    case "rejected":
    case "expired":
      return jobs.sort((a, b) =>
        (b.date_status_changed || "").localeCompare(a.date_status_changed || ""));
    default:
      return jobs;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
    });
  } catch { return iso; }
}

function formatTime(d) {
  if (!d) return "";
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function stripeClass(job) {
  if (job.status === "new") return job.gold ? "stripe-gold" : "stripe-new";
  return `stripe-${job.status}`;
}

function fitBadgeClass(score) {
  if (score >= 8) return "fit-gold";
  if (score >= 5) return "fit-green";
  if (score >= 3) return "fit-yellow";
  return "fit-red";
}

function fitColor(score) {
  if (score >= 8) return "#d4900a";
  if (score >= 5) return "#0d9a70";
  if (score >= 3) return "#b57810";
  return "#b04040";
}

function atsColor(pct) {
  if (pct >= 70) return "#0d9a70";
  if (pct >= 50) return "#b57810";
  return "#b04040";
}

// ── Render: Left Rail ─────────────────────────────────────────────────────
function renderRail() {
  const list = document.getElementById("groupList");
  list.innerHTML = GROUPS.map(g => {
    const count = Object.values(S.jobs).filter(j => j.status === g.status).length;
    const active = S.group === g.id ? " active" : "";
    return `
      <li class="group-item">
        <button class="group-btn${active}" data-group="${g.id}">
          <span class="group-dot ${g.dot}"></span>
          <span class="group-label">${g.label}</span>
          <span class="group-count">${count}</span>
        </button>
      </li>`;
  }).join("");

  list.querySelectorAll(".group-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      if (S.group !== btn.dataset.group) {
        S.group = btn.dataset.group;
        S.expandedId = null;
        S.selectedId = null;
        renderAll();
      }
    });
  });
}

// ── Render: Quick Search Links ────────────────────────────────────────────
// Called once from init() — static content, no need to re-render on every renderAll.
function renderSearchLinks() {
  const section = document.getElementById("searchSection");
  if (!section) return;
  section.innerHTML = `
    <div class="search-section-label">Quick Search</div>
    ${QUICK_SEARCHES.map(s => `
      <a class="search-link" href="${s.url}" target="_blank" rel="noopener noreferrer" title="${esc(s.label)}">
        <span class="search-link-icon">⌕</span>
        <span class="search-link-label">${esc(s.label)}</span>
      </a>
    `).join("")}
  `;
}

// ── Render: Center Column ─────────────────────────────────────────────────
function renderCenter() {
  const groupDef = GROUPS.find(g => g.id === S.group);
  document.getElementById("groupTitle").textContent = groupDef?.label ?? "";

  const jobs = getGroupJobs(S.group);
  document.getElementById("jobCountBadge").textContent =
    `${jobs.length} posting${jobs.length !== 1 ? "s" : ""}`;

  const list = document.getElementById("jobList");

  if (jobs.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">◎</div>
        <div>${EMPTY_MESSAGES[S.group] ?? "Nothing here"}</div>
      </div>`;
    return;
  }

  list.innerHTML = jobs.map(job => buildRowHTML(job)).join("");
}

// ── Build: Job Row HTML ───────────────────────────────────────────────────
function buildRowHTML(job) {
  const isExpanded = S.expandedId === job.id;
  const isSelected = S.selectedId === job.id;
  const stripe = stripeClass(job);
  const badge = fitBadgeClass(job.fit_score);
  const isSaved = job.status === "saved";
  const isNew   = job.status === "new";

  // Decide which action buttons to render
  const canApply  = !["applied","rejected","expired"].includes(job.status);
  const canReject = !["rejected","expired"].includes(job.status);
  const canStar   = ["new","saved"].includes(job.status);

  return `
<div class="job-row${isSelected ? " selected" : ""}" data-job-id="${job.id}">
  <div class="row-main ${stripe}">
    <div class="row-inner">
      <div class="row-left">
        ${job.gold && job.status !== "new" ? `<span class="gold-diamond" title="Gold match">♦</span>` : ""}
        ${canStar
          ? `<button class="star-btn${isSaved ? " starred" : ""}" data-action="star" title="${isSaved ? "Remove from Saved" : "Save posting"}">★</button>`
          : `<span style="width:18px;display:inline-block"></span>`}
        <div class="job-info">
          <div class="job-title">${esc(job.title)}</div>
          <div class="job-company">${esc(job.company)}${job.company && job.ats ? " · " : ""}${esc(job.ats)}</div>
        </div>
      </div>
      <div class="row-right">
        ${job.scored === false
          ? `<span class="fit-badge" style="background:#0a66c2;color:#fff;border-color:#0a66c2;font-size:0.7rem;letter-spacing:0.02em" title="LinkedIn posting — login required">LinkedIn</span>`
          : `<span class="fit-badge ${badge}" title="Fit score: ${job.fit_score}/10 — ${job.fit_score>=8?'Gold match':job.fit_score>=5?'Good fit':job.fit_score>=3?'Fair fit':'Low fit'}">${job.fit_score}/10</span>`
        }
        <div class="row-actions">
          <button class="btn btn-open" data-action="open" title="Open posting in browser">↗</button>
          ${canApply  ? `<button class="btn btn-applied"  data-action="applied">Applied</button>` : ""}
          ${canReject ? `<button class="btn btn-rejected" data-action="rejected">Reject</button>` : ""}
          <div class="move-dropdown-wrap">
            <button class="btn btn-move-row" data-action="move-toggle" title="Move to bucket or remove">Move ▾</button>
            <div class="move-dropdown-menu" data-move-menu="${job.id}">
              ${GROUPS.filter(g => g.status !== job.status).map(g =>
                `<button class="move-dropdown-item" data-action="move-row" data-status="${g.status}">${g.label}</button>`
              ).join("")}
              <div class="move-dropdown-divider"></div>
              <button class="move-dropdown-item move-dropdown-danger" data-action="delete-job">Remove Posting</button>
            </div>
          </div>
          <button class="btn btn-expand${isExpanded ? " active" : ""}" data-action="expand" title="${isExpanded ? "Collapse" : "Expand"}">${isExpanded ? "▲" : "▼"}</button>
        </div>
      </div>
    </div>
  </div>
  ${isExpanded ? buildDetailHTML(job) : ""}
</div>`;
}

// ── Build: Move-To Buttons ────────────────────────────────────────────────
function buildMoveSection(job) {
  const s = job.status;

  // Map current status → array of {label, target} move options
  const moves = [];
  if (s === "saved") {
    moves.push({ label: "← Back to New",  target: "new" });
  } else if (s === "applied" || s === "waiting") {
    moves.push({ label: "← Back to New",   target: "new"   });
    moves.push({ label: "★ Move to Saved", target: "saved" });
  } else if (s === "rejected") {
    moves.push({ label: "← Reconsider (→ New)", target: "new" });
  } else if (s === "expired") {
    moves.push({ label: "← Reopen (→ New)", target: "new" });
  }

  if (!moves.length) return "";   // "new" — row buttons handle forward moves

  return `
  <div class="move-section">
    <div class="section-label">Move to</div>
    <div class="move-btns">
      ${moves.map(m =>
        `<button class="btn btn-move" data-action="move-to" data-status="${m.target}">${m.label}</button>`
      ).join("")}
    </div>
  </div>`;
}

// ── Build: Expanded Detail HTML ───────────────────────────────────────────
function buildDetailHTML(job) {
  const fc = fitColor(job.fit_score);
  const ac = atsColor(job.ats_score);
  const fitBarW = Math.round((job.fit_score / 10) * 100);
  const atsBarW = job.ats_score;

  const matched = (job.matched_keywords || []).slice(0, 20);
  const missing = (job.missing_keywords || []).slice(0, 15);
  const hasRecs = !!job.recommendations;

  const postingPreview = job.posting_text
    ? esc(job.posting_text.slice(0, 2400)) + (job.posting_text.length > 2400 ? "…" : "")
    : "";

  return `
<div class="row-detail open">

  ${job.scored === false ? `
  <div style="padding:12px 14px;background:#e8f0fb;border-radius:6px;color:#0a66c2;font-size:0.85rem;line-height:1.5;margin-bottom:10px">
    LinkedIn requires you to be logged in. Please navigate directly to LinkedIn.
  </div>` : `
  <div class="score-cards">
    <div class="score-card">
      <div class="score-label">Fit Score</div>
      <div class="score-value" style="color:${fc}">
        ${job.fit_score}<span class="score-max">/10</span>
      </div>
      <div class="score-bar">
        <div class="score-bar-fill" style="width:${fitBarW}%;background:${fc}"></div>
      </div>
    </div>
    <div class="score-card">
      <div class="score-label">ATS Score</div>
      <div class="score-value" style="color:${ac}">
        ${job.ats_score}<span class="score-max">%</span>
      </div>
      <div class="score-bar">
        <div class="score-bar-fill" style="width:${atsBarW}%;background:${ac}"></div>
      </div>
    </div>
  </div>`}

  ${matched.length || missing.length ? `
  <div class="keyword-section">
    ${matched.length ? `
    <div class="keyword-group">
      <div class="section-label">Matched (${matched.length})</div>
      <div class="keyword-list">
        ${matched.map(k => `<span class="keyword-tag tag-matched">${esc(k)}</span>`).join("")}
      </div>
    </div>` : ""}
    ${missing.length ? `
    <div class="keyword-group">
      <div class="section-label">Missing (${missing.length})</div>
      <div class="keyword-list">
        ${missing.map(k => `<span class="keyword-tag tag-missing">${esc(k)}</span>`).join("")}
      </div>
    </div>` : ""}
  </div>` : ""}

  ${postingPreview ? `
  <div class="posting-section">
    <div class="section-label">Posting</div>
    <div class="posting-text">${postingPreview}</div>
  </div>` : ""}

  <div class="notes-section">
    <div class="section-label">Notes</div>
    <textarea class="notes-input" data-action="notes" placeholder="Add notes about this posting…">${esc(job.notes || "")}</textarea>
  </div>

  ${buildMoveSection(job)}

  <div class="rec-section">
    <button class="btn btn-rec" data-action="get-recs">
      ${hasRecs ? "↺ Refresh Recommendations" : "✦ Get Recommendations"}
    </button>
    <button class="btn btn-copy" data-action="copy-recs"${!hasRecs ? " disabled" : ""}>
      ⎘ Copy to Clipboard
    </button>
  </div>

</div>`;
}

// ── Wire: Row Event Delegation ────────────────────────────────────────────
function wireRowEvents(container) {
  // Single click handler on the container
  container.addEventListener("click", async e => {
    const row = e.target.closest(".job-row");
    if (!row) return;
    const jobId = row.dataset.jobId;
    const job   = S.jobs[jobId];
    if (!job) return;

    const actionEl = e.target.closest("[data-action]");
    const action   = actionEl?.dataset?.action;

    if (!action) {
      // Click on the job info area — toggle expand
      if (e.target.closest(".job-info")) {
        S.expandedId = S.expandedId === jobId ? null : jobId;
        S.selectedId = jobId;
      } else {
        // Bare row click elsewhere — select for right rail
        S.selectedId = S.selectedId === jobId ? null : jobId;
      }
      renderAll();
      return;
    }

    e.stopPropagation();

    switch (action) {
      // ── Move dropdown toggle ─────────────────────────────────────────────
      case "move-toggle": {
        const menu = row.querySelector(".move-dropdown-menu");
        if (!menu) break;
        const isOpen = menu.classList.contains("open");
        // Close any other open dropdowns first
        document.querySelectorAll(".move-dropdown-menu.open").forEach(m => m.classList.remove("open"));
        if (!isOpen) menu.classList.add("open");
        break;
      }

      // ── Move to bucket (from row dropdown) ───────────────────────────────
      case "move-row": {
        const targetStatus = actionEl.dataset.status;
        if (!targetStatus) break;
        // Close dropdown
        document.querySelectorAll(".move-dropdown-menu.open").forEach(m => m.classList.remove("open"));
        const toastLabels = {
          new: "Moved to New ✓", saved: "Moved to Saved ✓",
          applied: "Moved to Applied ✓", rejected: "Moved to Rejected",
          expired: "Moved to Expired",
        };
        try {
          await apiUpdateStatus(jobId, targetStatus);
          if (S.expandedId === jobId) S.expandedId = null;
          if (S.selectedId === jobId) S.selectedId = null;
          renderAll();
          showToast(toastLabels[targetStatus] ?? `Moved to ${targetStatus} ✓`);
        } catch (err) {
          console.error(err);
          showToast("Could not move posting");
        }
        break;
      }

      // ── Delete / remove posting ──────────────────────────────────────────
      case "delete-job": {
        document.querySelectorAll(".move-dropdown-menu.open").forEach(m => m.classList.remove("open"));
        try {
          await apiDeleteJob(jobId);
          if (S.expandedId === jobId) S.expandedId = null;
          if (S.selectedId === jobId) S.selectedId = null;
          renderAll();
          showToast("Posting removed");
        } catch (err) {
          console.error(err);
          showToast("Could not remove posting");
        }
        break;
      }

      // ── Expand / collapse ────────────────────────────────────────────────
      case "expand": {
        if (S.expandedId === jobId) {
          S.expandedId = null;
        } else {
          S.expandedId = jobId;
          S.selectedId = jobId;  // always populate right rail when expanding
        }
        renderAll();
        break;
      }

      // ── Star (save / unsave) ─────────────────────────────────────────────
      case "star": {
        const newStatus = job.status === "saved" ? "new" : "saved";
        try {
          await apiUpdateStatus(jobId, newStatus);
          // If we just unstarred while in the Saved group the job should leave
          if (S.group === "saved" && newStatus === "new") {
            if (S.expandedId === jobId) S.expandedId = null;
            if (S.selectedId === jobId) S.selectedId = null;
          }
          renderAll();
        } catch (err) {
          console.error(err);
          showToast("Could not update status");
        }
        break;
      }

      // ── Open posting in browser ──────────────────────────────────────────
      case "open": {
        window.open(job.url, "_blank");
        break;
      }

      // ── Applied ──────────────────────────────────────────────────────────
      case "applied": {
        try {
          await apiUpdateStatus(jobId, "applied"); // backend auto-transitions → waiting
          if (S.expandedId === jobId) S.expandedId = null;
          if (S.selectedId === jobId) S.selectedId = null;
          renderAll();
          showToast("Moved to Applied ✓");
        } catch (err) {
          console.error(err);
          showToast("Could not update status");
        }
        break;
      }

      // ── Rejected ─────────────────────────────────────────────────────────
      case "rejected": {
        try {
          await apiUpdateStatus(jobId, "rejected");
          if (S.expandedId === jobId) S.expandedId = null;
          if (S.selectedId === jobId) S.selectedId = null;
          renderAll();
          showToast("Marked as Rejected");
        } catch (err) {
          console.error(err);
          showToast("Could not update status");
        }
        break;
      }

      // ── Move to status (from detail panel) ───────────────────────────────
      case "move-to": {
        const targetStatus = actionEl.dataset.status;
        if (!targetStatus) break;
        const toastLabels = {
          new:     "Moved back to New ✓",
          saved:   "Moved to Saved ✓",
          applied: "Moved to Applied ✓",
        };
        try {
          await apiUpdateStatus(jobId, targetStatus);
          S.expandedId = null;
          S.selectedId = null;
          renderAll();
          showToast(toastLabels[targetStatus] ?? `Moved to ${targetStatus} ✓`);
        } catch (err) {
          console.error(err);
          showToast("Could not move posting");
        }
        break;
      }

      // ── Recommendations ──────────────────────────────────────────────────
      case "get-recs": {
        const btn = actionEl;
        btn.textContent = "⟳ Loading…";
        btn.disabled = true;
        try {
          await apiFetchRecommendations(jobId);
          // Re-render to show the recs and enable the copy button
          renderAll();
        } catch (err) {
          console.error(err);
          btn.disabled = false;
          btn.textContent = "✦ Get Recommendations";
          showToast("Could not load recommendations");
        }
        break;
      }

      // ── Copy recommendations ─────────────────────────────────────────────
      case "copy-recs": {
        const recs = S.jobs[jobId]?.recommendations;
        if (!recs) { showToast("No recommendations to copy"); break; }
        try {
          await navigator.clipboard.writeText(recs);
          showToast("Copied to clipboard ✓");
        } catch (err) {
          console.error(err);
          showToast("Clipboard access denied");
        }
        break;
      }
    }
  });

  // Notes — debounced auto-save (800ms)
  container.addEventListener("input", e => {
    if (e.target.dataset.action !== "notes") return;
    const row = e.target.closest(".job-row");
    if (!row) return;
    const jobId = row.dataset.jobId;
    clearTimeout(S.notesTimer);
    S.notesTimer = setTimeout(() => {
      apiSaveNotes(jobId, e.target.value).catch(err => {
        console.error("[Job Radar] Notes save failed:", err);
      });
    }, 800);
  });
}

// ── Render: Right Rail ────────────────────────────────────────────────────
function renderRightRail() {
  const panel = document.getElementById("companyPanel");
  const job = S.selectedId ? S.jobs[S.selectedId] : null;

  if (!job) {
    panel.innerHTML = `<div class="panel-placeholder">
      <span>Select a posting to see company context</span>
    </div>`;
    return;
  }

  const info    = job.company_info || {};
  const contact = job.contact || {};
  const fc = fitColor(job.fit_score);
  const ac = atsColor(job.ats_score);

  // Work style badge color
  const wsColor = { Remote: "#0d9a70", Hybrid: "#2f6fd4", Onsite: "#5a6270" };
  const wsStyle = wsColor[job.work_style] || "#404055";

  panel.innerHTML = `
<div class="company-panel">

  <div class="panel-company-header">
    <div class="company-name-heading">${esc(job.company || job.title.split(" at ").pop() || "—")}</div>
    <div class="panel-badges">
      ${job.work_style ? `<span class="ws-badge" style="background:${wsStyle}22;color:${wsStyle};border-color:${wsStyle}44">${esc(job.work_style)}</span>` : ""}
      ${job.ats && job.ats !== "Unknown" ? `<span class="ats-badge">${esc(job.ats)}</span>` : ""}
      ${job.gold ? `<span class="gold-pill">♦ Gold</span>` : ""}
    </div>
  </div>

  ${job.feed_label ? `<div class="feed-label" style="margin-bottom:10px">${esc(job.feed_label)}</div>` : ""}

  ${job.company ? `
  <a class="company-google-search"
     href="https://www.google.com/search?q=${encodeURIComponent('"' + job.company + '" careers')}"
     target="_blank" rel="noopener noreferrer">
    ⌕ Search Google for <em>${esc(job.company)}</em>
  </a>` : ""}

  ${job.scored === false ? `
  <div class="panel-section">
    <div style="padding:10px 12px;background:#e8f0fb;border-radius:6px;color:#0a66c2;font-size:0.82rem;line-height:1.5">
      LinkedIn requires you to be logged in. Please navigate directly to LinkedIn.
    </div>
  </div>` : `
  <div class="panel-section">
    <div class="rail-scores">
      <div class="rail-score-item">
        <div class="rail-score-num" style="color:${fc}">${job.fit_score}</div>
        <div class="rail-score-lbl">Fit /10</div>
      </div>
      <div class="rail-score-item">
        <div class="rail-score-num" style="color:${ac}">${job.ats_score}%</div>
        <div class="rail-score-lbl">ATS</div>
      </div>
    </div>
  </div>`}

  ${job.salary ? `
  <div class="panel-section">
    <div class="panel-section-label">Salary</div>
    <div class="panel-section-value panel-highlight">${esc(job.salary)}</div>
  </div>` : ""}

  ${job.location && job.location !== job.work_style ? `
  <div class="panel-section">
    <div class="panel-section-label">Location</div>
    <div class="panel-section-value">${esc(job.location)}</div>
  </div>` : ""}

  ${info.website ? `
  <div class="panel-section">
    <div class="panel-section-label">Website</div>
    <a class="panel-link" href="${esc(info.website)}" target="_blank">${esc(info.website)}</a>
  </div>` : ""}

  ${info.linkedin ? `
  <div class="panel-section">
    <div class="panel-section-label">LinkedIn</div>
    <a class="panel-link panel-link-linkedin" href="${esc(info.linkedin)}" target="_blank">${esc(info.linkedin.replace("https://www.", "").replace("https://", ""))}</a>
  </div>` : ""}

  ${info.description ? `
  <div class="panel-section">
    <div class="panel-section-label">About</div>
    <div class="panel-section-value">${esc(info.description)}</div>
  </div>` : ""}

  ${contact.name || contact.email ? `
  <div class="panel-section">
    <div class="panel-section-label">Contact</div>
    ${contact.name  ? `<div class="contact-name">${esc(contact.name)}</div>` : ""}
    ${contact.title ? `<div class="contact-title">${esc(contact.title)}</div>` : ""}
    ${contact.email ? `<div style="margin-top:3px">
      <a class="panel-link" href="mailto:${esc(contact.email)}">${esc(contact.email)}</a>
    </div>` : ""}
  </div>` : ""}

  <div class="panel-section">
    <div class="panel-section-label">Posting URL</div>
    <input
      class="url-edit-input"
      type="url"
      data-action="edit-url"
      data-job-id="${job.id}"
      value="${esc(job.url)}"
      placeholder="Paste career page URL…"
      spellcheck="false"
    />
  </div>

  <div class="panel-section">
    <div class="panel-section-label">Found</div>
    <div class="panel-section-value">${formatDate(job.date_found)}</div>
  </div>

  ${job.date_applied ? `
  <div class="panel-section">
    <div class="panel-section-label">Applied</div>
    <div class="panel-section-value">${formatDate(job.date_applied)}</div>
  </div>` : ""}

</div>`;
}

// ── Render: Refresh Meta ──────────────────────────────────────────────────
function updateRefreshMeta() {
  const lastEl = document.getElementById("lastRefreshTime");
  const nextEl = document.getElementById("nextRefreshTime");
  if (lastEl) {
    lastEl.textContent = S.lastRefresh ? `↻ ${formatTime(S.lastRefresh)}` : "Not refreshed yet";
  }
  if (nextEl) {
    nextEl.textContent = S.nextRefreshAt ? `Next: ${formatTime(S.nextRefreshAt)}` : "";
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────
function showToast(msg) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}

// ── Render All ────────────────────────────────────────────────────────────
function renderAll() {
  renderRail();
  renderCenter();
  renderRightRail();
  updateRefreshMeta();
}

// ── Init ──────────────────────────────────────────────────────────────────
async function init() {
  document.getElementById("refreshBtn").addEventListener("click", runRefresh);

  // Wire job list events ONCE on the persistent container — never repeated on re-render
  wireRowEvents(document.getElementById("jobList"));

  // URL edit — save on blur (right rail, event delegation on persistent container)
  document.getElementById("companyPanel").addEventListener("blur", async e => {
    if (e.target.dataset.action !== "edit-url") return;
    const jobId = e.target.dataset.jobId;
    const newUrl = e.target.value.trim();
    if (!jobId || !newUrl || newUrl === S.jobs[jobId]?.url) return;
    try {
      await apiSaveUrl(jobId, newUrl);
      showToast("URL updated ✓");
    } catch (err) {
      console.error("[Job Radar] URL save failed:", err);
      showToast("Could not save URL");
    }
  }, true); // useCapture — blur doesn't bubble

  // Close any open Move dropdowns when clicking outside of them
  document.addEventListener("click", e => {
    if (!e.target.closest(".move-dropdown-wrap")) {
      document.querySelectorAll(".move-dropdown-menu.open").forEach(m => m.classList.remove("open"));
    }
  });

  try {
    await loadJobs();
  } catch (err) {
    console.error("[Job Radar] Failed to load jobs:", err);
    document.getElementById("jobList").innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠</div>
        <div>Could not connect to Job Radar server.<br>Check the terminal for errors.</div>
      </div>`;
  }

  renderSearchLinks(); // Static — render once, not on every renderAll
  renderAll();
  scheduleHourlyRefresh();

  // Display app version in the footer
  try {
    const vr = await fetch("/api/version");
    if (vr.ok) {
      const { version } = await vr.json();
      const el = document.getElementById("appVersion");
      if (el && version) el.textContent = `v${version}`;
    }
  } catch (_) { /* non-critical — silent fail */ }

  // Check for updates after a short delay so it doesn't block startup
  setTimeout(checkForUpdates, 3000);
}

// ── Notification / Update System ─────────────────────────────────────────────

let _notifDismissed = false;

function showNotification(title, bodyHtml, actionsHtml = "") {
  const panel  = document.getElementById("notifPanel");
  const btn    = document.getElementById("notifBtn");
  const tEl    = document.getElementById("notifTitle");
  const bEl    = document.getElementById("notifBody");
  const aEl    = document.getElementById("notifActions");

  tEl.textContent = title;
  bEl.innerHTML   = bodyHtml;
  aEl.innerHTML   = actionsHtml;

  panel.style.display = "block";
  btn.style.display   = "inline-block";

  // Bell toggles the panel open/closed
  btn.onclick = () => {
    panel.style.display = panel.style.display === "none" ? "block" : "none";
  };

  // Close button dismisses for this session
  document.getElementById("notifClose").onclick = () => {
    panel.style.display = "none";
    btn.style.display   = "none";
    _notifDismissed = true;
  };
}

async function checkForUpdates() {
  if (_notifDismissed) return;
  try {
    const res  = await fetch("/api/check-update");
    if (!res.ok) return;
    const data = await res.json();
    if (!data.available) return;

    const body = `
      <strong>v${data.remote}</strong> is available.<br>
      You are on <strong>v${data.local}</strong>.
    `;

    let actions = "";
    if (data.has_git) {
      // Git users get a one-click update + restart
      actions = `
        <button class="notif-btn-action" id="doUpdateBtn">↑ Update &amp; Restart</button>
        <button class="notif-btn-action secondary" id="dismissUpdateBtn">Remind me later</button>
      `;
    } else {
      // ZIP users get download instructions
      actions = `
        <button class="notif-btn-action" onclick="window.open('https://github.com/${data.remote ? '' : ''}','_blank')">
          Download on GitHub
        </button>
        <button class="notif-btn-action secondary" id="dismissUpdateBtn">Dismiss</button>
      `;
    }

    showNotification("Update Available", body, actions);

    // Wire update button for git users
    const doBtn = document.getElementById("doUpdateBtn");
    if (doBtn) doBtn.addEventListener("click", () => runUpdate(data.remote));

    const dimBtn = document.getElementById("dismissUpdateBtn");
    if (dimBtn) dimBtn.addEventListener("click", () => {
      document.getElementById("notifPanel").style.display = "none";
      document.getElementById("notifBtn").style.display   = "none";
      _notifDismissed = true;
    });

  } catch (_) { /* non-critical */ }
}

async function runUpdate(newVersion) {
  const doBtn   = document.getElementById("doUpdateBtn");
  const bodyEl  = document.getElementById("notifBody");
  const actEl   = document.getElementById("notifActions");

  if (doBtn) doBtn.disabled = true;
  bodyEl.innerHTML = `Pulling <strong>v${newVersion}</strong>…<br>Your data is being preserved.`;
  actEl.innerHTML  = "";

  try {
    const res  = await fetch("/api/update", { method: "POST" });
    const data = await res.json();

    if (!data.ok) {
      bodyEl.innerHTML = `<span style="color:#f87171">Update failed:</span><br>${data.error}`;
      actEl.innerHTML  = `<button class="notif-btn-action secondary" id="dismissUpdateBtn">Close</button>`;
      document.getElementById("dismissUpdateBtn")?.addEventListener("click", () => {
        document.getElementById("notifPanel").style.display = "none";
        document.getElementById("notifBtn").style.display   = "none";
      });
      return;
    }

    // Server is restarting — poll until it's back, then reload
    bodyEl.innerHTML = `Update complete!<br>Restarting server…`;
    await pollUntilReady();
    bodyEl.innerHTML = `Restarted. Reloading…`;
    setTimeout(() => window.location.reload(), 800);

  } catch (err) {
    bodyEl.innerHTML = `<span style="color:#f87171">Error: ${err.message}</span>`;
  }
}

async function pollUntilReady(maxWaitMs = 20000, intervalMs = 800) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    await new Promise(r => setTimeout(r, intervalMs));
    try {
      const r = await fetch("/api/version");
      if (r.ok) return; // Server is back
    } catch (_) { /* still restarting */ }
  }
}

document.addEventListener("DOMContentLoaded", init);
