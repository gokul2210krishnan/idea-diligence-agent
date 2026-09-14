const form = document.getElementById("idea-form");
const ideaInput = document.getElementById("idea");
const demoBtn = document.getElementById("run-demo");
const liveBtn = document.getElementById("run-live");
const cancelRunBtn = document.getElementById("cancel-run");
const cancelProgressBtn = document.getElementById("cancel-progress");
const progress = document.getElementById("progress");
const errorBox = document.getElementById("error");
const results = document.getElementById("results");
const empty = document.getElementById("empty");

let activeJobId = null;

document.querySelectorAll("[data-idea]").forEach((button) => {
  button.addEventListener("click", () => {
    ideaInput.value = button.dataset.idea;
    ideaInput.focus();
  });
});

document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => showTab(button.dataset.tab));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await investigate({ idea: ideaInput.value, demo: false, live: true });
});

demoBtn.addEventListener("click", async () => {
  if (!ideaInput.value.trim()) {
    ideaInput.value = "An app that helps independent restaurants track food inventory to reduce waste";
  }
  await investigate({ idea: ideaInput.value, demo: true, live: false });
});

cancelRunBtn.addEventListener("click", () => requestCancel());
cancelProgressBtn.addEventListener("click", () => requestCancel());

function showTab(name) {
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === name);
  });
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.panel !== name);
  });
}

function setBusy(busy, { cancellable } = {}) {
  liveBtn.disabled = busy;
  demoBtn.disabled = busy;
  cancelRunBtn.classList.toggle("hidden", !cancellable);
  if (!cancellable) resetCancelButtons();
}

function setCancelling(stopping) {
  [cancelRunBtn, cancelProgressBtn].forEach((button) => {
    button.disabled = stopping;
    button.textContent = stopping ? "Stopping…" : "Stop";
  });
}

function resetCancelButtons() {
  setCancelling(false);
}

async function requestCancel() {
  if (!activeJobId) return;
  setCancelling(true);
  try {
    const job = await readJson(await fetch(`/api/diligence/${activeJobId}/cancel`, {
      method: "POST",
    }));
    renderActivity(job);
  } catch (err) {
    setCancelling(false);
    showError(err.message);
  }
}

function setProgress(active) {
  progress.classList.toggle("hidden", !active);
  empty.classList.toggle("hidden", active || !results.classList.contains("hidden"));
  if (!active) return;
  const title = document.getElementById("progress-title");
  if (title) title.textContent = "Investigation running";
  const log = document.getElementById("activity-log");
  if (log) log.innerHTML = "";
  const status = document.getElementById("progress-status");
  if (status) status.textContent = "Starting…";
  resetCancelButtons();
  renderStepper("safety");
}

function clearProgress() {
  progress.classList.add("hidden");
}

function renderStepper(phase) {
  const order = ["safety", "research", "verdict"];
  const current = phase === "done" ? "verdict" : phase;
  const idx = Math.max(0, order.indexOf(current));
  [...progress.querySelectorAll("[data-step]")].forEach((step, index) => {
    step.classList.toggle("done", index < idx || phase === "done");
    step.classList.toggle("active", phase !== "done" && index === idx);
  });
}

function renderActivity(job) {
  renderStepper(job.phase || "safety");
  const events = job.events || [];
  const status = document.getElementById("progress-status");
  const title = document.getElementById("progress-title");
  const latest = events[events.length - 1];
  const stopping = Boolean(job.cancel_requested) || job.status === "cancelled";
  if (title) {
    title.textContent = stopping ? "Stopping investigation" : "Investigation running";
  }
  if (stopping) setCancelling(true);
  if (status) {
    status.textContent = latest ? latest.message : "Waiting for the first pipeline event…";
  }
  const log = document.getElementById("activity-log");
  if (!log) return;
  log.innerHTML = events.map((event) => {
    const when = (event.at || "").slice(11, 19);
    const count = event.evidence_count == null ? "" : `${event.evidence_count} evidence`;
    return `<li class="${event.level || "info"}"><span class="when">${escapeHtml(when)}</span><span class="msg">${escapeHtml(event.message || "")}</span><span class="meta">${escapeHtml(count)}</span></li>`;
  }).join("");
  log.scrollTop = log.scrollHeight;
}

async function pollJob(jobId) {
  const deadline = Date.now() + 10 * 60 * 1000;
  while (Date.now() < deadline) {
    const job = await readJson(await fetch(`/api/diligence/${jobId}`));
    renderActivity(job);
    if (job.status === "done") return job.result;
    if (job.status === "cancelled") {
      throw Object.assign(new Error("Investigation stopped."), { name: "InvestigationStoppedError" });
    }
    if (job.status === "error") {
      throw new Error(job.error || "Investigation failed.");
    }
    await sleep(1000);
  }
  throw new Error("Investigation timed out after 10 minutes.");
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
  empty.classList.add("hidden");
}

function hideError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

function errorFrom(payload, status) {
  const detail = payload && payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  return `Request failed (${status})`;
}

async function readJson(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok && response.status !== 202) {
    throw new Error(errorFrom(payload, response.status));
  }
  return payload;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function investigate({ idea, demo, live }) {
  hideError();
  results.classList.add("hidden");
  empty.classList.add("hidden");
  setBusy(true, { cancellable: live });
  setProgress(true);
  activeJobId = null;

  try {
    const response = await fetch(demo ? "/api/demo" : "/api/diligence", {
      method: demo ? "GET" : "POST",
      headers: demo ? {} : { "Content-Type": "application/json" },
      body: demo ? undefined : JSON.stringify({ idea, demo: false }),
    });
    let payload = await readJson(response);
    if (payload.job_id && payload.status && payload.status !== "done") {
      activeJobId = payload.job_id;
      renderActivity(payload);
      payload = await pollJob(payload.job_id);
    } else if (payload.result) {
      payload = payload.result;
    }
    if (!payload) throw new Error("Investigation returned no dossier.");
    if (payload.rejected) {
      throw new Error(payload.rejection_reason || "Rejected by the safety gate.");
    }
    render(payload);
  } catch (err) {
    empty.classList.remove("hidden");
    if (err.name === "InvestigationStoppedError") {
      showError("Investigation stopped. Submit the idea again when you want to resume.");
    } else {
      showError(live
        ? `${err.message} Use “Load demo dossier” if you want to walk the UI without live model calls.`
        : err.message);
    }
  } finally {
    activeJobId = null;
    setBusy(false);
    clearProgress();
  }
}

function bar(label, value) {
  const pct = Math.round((value || 0) * 100);
  return `
    <div class="bar">
      <span><span>${label}</span><b>${pct}%</b></span>
      <div class="track"><div class="fill" style="width:${pct}%"></div></div>
    </div>`;
}

function list(el, items) {
  el.innerHTML = (items || []).length
    ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "<li>None recorded.</li>";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function render(payload) {
  const verdict = payload.verdict || {};
  const decision = (verdict.decision || "MODIFY").toLowerCase();
  const card = document.getElementById("verdict-card");
  const stamp = document.getElementById("stamp");
  card.className = `verdict-card ${decision}`;
  stamp.className = `stamp ${decision}`;
  stamp.textContent = verdict.decision || "—";
  document.getElementById("verdict-label").textContent = `${verdict.method || "deterministic"} synthesis`;
  document.getElementById("verdict-summary").textContent = verdict.summary || "";
  document.getElementById("confidence-line").textContent =
    `${Math.round((verdict.confidence || 0) * 100)}% confidence · ${payload.state.idea}`;

  const scores = verdict.dimension_scores || {};
  document.getElementById("bars").innerHTML =
    bar("Problem", scores.problem) +
    bar("Competition", scores.competition) +
    bar("Economics", scores.economics);

  const budget = payload.budget || {};
  const scope = payload.scope || {};
  const breakdown = verdict.evidence_breakdown || {};
  document.getElementById("governance").innerHTML = `
    <div><dt>Safety gate</dt><dd>${scope.is_valid ? "PASSED" : "REJECTED"}</dd></div>
    <div><dt>Iterations</dt><dd>${budget.iterations || "n/a"}</dd></div>
    <div><dt>Tool calls</dt><dd>${budget.tool_calls_total || "n/a"}</dd></div>
    <div><dt>Elapsed</dt><dd>${budget.elapsed_seconds || 0}s</dd></div>
    <div><dt>Evidence mix</dt><dd>F ${breakdown.facts || 0} · I ${breakdown.inferences || 0} · A ${breakdown.assumptions || 0} · U ${breakdown.unknowns || 0}</dd></div>
  `;

  list(document.getElementById("key-evidence"), verdict.key_evidence);
  list(
    document.getElementById("actions-list"),
    [...(verdict.modifications || []), ...(verdict.next_steps || [])],
  );
  list(
    document.getElementById("risks-list"),
    [...(verdict.remaining_unknowns || []), ...(verdict.risks || [])],
  );

  const ledger = document.getElementById("ledger");
  ledger.innerHTML = (payload.state.evidence || []).map((item) => `
    <tr>
      <td><span class="badge ${item.evidence_type}">${item.evidence_type}</span></td>
      <td>${escapeHtml(item.category || "general")}</td>
      <td>${escapeHtml(item.content)}${item.source ? `<span class="source-link">${escapeHtml(item.source)}</span>` : ""}</td>
      <td>${Math.round((item.confidence || 0) * 100)}%</td>
    </tr>
  `).join("");

  document.getElementById("markdown").textContent = payload.report_markdown || "";
  showTab("overview");
  results.classList.remove("hidden");
  empty.classList.add("hidden");
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}
