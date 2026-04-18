"""
Build benchmark/sessions.html — a static GHOST session viewer
Reads ghost.db and benchmark/metadata.json, bakes all session/message/tool data into the HTML as JSON,
then renders it with vanilla JS. No server needed after build.
"""
import sqlite3, json, re, os, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

# Paths relative to this script in benchmark/scripts/
script_dir = os.path.dirname(os.path.abspath(__file__))
base = os.path.join(script_dir, '..', '..')
db_path = os.path.join(base, 'ghost.db')
meta_path = os.path.join(base, 'benchmark', 'metadata.json')
out_path = os.path.join(base, 'benchmark', 'sessions.html')

# Load session metadata and list of target titles
if not os.path.exists(meta_path):
    print(f"Error: Metadata not found at {meta_path}")
    sys.exit(1)

with open(meta_path, 'r', encoding='utf-8') as f:
    SESSION_META = json.load(f)

# Sort sessions based on their keys in the JSON for a predictable order
TARGET_SESSIONS = list(SESSION_META.keys())

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT id, title FROM sessions")
all_sessions = {row['title'].strip(): row['id'] for row in c.fetchall()}

sessions_data = []
for title in TARGET_SESSIONS:
    sid = all_sessions.get(title)
    if not sid:
        print(f"Skipping: {title} (ID not found in DB)")
        continue
    meta = SESSION_META.get(title, {})

    # Messages
    c.execute("""
        SELECT id, role, content, toolEvents, timestamp
        FROM messages WHERE sessionId=? ORDER BY timestamp ASC
    """, (sid,))
    raw_msgs = c.fetchall()

    messages = []
    for i, m in enumerate(raw_msgs):
        tool_calls = []
        try:
            events = json.loads(m['toolEvents'] or '[]')
            for evt in events:
                tool_name = evt.get('toolName', '')
                args = evt.get('args', evt.get('input', {}))
                result = evt.get('result', {})
                # Truncate result for display
                result_str = json.dumps(result)[:800] if result else ''
                tool_calls.append({
                    'tool': tool_name,
                    'args': json.dumps(args)[:400] if args else '',
                    'result': result_str,
                    'status': 'error' if (isinstance(result, dict) and result.get('error')) else 'ok'
                })
        except:
            pass

        content = m['content'] or ''
        
        # FIX: Missing Operator prompt. 
        # If it's the first message and empty, pull from metadata if available.
        if not content.strip() and m['role'] == 'user':
            if i == 0 and meta.get('initial_prompt'):
                content = meta['initial_prompt']
            elif 'continue' in meta.get('initial_prompt', '').lower() or i > 0:
                # If there are subsequent empty user messages, they are likely "continue" steps
                content = "continue"

        flags_in_msg = re.findall(r'\^FLAG\^([0-9a-f]{20,})\$FLAG\$', content)

        # Truncate display content to keep HTML size manageable but enough for readability
        display_content = content[:4000]

        messages.append({
            'role': m['role'],
            'ts': m['timestamp'] or '',
            'content': display_content,
            'flags': flags_in_msg,
            'toolCalls': tool_calls
        })

    # Tasks
    c.execute("SELECT title, status, notes FROM tasks WHERE sessionId=? ORDER BY createdAt ASC", (sid,))
    tasks = [{'title': t['title'], 'status': t['status'], 'notes': (t['notes'] or '')[:1000]} for t in c.fetchall()]

    # Memory nodes
    c.execute("SELECT label, name FROM memory_nodes WHERE sessionId=? ORDER BY timestamp ASC", (sid,))
    mem_nodes = [{'label': n['label'], 'name': n['name']} for n in c.fetchall()]

    sessions_data.append({
        'id': sid,
        'title': title,
        'model': meta.get('model', ''),
        'type': meta.get('type', ''),
        'flags': meta.get('flags', ''),
        'messages': messages,
        'tasks': tasks,
        'memoryNodes': mem_nodes,
        'totalTools': sum(len(m['toolCalls']) for m in messages),
        'userCount': sum(1 for m in messages if m['role'] == 'user'),
        'assistantCount': sum(1 for m in messages if m['role'] == 'assistant'),
    })

conn.close()

# Escape for embedding in HTML
data_json = json.dumps(sessions_data, ensure_ascii=False)
data_json_escaped = data_json.replace('</script>', '<\\/script>')

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>GHOST — Session Viewer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --bg: #030810;
      --sidebar: #060f1c;
      --sidebar-hover: #0c1c30;
      --sidebar-active: #0d2240;
      --panel: #080e1a;
      --card: #0a1628;
      --border: #142035;
      --border-bright: #1e3555;
      --accent: #00e5ff;
      --accent2: #0088cc;
      --green: #00ff9d;
      --red: #ff3d6b;
      --orange: #ff8c42;
      --yellow: #ffd700;
      --text: #e0f0ff;
      --text-muted: #6b90b8;
      --text-dim: #3a5572;
      --mono: 'JetBrains Mono', monospace;
      --sans: 'Inter', sans-serif;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ height: 100%; overflow: hidden; }}
    body {{
      font-family: var(--sans);
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
    }}
    /* TOP NAV */
    .topnav {{
      height: 44px;
      background: var(--sidebar);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      padding: 0 1rem;
      gap: 1rem;
      flex-shrink: 0;
      z-index: 10;
    }}
    .topnav-brand {{
      font-family: var(--mono);
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--accent);
      letter-spacing: 0.04em;
    }}
    .topnav-sep {{ color: var(--text-dim); font-size: 0.7rem; }}
    .topnav-title {{ font-size: 0.78rem; color: var(--text-muted); }}
    .topnav-links {{ margin-left: auto; display: flex; gap: 0.75rem; }}
    .topnav-links a {{
      font-size: 0.75rem;
      color: var(--text-dim);
      text-decoration: none;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      transition: all 0.15s;
    }}
    .topnav-links a:hover {{ color: var(--accent); background: rgba(0,229,255,0.06); }}
    /* MAIN LAYOUT */
    .app {{ display: flex; flex: 1; overflow: hidden; }}
    /* SIDEBAR */
    .sidebar {{
      width: 250px;
      flex-shrink: 0;
      background: var(--sidebar);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .sidebar-header {{
      padding: 0.75rem 0.85rem 0.5rem;
      border-bottom: 1px solid var(--border);
    }}
    .sidebar-label {{
      font-size: 0.62rem;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-weight: 600;
      margin-bottom: 0.5rem;
    }}
    .sidebar-search {{
      width: 100%;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text);
      font-size: 0.78rem;
      font-family: var(--sans);
      padding: 0.35rem 0.6rem;
      outline: none;
    }}
    .sidebar-search:focus {{ border-color: var(--accent2); }}
    .session-list {{ flex: 1; overflow-y: auto; padding: 0.4rem 0; }}
    .session-list::-webkit-scrollbar {{ width: 4px; }}
    .session-list::-webkit-scrollbar-track {{ background: transparent; }}
    .session-list::-webkit-scrollbar-thumb {{ background: var(--border-bright); border-radius: 2px; }}
    .session-item {{
      padding: 0.55rem 0.85rem;
      cursor: pointer;
      border-left: 2px solid transparent;
      transition: all 0.12s;
    }}
    .session-item:hover {{ background: var(--sidebar-hover); }}
    .session-item.active {{
      background: var(--sidebar-active);
      border-left-color: var(--accent);
    }}
    .session-item-name {{
      font-size: 0.78rem;
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--text);
    }}
    .session-item.active .session-item-name {{ color: var(--accent); }}
    .session-item-meta {{
      display: flex;
      gap: 0.5rem;
      margin-top: 0.2rem;
      align-items: center;
    }}
    .badge {{
      font-size: 0.58rem;
      font-family: var(--mono);
      padding: 0.1rem 0.35rem;
      border-radius: 3px;
      font-weight: 600;
    }}
    .badge-codex {{ background: rgba(0,229,255,0.12); color: var(--accent); border: 1px solid rgba(0,229,255,0.2); }}
    .badge-minimax {{ background: rgba(255,61,107,0.1); color: #ff6b8a; border: 1px solid rgba(255,61,107,0.2); }}
    .badge-ctf {{ background: rgba(255,215,0,0.08); color: var(--yellow); border: 1px solid rgba(255,215,0,0.15); }}
    .badge-pentest {{ background: rgba(0,255,157,0.08); color: var(--green); border: 1px solid rgba(0,255,157,0.15); }}
    .badge-flags {{ font-size: 0.62rem; color: var(--text-dim); }}
    /* MAIN PANEL */
    .main-panel {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
    /* SESSION HEADER */
    .session-header {{
      padding: 0.85rem 1.2rem;
      border-bottom: 1px solid var(--border);
      background: var(--panel);
      display: flex;
      align-items: center;
      gap: 1rem;
      flex-shrink: 0;
    }}
    .session-header-name {{ font-size: 0.95rem; font-weight: 700; flex: 1; }}
    .session-header-badges {{ display: flex; gap: 0.5rem; align-items: center; }}
    .stat-pill {{
      font-family: var(--mono);
      font-size: 0.68rem;
      padding: 0.2rem 0.55rem;
      background: var(--card);
      border: 1px solid var(--border-bright);
      border-radius: 20px;
      color: var(--text-muted);
    }}
    /* CONTENT AREA */
    .content-area {{ flex: 1; display: flex; overflow: hidden; }}
    /* CHAT PANEL */
    .chat-panel {{
      flex: 1;
      overflow-y: auto;
      padding: 1rem 1.2rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .chat-panel::-webkit-scrollbar {{ width: 5px; }}
    .chat-panel::-webkit-scrollbar-track {{ background: transparent; }}
    .chat-panel::-webkit-scrollbar-thumb {{ background: var(--border-bright); border-radius: 3px; }}
    /* MESSAGE BUBBLES */
    .msg {{ display: flex; flex-direction: column; gap: 0.4rem; }}
    .msg-user {{ align-items: flex-end; }}
    .msg-assistant {{ align-items: flex-start; }}
    .msg-role-label {{
      font-size: 0.65rem;
      color: var(--text-dim);
      font-family: var(--mono);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 0 0.3rem;
    }}
    .msg-bubble {{
      max-width: 85%;
      padding: 0.7rem 0.9rem;
      border-radius: 10px;
      font-size: 0.83rem;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .msg-user .msg-bubble {{
      background: rgba(0,136,204,0.12);
      border: 1px solid rgba(0,136,204,0.25);
      color: var(--text);
    }}
    .msg-assistant .msg-bubble {{
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--text-muted);
    }}
    .flag-found {{
      font-family: var(--mono);
      font-size: 0.7rem;
      color: var(--green);
      background: rgba(0,255,157,0.07);
      border: 1px solid rgba(0,255,157,0.2);
      border-radius: 4px;
      padding: 0.2rem 0.5rem;
      margin-top: 0.3rem;
      word-break: break-all;
    }}
    /* TOOL CALLS */
    .tool-calls {{ display: flex; flex-direction: column; gap: 0.3rem; max-width: 85%; }}
    .msg-assistant .tool-calls {{ align-self: flex-start; width: 100%; max-width: 100%; }}
    .tool-call {{
      background: rgba(0,0,0,0.3);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }}
    .tool-call-header {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.4rem 0.7rem;
      cursor: pointer;
      background: var(--panel);
      transition: background 0.12s;
    }}
    .tool-call-header:hover {{ background: var(--sidebar-hover); }}
    .tool-icon {{ font-size: 0.7rem; }}
    .tool-name {{
      font-family: var(--mono);
      font-size: 0.72rem;
      color: var(--accent);
      font-weight: 600;
    }}
    .tool-args-preview {{
      font-family: var(--mono);
      font-size: 0.66rem;
      color: var(--text-dim);
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      max-width: 300px;
    }}
    .tool-status-ok {{ margin-left: auto; color: var(--green); font-size: 0.65rem; }}
    .tool-status-err {{ margin-left: auto; color: var(--red); font-size: 0.65rem; }}
    .tool-chevron {{
      font-size: 0.6rem;
      color: var(--text-dim);
      transition: transform 0.15s;
    }}
    .tool-call.open .tool-chevron {{ transform: rotate(90deg); }}
    .tool-call-body {{
      display: none;
      padding: 0.5rem 0.7rem;
      border-top: 1px solid var(--border);
      font-family: var(--mono);
      font-size: 0.7rem;
      color: var(--text-muted);
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-all;
    }}
    .tool-call.open .tool-call-body {{ display: block; }}
    .tool-result-label {{ color: var(--text-dim); font-size: 0.62rem; margin-top: 0.4rem; margin-bottom: 0.15rem; }}
    /* RIGHT PANEL - TASKS / MEMORY */
    .right-panel {{
      width: 250px;
      flex-shrink: 0;
      border-left: 1px solid var(--border);
      background: var(--panel);
      overflow-y: auto;
      padding: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .right-panel::-webkit-scrollbar {{ width: 4px; }}
    .right-panel::-webkit-scrollbar-thumb {{ background: var(--border-bright); border-radius: 2px; }}
    .right-section-title {{
      font-size: 0.62rem;
      font-family: var(--mono);
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-bottom: 0.5rem;
    }}
    .task-item {{
      padding: 0.4rem 0.5rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 6px;
      margin-bottom: 0.35rem;
    }}
    .task-item-title {{
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--text);
      word-break: break-word;
    }}
    .task-status {{
      font-size: 0.6rem;
      font-family: var(--mono);
      margin-top: 0.2rem;
    }}
    .task-status.done {{ color: var(--green); }}
    .task-status.pending {{ color: var(--orange); }}
    .task-status.in_progress {{ color: var(--accent); }}
    .task-notes {{
      font-size: 0.68rem;
      color: var(--text-dim);
      margin-top: 0.3rem;
      line-height: 1.4;
      word-break: break-word;
    }}
    .mem-node {{
      font-size: 0.72rem;
      padding: 0.3rem 0.5rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 5px;
      margin-bottom: 0.3rem;
    }}
    .mem-label {{ font-size: 0.58rem; color: var(--accent2); font-family: var(--mono); }}
    .mem-name {{ color: var(--text-muted); word-break: break-word; margin-top: 0.1rem; }}
    /* EMPTY STATE */
    .empty-state {{
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: var(--text-dim);
      gap: 0.75rem;
    }}
    .empty-ghost {{ font-size: 3rem; opacity: 0.3; }}
    .empty-text {{ font-size: 0.85rem; }}
  </style>
</head>
<body>

<nav class="topnav">
  <span class="topnav-brand">👻 GHOST</span>
  <span class="topnav-sep">/</span>
  <span class="topnav-title">Session Viewer — 15 Benchmark Sessions</span>
  <div class="topnav-links">
    <a href="index.html">← Dashboard</a>
    <a href="docs.html">Docs</a>
  </div>
</nav>

<div class="app">
  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-label">Recent Missions</div>
      <input class="sidebar-search" type="text" id="search" placeholder="Filter sessions..." oninput="filterSessions(this.value)"/>
    </div>
    <div class="session-list" id="session-list"></div>
  </aside>

  <!-- MAIN PANEL -->
  <div class="main-panel" id="main-panel">
    <div class="empty-state">
      <div class="empty-ghost">👻</div>
      <div class="empty-text">Select a session to view its log</div>
    </div>
  </div>
</div>

<script>
const SESSIONS = {data_json_escaped};

let activeId = null;

function filterSessions(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('.session-item').forEach(el => {{
    const name = el.dataset.name.toLowerCase();
    el.style.display = name.includes(q) ? '' : 'none';
  }});
}}

function buildSidebar() {{
  const list = document.getElementById('session-list');
  SESSIONS.forEach((s, i) => {{
    const item = document.createElement('div');
    item.className = 'session-item';
    item.dataset.name = s.title;
    item.dataset.idx = i;
    item.onclick = () => loadSession(i, item);

    const modelBadge = s.model === 'Codex' ? 'badge-codex' : 'badge-minimax';
    const typeBadge = s.type === 'CTF' ? 'badge-ctf' : 'badge-pentest';
    const flagsOk = (s.flags || '').includes('FAIL') ? '❌' : (s.flags || '').includes('🚫') ? '🚫' : '✅';

    item.innerHTML = `
      <div class="session-item-name">${{escHtml(s.title)}}</div>
      <div class="session-item-meta">
        <span class="badge ${{modelBadge}}">${{s.model}}</span>
        <span class="badge ${{typeBadge}}">${{s.type}}</span>
        <span class="badge-flags">${{flagsOk}} ${{s.flags || ''}}</span>
      </div>
    `;
    list.appendChild(item);
  }});
}}

function loadSession(idx, itemEl) {{
  // Deactivate old
  document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
  if (itemEl) itemEl.classList.add('active');
  activeId = idx;
  const s = SESSIONS[idx];
  renderSession(s);
}}

function renderSession(s) {{
  const panel = document.getElementById('main-panel');
  const modelBadge = s.model === 'Codex' ? 'badge-codex' : 'badge-minimax';
  const typeBadge = s.type === 'CTF' ? 'badge-ctf' : 'badge-pentest';

  let messagesHtml = '';
  let toolCount = 0;
  let flagCount = 0;

  s.messages.forEach(msg => {{
    const isUser = msg.role === 'user';
    const roleClass = isUser ? 'msg-user' : 'msg-assistant';
    const roleLabel = isUser ? '🧑 Operator' : '👻 GHOST Agent';

    // Tool calls
    let toolsHtml = '';
    if (msg.toolCalls && msg.toolCalls.length > 0) {{
      toolCount += msg.toolCalls.length;
      toolsHtml = '<div class="tool-calls">';
      msg.toolCalls.forEach((tc, ti) => {{
        const statusClass = tc.status === 'error' ? 'tool-status-err' : 'tool-status-ok';
        const statusIcon = tc.status === 'error' ? '✗ ERR' : '✓ OK';
        const uid = `tc-${{s.id}}-${{ti}}`;
        toolsHtml += `
          <div class="tool-call" id="${{uid}}">
            <div class="tool-call-header" onclick="toggleTool('${{uid}}')">
              <span class="tool-icon">⚡</span>
              <span class="tool-name">${{escHtml(tc.tool)}}</span>
              <span class="tool-args-preview">${{escHtml((tc.args||'').slice(0,80))}}</span>
              <span class="${{statusClass}}">${{statusIcon}}</span>
              <span class="tool-chevron">▶</span>
            </div>
            <div class="tool-call-body">
              <div><strong>Args:</strong> ${{escHtml(tc.args||'(none)')}}</div>
              ${{tc.result ? `<div class="tool-result-label">↳ Result:</div><div>${{escHtml(tc.result)}}</div>` : ''}}
            </div>
          </div>`;
      }});
      toolsHtml += '</div>';
    }}

    // Flags in content
    let flagsHtml = '';
    if (msg.flags && msg.flags.length > 0) {{
      flagCount += msg.flags.length;
      msg.flags.forEach(f => {{
        flagsHtml += `<div class="flag-found">🏴 ^FLAG^${{f.slice(0,12)}}...${{f.slice(-8)}}$FLAG$</div>`;
      }});
    }}

    const contentText = (msg.content||'').trim();

    messagesHtml += `
      <div class="msg ${{roleClass}}">
        <div class="msg-role-label">${{roleLabel}}</div>
        ${{contentText ? `<div class="msg-bubble">${{escHtml(contentText)}}</div>` : ''}}
        ${{flagsHtml}}
        ${{toolsHtml}}
      </div>`;
  }});

  // Tasks HTML
  let tasksHtml = '';
  if (s.tasks.length > 0) {{
    s.tasks.forEach(t => {{
      const statusCls = t.status === 'done' ? 'done' : t.status === 'in_progress' ? 'in_progress' : 'pending';
      const statusIcon = t.status === 'done' ? '✅' : t.status === 'in_progress' ? '🔄' : '⏳';
      tasksHtml += `
        <div class="task-item">
          <div class="task-item-title">${{escHtml(t.title)}}</div>
          <div class="task-status ${{statusCls}}">${{statusIcon}} ${{t.status.toUpperCase()}}</div>
          ${{t.notes ? `<div class="task-notes">${{escHtml(t.notes.slice(0,300))}}</div>` : ''}}
        </div>`;
    }});
  }} else {{
    tasksHtml = '<div style="font-size:0.75rem;color:var(--text-dim)">No tasks created</div>';
  }}

  // Memory nodes HTML
  let memHtml = '';
  if (s.memoryNodes.length > 0) {{
    s.memoryNodes.forEach(n => {{
      memHtml += `
        <div class="mem-node">
          <div class="mem-label">${{escHtml(n.label)}}</div>
          <div class="mem-name">${{escHtml(n.name.slice(0,60))}}</div>
        </div>`;
    }});
  }} else {{
    memHtml = '<div style="font-size:0.75rem;color:var(--text-dim)">No memory nodes committed</div>';
  }}

  panel.innerHTML = `
    <div class="session-header">
      <div class="session-header-name">${{escHtml(s.title)}}</div>
      <div class="session-header-badges">
        <span class="badge ${{modelBadge}}">${{s.model}}</span>
        <span class="badge ${{typeBadge}}">${{s.type}}</span>
        <span class="stat-pill">${{s.userCount}}U / ${{s.assistantCount}}A msgs</span>
        <span class="stat-pill">${{toolCount}} tool calls</span>
        <span class="stat-pill">${{s.flags}}</span>
      </div>
    </div>
    <div class="content-area">
      <div class="chat-panel">${{messagesHtml || '<div style="color:var(--text-dim);font-size:0.85rem;margin:auto">No messages found</div>'}}</div>
      <div class="right-panel">
        <div>
          <div class="right-section-title">📋 Tasks</div>
          ${{tasksHtml}}
        </div>
        <div>
          <div class="right-section-title">🧠 Memory Graph</div>
          ${{memHtml}}
        </div>
      </div>
    </div>
  `;
}}

function toggleTool(uid) {{
  const el = document.getElementById(uid);
  if (el) el.classList.toggle('open');
}}

function escHtml(str) {{
  if (!str) return '';
  return str
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}}

buildSidebar();
// Auto-load first session
if (SESSIONS.length > 0) {{
  const firstItem = document.querySelector('.session-item');
  loadSession(0, firstItem);
}}
</script>
</body>
</html>'''

with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Written: {out_path} ({len(html):,} bytes)")
print(f"Sessions baked in: {len(sessions_data)}")
