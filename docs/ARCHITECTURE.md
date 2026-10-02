# Architecture

## Overview

AGent is a three-tier system:

1. **User Commands** — `ingest`, `compile`, `search`, `analyze`
2. **AI Agent Orchestrator** — Behavioral rules + mode dispatcher
3. **Markdown Knowledge Vault** — Raw feeds → compiled graph nodes

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Commands                         │
│  ingest <url>  │  compile <file>  │  search <query>  │ ... │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI Agent Orchestrator                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  AGENTS.md  │  │   .agent/   │  │  Mode Dispatcher    │  │
│  │  (Rules)    │  │ (Firmware)  │  │  (Routing)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Markdown Knowledge Vault                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   inbox/    │  │  articles/  │  │    visualizer/      │  │
│  │  (Raw)      │  │  (Compiled) │  │    (Graph)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. AGENTS.md — Master Orchestrator

The entry point for every session. Contains:
- **Intake Gate** (Step 0) — Enforces APK path before any action
- **Mode Dispatcher** — Routes tasks to instruction files
- **Quick Commands** — Shorthand command reference

### 2. .agent/ — Agent Firmware

The agent's "firmware" — rules, protocols, schemas, and scripts.

| File | Purpose |
|------|---------|
| `core-rules.md` | Anti-hallucination system + behavioral rules |
| `read-protocol.md` | Query mode: how to traverse the KB |
| `write-pipeline.md` | Compile mode: raw → structured wiki |
| `ingest-protocol.md` | Crawl mode: URL → raw markdown |
| `index-formats.md` | Templates for indexes |
| `maintenance.md` | Health-check / gap reports |
| `experiment-protocol.md` | Research loop (APK analysis) |
| `schemas/` | Per-content-type article schemas |
| `scripts/` | Python scripts for automation |

### 3. knowledge_base/ — The Vault

All persistent state lives here.

| Directory | Purpose |
|-----------|---------|
| `inbox/` | Unprocessed feeds/reports + downloaded assets |
| `articles/` | The compiled markdown KB (Obsidian-style links) |
| `visualizer/` | Interactive knowledge-graph visualizer |

## Data Flow

### Ingest → Compile → Search

```
ingest <url>   →   compile <file>   →   search <query>
   crawl            structure             answer
   ─────            ─────────             ──────
 inbox/feeds/*    articles/**/*.md +    unified technical
 inbox/assets/*   updated indexes +     response with inline
                   regenerated graph     provenance markers
```

### Research Loop (APK Analysis)

```
analyze <apk>
    │
    ▼
┌─────────────────┐
│ 1. Environment  │  env_probe.py --health
│    & Tools      │  tool_discover.py
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 2. Fingerprint  │  apk_fingerprint.py
│    & Plan       │  kb_search.py
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 3. Experiments  │  verify_result.py
│    & Verify     │  record_experiment.py
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 4. Success      │  record_success_trace.py
    & Techniques  │  record_technique.py
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 5. Knowledge    │  index_builder.py
│    Graph        │  graph_generator.py
└─────────────────┘
```

## Design Principles

- **Files, not a database** — The entire KB is markdown + YAML on disk
- **Mechanisms are the unit of knowledge** — Articles split by technical mechanism
- **No orphans** — Every article is indexed and linked
- **Version-pin everything** — Tool and SDK versions are always explicit
- **Verify, then trust** — Mandatory verification loop

## Security Considerations

- **APK Analysis** — Analyzes potentially malicious APKs; run in sandbox
- **Token Security** — Never commit API tokens or credentials
- **File System** — Writes files next to input APKs; ensure backups
- **Network** — Crawl script fetches URLs; be cautious with untrusted sources
