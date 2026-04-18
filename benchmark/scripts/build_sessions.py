"""
Build benchmark/sessions.html — a static GHOST session viewer
Reads various databases (per metadata.json) and benchmark/metadata.json, 
bakes all session/message/tool data into the HTML as JSON.
"""
import sqlite3, json, re, os, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

# Paths relative to this script in benchmark/scripts/
script_dir = os.path.dirname(os.path.abspath(__file__))
base = os.path.join(script_dir, '..', '..')
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

sessions_data = []
for title in TARGET_SESSIONS:
    meta = SESSION_META.get(title, {})
    
    # Resolve DB path for this session
    db_name = meta.get('db', 'ghost.db')
    session_db_path = os.path.join(base, db_name)
    
    if not os.path.exists(session_db_path):
        print(f"  Warning: DB {db_name} not found for session '{title}'. Skipping.")
        continue

    conn = sqlite3.connect(session_db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get session ID by title
    c.execute("SELECT id FROM sessions WHERE title = ?", (title,))
    row = c.fetchone()
    if not row:
        print(f"  Warning: Session '{title}' not found in {db_name}. Skipping.")
        conn.close()
        continue
    sid = row['id']

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
        if not content.strip() and m['role'] == 'user':
            if i == 0 and meta.get('initial_prompt'):
                content = meta['initial_prompt']
            elif 'continue' in meta.get('initial_prompt', '').lower() or i > 0:
                content = "continue"

        flags_in_msg = re.findall(r'\^FLAG\^([0-9a-f]{20,})\$FLAG\$', content)
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

# Template (abbreviated for the write_to_file tool, but I'll include the whole JS logic part)
# Actually, I'll just write the full file back but with the improved extraction loop.
# I'll use the content I just viewed.

html_template = f'''<!DOCTYPE html>
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
    .topnav-links {{ margin-left: auto; display: flex; gap: 0.75rem; align-items: center; }}
    .menu-toggle {{
      display: none;
      background: none;
      border: none;
      color: var(--text);
      font-size: 1.2rem;
      cursor: pointer;
      padding: 0.5rem;
    }}
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
      box-shadow: inset 0 0 40px rgba(0,0,0,0.3);
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
      border-radius: 12px;
      font-size: 0.83rem;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .msg-user .msg-bubble {{
      background: rgba(0,136,204,0.1);
      border: 1px solid rgba(0, 136, 204, 0.2);
      color: var(--text);
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }}
    .msg-assistant .msg-bubble {{
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
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
    .tool-calls {{ display: flex; flex-direction: column; gap: 0.3rem; max-width: 90%; }}
    .msg-assistant .tool-calls {{ align-self: flex-start; width: 100%; max-width: 100%; }}
    .tool-call {{
      background: rgba(0,0,0,0.2);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      margin-top: 0.25rem;
    }}
    .tool-call-header {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.45rem 0.75rem;
      cursor: pointer;
      background: rgba(255,255,255,0.02);
      transition: background 0.12s;
    }}
    .tool-call-header:hover {{ background: var(--sidebar-hover); }}
    .tool-icon {{ font-size: 0.75rem; }}
    .tool-name {{
      font-family: var(--mono);
      font-size: 0.72rem;
      color: var(--accent);
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .tool-args-preview {{
      font-family: var(--mono);
      font-size: 0.64rem;
      color: var(--text-dim);
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      max-width: 400px;
    }}
    .tool-status-ok {{ margin-left: auto; color: var(--green); font-size: 0.6rem; font-weight: 700; }}
    .tool-status-err {{ margin-left: auto; color: var(--red); font-size: 0.6rem; font-weight: 700; }}
    .tool-chevron {{
      font-size: 0.6rem;
      color: var(--text-dim);
      transition: transform 0.2s;
    }}
    .tool-call.open .tool-chevron {{ transform: rotate(90deg); }}
    .tool-call-body {{
      display: none;
      padding: 0.6rem 0.8rem;
      border-top: 1px solid var(--border);
      font-family: var(--mono);
      font-size: 0.72rem;
      color: var(--text-muted);
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-all;
      background: rgba(0,0,0,0.1);
    }}
    .tool-call.open .tool-call-body {{ display: block; }}
    .tool-result-header {{ color: var(--text-dim); font-size: 0.6rem; text-transform: uppercase; margin-top: 0.8rem; margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.4rem; }}
    .tool-result-header::after {{ content: ''; flex: 1; height: 1px; background: var(--border); }}
    /* RIGHT PANEL - TASKS / MEMORY */
    .right-panel {{
      width: 280px;
      flex-shrink: 0;
      border-left: 1px solid var(--border);
      background: var(--panel);
      overflow-y: auto;
      padding: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}
    .right-panel::-webkit-scrollbar {{ width: 4px; }}
    .right-panel::-webkit-scrollbar-thumb {{ background: var(--border-bright); border-radius: 2px; }}
    .right-section-title {{
      font-size: 0.62rem;
      font-family: var(--mono);
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-weight: 700;
      margin-bottom: 0.6rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}
    .task-item {{
      padding: 0.5rem 0.6rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-top-width: 2px;
      border-radius: 6px;
      margin-bottom: 0.5rem;
    }}
    .task-item.done {{ border-top-color: var(--green); }}
    .task-item.in_progress {{ border-top-color: var(--accent); }}
    .task-item.pending {{ border-top-color: var(--orange); }}
    .task-item-title {{
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text);
      word-break: break-word;
      line-height: 1.3;
    }}
    .task-status {{
      font-size: 0.6rem;
      font-family: var(--mono);
      margin-top: 0.25rem;
      font-weight: 800;
    }}
    .task-status.done {{ color: var(--green); opacity: 0.8; }}
    .task-status.pending {{ color: var(--orange); opacity: 0.8; }}
    .task-status.in_progress {{ color: var(--accent); opacity: 0.8; }}
    .task-notes {{
      font-size: 0.68rem;
      color: var(--text-dim);
      margin-top: 0.4rem;
      line-height: 1.4;
      word-break: break-word;
      font-style: italic;
    }}
    .mem-node {{
      font-size: 0.7rem;
      padding: 0.4rem 0.6rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 6px;
      margin-bottom: 0.4rem;
      transition: border-color 0.2s;
    }}
    .mem-node:hover {{ border-color: var(--accent2); }}
    .mem-label {{ font-size: 0.58rem; color: var(--accent2); font-family: var(--mono); font-weight: 700; }}
    .mem-name {{ color: var(--text-muted); word-break: break-word; margin-top: 0.15rem; line-height: 1.3; }}
    /* EMPTY STATE */
    .empty-state {{
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: var(--text-dim);
      gap: 1rem;
    }}
    .empty-ghost {{ font-size: 4rem; opacity: 0.1; animation: float 3s ease-in-out infinite; }}
    @keyframes float {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-10px); }} }}
    .empty-text {{ font-size: 0.9rem; font-weight: 500; letter-spacing: 0.02em; }}

    /* MOBILE RESPONSIVE */
    @media (max-width: 900px) {{
      .menu-toggle {{ display: block; }}
      .sidebar {{
        position: fixed;
        top: 44px;
        left: -100%;
        bottom: 0;
        z-index: 100;
        width: 85%;
        transition: left 0.3s ease;
        box-shadow: 20px 0 50px rgba(0,0,0,0.5);
      }}
      body.menu-open .sidebar {{ left: 0; }}
      .content-area {{ flex-direction: column; overflow-y: auto; }}
      .chat-panel {{ flex: none; overflow-y: visible; width: 100%; }}
      .right-panel {{ width: 100%; border-left: none; border-top: 1px solid var(--border); }}
      .msg-bubble {{ max-width: 95%; }}
      .msg-assistant .tool-calls {{ max-width: 100%; }}
      .sidebar-overlay {{
        display: none;
        position: fixed;
        top: 44px;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.6);
        z-index: 99;
      }}
      body.menu-open .sidebar-overlay {{ display: block; }}
    }}
  </style>
</head>
<body>

<nav class="topnav">
  <button class="menu-toggle" onclick="toggleMenu()" aria-label="Toggle Sessions">☰</button>
  <span class="topnav-brand">👻 GHOST::TRACE</span>
  <span class="topnav-sep">|</span>
  <span class="topnav-title">Multi-DB Reasoning Logs</span>
  <div class="topnav-links">
    <a href="index.html">← Dashboard</a>
    <a href="docs.html">Docs</a>
    <a href="https://github.com/mrhahahaexe/OpenKaliClaw" target="_blank" aria-label="GitHub">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="vertical-align:middle;opacity:0.6;transition:opacity 0.2s" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22v3.293c0 .319.192.694.805.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
    </a>
  </div>
</nav>

<div class="app">
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-label">Select Mission</div>
      <input class="sidebar-search" type="text" id="search" placeholder="Type to filter..." oninput="filterSessions(this.value)"/>
    </div>
    <div class="session-list" id="session-list"></div>
  </aside>

  <div class="main-panel" id="main-panel">
    <div class="empty-state">
      <div class="empty-ghost">👻</div>
      <div class="empty-text">Select mission trace to initialize analyzer</div>
    </div>
  </div>
</div>

<div class="sidebar-overlay" onclick="toggleMenu()"></div>

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

    const modelBadge = s.model === 'GPT 5.2 Codex' ? 'badge-codex' : 'badge-minimax';
    const typeBadge = s.type === 'CTF' ? 'badge-ctf' : 'badge-pentest';
    const flagsOk = (s.flags || '').includes('FAIL') ? '❌' : (s.flags || '').includes('🚫') ? '🚫' : '✅';

    item.innerHTML = `
      <div class="session-item-name">${{escHtml(s.title)}}</div>
      <div class="session-item-meta">
        <span class="badge ${{modelBadge}}">${{s.model}}</span>
        <span class="badge ${{typeBadge}}">${{s.type}}</span>
        <span class="badge-flags" style="font-size:0.55rem; color:var(--text-dim)">${{flagsOk}} ${{s.flags || ''}}</span>
      </div>
    `;
    list.appendChild(item);
  }});
}}

function toggleMenu() {{
  document.body.classList.toggle('menu-open');
}}

function loadSession(idx, itemEl) {{
  document.body.classList.remove('menu-open'); // Auto-close on select
  document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
  if (itemEl) itemEl.classList.add('active');
  activeId = idx;
  renderSession(SESSIONS[idx]);
}}

function renderSession(s) {{
  const panel = document.getElementById('main-panel');
  const modelBadge = s.model === 'GPT 5.2 Codex' ? 'badge-codex' : 'badge-minimax';
  const typeBadge = s.type === 'CTF' ? 'badge-ctf' : 'badge-pentest';

  let messagesHtml = '';
  let toolCount = 0;

  s.messages.forEach(msg => {{
    const isUser = msg.role === 'user';
    const roleClass = isUser ? 'msg-user' : 'msg-assistant';
    const roleLabel = isUser ? '🧑 OPERATOR' : '👻 GHOST_ENGINE';

    let toolsHtml = '';
    if (msg.toolCalls && msg.toolCalls.length > 0) {{
      toolCount += msg.toolCalls.length;
      toolsHtml = '<div class="tool-calls">';
      msg.toolCalls.forEach((tc, ti) => {{
        const statusClass = tc.status === 'error' ? 'tool-status-err' : 'tool-status-ok';
        const statusIcon = tc.status === 'error' ? '× FAIL' : '● SUCCESS';
        const uid = `tc-${{s.id}}-${{ti}}`;
        toolsHtml += `
          <div class="tool-call" id="${{uid}}">
            <div class="tool-call-header" onclick="toggleTool('${{uid}}')">
              <span class="tool-icon">⚡</span>
              <span class="tool-name">${{escHtml(tc.tool)}}</span>
              <span class="tool-args-preview">${{escHtml((tc.args||'').slice(0,100))}}</span>
              <span class="${{statusClass}}">${{statusIcon}}</span>
              <span class="tool-chevron">▶</span>
            </div>
            <div class="tool-call-body">
              <div style="margin-bottom:0.5rem"><strong>Inputs:</strong><br/>${{escHtml(tc.args||'(none)')}}</div>
              ${{tc.result ? `<div class="tool-result-header">Result Stream</div><div style="max-height:300px; overflow-y:auto;">${{escHtml(tc.result)}}</div>` : ''}}
            </div>
          </div>`;
      }});
      toolsHtml += '</div>';
    }}

    let flagsHtml = '';
    if (msg.flags && msg.flags.length > 0) {{
      msg.flags.forEach(f => {{
        flagsHtml += `<div class="flag-found">🏴 DETECTED_FLAG: ^FLAG^${{f.slice(0,12)}}...${{f.slice(-8)}}$FLAG$</div>`;
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

  let tasksHtml = s.tasks.map(t => {{
    const statusCls = t.status === 'done' ? 'done' : t.status === 'in_progress' ? 'in_progress' : 'pending';
    return `<div class="task-item ${{statusCls}}">
      <div class="task-item-title">${{escHtml(t.title)}}</div>
      <div class="task-status ${{statusCls}}">${{t.status.toUpperCase()}}</div>
      ${{t.notes ? `<div class="task-notes">${{escHtml(t.notes)}}</div>` : ''}}
    </div>`;
  }}).join('') || '<div style="font-size:0.75rem;color:var(--text-dim)">No active tasks</div>';

  let memHtml = s.memoryNodes.map(n => `
    <div class="mem-node">
      <div class="mem-label">${{escHtml(n.label)}}</div>
      <div class="mem-name">${{escHtml(n.name)}}</div>
    </div>`).join('') || '<div style="font-size:0.75rem;color:var(--text-dim)">Memory graph empty</div>';

  panel.innerHTML = `
    <div class="session-header">
      <div class="session-header-name">${{escHtml(s.title)}}</div>
      <div class="session-header-badges">
        <span class="badge ${{modelBadge}}">${{s.model}}</span>
        <span class="badge ${{typeBadge}}">${{s.type}}</span>
        <span class="stat-pill">${{toolCount}} CALLS</span>
        <span class="stat-pill">${{s.flags}}</span>
      </div>
    </div>
    <div class="content-area">
      <div class="chat-panel">${{messagesHtml || '<div style="margin:auto; opacity:0.3">Empty mission trace</div>'}}</div>
      <div class="right-panel">
        <div><div class="right-section-title"><span>📋</span> Task Stack</div>${{tasksHtml}}</div>
        <div><div class="right-section-title"><span>🧠</span> Reasoning Context</div>${{memHtml}}</div>
      </div>
    </div>
  `;
  // Scroll to bottom of chat
  const chat = panel.querySelector('.chat-panel');
  if(chat) chat.scrollTop = chat.scrollHeight;
}}

function toggleTool(uid) {{
  document.getElementById(uid).classList.toggle('open');
}}

function escHtml(str) {{
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}}

buildSidebar();
if (SESSIONS.length > 0) loadSession(0, document.querySelector('.session-item'));
</script>
</body>
</html>'''

with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f"Written: {out_path}")
print(f"Sessions baked in: {len(sessions_data)} (from various sources)")
