# API Reference

## Script APIs

### `crawl.py`

Crawl a URL into a raw markdown file.

```bash
python .agent/scripts/crawl.py <URL> [--kb-root <path>]
```

**Arguments:**
- `url` — The URL to crawl
- `--kb-root` — Path to the KB project root (default: auto-detect)

**Output:**
- `knowledge_base/inbox/feeds/<slug>.md`
- `knowledge_base/inbox/assets/<slug>/<image-files>`

---

### `graph_generator.py`

Generate the knowledge graph visualizer.

```bash
python .agent/scripts/graph_generator.py [--open]
```

**Arguments:**
- `--open` — Automatically open visualizer in default browser

**Output:**
- `knowledge_base/visualizer/graph_data.js`

---

### `env_probe.py`

Probe the analysis environment.

```bash
python .agent/scripts/env_probe.py [--adb <path>] [--serial <serial>] [--health]
```

**Arguments:**
- `--adb` — Path to adb executable
- `--serial` — Device serial to target
- `--health` — One-line health verdict

**Exit Codes:**
- `0` — READY
- `2` — DEGRADED
- `3` — UNAVAILABLE
- `4` — ENVIRONMENT_ISSUE

---

### `tool_discover.py`

Discover tools and maintain the Tool Registry.

```bash
python .agent/scripts/tool_discover.py [--write] [--markdown] [--serial <serial>]
```

**Arguments:**
- `--write` — Create/update registry articles
- `--markdown` — Summary table instead of JSON
- `--serial` — ADB serial (device tools probed at runtime)

---

### `apk_fingerprint.py`

Fingerprint an APK.

```bash
python .agent/scripts/apk_fingerprint.py <apk> [--write] [--markdown] [--analysis-id <id>]
```

**Arguments:**
- `apk` — Path to the APK
- `--write` — Write wiki/apks/<A-ID>-<pkg>.md
- `--markdown` — Print draft article markdown
- `--analysis-id` — Reuse a specific A-XXXXXX id

**Exit Codes:**
- `0` — OK
- `1` — Bad input
- `4` — Tooling failure

---

### `verify_result.py`

Verification gate for experiment results.

```bash
python .agent/scripts/verify_result.py structural --file <path> [--kind <kind>]
python .agent/scripts/verify_result.py parser --dex <path> | --xml <path> | --json <path>
python .agent/scripts/verify_result.py content --file <path> [--entry <name>] [--class <class>] [--string <string>]
python .agent/scripts/verify_result.py downstream --tool <tool> --file <path>
python .agent/scripts/verify_result.py reproducibility --file <path> [--expected-sha <hex>]
python .agent/scripts/verify_result.py gate <result.json> [result2.json ...]
```

**Exit Codes:**
- Check: `0` PASS, `1` FAIL, `4` error
- Gate: `0` VERIFIED_SUCCESS, `10` COMMAND_SUCCESS, `1` FAILED, `4` error

---

### `record_experiment.py`

Record an experiment.

```bash
python .agent/scripts/record_experiment.py --payload <exp.json> [--stdin] [--dry-run]
```

---

### `record_packer.py`

Create or update a packer article.

```bash
python .agent/scripts/record_packer.py --payload <p.json> [--stdin] [--dry-run]
```

---

### `record_success_trace.py`

Record a success trace.

```bash
python .agent/scripts/record_success_trace.py --payload <st.json> [--stdin] [--dry-run]
```

---

### `record_technique.py`

Extract or update a technique article.

```bash
python .agent/scripts/record_technique.py --payload <t.json> [--stdin] [--dry-run]
```

---

### `index_builder.py`

Rebuild generated indexes.

```bash
python .agent/scripts/index_builder.py [--type <type>] [--force] [--dry-run]
```

---

### `kb_ids.py`

Allocate knowledge-base IDs.

```bash
python .agent/scripts/kb_ids.py [--list] [--next <prefix>] [--has <id>]
```

---

### `kb_search.py`

Search KB knowledge.

```bash
python .agent/scripts/kb_search.py [--indicators <list>] [--text <text>] [--analysis <id>] [--env <id>] [--markdown]
```

---

## ID Formats

| Prefix | Format | Width | Usage |
|--------|--------|-------|-------|
| A | A-XXXXXX | 6 | APK analysis |
| EXP | EXP-XXXX | 4 | Experiment |
| ST | ST-XXXX | 4 | Success trace |
| T | T-XXXX | 4 | Technique |
| ART | ART-XXXX | 4 | Artifact |
| P | P-XXXX | 4 | Pattern |
| KD | KD-XXXX | 4 | Knowledge diff |
| TR | TR-XXXX | 4 | Tool registry |

IDs are never reused — the allocator always returns (max_seen + 1).
