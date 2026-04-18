import json
import sys
import os
import re

sys.stdout.reconfigure(encoding='utf-8')

# Read README
base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
readme_path = os.path.join(base, 'benchmark', 'README.md')

with open(readme_path, encoding='utf-8') as f:
    readme_content = f.read()

# Read session data
data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'full_session_analysis.json')
with open(data_path, encoding='utf-8') as f:
    sessions = json.load(f)

# Escape for JS string embedding
def js_escape(s):
    return s.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

readme_js = js_escape(readme_content)

# Build the complete docs.html
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>GHOST Benchmark — Full Research Documentation</title>
  <meta name="description" content="Full research documentation for the GHOST AI agent benchmark study: Minimax vs. Codex across 15 live hacking sessions."/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet"/>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {{
      --bg: #020408;
      --bg-card: #0d1825;
      --border: #1a2d45;
      --accent: #00e5ff;
      --accent-dim: rgba(0,229,255,0.15);
      --text: #e8f4ff;
      --text-muted: #8badc8;
      --text-dim: #4a6a85;
      --green: #00ff9d;
      --red: #ff3d6b;
      --orange: #ff8c42;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.7;
      overflow-x: hidden;
    }}
    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      background: radial-gradient(ellipse 70% 50% at 15% 10%, rgba(0,100,200,0.06) 0%, transparent 60%);
      pointer-events: none;
      z-index: 0;
    }}
    body::after {{
      content: '';
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(0,168,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,168,255,0.025) 1px, transparent 1px);
      background-size: 50px 50px;
      pointer-events: none;
      z-index: 0;
    }}
    nav {{
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 100;
      background: rgba(2,4,8,0.92);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border);
      padding: 0 2rem;
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .nav-brand {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 0.9rem; color: var(--accent); text-decoration: none; }}
    .nav-links {{ display: flex; gap: 1.5rem; list-style: none; }}
    .nav-links a {{ color: var(--text-muted); text-decoration: none; font-size: 0.82rem; transition: color 0.2s; }}
    .nav-links a:hover, .nav-links a.active {{ color: var(--accent); }}
    .nav-back {{ background: rgba(0,229,255,0.08); border: 1px solid rgba(0,229,255,0.25); color: var(--accent); padding: 0.3rem 0.9rem; border-radius: 20px; font-size: 0.8rem; text-decoration: none; font-weight: 500; transition: background 0.2s; }}
    .nav-back:hover {{ background: rgba(0,229,255,0.15); }}
    .page-wrapper {{ position: relative; z-index: 1; max-width: 900px; margin: 0 auto; padding: 5rem 2rem 4rem; }}
    .doc-hero {{ padding: 2.5rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: 20px; margin-bottom: 2rem; position: relative; overflow: hidden; }}
    .doc-hero::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--accent), #0088cc, var(--green)); }}
    .doc-hero-tag {{ font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--green); text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.75rem; }}
    .doc-hero h1 {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 0.5rem; }}
    .doc-hero h1 .cyan {{ color: var(--accent); }}
    .doc-hero p {{ font-size: 0.92rem; color: var(--text-muted); }}
    .doc-meta {{ display: flex; gap: 1.5rem; flex-wrap: wrap; margin-top: 1.25rem; padding-top: 1.25rem; border-top: 1px solid var(--border); }}
    .doc-meta-item .label {{ font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; }}
    .doc-meta-item .value {{ font-size: 0.85rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; }}
    .toc-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 2.5rem; }}
    .toc-title {{ font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.85rem; }}
    .toc-list {{ list-style: none; padding: 0; columns: 2; column-gap: 2rem; }}
    .toc-list li {{ margin-bottom: 0.35rem; break-inside: avoid; }}
    .toc-list a {{ color: var(--text-muted); text-decoration: none; font-size: 0.82rem; transition: color 0.2s; display: flex; align-items: center; gap: 0.4rem; }}
    .toc-list a::before {{ content: '→'; color: var(--text-dim); font-size: 0.7rem; }}
    .toc-list a:hover {{ color: var(--accent); }}
    .doc-content h1 {{ font-size: 1.7rem; font-weight: 800; margin: 2.5rem 0 0.85rem; padding-bottom: 0.65rem; border-bottom: 1px solid var(--border); color: var(--accent); }}
    .doc-content h2 {{ font-size: 1.3rem; font-weight: 700; margin: 2rem 0 0.65rem; padding-left: 0.75rem; border-left: 3px solid var(--accent); }}
    .doc-content h3 {{ font-size: 1.05rem; font-weight: 700; margin: 1.75rem 0 0.5rem; color: var(--accent); }}
    .doc-content h4 {{ font-size: 0.9rem; font-weight: 700; margin: 1.25rem 0 0.35rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }}
    .doc-content p {{ margin-bottom: 0.85rem; color: var(--text-muted); font-size: 0.92rem; }}
    .doc-content strong {{ color: var(--text); font-weight: 600; }}
    .doc-content a {{ color: var(--accent); text-decoration: none; }}
    .doc-content a:hover {{ text-decoration: underline; }}
    .doc-content ul, .doc-content ol {{ padding-left: 1.4rem; margin-bottom: 0.85rem; }}
    .doc-content li {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 0.3rem; }}
    .doc-content code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; background: rgba(0,168,255,0.08); border: 1px solid rgba(0,168,255,0.15); padding: 0.1rem 0.4rem; border-radius: 4px; color: var(--accent); }}
    .doc-content pre {{ background: #060d18; border: 1px solid var(--border); border-radius: 10px; padding: 1.2rem 1.4rem; overflow-x: auto; margin: 0.85rem 0 1.25rem; }}
    .doc-content pre code {{ background: none; border: none; padding: 0; font-size: 0.78rem; color: var(--text-muted); }}
    .doc-content blockquote {{ margin: 0.85rem 0; padding: 0.85rem 1.2rem; background: rgba(0,229,255,0.04); border-left: 3px solid var(--accent); border-radius: 0 8px 8px 0; }}
    .doc-content blockquote p {{ color: var(--text-muted); margin: 0; font-style: italic; }}
    .doc-content table {{ width: 100%; border-collapse: collapse; margin: 1.25rem 0; font-size: 0.84rem; }}
    .doc-content th {{ text-align: left; padding: 0.6rem 0.8rem; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); border-bottom: 1px solid var(--border); font-weight: 600; }}
    .doc-content td {{ padding: 0.7rem 0.8rem; border-bottom: 1px solid rgba(26,45,69,0.5); color: var(--text-muted); vertical-align: top; }}
    .doc-content tr:hover td {{ background: rgba(255,255,255,0.02); }}
    .doc-content hr {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}
    footer {{ position: relative; z-index: 1; border-top: 1px solid var(--border); padding: 1.75rem 2rem; text-align: center; margin-top: 3rem; }}
    footer p {{ font-size: 0.8rem; color: var(--text-dim); }}
    footer a {{ color: var(--accent); text-decoration: none; }}
    @media (max-width: 640px) {{
      .toc-list {{ columns: 1; }}
      .doc-meta {{ gap: 1rem; }}
    }}
  </style>
</head>
<body>
  <nav>
    <a href="index.html" class="nav-brand">👻 GHOST::BENCH</a>
    <ul class="nav-links">
      <li><a href="index.html">Dashboard</a></li>
      <li><a href="docs.html" class="active">Full Docs</a></li>
    </ul>
    <a href="index.html" class="nav-back">← Dashboard</a>
  </nav>

  <div class="page-wrapper">
    <div class="doc-hero">
      <div class="doc-hero-tag">◉ Full Research Documentation — Verified from ghost.db</div>
      <h1>GHOST Offensive Engine<br/><span class="cyan">Complete Benchmark Study</span></h1>
      <p>Session-by-session deep analysis of every hacking mission. All findings extracted directly from live session logs — timestamps, user interactions, tool calls, flags, and context compressions included.</p>
      <div class="doc-meta">
        <div class="doc-meta-item"><div class="label">Sessions</div><div class="value">15</div></div>
        <div class="doc-meta-item"><div class="label">Models</div><div class="value">Minimax vs Codex</div></div>
        <div class="doc-meta-item"><div class="label">Data Source</div><div class="value">ghost.db (live)</div></div>
        <div class="doc-meta-item"><div class="label">Published</div><div class="value">April 2026</div></div>
      </div>
    </div>

    <div class="toc-card">
      <div class="toc-title">📋 Table of Contents</div>
      <ul class="toc-list" id="toc"><li style="color:var(--text-dim);font-size:0.82rem">Building...</li></ul>
    </div>

    <div class="doc-content" id="doc-body"></div>
  </div>

  <footer>
    <p>GHOST Benchmark Study · April 2026 · <a href="README.md">Raw README.md</a> · <a href="ghost_traces_extracted.json">Trace JSON</a> · <a href="index.html">← Dashboard</a></p>
  </footer>

  <script>
    const README_CONTENT = `{readme_js}`;

    marked.setOptions({{ breaks: true, gfm: true }});
    document.getElementById('doc-body').innerHTML = marked.parse(README_CONTENT);

    // Build TOC
    const toc = document.getElementById('toc');
    toc.innerHTML = '';
    document.querySelectorAll('#doc-body h2').forEach(h => {{
      const id = h.textContent.toLowerCase().replace(/[^a-z0-9\\s-]/g, '').trim().replace(/\\s+/g, '-');
      h.id = id;
      const li = document.createElement('li');
      li.innerHTML = `<a href="#${{id}}">${{h.textContent}}</a>`;
      toc.appendChild(li);
    }});

    // Anchor h3s too
    document.querySelectorAll('#doc-body h3').forEach(h => {{
      const id = h.textContent.toLowerCase().replace(/[^a-z0-9\\s-]/g, '').trim().replace(/\\s+/g, '-');
      h.id = id;
    }});
  </script>
</body>
</html>'''

out_path = os.path.join(base, 'benchmark', 'docs.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Written: {out_path} ({len(html):,} bytes)")
