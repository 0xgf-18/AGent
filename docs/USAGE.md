# Usage Guide

## Quick Start

### 1. Ingest a URL

```bash
python .agent/scripts/crawl.py "https://example.com/some-re-writeup"
```

This crawls the URL, extracts the main article, downloads images, and writes clean markdown to `knowledge_base/inbox/feeds/<slug>.md`.

### 2. Compile a Raw Feed

Ask your agent to compile a raw feed:

```
compile <slug>.md
```

The agent will:
1. Classify the content type
2. Load the matching schema
3. Split into hub + semantic chunks
4. Write YAML frontmatter and cross-links
5. Update indexes and graph

### 3. Search the Knowledge Base

Ask your agent to search:

```
search "DexProtector anti-frida"
```

The agent will:
1. Route through the master index
2. Navigate topic indexes
3. Read relevant articles
4. Compose a unified technical response with provenance markers

### 4. Analyze an APK

```
analyze C:\path\to\app.apk
```

The agent will:
1. Fingerprint the APK
2. Search the KB for known packer methods
3. Plan experiments
4. Run experiments with verification
5. Record results and extract techniques

## Commands

| Command | Action |
|---|---|
| `ingest <url>` | Crawl URL → raw markdown + local images |
| `compile <file>` | Process raw file → structured wiki articles |
| `search <query>` | Query KB → unified answer |
| `graph` | Build & open knowledge graph |
| `health-check` | Scan for dead links, orphans, stale stubs |
| `gap report` | Report dead links, stale stubs, underdeveloped topics |
| `contradictions` | List articles with `[X]` conflict markers |
| `analyze <apk>` | Research loop: fingerprint → plan → experiment → verify → learn |
| `env-probe` | Runtime environment health gate |
| `tool-registry` | Discover host tools, sync registry articles |
| `reindex` | Rebuild generated indexes + graph |

## Folder Path Exception

If you provide a folder path instead of an APK path, the agent will search for `.apk` files inside:

```
C:\Users\me\Desktop\apps
```

- **1 APK found** → proceeds automatically
- **Multiple APKs found** → lists them and asks you to pick one
- **No APKs found** → asks for an APK path

## Provenance Markers

Every factual claim in the KB carries a marker:

| Marker | Meaning |
|---|---|
| `[V]` | Verified — directly confirmed from the cited primary source |
| `[I]` | Inferred — logical conclusion from verified facts |
| `[U]` | Unverified — from blog/forum/secondary source |
| `[VS: Frida 16.x]` | Version-specific — only applies to stated version |
| `[X: see <article>]` | Contradicted — conflicts with another article |
| `[AI Synthesis]` | AI Model Intelligence — general pre-trained reasoning |

## Output Location

The unpacked APK is written **next to the packed APK it came from**:

```
<same folder>/
├── app.apk              ← packed input (READ-ONLY)
└── app-unpacked.apk     ← the deliverable
```

Recovered dex belong in `<input-stem>-unpacked-dex/` in that same folder.
