/**
 * Popup script — all UI logic for the Chrome extension.
 *
 * Handles three tabs: Search, Surveillance, Rank.
 * All data goes through the FastAPI backend at localhost:8000.
 */

const API_BASE = "http://localhost:8000/api";

// ─── Helper: call the backend API ────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: {} };

  if (body instanceof FormData) {
    opts.body = body; // browser sets Content-Type with boundary automatically
  } else if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }

  const resp = await fetch(`${API_BASE}${path}`, opts);

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }

  if (resp.status === 204) return null; // no content (e.g. DELETE)
  return resp.json();
}

// ─── Helper: get the current tab's HTML via the content script ───

function getPageHTML() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]) return reject(new Error("No active tab"));
      chrome.tabs.sendMessage(tabs[0].id, { action: "getPageHTML" }, (response) => {
        if (chrome.runtime.lastError) {
          return reject(new Error("Cannot access this page. Try refreshing."));
        }
        resolve(response);
      });
    });
  });
}

// ─── Helper: show a message in a results div ────────────────────

function showMessage(elementId, text, type = "info") {
  const el = document.getElementById(elementId);
  const cls = type === "error" ? "error" : type === "success" ? "success" : "hint";
  el.innerHTML = `<p class="${cls}">${text}</p>`;
}

// ─── Tab switching ──────────────────────────────────────────────

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    // Deactivate all tabs and content
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    // Activate clicked tab and its content
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab).classList.add("active");
  });
});

// ─── Tab 1: Search/Scrape ───────────────────────────────────────

document.getElementById("search-btn").addEventListener("click", async () => {
  const titlesText = document.getElementById("search-titles").value.trim();
  if (!titlesText) return showMessage("search-results", "Enter at least one job title.", "error");

  const titles = titlesText.split("\n").map((t) => t.trim()).filter(Boolean);
  const btn = document.getElementById("search-btn");

  try {
    btn.disabled = true;
    btn.textContent = "Searching...";
    showMessage("search-results", "Grabbing page HTML and searching...");

    // Get the current page's HTML from the content script
    const page = await getPageHTML();

    // Send to backend for scraping + LLM matching
    const data = await api("POST", "/scrape", {
      url: page.url,
      titles: titles,
      page_html: page.html,
    });

    // Render results
    const resultsDiv = document.getElementById("search-results");
    if (!data.matches.length) {
      resultsDiv.innerHTML = '<p class="hint">No matching jobs found on this page.</p>';
      return;
    }

    resultsDiv.innerHTML = data.matches
      .map(
        (job) => `
        <div class="job-card">
          <div class="title">${job.title}</div>
          <div class="meta">
            Match: ${job.relevance}
            ${job.url ? `· <a href="${job.url}" target="_blank">View</a>` : ""}
          </div>
        </div>`
      )
      .join("");
  } catch (err) {
    showMessage("search-results", err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Search This Page";
  }
});

// ─── Tab 2: Surveillance ───────────────────────────────────────

// Load companies on tab open
async function loadCompanies() {
  try {
    const companies = await api("GET", "/companies");
    const listDiv = document.getElementById("company-list");

    if (!companies.length) {
      listDiv.innerHTML = '<p class="hint">No companies tracked yet.</p>';
      return;
    }

    listDiv.innerHTML = companies
      .map(
        (c) => `
        <div class="company-row">
          <span class="name">${c.name}</span>
          <span class="hint">${c.last_checked_at ? "Checked: " + new Date(c.last_checked_at).toLocaleDateString() : "Never checked"}</span>
          <button class="delete-btn" data-id="${c.id}" title="Remove">✕</button>
        </div>`
      )
      .join("");

    // Wire up delete buttons
    listDiv.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await api("DELETE", `/companies/${btn.dataset.id}`);
        loadCompanies();
      });
    });
  } catch (err) {
    showMessage("company-list", err.message, "error");
  }
}

// Add current page as a tracked company
document.getElementById("add-company-btn").addEventListener("click", async () => {
  const name = document.getElementById("company-name").value.trim();
  if (!name) return showMessage("company-list", "Enter a company name.", "error");

  try {
    const page = await getPageHTML();
    await api("POST", "/companies", { name, career_url: page.url });
    document.getElementById("company-name").value = "";
    loadCompanies();
  } catch (err) {
    showMessage("company-list", err.message, "error");
  }
});

// Check all tracked companies for new jobs
document.getElementById("check-btn").addEventListener("click", async () => {
  const btn = document.getElementById("check-btn");

  try {
    btn.disabled = true;
    btn.textContent = "Checking...";
    showMessage("surveillance-results", "Scraping all tracked career pages...");

    const data = await api("POST", "/surveillance/check");

    const resultsDiv = document.getElementById("surveillance-results");
    if (!data.new_jobs.length) {
      resultsDiv.innerHTML = '<p class="success">No new jobs found. Everything is up to date.</p>';
    } else {
      resultsDiv.innerHTML =
        `<p class="success">Found ${data.new_jobs.length} new job(s)!</p>` +
        data.new_jobs
          .map(
            (job) => `
          <div class="job-card">
            <div class="title">${job.title}</div>
            <div class="meta">
              ${job.company}
              ${job.posted_at ? "· " + new Date(job.posted_at).toLocaleDateString() : ""}
              ${job.url ? `· <a href="${job.url}" target="_blank">View</a>` : ""}
            </div>
          </div>`
          )
          .join("");
    }

    loadCompanies(); // refresh last_checked_at timestamps
  } catch (err) {
    showMessage("surveillance-results", err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Check All for New Jobs";
  }
});

// ─── Tab 3: Rank ───────────────────────────────────────────────

// Upload resume
document.getElementById("upload-btn").addEventListener("click", async () => {
  const fileInput = document.getElementById("resume-file");
  if (!fileInput.files.length) return showMessage("resume-status", "Select a file first.", "error");

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const data = await api("POST", "/resume", formData);
    showMessage("resume-status", `Resume uploaded: ${data.filename}`, "success");
  } catch (err) {
    showMessage("resume-status", err.message, "error");
  }
});

// Rank stored jobs against resume
document.getElementById("rank-btn").addEventListener("click", async () => {
  const btn = document.getElementById("rank-btn");

  try {
    btn.disabled = true;
    btn.textContent = "Ranking...";
    showMessage("rank-results", "Analyzing jobs against your resume...");

    const ranked = await api("GET", "/rank");

    const resultsDiv = document.getElementById("rank-results");
    if (!ranked.length) {
      resultsDiv.innerHTML = '<p class="hint">No jobs to rank.</p>';
      return;
    }

    resultsDiv.innerHTML = ranked
      .map(
        (job, i) => `
        <div class="job-card">
          <div class="title">
            #${i + 1} <span class="score">${job.combined_score}</span> — ${job.title}
          </div>
          <div class="meta">
            ${job.company} · Score: ${job.score}/10
            ${job.posted_at ? "· " + new Date(job.posted_at).toLocaleDateString() : ""}
            ${job.url ? `· <a href="${job.url}" target="_blank">View</a>` : ""}
          </div>
          <div class="meta">${job.reason}</div>
        </div>`
      )
      .join("");
  } catch (err) {
    showMessage("rank-results", err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Rank My Jobs";
  }
});

// ─── Tab 4: Settings ──────────────────────────────────────────

const providerSelect = document.getElementById("llm-provider");
const ollamaModelLabel = document.getElementById("ollama-model-label");
const apiKeyLabel = document.getElementById("api-key-label");

// Show/hide fields based on provider selection
providerSelect.addEventListener("change", () => {
  const isOllama = providerSelect.value === "ollama";
  ollamaModelLabel.style.display = isOllama ? "block" : "none";
  apiKeyLabel.style.display = isOllama ? "none" : "block";
});

// Save settings
document.getElementById("save-settings-btn").addEventListener("click", async () => {
  const body = {
    llm_provider: providerSelect.value,
    api_key: document.getElementById("api-key").value || null,
    ollama_model: document.getElementById("ollama-model").value || null,
  };

  try {
    await api("PUT", "/settings", body);
    showMessage("settings-status", "Settings saved!", "success");
  } catch (err) {
    showMessage("settings-status", err.message, "error");
  }
});

// ─── Init: load companies on popup open ─────────────────────────

loadCompanies();
