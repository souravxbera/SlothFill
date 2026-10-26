const button = document.getElementById("fill");
const status = document.getElementById("status");

function send(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      const err = chrome.runtime.lastError;
      if (err) reject(new Error(err.message));
      else resolve(response);
    });
  });
}

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "Filling from this computer…";
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || tab.id === undefined) throw new Error("No active tab.");
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
    const result = await send(tab.id, { type: "fill" });
    if (!result || result.error) throw new Error((result && result.error) || "This page did not answer.");
    status.textContent = `Filled ${result.filled}. ${result.unsure} need a look. Nothing was submitted.`;
  } catch (error) {
    const message = String(error.message || error);
    status.textContent = message.includes("Cannot access") || message.includes("cannot be scripted")
      ? "Chrome pages can't be filled. Open a normal form."
      : message;
  } finally {
    button.disabled = false;
  }
});
