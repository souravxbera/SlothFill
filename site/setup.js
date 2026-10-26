(function () {
  const status = document.getElementById("slothfill-status");
  const read = document.getElementById("read");
  const sample = document.getElementById("sample");
  const input = document.getElementById("pdfs");
  const folderInput = document.getElementById("folder");
  const listButton = document.getElementById("list");
  const readFolder = document.getElementById("read-folder");
  const pdfList = document.getElementById("pdf-list");
  const scan = document.getElementById("scan");
  const scanLabel = document.getElementById("scan-label");
  const scanBar = document.getElementById("scan-bar");
  let scanTimer = 0;

  function busy(isBusy, message) {
    read.disabled = isBusy;
    sample.disabled = isBusy;
    listButton.disabled = isBusy;
    readFolder.disabled = isBusy;
    if (message) status.textContent = message;
  }

  function showReport(report) {
    sessionStorage.setItem("slothfill-report", JSON.stringify(report || {}));
    location.href = "review.html";
  }

  async function finish(response) {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body.detail || "The PDF could not be read.";
      throw new Error(typeof detail === "string" ? detail : "The PDF could not be read.");
    }
    showReport(body.report);
  }

  function renderList(files) {
    pdfList.replaceChildren();
    let checked = 0;
    files.forEach((file) => {
      const item = document.createElement("li");
      const box = document.createElement("input");
      box.type = "checkbox";
      box.value = file.name;
      const canCheck = file.readable && checked < 20;
      box.checked = canCheck;
      box.disabled = !file.readable;
      if (canCheck) checked += 1;
      const name = document.createElement("span");
      name.textContent = file.reason ? `${file.name} (${file.reason})` : file.name;
      item.append(box, name);
      pdfList.append(item);
    });
    pdfList.hidden = false;
    readFolder.hidden = false;
  }

  function watch(job) {
    scan.hidden = false;
    scanLabel.textContent = "Starting the scan…";
    scanBar.max = 1;
    scanBar.value = 0;

    async function tick() {
      try {
        const response = await fetch("/ingest/jobs/" + job);
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          const detail = body.detail || "The scan status could not be read.";
          throw new Error(typeof detail === "string" ? detail : "The scan status could not be read.");
        }
        const total = body.total || 1;
        scanBar.max = total;
        if (body.state === "reading") {
          const place = body.index || 1;
          const name = body.file ? ` — ${body.file}` : "";
          scanLabel.textContent = `Reading ${place} of ${total}${name} — ${body.elapsed}s`;
          scanBar.value = Math.max(0, place - 1);
          return;
        }
        window.clearInterval(scanTimer);
        if (body.state === "done") {
          scanBar.value = total;
          scanLabel.textContent = `Read ${total} of ${total}. Opening the review.`;
          showReport(body.report);
          return;
        }
        scan.hidden = true;
        throw new Error(body.detail || "The folder could not be read.");
      } catch (error) {
        window.clearInterval(scanTimer);
        busy(false, error.message);
      }
    }

    tick();
    scanTimer = window.setInterval(tick, 1000);
  }

  document.getElementById("upload").addEventListener("submit", async (event) => {
    event.preventDefault();
    const files = [...input.files];
    if (!files.length) {
      status.textContent = "Choose a PDF first, or read the sample.";
      return;
    }
    if (files.some((file) => !file.name.toLowerCase().endsWith(".pdf"))) {
      status.textContent = "SlothFill reads PDFs only.";
      return;
    }
    const data = new FormData();
    files.forEach((file) => data.append("files", file));
    busy(true, "Reading on this computer. Gemma can take a few minutes on CPU.");
    try {
      await finish(await fetch("/ingest", { method: "POST", body: data }));
    } catch (error) {
      busy(false, error.message);
    }
  });

  sample.addEventListener("click", async () => {
    busy(true, "Reading the sample PDF on this computer. Gemma can take a few minutes on CPU.");
    try {
      await finish(await fetch("/ingest/sample", { method: "POST" }));
    } catch (error) {
      busy(false, error.message);
    }
  });

  document.getElementById("folder-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    busy(true, "Looking for PDFs in that folder.");
    try {
      const response = await fetch("/ingest/folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: folderInput.value }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body.detail || "That folder could not be read.";
        throw new Error(typeof detail === "string" ? detail : "That folder could not be read.");
      }
      if (!body.files.length) {
        pdfList.hidden = true;
        readFolder.hidden = true;
        busy(false, "No PDFs in that folder.");
        return;
      }
      renderList(body.files);
      busy(false, `Found ${body.files.length} PDF${body.files.length === 1 ? "" : "s"}. Uncheck any that should stay out, then read.`);
    } catch (error) {
      busy(false, error.message);
    }
  });

  readFolder.addEventListener("click", async () => {
    const names = [...pdfList.querySelectorAll("input:checked")].map((box) => box.value);
    if (!names.length) {
      status.textContent = "Select a PDF first.";
      return;
    }
    busy(true, "Gemma is reading the selected PDFs on this computer.");
    try {
      const response = await fetch("/ingest/folder/read", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: folderInput.value, names }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body.detail || "That folder could not be read.";
        throw new Error(typeof detail === "string" ? detail : "That folder could not be read.");
      }
      watch(body.job);
    } catch (error) {
      busy(false, error.message);
    }
  });
})();
