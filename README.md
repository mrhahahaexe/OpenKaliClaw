 👻 GHOST :: Autonomous Offensive Security Engine

> **"Reasoning is the ultimate weapon."**



This repository contains the official benchmark research comparing **Minimax** and **Codex** reasoning engines as the central intelligence for **GHOST** — an autonomous agent designed for end-to-end offensive operations.

## ◉ The Research: Minimax vs. Codex(more ai models are comming)
We evaluated these models across 15 high-fidelity sessions involving:
*   **Hacker101 CTF Track**: Real-world flag extraction across SQLi, Crypto, and IDOR vectors.
*   **Pentest-Ground Track**: Systematic vulnerability assessment against hardened targets.

### Key Finding
While Minimax showed high reliability in systematic recon, **Codex** demonstrated superior chaining capability — achieving a **4/5 completion rate** on targets where Minimax often reached "satisficing traps."

[→ View Full Research Dashboard](https://openkaliclaw.onrender.com)

---

## 💀 GHOST Engine Release
**Status: [UNDER ACTIVE DEVELOPMENT]**

GHOST is not just another script wrapper. It is a sovereign offensive architecture that uses multi-turn cognitive state management and historical memory chaining to navigate complex attack surfaces without human intervention.

The engine features:
- **Drip Memory Compression**: Infinite context window through recursive state distillation.
- **Sovereign Safety Engine**: Hardcoded ethical bounds that even the agent cannot bypass.
- **Multi-Vector Chaining**: Seamless pivoting between Browser, SSH, and Kali toolsets.

### Is it ready?
Not yet. The logs in this benchmark are live traces of the engine's current reasoning path. We are perfecting the **Metacognitive Error Recovery** before the public preview.

Stay tuned. When GHOST wakes up, the game changes.

---

## 📊 Benchmark System
This repo includes a modular benchmarking suite designed for scale.
*   **Static Viewer**: Headless mission traces with full tool-call visibility.
*   **Multi-DB Registry**: Support for historical data across multiple execution runs.
*   **Automated Metrics**: One-click generation of performance leaderboards.

### Running the Benchmark Site
```bash
# Sync dashboard with latest session data
python benchmark/scripts/build_all.py
```

---
*Disclaimer: All research performed in authorized, isolated environments. This software is for educational and professional security research only.some info and details results might not be fully correct and its prone to correction
*
