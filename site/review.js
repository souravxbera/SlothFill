(function () {
  const status = document.getElementById("slothfill-status");
  const keys = ["name", "father_name", "dob", "gender", "phone", "email", "pan", "aadhaar_masked", "category", "nationality"];
  const addressKeys = ["line1", "line2", "city", "state", "pincode", "country"];

  function edu(profile, level) {
    return (profile.education || []).find((row) => String(row.level) === level) || {};
  }

  function fill(profile) {
    keys.forEach((key) => {
      document.getElementById(key).value = profile[key] || "";
    });
    addressKeys.forEach((key) => {
      document.getElementById(key).value = (profile.address && profile.address[key]) || "";
    });
    ["10", "12"].forEach((level) => {
      const row = edu(profile, level);
      document.getElementById("board" + level).value = row.board || "";
      document.getElementById("year" + level).value = row.year || "";
      document.getElementById("marks" + level).value = row.marks || "";
      document.getElementById("school" + level).value = row.institution || "";
    });
  }

  function collect() {
    const profile = { address: {}, education: [] };
    keys.forEach((key) => {
      profile[key] = document.getElementById(key).value.trim();
    });
    addressKeys.forEach((key) => {
      profile.address[key] = document.getElementById(key).value.trim();
    });
    ["10", "12"].forEach((level) => {
      const row = {
        level,
        board: document.getElementById("board" + level).value.trim(),
        year: document.getElementById("year" + level).value.trim(),
        marks: document.getElementById("marks" + level).value.trim(),
        institution: document.getElementById("school" + level).value.trim(),
      };
      if (row.board || row.year || row.marks || row.institution) profile.education.push(row);
    });
    return profile;
  }

  document.getElementById("review").addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = "Saving on this computer…";
    try {
      const response = await fetch("/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collect()),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not save.");
      fill(body.profile);
      status.textContent = "Saved on this computer. The next form can use it. Nothing was sent away.";
    } catch (error) {
      status.textContent = error.message;
    }
  });

  const savedReport = sessionStorage.getItem("slothfill-report");
  if (savedReport) {
    try {
      const report = JSON.parse(savedReport);
      const lines = (report.files || []).map((file) => {
        const how = file.mode === "vision" ? "scan, read with Gemma vision" : "text layer, then Gemma";
        const conflicts = (file.conflicts || []).length ? ` Disagreed on ${file.conflicts.join(", ")}.` : "";
        return `${file.file}: ${how}.${conflicts}`;
      });
      document.getElementById("report").textContent = lines.join(" ");
    } catch (error) {
      document.getElementById("report").textContent = "";
    }
  }

  fetch("/profile")
    .then((response) => response.json())
    .then((body) => {
      fill(body.profile || {});
      document.getElementById("source").textContent = body.source === "local"
        ? "These values are saved on this computer. Correct anything Gemma got wrong, then save."
        : "This is the built-in sample, not a PDF you uploaded. Read a PDF from Setup, or edit these values and save.";
    })
    .catch(() => {
      status.textContent = "The local server is not running.";
    });
})();
