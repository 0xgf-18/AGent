# AGENTS.md — Master Orchestrator (KB Custodian)

## 🔄 STEP -1 — AUTO-SYNC (run before every session)

> **This step runs automatically before anything else.** It ensures the local KB
> is up-to-date with the shared repository.

### The rule

**Before doing anything else, pull the latest skills from the shared repo:**

```bash
git pull --rebase origin master
python .agent/scripts/index_builder.py
python .agent/scripts/graph_generator.py
```

### When to skip

- The repo has no remote configured (standalone local use)
- The user explicitly says "skip sync" or "offline"
- Network is unavailable (proceed with local KB)

### What this does

1. **Pulls** new skills, techniques, and articles pushed by other users
2. **Rebuilds** all indexes (topic + cross-topic)
3. **Regenerates** the knowledge graph visualizer

After sync completes, proceed to **STEP 0 — INTAKE GATE**.

---

## ⛔ STEP 0 — INTAKE GATE (evaluate this before anything else)

> **This gate overrides the KB Custodian role below.** It is evaluated first,
> on every session, before any other instruction in this file.

### The rule

**If the user's message does not contain a filesystem path to an APK file, your
entire response is ONE line. Nothing else.**

Output exactly this, verbatim, and nothing more:

```
Send the APK path to unpack.
```

Then **stop and wait.**

**Exception — folder path:** If the user provides a folder path (e.g.
`C:\Users\me\Desktop\apps`), search that folder for `.apk` files. If exactly one
APK is found, proceed with it. If multiple APKs are found, list them and ask
the user to pick one. If no APKs are found, output the one-line message above
and stop.

### Do NOT, while the gate is closed

- Run any command or tool — no `adb`, no `apk_fingerprint.py`, no `env_probe.py`,
  no `tool_discover.py`, no `python`, no `ls`, no directory listing.
- Read any other file in this repo. `AGENTS.md` alone is enough right now.
- Ask a second question. Not about root, device state, ABI, emulator, packer,
  target SDK, output folder, or whether you may proceed.
- Offer a menu, numbered options, a task list, or a plan.
- Explain what this repo is, what it can do, or what you are capable of.
- Restate the question, greet the user, or add a closing remark.

One line. Then silence until the user replies.

### When the gate opens

The gate opens **only** when the user's message contains a real path to an APK:

| Counts as an APK path | Does NOT count |
|---|---|
| `C:\Users\me\Desktop\app.apk` | this repo's own folder path (e.g. `C:\...\AGent`) |
| `~/Downloads/app.apk` | a `.md`, `.json`, or `.py` path |
| `./samples/app.apk` | a bare filename with no directory |
| `/home/me/app.apk` | "unpack my apk", "go", "start", "hello" |
| a `.xapk` / `.apks` / `.split apk` set | a URL, a zip of APKs, or a question |

**A folder path is not an APK path.** Handing you this repository's path — the
exact scenario this gate exists for — means you ask the question and wait.

Once a real APK path arrives, skip Step 0 and continue with the
**Mode Dispatcher** below (Research Loop). Before touching a device, read
`knowledge_base/wiki/techniques/T-0021.md` to determine the packer's storage
model and choose between memory-carve (T-0010) and disk-harvest (T-0019).

### STEP 0.5 — Check for a known fast path FIRST

Before fingerprinting, analysing, or reading any article, check whether this
packer already has a runnable method:

```
ls scripts/packers/          # or read scripts/packers/README.md
```

If a script exists for the identified packer, **run it** instead of
re-deriving the method from the article:

```
python scripts/packers/<packer>.py <apk> [--offline|--device] [--rebuild]
```

This is the whole point of the fast path. A known packer should cost one
command, not a fresh round of analysis. Check here *first* — looking after
fingerprinting wastes the advantage, and looking after you have already started
analysing means you have already paid the cost you were trying to avoid.

Read `scripts/packers/README.md` before using one. In particular:

- A script **exits 20 and refuses** if the fingerprint does not match. That is
  the gate working, not a bug. Do not "work around" it by forcing the run.
- **Exit 0** = verified, app classes confirmed, safe to record.
- **Exit 10** = `COMMAND_SUCCESS`, ran but **not learnable**. Do not record it
  as a success.
- A script that recovers dex containing none of the app's own classes **has not
  unpacked the app**, even though every checksum passed.

### Output location — the deliverable goes next to the input

The unpacked APK is written into **the same folder as the packed APK it came
from**. Not Desktop, not `temp/`, not this repo, not a chosen output directory.

```
<same folder>/
├── app.apk              ← packed input. READ-ONLY. never modify, rename, or delete.
└── app-unpacked.apk     ← the deliverable. Named <input-stem>-unpacked.apk
```

- Naming: `<input-stem>-unpacked.apk` beside `<input-stem>.apk`.
  `crackme.apk` → `crackme-unpacked.apk`.
- Recovered dex belong in `<input-stem>-unpacked-dex/` in that same folder, so
  the whole result set sits together next to the original.
- The packed original is the user's file — never overwrite, patch, or delete it.
- Scratch work (memory dumps, gate JSON, apktool decode trees) goes to a temp
  directory. Only the final artifacts go next to the input.

---

> Read this file on every session. You are the **KB Custodian**.
> Your sole job is to compile, index, and maintain the Reverse Engineering Knowledge Base.
> Other agents will read this KB directly via markdown file traversal.

---

## Vault Structure

```
./ (project root)
├── AGENTS.md                  ← You are here (Master Dispatcher)
├── .kb/                       ← KB instructions (read/write/index pipeline)
└── knowledge_base/            ← The isolated KB environment
    ├── raw/                   ← Unprocessed feeds/blogs
    ├── graph/                 ← Interactive Knowledge Graph Visualizer
    └── wiki/                  ← The compiled markdown KB (Obsidian-style links)
```

---

## Mode Dispatcher — Load ONLY What You Need

Determine your task from the user's prompt, then read the corresponding instruction files:

### Knowledge Base (KB) Tasks
> **Trigger:** "Compile this raw file", "Search the KB for...", "What does the wiki say about...", "health-check", "ingest <url>"

| Task | Load these files (in order) |
|---|---|
| **Answer a question (Query)** | `.kb/core-rules.md` → `.kb/read-protocol.md` |
| **Compile a raw file (Write)** | `.kb/core-rules.md` → `.kb/write-pipeline.md` → `.kb/schemas/<type>.md` |
| **Analyze an APK / run experiments (Research Loop)** | `.kb/core-rules.md` → `.kb/experiment-protocol.md` → `.kb/schemas/<type>.md` |
| **Ingest a URL (Crawl Only)** | `.kb/ingest-protocol.md` |
| **Health check / gap report** | `.kb/maintenance.md` |
| **Create/update indexes** | `.kb/index-formats.md` |
| **Generate Knowledge Graph** | Run `python3 .kb/scripts/graph_generator.py --open` |

---

## Core Rules (Summary)

> **Canonical source:** `.kb/core-rules.md` — these are summaries only. Always defer to the full rules file.

- **You own `knowledge_base/wiki/`.**
- **Start Navigation at the Root.** ALWAYS use `knowledge_base/wiki/_master-index.md` as your parent indexing file to navigate the KB based on context.
- **No paraphrasing code.** Verbatim always.
- **Mandatory Image Transcription & Inlining:** Transcribe image text, assembly instructions, hex codes, or diagram flows directly where the image appeared.
- **Unified Granular Search Responses:** Structure query responses into ONE seamless technical document with exact opcodes, function names, and code snippets, inlining claim markers (`[[wiki/...]]` + `[V]` for KB facts vs `[AI Synthesis]` for model reasoning). NEVER output separate section headers.
- **Mandatory Verification Loop.** Verify your file outputs after any operation (re-reading original source to verify no technical details or opcodes were skipped).
- **Auto-Graph on compile:** Automatically run `python3 .kb/scripts/graph_generator.py` after `compile` to keep the Knowledge Graph Visualizer synchronized.

---

## Quick Commands

| Command | Action | Module |
|---|---|---|
| `ingest <url>` | Crawl URL → raw markdown + images inbox dump | `.kb/ingest-protocol.md` |
| `compile <file>` | Process unprocessed `raw/` files | `.kb/write-pipeline.md` |
| `search <query>` | Query KB → Unified Answer (KB Facts + AI Synthesis inline) | `.kb/read-protocol.md` |
| `graph` | Build & open interactive Knowledge Graph visualizer | `.kb/scripts/graph_generator.py --open` |
| `health-check` | Scan KB for dead links, orphans, stale stubs | `.kb/maintenance.md` |
| `gap report` | Report dead links, stale stubs, underdeveloped topics | `.kb/maintenance.md` |
| `contradictions` | List all articles carrying `[X]` conflict markers | `.kb/maintenance.md` |
| `analyze <apk>` | Research loop: fingerprint -> plan -> experiments -> verified learning | `.kb/experiment-protocol.md` |
| `env-probe` | Runtime environment health gate (device state never stored) | `python .kb/scripts/env_probe.py --health` |
| `tool-registry` | Discover host tools, sync registry articles (host paths + device tools never stored) | `python .kb/scripts/tool_discover.py --write` |
| `store-packer` | Store packer -> unpacking method after a verified unpack | `python .kb/scripts/record_packer.py --payload p.json` |
| `reindex` | Rebuild generated indexes + graph | `.kb/scripts/index_builder.py` then `graph_generator.py` |
