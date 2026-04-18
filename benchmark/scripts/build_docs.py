"""
Build benchmark/docs.html — Formats README.md as a website
Reads README.md and metadata.json to update session counts and content.
"""
import os, sys, json

sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))
base = os.path.join(script_dir, '..', '..')
readme_path = os.path.join(base, 'benchmark', 'README.md')
meta_path = os.path.join(base, 'benchmark', 'metadata.json')
out_path = os.path.join(base, 'benchmark', 'docs.html')

if not os.path.exists(readme_path):
    print("README.md missing.")
    sys.exit(1)

with open(readme_path, 'r', encoding='utf-8') as f:
    readme_content = f.read()

# Load metadata for session counts
session_count = 0
models_str = "Minimax M2 vs GPT 5.2 Codex"
if os.path.exists(meta_path):
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
        session_count = len(meta)
        models = sorted(list(set(m.get('model') for m in meta.values() if m.get('model'))))
        if models:
            models_str = " vs ".join(models)

# Escape for JS string embedding
def js_escape(s):
    return s.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

readme_js = js_escape(readme_content)

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>GHOST Benchmark — Research Documentation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet"/>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {{
      --bg: #020408;
      --bg-card: #0d1825;
      --border: #1a2d45;
      --accent: #00e5ff;
      --text: #e8f4ff;
      --text-muted: #8badc8;
      --text-dim: #4a6a85;
      --green: #00ff9d;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.7;
    }}
    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      background: radial-gradient(ellipse 70% 50% at 15% 10%, rgba(0,100,200,0.06) 0%, transparent 60%);
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
    .page-wrapper {{ position: relative; z-index: 1; max-width: 900px; margin: 0 auto; padding: 5rem 2rem 4rem; }}
    .doc-hero {{ padding: 2.5rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: 20px; margin-bottom: 2rem; position: relative; overflow: hidden; }}
    .doc-hero::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--accent), #0088cc, var(--green)); }}
    .doc-hero h1 {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 0.5rem; }}
    .doc-meta {{ display: flex; gap: 1.5rem; flex-wrap: wrap; margin-top: 1.25rem; padding-top: 1.25rem; border-top: 1px solid var(--border); }}
    .doc-meta-item .label {{ font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; }}
    .doc-meta-item .value {{ font-size: 0.85rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; }}
    .toc-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 2.5rem; }}
    .doc-content h1 {{ font-size: 1.7rem; font-weight: 800; margin: 2.5rem 0 0.85rem; padding-bottom: 0.65rem; border-bottom: 1px solid var(--border); color: var(--accent); }}
    .doc-content h2 {{ font-size: 1.3rem; font-weight: 700; margin: 2rem 0 0.65rem; padding-left: 0.75rem; border-left: 3px solid var(--accent); }}
    .doc-content p {{ margin-bottom: 0.85rem; color: var(--text-secondary); font-size: 0.92rem; }}
    .doc-content table {{ width: 100%; border-collapse: collapse; margin: 1.25rem 0; font-size: 0.84rem; }}
    .doc-content th {{ text-align: left; padding: 0.6rem 0.8rem; border-bottom: 1px solid var(--border); color: var(--text-dim); }}
    .doc-content td {{ padding: 0.7rem 0.8rem; border-bottom: 1px solid rgba(26,45,69,0.5); }}
    footer {{ border-top: 1px solid var(--border); padding: 2rem; text-align: center; margin-top: 3rem; }}
    footer p {{ font-size: 0.8rem; color: var(--text-dim); }}
    footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <nav>
    <a href="index.html" class="nav-brand">👻 GHOST::BENCH</a>
    <ul class="nav-links">
      <li><a href="index.html">Dashboard</a></li>
      <li><a href="docs.html" class="active">Full Docs</a></li>
      <li>
        <a href="https://github.com/mrhahahaexe/OpenKaliClaw" target="_blank" aria-label="GitHub">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="vertical-align:middle;opacity:0.6;transition:opacity 0.2s" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22v3.293c0 .319.192.694.805.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
        </a>
      </li>
    </ul>
    <a href="index.html" class="nav-back">← Dashboard</a>
  </nav>

  <div class="page-wrapper">
    <div class="doc-hero">
      <h1>GHOST Offensive Engine<br/><span style="color:var(--accent)">Research Documentation</span></h1>
      <div class="doc-meta">
        <div class="doc-meta-item"><div class="label">Sessions</div><div class="value">{session_count}</div></div>
        <div class="doc-meta-item"><div class="label">Models</div><div class="value">{models_str}</div></div>
        <div class="doc-meta-item"><div class="label">Data Source</div><div class="value">ghost.db</div></div>
        <div class="doc-meta-item"><div class="label">Published</div><div class="value">April 2026</div></div>
      </div>
    </div>

    <div class="toc-card">
      <div style="font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; color: var(--accent); margin-bottom: 0.85rem;">📋 Table of Contents</div>
      <ul id="toc" style="list-style: none; columns: 2; column-gap: 2rem; font-size: 0.82rem;"></ul>
    </div>

    <div class="doc-content" id="doc-body"></div>
  </div>

  <footer>
    <p>GHOST Benchmark Study · April 2026 · <a href="README.md">README.md</a> · <a href="index.html">Dashboard</a></p>
  </footer>

  <script>
    const README_CONTENT = `{readme_js}`;
    marked.setOptions({{ breaks: true, gfm: true }});
    document.getElementById('doc-body').innerHTML = marked.parse(README_CONTENT);

    // Build TOC
    const toc = document.getElementById('toc');
    document.querySelectorAll('#doc-body h2').forEach(h => {{
      const id = h.textContent.toLowerCase().replace(/[^a-z0-9\\s-]/g, '').trim().replace(/\\s+/g, '-');
      h.id = id;
      const li = document.createElement('li');
      li.innerHTML = `<a href="#${{id}}" style="color:var(--text-muted); text-decoration:none;">${{h.textContent}}</a>`;
      toc.appendChild(li);
    }});
  </script>
</body>
</html>'''

with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Written: {out_path}")
