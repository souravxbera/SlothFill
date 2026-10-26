(function () {
  const SKIP = new Set(["password", "hidden", "file", "submit", "button", "reset", "image", "checkbox"]);
  const GENERIC = new Set(["your answer", "your answer here", "short answer", "long answer"]);

  function textOf(node) {
    return (node && node.innerText ? node.innerText : "").replace(/\s+/g, " ").trim();
  }

  function clean(value) {
    return textOf({ innerText: value }).replace(/\s*\*\s*$/, "").trim();
  }

  function elementId(el) {
    if (!el.id) el.id = "slothfill-" + Math.random().toString(36).slice(2, 9);
    return el.id;
  }

  function labelledBy(el) {
    return (el.getAttribute("aria-labelledby") || "")
      .split(/\s+/)
      .map((id) => clean(textOf(document.getElementById(id))))
      .filter((part) => part && norm(part) !== "this is a required question");
  }

  function questionOf(el) {
    const fromAria = labelledBy(el);
    if (fromAria.length) return fromAria[0];
    const aria = clean(el.getAttribute("aria-label") || "");
    if (aria) return aria;
    const isChoice = el.getAttribute("type") === "radio" || el.getAttribute("role") === "radio";
    if (!isChoice && el.id) {
      const explicit = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (explicit) return clean(textOf(explicit));
    }
    if (!isChoice) {
      const wrap = el.closest("label");
      if (wrap && !wrap.querySelector("[role='radiogroup']")) return clean(textOf(wrap));
    }
    const item = el.closest("[role='listitem'], fieldset, [role='radiogroup']");
    if (item) {
      const heading = item.querySelector("[role='heading'], legend");
      if (heading && !el.contains(heading)) {
        const text = clean(textOf(heading));
        if (text) return text;
      }
    }
    return "";
  }

  function optionText(el) {
    const wrap = el.closest("label");
    if (wrap) {
      const copy = wrap.cloneNode(true);
      copy.querySelectorAll("[role='radio'], input").forEach((node) => node.remove());
      const text = clean(textOf(copy));
      if (text) return text;
    }
    return clean(el.getAttribute("data-value") || el.getAttribute("aria-label") || textOf(el));
  }

  function usefulPlaceholder(value) {
    const text = norm(value || "");
    return Boolean(text) && !GENERIC.has(text);
  }

  function collect() {
    const fields = [];
    const seenRadios = new Set();
    document.querySelectorAll("[role='radiogroup']").forEach((group) => {
      const radios = [...group.querySelectorAll("[role='radio']")];
      if (!radios.length) return;
      const label = questionOf(group);
      const options = radios.map(optionText).filter(Boolean);
      if (!label || !options.length) return;
      fields.push({
        id: elementId(group),
        label,
        name: "",
        placeholder: "",
        type: "radio",
        tag: "radio",
        options,
      });
    });
    document.querySelectorAll("input, textarea, select").forEach((el) => {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (el.tagName === "INPUT" && SKIP.has(type)) return;
      if (type === "radio") {
        const name = el.name || el.id;
        if (!name || seenRadios.has(name)) return;
        seenRadios.add(name);
        const group = [...document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`)];
        const label = questionOf(el);
        if (!label) return;
        fields.push({
          id: name,
          label,
          name,
          placeholder: "",
          type: "radio",
          tag: "radio",
          options: group.map((radio) => optionText(radio) || radio.value).filter(Boolean),
        });
        return;
      }
      const label = questionOf(el);
      const placeholder = el.placeholder || "";
      if (!label && !usefulPlaceholder(placeholder)) return;
      fields.push({
        id: elementId(el),
        label,
        name: el.name || "",
        placeholder: usefulPlaceholder(placeholder) ? placeholder : "",
        type: el.tagName === "SELECT" ? "select" : type,
        tag: el.tagName.toLowerCase(),
        options: el.tagName === "SELECT" ? [...el.options].map((option) => textOf(option)).filter(Boolean) : [],
      });
    });
    return fields;
  }

  function norm(value) {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  function mark(el, confidence) {
    const sure = confidence >= 0.9;
    el.dataset.slothfill = sure ? "sure" : "unsure";
    const box = el.closest("[role='listitem'], .field, fieldset") || el;
    box.classList.remove("is-sure", "is-unsure");
    box.classList.add(sure ? "is-sure" : "is-unsure");
  }

  function sameOption(hay, target) {
    return hay === target || hay.includes(target) || (hay && target.includes(hay));
  }

  function setValue(el, value) {
    if (el.tagName !== "INPUT" && el.tagName !== "TEXTAREA") return false;
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function fillChoice(name, value, confidence) {
    const target = norm(value);
    const host = document.getElementById(name);
    if (host && host.getAttribute("role") === "radiogroup") {
      const choice = [...host.querySelectorAll("[role='radio']")].find((radio) => sameOption(norm(optionText(radio)), target));
      if (!choice) return "unmatched";
      choice.click();
      mark(choice, confidence);
      return "filled";
    }
    const group = [...document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`)];
    if (!group.length) return "none";
    const choice = group.find((radio) => sameOption(norm(optionText(radio) || radio.value), target));
    if (!choice) return "unmatched";
    choice.checked = true;
    choice.dispatchEvent(new Event("input", { bubbles: true }));
    choice.dispatchEvent(new Event("change", { bubbles: true }));
    mark(choice, confidence);
    return "filled";
  }

  function apply(results) {
    let filled = 0;
    let unsure = 0;
    for (const result of results) {
      if (!result.value) continue;
      const outcome = fillChoice(result.id, result.value, result.confidence);
      if (outcome === "filled") {
        filled += 1;
        if (result.confidence < 0.9) unsure += 1;
        continue;
      }
      if (outcome === "unmatched") continue;
      const el = document.getElementById(result.id);
      if (!el || el.tagName === "BUTTON" || el.type === "submit") continue;
      if (el.tagName === "SELECT") {
        const target = norm(result.value);
        const option = [...el.options].find((item) => {
          const hay = norm(item.text || item.value);
          return hay === target || hay.includes(target) || (target.length > 2 && target.includes(hay));
        });
        if (!option) continue;
        el.value = option.value;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      } else if (!setValue(el, result.value)) {
        continue;
      }
      mark(el, result.confidence);
      filled += 1;
      if (result.confidence < 0.9) unsure += 1;
    }
    return { filled, unsure };
  }

  async function fill() {
    const status = document.getElementById("slothfill-status");
    const button = document.getElementById("slothfill");
    if (button) button.disabled = true;
    if (status) status.textContent = "Reading this form on this computer…";
    try {
      const response = await fetch("/map", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: location.href, fields: collect() }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const body = await response.json();
      const summary = apply(body.fields || []);
      if (status) {
        status.textContent = `Filled ${summary.filled} fields from this computer. ${summary.unsure} need a look. Empty fields are not in the profile. Nothing was submitted.`;
      }
    } catch (error) {
      if (status) {
        status.textContent = "The local SlothFill server is not running. Start it, then open this page from http://127.0.0.1:8787/demo/.";
      }
    } finally {
      if (button) button.disabled = false;
    }
  }

  function bind() {
    const form = document.querySelector("form");
    if (form) {
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const status = document.getElementById("slothfill-status");
        if (status) status.textContent = "Not submitted. SlothFill never sends the form.";
      });
    }
    const button = document.getElementById("slothfill");
    if (button) button.addEventListener("click", fill);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();
