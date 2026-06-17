const messagesEl = document.querySelector("#messages");
const formEl = document.querySelector("#chatForm");
const inputEl = document.querySelector("#messageInput");
const sendBtn = document.querySelector("#sendBtn");
const statusEl = document.querySelector("#status");
const toolsListEl = document.querySelector("#toolsList");
const toolCallsEl = document.querySelector("#toolCalls");
const jsonOutputEl = document.querySelector("#jsonOutput");
const structuredEl = document.querySelector("#structured");
const threadIdEl = document.querySelector("#threadId");

const text = {
  example:
    "\u6211\u4ece\u4e0a\u6d77\u8679\u6865\u7ad9\u53bb\u5916\u6ee9\uff0c\u5e2e\u6211\u89c4\u5212\u5730\u94c1\u548c\u9a7e\u8f66\u65b9\u6848\uff0c\u5e76\u641c\u7d22\u7f51\u9875\u6574\u7406\u5916\u6ee9\u5f00\u653e\u65f6\u95f4\u548c\u6e38\u73a9\u6ce8\u610f\u4e8b\u9879\u3002",
  none: "\u6682\u65e0",
  loading: "\u52a0\u8f7d\u4e2d...",
  noTools: "\u6682\u65e0\u5de5\u5177",
  toolsFailed: "\u5de5\u5177\u52a0\u8f7d\u5931\u8d25\uff1a",
  thinking: "\u6d41\u5f0f\u751f\u6210\u4e2d",
  clearing: "\u6b63\u5728\u6e05\u7406",
  done: "\u5b8c\u6210",
  error: "\u51fa\u9519",
  requestFailed: "\u8bf7\u6c42\u5931\u8d25\uff1a",
  completed: "\u5df2\u5b8c\u6210\u3002",
  user: "\u4f60",
  newThread: "\u5df2\u5207\u6362\u5230\u65b0\u4f1a\u8bdd\u3002",
  threadCleared: "\u5df2\u6e05\u7a7a\u5f53\u524d\u7ebf\u7a0b\u7684\u8bb0\u5fc6\u3002",
};

function setStatus(value) {
  statusEl.textContent = value;
}

function addMessage(role, value = "") {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? text.user : "A";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  const p = document.createElement("p");
  p.textContent = value;
  bubble.appendChild(p);

  article.appendChild(avatar);
  article.appendChild(bubble);
  messagesEl.appendChild(article);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return p;
}

function renderChips(container, items) {
  container.innerHTML = "";
  if (!items || items.length === 0) {
    container.classList.add("empty");
    container.textContent = text.none;
    return;
  }

  container.classList.remove("empty");
  for (const item of items) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = item;
    container.appendChild(chip);
  }
}

async function loadTools() {
  toolsListEl.textContent = text.loading;
  try {
    const response = await fetch("/tools");
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    toolsListEl.innerHTML = "";
    for (const tool of data.tools || []) {
      const item = document.createElement("span");
      item.textContent = tool;
      toolsListEl.appendChild(item);
    }
    if (!data.tools?.length) {
      toolsListEl.textContent = text.noTools;
    }
  } catch (error) {
    toolsListEl.textContent = `${text.toolsFailed}${error.message}`;
  }
}

function parseSseEvents(buffer) {
  const events = [];
  let cursor = 0;

  while (true) {
    const boundary = buffer.indexOf("\n\n", cursor);
    if (boundary === -1) {
      break;
    }

    const raw = buffer.slice(cursor, boundary);
    cursor = boundary + 2;
    let eventName = "message";
    const dataLines = [];

    for (const line of raw.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (dataLines.length) {
      events.push({ eventName, data: JSON.parse(dataLines.join("\n")) });
    }
  }

  return { events, rest: buffer.slice(cursor) };
}

async function sendMessage(message) {
  setStatus(text.thinking);
  sendBtn.disabled = true;
  addMessage("user", message);
  const assistantText = addMessage("assistant", "");
  const toolCalls = [];
  let streamedText = "";

  renderChips(toolCallsEl, []);
  jsonOutputEl.textContent = "{}";

  try {
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        thread_id: threadIdEl.value.trim() || "web-demo",
        structured: structuredEl.checked,
      }),
    });

    if (!response.ok || !response.body) {
      const body = await response.text();
      throw new Error(body || response.statusText);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      const parsed = parseSseEvents(buffer);
      buffer = parsed.rest;

      for (const item of parsed.events) {
        if (item.eventName === "token") {
          streamedText += item.data.text || "";
          assistantText.textContent = streamedText;
          messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (item.eventName === "tool_start") {
          if (item.data.name && !toolCalls.includes(item.data.name)) {
            toolCalls.push(item.data.name);
            renderChips(toolCallsEl, toolCalls);
          }
        } else if (item.eventName === "final") {
          if (!streamedText) {
            assistantText.textContent = item.data.answer || text.completed;
          }
          renderChips(toolCallsEl, item.data.tool_calls || toolCalls);
          jsonOutputEl.textContent = JSON.stringify(item.data.structured_response || {}, null, 2);
          setStatus(text.done);
        } else if (item.eventName === "error") {
          throw new Error(item.data.message || "stream error");
        }
      }
    }
  } catch (error) {
    assistantText.textContent = `${text.requestFailed}${error.message}`;
    setStatus(text.error);
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = inputEl.value.trim();
  if (!message || sendBtn.disabled) {
    return;
  }
  inputEl.value = "";
  sendMessage(message);
});

inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    formEl.requestSubmit();
  }
});

document.querySelector("#exampleBtn").addEventListener("click", () => {
  inputEl.value = text.example;
  inputEl.focus();
});

document.querySelector("#newThread").addEventListener("click", () => {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  threadIdEl.value = `web-${stamp}`;
  messagesEl.innerHTML = "";
  addMessage("assistant", text.newThread);
  renderChips(toolCallsEl, []);
  jsonOutputEl.textContent = "{}";
});

document.querySelector("#clearThread").addEventListener("click", async () => {
  setStatus(text.clearing);
  try {
    const response = await fetch("/threads/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadIdEl.value.trim() || "web-demo" }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    messagesEl.innerHTML = "";
    addMessage("assistant", text.threadCleared);
    renderChips(toolCallsEl, []);
    jsonOutputEl.textContent = "{}";
    setStatus(text.done);
  } catch (error) {
    addMessage("assistant", `${text.requestFailed}${error.message}`);
    setStatus(text.error);
  }
});

document.querySelector("#refreshTools").addEventListener("click", loadTools);

loadTools();
