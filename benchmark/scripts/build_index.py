"""
Build benchmark/index.html — Updates summary stats and the results table
Reads various databases and metadata.json, then injects data into markers in index.html.
"""
import sqlite3, json, os, sys, re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))
base = os.path.join(script_dir, '..', '..')
meta_path = os.path.join(base, 'benchmark', 'metadata.json')
index_path = os.path.join(base, 'benchmark', 'index.html')

if not os.path.exists(meta_path):
    print("Metadata missing.")
    sys.exit(1)

with open(meta_path, 'r', encoding='utf-8') as f:
    meta = json.load(f)

results = []
total_tools = 0
total_flags = 0
minimax_fails = 0
codex_refusals = 0
models_tested = set()

for title, config in meta.items():
    model_name = config.get('model', 'Unknown')
    models_tested.add(model_name)
    
    # Resolve DB path for this session
    db_name = config.get('db', 'ghost.db')
    session_db_path = os.path.join(base, db_name)
    
    if not os.path.exists(session_db_path):
        print(f"  Warning: DB {db_name} not found for session '{title}'. Skipping stats.")
        continue

    conn = sqlite3.connect(session_db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get session ID by title
    c.execute("SELECT id FROM sessions WHERE title = ?", (title,))
    row = c.fetchone()
    if not row:
        print(f"  Warning: Session '{title}' not found in {db_name}. Skipping stats.")
        conn.close()
        continue
    sid = row['id']
    
    # Get message counts
    c.execute("SELECT role, COUNT(*) as count FROM messages WHERE sessionId=? GROUP BY role", (sid,))
    counts = {r['role']: r['count'] for r in c.fetchall()}
    u_count = counts.get('user', 0)
    a_count = counts.get('assistant', 0)
    
    # Get tool call count
    c.execute("SELECT toolEvents FROM messages WHERE sessionId=?", (sid,))
    tools = 0
    for row in c.fetchall():
        try:
            evts = json.loads(row['toolEvents'] or '[]')
            tools += len(evts)
        except: pass
    
    total_tools += tools
    
    # Parse flags from metadata string
    flag_str = config.get('flags', '0')
    if '/' in flag_str:
        try: total_flags += int(flag_str.split('/')[0])
        except: pass
    elif 'vuln' in flag_str.lower():
        try:
            val = re.search(r'\d+', flag_str)
            if val: total_flags += int(val.group())
        except: pass
        
    if model_name == 'Minimax' and ('FAIL' in flag_str.upper() or '0/' in flag_str or '1/' in flag_str):
        if config.get('type') == 'Pentest' and 'FAIL' in flag_str.upper():
            minimax_fails += 1
            
    if model_name == 'Codex' and '🚫' in flag_str:
        codex_refusals += 1

    results.append({
        'title': title,
        'model': model_name,
        'type': config.get('type'),
        'outcome': flag_str,
        'msgs': f"{u_count}U / {a_count}A",
        'tools': tools
    })

    conn.close()

# Generate Table HTML
table_html = ""
ctf_results = [r for r in results if r['type'] == 'CTF']
pen_results = [r for r in results if r['type'] == 'Pentest']

def gen_row(r):
    m_cls = "codex" if r['model'] == 'Codex' else "minimax"
    is_pass = ("✅" in r['outcome'] or re.search(r'^[3-9]/', r['outcome']))
    is_fail = ("🚫" in r['outcome'] or "FAIL" in r['outcome'].upper() or r['outcome'].startswith('0/'))
    s_cls = "pass" if is_pass else "fail" if is_fail else "unknown"
    
    return f"""
            <tr>
              <td><span class="mono">{r['title']}</span></td>
              <td><span class="model-badge {m_cls}">{r['model']}</span></td>
              <td style="color:var(--text-secondary);font-size:0.82rem">{r['type']}</td>
              <td><span class="status-badge {s_cls}">{r['outcome']}</span></td>
              <td class="mono">{r['msgs']}</td>
              <td class="mono">{r['tools']}</td>
            </tr>"""

table_html += '            <tr><td colspan="6" style="background:rgba(0,229,255,0.04);color:var(--accent-cyan);font-size:0.72rem;font-weight:700;letter-spacing:0.1em;padding:0.5rem 1rem;">🎯 CTF TRACK — Hacker101 Flag Extraction</td></tr>'
for r in ctf_results: table_html += gen_row(r)

table_html += '            <tr><td colspan="6" style="background:rgba(0,255,157,0.04);color:var(--accent-green);font-size:0.72rem;font-weight:700;letter-spacing:0.1em;padding:0.5rem 1rem;">🔍 VULN ASSESSMENT TRACK — Pentest-Ground.com</td></tr>'
for r in pen_results: table_html += gen_row(r)

# Generate Dynamic Hero Stats
hero_stats_html = f"""
          <div class="hero-stat">
            <span class="val">{len(results)}</span>
            <span class="lbl">Total Sessions</span>
          </div>
          <div class="hero-stat">
            <span class="val">{len(models_tested)}</span>
            <span class="lbl">Models Tested</span>
          </div>
          <div class="hero-stat">
            <span class="val text-cyan">{total_flags}</span>
            <span class="lbl">Flags/Vulns</span>
          </div>
"""

# Inject into index.html
with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

def replace_marker(c, marker, val):
    start = f"<!-- {marker} -->"
    end = f"<!-- /{marker} -->"
    pattern = re.escape(start) + r".*?" + re.escape(end)
    return re.sub(pattern, f"{start}{val}{end}", c, flags=re.DOTALL)

# Date formatting: dd, mm, yyyy
now = datetime.now()
date_str = now.strftime("%d, %m, %Y")

content = replace_marker(content, "STATS_FLAGS", total_flags)
content = replace_marker(content, "STATS_TOOLS", total_tools)
content = replace_marker(content, "STATS_FAILURES", minimax_fails)
content = replace_marker(content, "STATS_REFUSALS", codex_refusals)
content = replace_marker(content, "RESULTS_TABLE_CONTENT", table_html)
content = replace_marker(content, "HERO_STATS", hero_stats_html)
content = replace_marker(content, "LAST_UPDATED_NAV", date_str)

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated index.html: {total_flags} flags/vulns, {len(results)} sessions, {len(models_tested)} models.")
print(f"Timestamp: {date_str}")
