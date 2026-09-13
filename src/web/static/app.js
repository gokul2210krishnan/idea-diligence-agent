const form = document.getElementById("idea-form");
const ideaInput = document.getElementById("idea");
const demoBtn = document.getElementById("run-demo");
const progress = document.getElementById("progress");
const errorBox = document.getElementById("error");
const results = document.getElementById("results");

document.querySelectorAll("[data-idea]").forEach((button) => {
  button.addEventListener("click", () => {
    ideaInput.value = button.dataset.idea;
  });
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

function setProgress(active) {
  progress.classList.toggle("hidden", !active);
  const steps = [...progress.querySelectorAll("[data-step]")];
  steps.forEach((step, index) => {
    step.classList.toggle("active", index === 0);
    step.classList.remove("done");
  });
  if (!active) return;
  let i = 0;
  window._progressTimer = setInterval(() => {
    if (i < steps.length) {
      steps[i].classList.add("done");
      steps[i].classList.remove("active");
      if (steps[i + 1]) steps[i + 1].classList.add("active");
      i += 1;
    }
  }, 900);
}

function clearProgress() {
  if (window._progressTimer) clearInterval(window._progressTimer);
  progress.classList.add("hidden");
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function hideError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

async function investigate({ idea, demo, live }) {
  hideError();
  results.classList.add("hidden");
  setProgress(true);

  try {
    const response = await fetch(demo ? "/api/demo" : "/api/diligence", {
      method: demo ? "GET" : "POST",
      headers: demo ? {} : { "Content-Type": "application/json" },
      body: demo ? undefined : JSON.stringify({ idea, demo: false }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `Request failed (${response.status})`);
    }
    const payload = await response.json();
    if (payload.rejected) {
      throw new Error(payload.rejection_reason || "Rejected by the safety gate.");
    }
    render(payload);
  } catch (err) {
    showError(live
      ? `${err.message} Use “Load demo dossier” if you want to walk the UI without live model calls.`
      : err.message);
  } finally {
    clearProgress();
  }
}

function bar(label, value) {
  const pct = Math.round((value || 0) * 100);
  return `
    <div class="bar">
      <span><b>${label}</b><b>${pct}%</b></span>
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
    `Confidence ${Math.round((verdict.confidence || 0) * 100)}% · ${payload.state.idea}`;

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
      <td>${escapeHtml(item.content)}${item.source ? `<div class="hint">${escapeHtml(item.source)}</div>` : ""}</td>
      <td>${Math.round((item.confidence || 0) * 100)}%</td>
    </tr>
  `).join("");

  document.getElementById("markdown").textContent = payload.report_markdown || "";
  results.classList.remove("hidden");
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}
