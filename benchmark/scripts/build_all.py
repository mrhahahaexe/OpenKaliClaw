import os, subprocess, sys

script_dir = os.path.dirname(os.path.abspath(__file__))
scripts = [
    "build_sessions.py",
    "build_index.py",
    "build_docs.py"
]

print("=== GHOST BENCHMARK SITE BUILDER ===")
for s in scripts:
    p = os.path.join(script_dir, s)
    if os.path.exists(p):
        print(f"\n--- Running {s} ---")
        try:
            # Run with same python executable
            result = subprocess.run([sys.executable, p], capture_output=True, text=True, check=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error running {s}:")
            print(e.stderr)
    else:
        print(f"Skipping {s} (not found)")

print("\nBuild complete. All static pages updated in /benchmark/")
