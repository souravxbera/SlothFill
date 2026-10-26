chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "map") return;
  fetch("http://127.0.0.1:8787/map", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: message.url, fields: message.fields }),
  })
    .then((response) => {
      if (!response.ok) throw new Error("status " + response.status);
      return response.json();
    })
    .then((body) => sendResponse(body))
    .catch(() => {
      sendResponse({ error: "The local SlothFill server is not running on this computer." });
    });
  return true;
});
