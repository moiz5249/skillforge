/**
 * app.js - SkillForge Developer Studio Controller
 * Utilitarian compilation, verification, and installation manager.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const sourceTypeSelect = document.getElementById("source-type-select");
  const skillNameInput = document.getElementById("skill-name-input");
  const sourceCodeEditor = document.getElementById("source-code-editor");
  const btnLoadSample = document.getElementById("btn-load-sample");
  const btnCompile = document.getElementById("btn-compile");
  const editorModeLabel = document.getElementById("editor-mode-label");

  const compScore = document.getElementById("comp-score");
  const btnInstallWorkspace = document.getElementById("btn-install-workspace");

  const viewSkillMd = document.getElementById("view-skill-md");
  const viewScriptCode = document.getElementById("view-script-code");
  const scriptFileSelect = document.getElementById("script-file-select");
  const auditStatusText = document.getElementById("audit-status-text");
  const auditTableBody = document.getElementById("audit-table-body");
  const treeViewContainer = document.getElementById("tree-view-container");

  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  let compiledData = null;

  // 1. Tab Switching
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      tabBtns.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // 2. Mode Change
  sourceTypeSelect.addEventListener("change", (e) => {
    editorModeLabel.textContent = e.target.value === "python" ? "python_ast" : "cli_help";
  });

  // 3. Load Sample Library
  btnLoadSample.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/sample-inputs");
      const data = await res.json();
      sourceCodeEditor.value = data.sample_code || "";
      skillNameInput.value = data.sample_name || "audio-dsp-toolkit";
      sourceTypeSelect.value = "python";
      editorModeLabel.textContent = "python_ast";
    } catch (err) {
      alert("Failed to load sample input: " + err.message);
    }
  });

  // 4. Compile Action
  btnCompile.addEventListener("click", async () => {
    const sourceCode = sourceCodeEditor.value.trim();
    const skillName = skillNameInput.value.trim() || "custom-skill";
    const sourceType = sourceTypeSelect.value;

    if (!sourceCode) {
      alert("Source specification cannot be empty.");
      return;
    }

    btnCompile.disabled = true;
    btnCompile.textContent = "Compiling Skill Package...";

    try {
      const response = await fetch("/api/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_code: sourceCode,
          skill_name: skillName,
          source_type: sourceType
        })
      });

      const data = await response.json();
      if (data.error) {
        alert("Compilation failed: " + data.error);
        return;
      }

      compiledData = data;
      renderCompilationResults(data);
    } catch (err) {
      alert("Network or compilation error: " + err.message);
    } finally {
      btnCompile.disabled = false;
      btnCompile.textContent = "Compile Agent Skill Package";
    }
  });

  function renderCompilationResults(data) {
    // Audit score
    const report = data.validation_report || {};
    compScore.textContent = `${report.score || 100}/100 (${report.compliant ? "PASS" : "FAIL"})`;
    compScore.style.color = report.compliant ? "var(--status-pass)" : "var(--status-fail)";

    btnInstallWorkspace.disabled = false;

    // View SKILL.md
    viewSkillMd.textContent = data.skill_md || "";

    // Populate scripts
    scriptFileSelect.innerHTML = "";
    const scripts = data.scripts || {};
    const scriptNames = Object.keys(scripts);
    if (scriptNames.length > 0) {
      scriptNames.forEach(name => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        scriptFileSelect.appendChild(opt);
      });
      viewScriptCode.textContent = scripts[scriptNames[0]];
    } else {
      viewScriptCode.textContent = "# No runner scripts generated.";
    }

    // Audit checklist
    auditStatusText.textContent = `Status: ${report.compliant ? "100% Agent Skill Open Standard Compliant" : "Validation Failed"}. Evaluated ${report.checks ? report.checks.length : 0} rules.`;
    auditTableBody.innerHTML = "";
    if (report.checks && report.checks.length > 0) {
      report.checks.forEach(chk => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${chk.name}</strong></td>
          <td><span class="${chk.passed ? 'status-pass-tag' : 'status-fail-tag'}">${chk.passed ? '[PASS]' : '[FAIL]'}</span></td>
          <td style="color:var(--text-muted);">${chk.message}</td>
        `;
        auditTableBody.appendChild(tr);
      });
    }

    // Tree view
    treeViewContainer.innerHTML = `
      <div class="tree-item"><span class="tree-dir">📁 ${data.skill_name}/</span></div>
      <div class="tree-item">&nbsp;&nbsp;├── 📄 SKILL.md</div>
      <div class="tree-item">&nbsp;&nbsp;├── <span class="tree-dir">📁 scripts/</span></div>
      ${scriptNames.map(s => `      <div class="tree-item">&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;├── ⚙️ ${s}</div>`).join("\n")}
      <div class="tree-item">&nbsp;&nbsp;├── <span class="tree-dir">📁 examples/</span></div>
      <div class="tree-item">&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;└── 🧪 sample_usage.json</div>
      <div class="tree-item">&nbsp;&nbsp;└── <span class="tree-dir">📁 references/</span></div>
      <div class="tree-item">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── 📚 api_reference.md</div>
    `;
  }

  // Script Selector Change
  scriptFileSelect.addEventListener("change", (e) => {
    if (compiledData && compiledData.scripts && compiledData.scripts[e.target.value]) {
      viewScriptCode.textContent = compiledData.scripts[e.target.value];
    }
  });

  // Install to workspace
  btnInstallWorkspace.addEventListener("click", async () => {
    if (!compiledData) return;
    btnInstallWorkspace.disabled = true;
    btnInstallWorkspace.textContent = "Installing...";

    try {
      const res = await fetch("/api/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_name: compiledData.skill_name,
          target_type: "workspace"
        })
      });
      const data = await res.json();
      if (data.success) {
        btnInstallWorkspace.textContent = "Installed [OK]";
        setTimeout(() => {
          btnInstallWorkspace.textContent = "Install to .agents/skills";
          btnInstallWorkspace.disabled = false;
        }, 2000);
      } else {
        alert("Installation failed: " + data.error);
        btnInstallWorkspace.disabled = false;
        btnInstallWorkspace.textContent = "Install to .agents/skills";
      }
    } catch (err) {
      alert("Error: " + err.message);
      btnInstallWorkspace.disabled = false;
    }
  });

  // Load sample on init
  btnLoadSample.click();
});
