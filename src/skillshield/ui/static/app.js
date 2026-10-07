// SkillShield UI client script (docs/product-plan.md P6).
//
// This file contains zero security logic. It sends one request to
// /api/assess and renders exactly what comes back -- it never computes a
// recommendation, severity, or D/S/R/P comparison itself. The staged
// "Preparing... / Analyzing..." messages below are purely a client-side
// progress simulation around that one real request, per the decision
// recorded in DECISIONS.md ("P5/P6") -- there is no second server call
// behind them.

(function () {
  "use strict";

  const zipInput = document.getElementById("zip-input");
  const dirInput = document.getElementById("dir-input");
  const selectionSummary = document.getElementById("selection-summary");
  const assessForm = document.getElementById("assess-form");
  const assessButton = document.getElementById("assess-button");

  const uploadPanel = document.getElementById("upload-panel");
  const progressPanel = document.getElementById("progress-panel");
  const progressMessage = document.getElementById("progress-message");
  const errorPanel = document.getElementById("error-panel");
  const errorMessage = document.getElementById("error-message");
  const resultPanel = document.getElementById("result-panel");

  const recommendationBanner = document.getElementById("recommendation-banner");
  const capabilityTableBody = document.querySelector("#capability-table tbody");
  const findingsList = document.getElementById("findings-list");
  const limitationsList = document.getElementById("limitations-list");
  const resultMeta = document.getElementById("result-meta");

  const resetButton = document.getElementById("reset-button");
  const errorResetButton = document.getElementById("error-reset-button");

  const PROGRESS_MESSAGES = [
    "Preparing skill...",
    "Analyzing declaration...",
    "Running static analysis...",
    "Running controlled execution...",
    "Correlating evidence...",
    "Generating assessment...",
  ];

  let progressTimer = null;

  function showOnly(panel) {
    [uploadPanel, progressPanel, errorPanel, resultPanel].forEach((p) => {
      p.hidden = p !== panel;
    });
  }

  function updateSelectionSummary() {
    const hasZip = zipInput.files.length > 0;
    const hasDir = dirInput.files.length > 0;

    if (hasZip) {
      selectionSummary.textContent = `Selected ZIP: ${zipInput.files[0].name}`;
    } else if (hasDir) {
      selectionSummary.textContent = `Selected folder: ${dirInput.files.length} file(s)`;
    } else {
      selectionSummary.textContent = "No skill selected yet.";
    }

    assessButton.disabled = !(hasZip || hasDir);
  }

  zipInput.addEventListener("change", () => {
    if (zipInput.files.length > 0) {
      dirInput.value = "";
    }
    updateSelectionSummary();
  });

  dirInput.addEventListener("change", () => {
    if (dirInput.files.length > 0) {
      zipInput.value = "";
    }
    updateSelectionSummary();
  });

  function startProgressAnimation() {
    let index = 0;
    progressMessage.textContent = PROGRESS_MESSAGES[0];
    progressTimer = setInterval(() => {
      index = (index + 1) % PROGRESS_MESSAGES.length;
      progressMessage.textContent = PROGRESS_MESSAGES[index];
    }, 1200);
  }

  function stopProgressAnimation() {
    if (progressTimer !== null) {
      clearInterval(progressTimer);
      progressTimer = null;
    }
  }

  function buildFormData() {
    const formData = new FormData();
    if (zipInput.files.length > 0) {
      formData.append("skill_zip", zipInput.files[0]);
    } else {
      for (const file of dirInput.files) {
        const relativePath = file.webkitRelativePath || file.name;
        formData.append("skill_files", file, relativePath);
      }
    }
    return formData;
  }

  function recommendationClass(recommendation) {
    return (
      "recommendation--" +
      recommendation.toLowerCase().trim().replace(/\s+/g, "-")
    );
  }

  function renderCapabilityRow(label, capabilities) {
    const row = document.createElement("tr");

    const labelCell = document.createElement("td");
    labelCell.textContent = label;
    row.appendChild(labelCell);

    const countCell = document.createElement("td");
    countCell.textContent = String(capabilities.length);
    row.appendChild(countCell);

    const namesCell = document.createElement("td");
    namesCell.textContent = capabilities.length > 0 ? capabilities.join(", ") : "none";
    row.appendChild(namesCell);

    return row;
  }

  function renderEvidence(evidence) {
    const container = document.createElement("div");
    for (const item of evidence) {
      const line = document.createElement("div");
      line.className = "evidence-item";
      const detailParts = Object.keys(item.detail || {})
        .sort()
        .map((key) => `${key}=${item.detail[key]}`);
      const detailText = detailParts.length > 0 ? ` [${detailParts.join(", ")}]` : "";
      line.textContent = `${item.source}: ${item.capability}${detailText}`;
      container.appendChild(line);
    }
    return container;
  }

  function renderFinding(finding) {
    const wrapper = document.createElement("div");
    wrapper.className = "finding";

    const header = document.createElement("div");
    header.className = "finding-header";

    const badge = document.createElement("span");
    badge.className = `severity-badge severity-${finding.severity}`;
    badge.textContent = finding.severity;
    header.appendChild(badge);

    const type = document.createElement("span");
    type.className = "finding-type";
    type.textContent = finding.finding_type;
    header.appendChild(type);

    if (finding.capability) {
      const capability = document.createElement("span");
      capability.className = "finding-capability";
      capability.textContent = finding.capability;
      header.appendChild(capability);
    }

    wrapper.appendChild(header);

    const explanation = document.createElement("p");
    explanation.textContent = finding.explanation;
    wrapper.appendChild(explanation);

    if (finding.policy_info) {
      const policyLine = document.createElement("p");
      const permitted = finding.policy_info.permitted ? "permitted" : "denied";
      policyLine.textContent = `Policy: ${finding.policy_info.policy_name} (${permitted})`;
      wrapper.appendChild(policyLine);
    }

    if (finding.evidence && finding.evidence.length > 0) {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "View Evidence";
      details.appendChild(summary);
      details.appendChild(renderEvidence(finding.evidence));
      wrapper.appendChild(details);
    }

    return wrapper;
  }

  function renderResult(assessment) {
    recommendationBanner.textContent = assessment.recommendation;
    recommendationBanner.className = "recommendation " + recommendationClass(assessment.recommendation);

    capabilityTableBody.innerHTML = "";
    capabilityTableBody.appendChild(renderCapabilityRow("Declared (D)", assessment.capabilities.declared));
    capabilityTableBody.appendChild(renderCapabilityRow("Static (S)", assessment.capabilities.static));
    capabilityTableBody.appendChild(renderCapabilityRow("Runtime (R)", assessment.capabilities.runtime));
    capabilityTableBody.appendChild(
      renderCapabilityRow("Policy-permitted (P)", assessment.capabilities.policy_permitted)
    );

    findingsList.innerHTML = "";
    if (assessment.findings.length === 0) {
      const none = document.createElement("p");
      none.textContent = "No findings.";
      findingsList.appendChild(none);
    } else {
      for (const finding of assessment.findings) {
        findingsList.appendChild(renderFinding(finding));
      }
    }

    limitationsList.innerHTML = "";
    for (const limitation of assessment.limitations) {
      const item = document.createElement("li");
      item.textContent = limitation;
      limitationsList.appendChild(item);
    }

    resultMeta.textContent =
      `Skill: ${assessment.skill_name} (v${assessment.skill_version}, id=${assessment.skill_id}) | ` +
      `policy=${assessment.policy_name} | artifact_digest=${assessment.artifact_digest} | ` +
      `generated_at=${assessment.generated_at}`;

    showOnly(resultPanel);
  }

  function renderError(message) {
    errorMessage.textContent = message;
    showOnly(errorPanel);
  }

  function resetToUpload() {
    zipInput.value = "";
    dirInput.value = "";
    updateSelectionSummary();
    showOnly(uploadPanel);
  }

  assessForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showOnly(progressPanel);
    startProgressAnimation();

    try {
      const response = await fetch("/api/assess", {
        method: "POST",
        body: buildFormData(),
      });
      const body = await response.json();

      if (!response.ok) {
        const detail = body && body.error ? body.error.message : `HTTP ${response.status}`;
        renderError(detail);
        return;
      }

      renderResult(body);
    } catch (err) {
      renderError(String(err));
    } finally {
      stopProgressAnimation();
    }
  });

  resetButton.addEventListener("click", resetToUpload);
  errorResetButton.addEventListener("click", resetToUpload);

  updateSelectionSummary();
})();
