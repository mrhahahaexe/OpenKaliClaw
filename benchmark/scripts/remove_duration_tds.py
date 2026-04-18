import re, sys, os
sys.stdout.reconfigure(encoding='utf-8')
base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
html_path = os.path.join(base, 'benchmark', 'index.html')
with open(html_path, encoding='utf-8') as f:
    html = f.read()

before = len(re.findall(r'<td[^>]*>\s*\d+[ms]', html))

# Remove all td cells that contain ONLY a time string (m/s format), with optional styling
html = re.sub(r'<td class="mono"(?:\s+style="[^"]*")?>\s*\d+m\s+\d+s\s*(?:⚡)?\s*</td>', '', html)
html = re.sub(r'<td class="mono"(?:\s+style="[^"]*")?>\s*\d+s\s*(?:⚡)?\s*</td>', '', html)
html = re.sub(r'<td class="mono"(?:\s+style="[^"]*")?>\s*\d+m\s+\d+s\s*</td>', '', html)
html = re.sub(r'<td class="mono"(?:\s+style="[^"]*")?>\s*1m\s+\d+s.*?</td>', '', html)

after = len(re.findall(r'<td[^>]*>\s*\d+[ms]', html))

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Before: {before} | After: {after} | Removed: {before-after}')
