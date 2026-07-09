/**
 * GateFlow — Frontend Application JS Control Script
 * Controls interactive widgets, tab navigation, theme toggling, and asynchronous API calls.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const themeToggle = document.getElementById("theme-toggle");
  const assistForm = document.getElementById("assist-form");
  const languageSelect = document.getElementById("language-select");
  const locationSelect = document.getElementById("location-select");
  const sectionSelect = document.getElementById("section-select");
  const arrivalModeSelect = document.getElementById("arrival-mode-select");
  const kickoffSlider = document.getElementById("kickoff-slider");
  const kickoffValue = document.getElementById("kickoff-value");
  const questionInput = document.getElementById("question-input");
  const submitBtn = document.getElementById("submit-btn");
  const responseRegion = document.getElementById("response-region");
  const systemStatusDot = document.getElementById("system-status-dot");
  const systemStatusText = document.getElementById("system-status-text");

  // Tab Elements
  const tabGates = document.getElementById("tab-gates");
  const tabTransport = document.getElementById("tab-transport");
  const panelGates = document.getElementById("panel-gates");
  const panelTransport = document.getElementById("panel-transport");
  const gatesStatusList = document.getElementById("gates-status-list");
  const transportAdviceList = document.getElementById("transport-advice-list");

  // Accessibility Need Checkboxes
  const needMobility = document.getElementById("need-mobility");
  const needVisual = document.getElementById("need-visual");
  const needHearing = document.getElementById("need-hearing");

  // Theme Management
  const currentTheme = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", currentTheme);

  themeToggle.addEventListener("click", () => {
    const theme = document.documentElement.getAttribute("data-theme");
    const newTheme = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
  });

  // Kickoff Slider update
  function updateSliderDisplay() {
    const minutes = parseInt(kickoffSlider.value, 10);
    if (minutes === 0) {
      kickoffValue.textContent = "Kickoff Now";
    } else if (minutes < 0) {
      const positiveMinutes = Math.abs(minutes);
      if (positiveMinutes > 105) {
        kickoffValue.textContent = `${positiveMinutes}m post-kickoff (Egress)`;
      } else {
        kickoffValue.textContent = `${positiveMinutes}m post-kickoff`;
      }
    } else {
      kickoffValue.textContent = `${minutes} minutes to kickoff`;
    }
  }

  kickoffSlider.addEventListener("input", () => {
    updateSliderDisplay();
    refreshLiveWidgets();
  });

  // Checkbox interactions trigger live updates
  needMobility.addEventListener("change", refreshLiveWidgets);
  needVisual.addEventListener("change", refreshLiveWidgets);
  needHearing.addEventListener("change", refreshLiveWidgets);

  // Focus utility: return focus to question input
  function resetFocus() {
    questionInput.focus();
  }

  // Helper: map congestion level to indicators and pattern shapes
  const CONGESTION_PATTERNS = {
    low: { text: "Low", pattern: "●○○" },
    medium: { text: "Medium", pattern: "●●○" },
    high: { text: "High", pattern: "●●●" },
    critical: { text: "Critical", pattern: "⚠️ ●●●" },
  };

  // Helper: escape/safe render dynamic values
  function createSafeText(text) {
    return document.createTextNode(text);
  }

  // Dynamic status loaders
  async function checkSystemHealth() {
    try {
      const res = await fetch("/healthz");
      if (res.ok) {
        const data = await res.json();
        systemStatusDot.className = "status-dot online";
        systemStatusText.textContent = `Live Copilot Engine Ready (${data.llm === "live" ? "Gemini online" : "template fallback"})`;
      } else {
        systemStatusDot.className = "status-dot offline";
        systemStatusText.textContent = "Offline Mode";
      }
    } catch {
      systemStatusDot.className = "status-dot offline";
      systemStatusText.textContent = "Disconnected";
    }
  }

  async function loadGatesStatus(minutes) {
    try {
      const res = await fetch(`/api/venue/gates?minutes_to_kickoff=${minutes}`);
      if (!res.ok) throw new Error("API error");
      const gates = await res.json();
      
      gatesStatusList.innerHTML = ""; // Clear loader safely (no user inputs here)

      gates.forEach(gate => {
        const li = document.createElement("li");
        li.className = "status-item";

        const left = document.createElement("div");
        left.className = "item-left";
        const title = document.createElement("span");
        title.className = "item-title";
        title.appendChild(createSafeText(gate.name));
        const sub = document.createElement("span");
        sub.className = "item-sub";
        
        let subText = `Step-free: ${gate.step_free ? "Yes" : "No"}`;
        if (gate.sensory_friendly) subText += " | 🧘 Sensory Quiet";
        if (gate.audio_cues) subText += " | 🔊 Audio Cues";
        sub.appendChild(createSafeText(subText));

        left.appendChild(title);
        left.appendChild(sub);

        const right = document.createElement("div");
        right.className = "item-right";
        const badge = document.createElement("span");
        const patternData = CONGESTION_PATTERNS[gate.congestion] || { text: gate.congestion, pattern: "" };
        badge.className = `congestion-badge ${gate.congestion}`;
        badge.appendChild(createSafeText(`${patternData.pattern} ${patternData.text}`));
        right.appendChild(badge);

        li.appendChild(left);
        li.appendChild(right);
        gatesStatusList.appendChild(li);
      });
    } catch {
      gatesStatusList.innerHTML = "";
      const errLi = document.createElement("li");
      errLi.className = "loading";
      errLi.appendChild(createSafeText("Failed to load gate congestion metrics."));
      gatesStatusList.appendChild(errLi);
    }
  }

  async function loadTransportAdvice(minutes, accessibilityList) {
    try {
      let url = `/api/transport/advice?minutes_to_kickoff=${minutes}`;
      accessibilityList.forEach(need => {
        url += `&accessibility_needs=${need}`;
      });

      const res = await fetch(url);
      if (!res.ok) throw new Error("API error");
      const data = await res.json();

      transportAdviceList.innerHTML = ""; // Clear loader safely

      data.options.forEach(opt => {
        const li = document.createElement("li");
        li.className = "status-item";

        const left = document.createElement("div");
        left.className = "item-left";
        const title = document.createElement("span");
        title.className = "item-title";
        title.appendChild(createSafeText(opt.name));
        const sub = document.createElement("span");
        sub.className = "item-sub";
        
        const subText = `ETA: ${opt.eta_minutes.toFixed(0)}m | Wait Time: ${opt.wait_minutes.toFixed(0)}m`;
        sub.appendChild(createSafeText(subText));

        left.appendChild(title);
        left.appendChild(sub);

        const right = document.createElement("div");
        right.className = "item-right";
        
        const timeBadge = document.createElement("span");
        timeBadge.className = "badge";
        timeBadge.appendChild(createSafeText(`${opt.total_travel_time_minutes.toFixed(0)} mins total`));

        const badge = document.createElement("span");
        const patternData = CONGESTION_PATTERNS[opt.congestion] || { text: opt.congestion, pattern: "" };
        badge.className = `congestion-badge ${opt.congestion}`;
        badge.appendChild(createSafeText(`${patternData.pattern} ${patternData.text}`));

        right.appendChild(timeBadge);
        right.appendChild(badge);

        li.appendChild(left);
        li.appendChild(right);
        transportAdviceList.appendChild(li);
      });
    } catch {
      transportAdviceList.innerHTML = "";
      const errLi = document.createElement("li");
      errLi.className = "loading";
      errLi.appendChild(createSafeText("Failed to load transportation schedule advice."));
      transportAdviceList.appendChild(errLi);
    }
  }

  function getSelectedAccessibilityNeeds() {
    const list = [];
    if (needMobility.checked) list.push("mobility");
    if (needVisual.checked) list.push("visual");
    if (needHearing.checked) list.push("hearing");
    return list;
  }

  function refreshLiveWidgets() {
    const minutes = parseInt(kickoffSlider.value, 10);
    const needs = getSelectedAccessibilityNeeds();
    loadGatesStatus(minutes);
    loadTransportAdvice(minutes, needs);
  }

  // Form submit route calculator
  assistForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!locationSelect.value || !sectionSelect.value) {
      alert("Please select both your current location and ticket section.");
      return;
    }

    // Set aria-busy="true"
    responseRegion.setAttribute("aria-busy", "true");
    submitBtn.disabled = true;
    submitBtn.textContent = "Calculating dynamics...";

    // Build payload
    const payload = {
      language: languageSelect.value,
      arrival_mode: arrivalModeSelect.value,
      current_location: locationSelect.value,
      ticket_section: sectionSelect.value,
      accessibility_needs: getSelectedAccessibilityNeeds(),
      minutes_to_kickoff: parseInt(kickoffSlider.value, 10),
      question: questionInput.value.trim() || null,
    };

    try {
      const res = await fetch("/api/assist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": uuidv4(),
        },
        body: JSON.stringify(payload),
      });

      // Clear response area safely
      responseRegion.innerHTML = "";

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Server failed to calculate route.");
      }

      const data = await res.json();

      // Scope language attribute to the guidance text only (WCAG 3.1.2)
      // The surrounding UI stays in English — only the answer text changes language
      const guidanceText = document.getElementById("guidance-text");
      if (guidanceText) {
          guidanceText.setAttribute("lang", data.language || "en");
      }

      // Create Guidance Bubble
      const bubble = document.createElement("div");
      bubble.className = "guidance-bubble";

      const gTitle = document.createElement("div");
      gTitle.className = "guidance-title";
      gTitle.appendChild(createSafeText("Copilot Directions"));
      
      const gText = document.createElement("p");
      gText.className = "guidance-text";
      gText.id = "guidance-text";
      gText.appendChild(createSafeText(data.answer));

      bubble.appendChild(gTitle);
      bubble.appendChild(gText);

      // Create Decision metadata card
      const card = document.createElement("div");
      card.className = "decision-card";

      const meta = document.createElement("div");
      meta.className = "decision-meta";

      const gateMeta = document.createElement("span");
      gateMeta.className = "meta-item";
      gateMeta.appendChild(createSafeText(`Recommended Gate: ${data.decision.recommended_gate.toUpperCase()}`));
      
      const urgencyMeta = document.createElement("span");
      urgencyMeta.className = "meta-item";
      urgencyMeta.appendChild(createSafeText(`Urgency: ${data.decision.urgency_tier}`));

      const modeMeta = document.createElement("span");
      modeMeta.className = "meta-item";
      const tags = data.decision.accessibility_mode.join(", ") || "standard";
      modeMeta.appendChild(createSafeText(`Access Mode: ${tags}`));

      const modelMeta = document.createElement("span");
      modelMeta.className = "meta-item";
      modelMeta.appendChild(createSafeText(data.decision.used_llm ? "Gemini Phrased" : "Template Math"));

      meta.appendChild(gateMeta);
      meta.appendChild(urgencyMeta);
      meta.appendChild(modeMeta);
      meta.appendChild(modelMeta);

      const pathTitle = document.createElement("h4");
      pathTitle.className = "form-group label"; // Re-use label styling
      pathTitle.style.marginBottom = "10px";
      pathTitle.appendChild(createSafeText("Navigation Steps"));

      const pathDiv = document.createElement("div");
      pathDiv.className = "route-path";

      data.decision.route_steps.forEach((step, idx, arr) => {
        const stepDiv = document.createElement("div");
        let stepClass = "path-step";
        if (idx === 0) stepClass += " start";
        else if (idx === arr.length - 1) stepClass += " end";
        else if (step.startsWith("gate_")) stepClass += " gate";
        
        stepDiv.className = stepClass;
        
        const readableStep = step.replace(/_/g, " ").toUpperCase();
        stepDiv.appendChild(createSafeText(readableStep));

        pathDiv.appendChild(stepDiv);
      });

      card.appendChild(meta);
      card.appendChild(pathTitle);
      card.appendChild(pathDiv);

      responseRegion.appendChild(bubble);
      responseRegion.appendChild(card);

    } catch (err) {
      responseRegion.innerHTML = "";
      const errorDiv = document.createElement("div");
      errorDiv.className = "guidance-bubble";
      errorDiv.setAttribute("role", "alert");
      errorDiv.style.borderLeftColor = "var(--danger)";
      
      const errTitle = document.createElement("div");
      errTitle.className = "guidance-title";
      errTitle.style.color = "var(--danger)";
      errTitle.appendChild(createSafeText("Route Calculation Error"));

      const errText = document.createElement("p");
      errText.className = "guidance-text";
      errText.appendChild(createSafeText(err.message));

      errorDiv.appendChild(errTitle);
      errorDiv.appendChild(errText);
      responseRegion.appendChild(errorDiv);
    } finally {
      responseRegion.setAttribute("aria-busy", "false");
      submitBtn.disabled = false;
      submitBtn.textContent = "Calculate Best Route";
      resetFocus();
    }
  });

  // Tab keyboard & click navigation
  function switchTab(selectedTab, targetPanel, otherTab, otherPanel) {
    selectedTab.setAttribute("aria-selected", "true");
    selectedTab.setAttribute("tabindex", "0");
    selectedTab.setAttribute("aria-current", "page");
    targetPanel.classList.remove("hidden");

    otherTab.setAttribute("aria-selected", "false");
    otherTab.setAttribute("tabindex", "-1");
    otherTab.removeAttribute("aria-current");
    otherPanel.classList.add("hidden");

    selectedTab.focus();
  }

  tabGates.addEventListener("click", () => {
    switchTab(tabGates, panelGates, tabTransport, panelTransport);
  });

  tabTransport.addEventListener("click", () => {
    switchTab(tabTransport, panelTransport, tabGates, panelGates);
  });

  // Keyboard-accessible tab navigation with roving tabindex (WAI-ARIA Tabs pattern)
  const tabList = [tabGates, tabTransport];
  tabList.forEach((tab, idx) => {
    tab.addEventListener("keydown", (e) => {
      let targetIdx = null;
      if (e.key === "ArrowRight") {
        targetIdx = (idx + 1) % tabList.length;
      } else if (e.key === "ArrowLeft") {
        targetIdx = (idx - 1 + tabList.length) % tabList.length;
      }

      if (targetIdx !== null) {
        e.preventDefault();
        const nextTab = tabList[targetIdx];
        if (nextTab === tabGates) {
          switchTab(tabGates, panelGates, tabTransport, panelTransport);
        } else {
          switchTab(tabTransport, panelTransport, tabGates, panelGates);
        }
      }
    });
  });

  // UUID generator for Request ID
  function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
  }

  // Bootstrapping
  checkSystemHealth();
  updateSliderDisplay();
  refreshLiveWidgets();
});
