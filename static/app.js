/* AegisOps lightweight frontend (no build step, no framework). */
const state = {
  userId: "demo-user",
  threadId: null,
  streamingBubble: null,
  interrupt: null,
};

const $ = (id) => document.getElementById(id);

function addChat(role, html) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  if (html.startsWith("#")) {
    const pre = document.createElement("pre");
    pre.textContent = html;
    div.appendChild(pre);
  } else {
    div.innerHTML = html;
  }
  $("chat-log").appendChild(div);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
  return div;
}

function addActivity(text, cls = "") {
  const li = document.createElement("li");
  li.textContent = text;
  if (cls) li.className = cls;
  const list = $("activity-list");
  list.prepend(li);
  while (list.children.length > 60) list.removeChild(list.lastChild);
}

function renderTodos(steps) {
  const list = $("todo-list");
  list.innerHTML = "";
  for (const step of steps) {
    const li = document.createElement("li");
    const icon = { pending: "⬜", in_progress: "🔄", completed: "✅", failed: "❌" }[step.status] || "⬜";
    li.textContent = `${icon} ${step.id} · ${step.title}`;
    list.appendChild(li);
  }
}

function showInterrupt(payload) {
  state.interrupt = payload;
  $("interrupt-banner").classList.remove("hidden");
  $("interrupt-message").textContent = payload.message || "需要人工介入";
  const actions = $("interrupt-actions");
  actions.innerHTML = "";
  if (payload.interrupt_type === "missing_info" || payload.type === "missing_info") {
    $("interrupt-supplement").classList.remove("hidden");
  } else if (payload.action_requests) {
    $("interrupt-supplement").classList.add("hidden");
    for (const req of payload.action_requests) {
      const row = document.createElement("div");
      row.innerHTML = `<strong>${req.tool_name}</strong> (risk L${req.risk_level})<br>reason: ${req.reason}<br>before: ${JSON.stringify(req.before_state)}<br>impact: ${req.expected_impact}`;
      actions.appendChild(row);
      const approve = document.createElement("button");
      approve.textContent = `Approve ${req.tool_name}`;
      approve.onclick = () => resume({ decisions: [{ type: "approve", tool_name: req.tool_name }] });
      const reject = document.createElement("button");
      reject.textContent = "Reject";
      reject.onclick = () => resume({ decisions: [{ type: "reject", tool_name: req.tool_name, comment: "rejected by operator" }] });
      actions.append(approve, reject, document.createElement("br"));
    }
  }
}

function hideInterrupt() {
  state.interrupt = null;
  $("interrupt-banner").classList.add("hidden");
  $("interrupt-supplement").classList.add("hidden");
}

async function resume(payload) {
  if (!state.threadId) return;
  hideInterrupt();
  const response = await fetch(`/api/chat/${state.threadId}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (data.interrupt) {
    showInterrupt(data.interrupt);
  } else if (data.final_report) {
    addChat("assistant", data.final_report);
  }
  refreshHistory();
}

async function sendSupplement() {
  const text = $("supplement-input").value.trim();
  if (!text) return;
  await resume({ supplement: text });
}

async function streamChat(message) {
  addChat("user", message);
  hideInterrupt();
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, user_id: state.userId, thread_id: state.threadId }),
  });
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  state.streamingBubble = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop();
    for (const frame of frames) {
      if (!frame.startsWith("data: ")) continue;
      let event;
      try { event = JSON.parse(frame.slice(6)); } catch { continue; }
      handleEvent(event);
    }
  }
  refreshHistory();
}

function handleEvent(event) {
  switch (event.type) {
    case "run_start":
      state.threadId = event.thread_id;
      break;
    case "token":
      if (!state.streamingBubble) {
        state.streamingBubble = addChat("assistant", "");
        const pre = document.createElement("pre");
        pre.className = "token-stream";
        state.streamingBubble.appendChild(pre);
      }
      state.streamingBubble.querySelector("pre").textContent += event.content;
      $("chat-log").scrollTop = $("chat-log").scrollHeight;
      break;
    case "plan":
      renderTodos(event.steps);
      break;
    case "agent_start":
      addActivity(`▶ ${event.source} started`, "status-ok");
      break;
    case "agent_end":
      addActivity(`■ ${event.source} done (confidence=${event.confidence ?? ""})`, "status-ok");
      break;
    case "tool_start":
      addActivity(`⚙ ${event.source} → ${event.tool_name}`);
      break;
    case "tool_args":
      addActivity(`   args: ${JSON.stringify(event.args).slice(0, 160)}`);
      break;
    case "tool_result":
      addActivity(`   result: ${event.ok ? "ok" : "ERROR " + event.error}`, event.ok ? "status-ok" : "status-danger");
      break;
    case "interrupt":
      showInterrupt(event);
      break;
    case "report":
      addChat("assistant", event.content);
      break;
    case "error":
      addActivity(`✖ ${event.message}`, "status-danger");
      break;
    case "done":
      state.streamingBubble = null;
      break;
  }
}

async function refreshHistory() {
  const response = await fetch(`/api/history?user_id=${encodeURIComponent(state.userId)}`);
  const items = await response.json();
  const list = $("history-list");
  list.innerHTML = "";
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = `${item.status} · ${item.preview || item.thread_id}`;
    li.title = item.thread_id;
    li.onclick = () => { state.threadId = item.thread_id; };
    list.appendChild(li);
  }
}

async function loadRuntime() {
  try {
    const response = await fetch("/api/runtime");
    const info = await response.json();
    $("runtime-badge").textContent = `${info.llm_mode} · sandbox=${info.sandbox_backend}`;
  } catch { /* UI only */ }
}

$("chat-form").onsubmit = (event) => {
  event.preventDefault();
  const input = $("message-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  streamChat(message);
};
$("refresh-history").onclick = refreshHistory;
$("send-supplement").onclick = sendSupplement;

refreshHistory();
loadRuntime();
