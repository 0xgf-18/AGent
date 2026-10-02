# INGEST MODE — URL Crawl Protocol

> **Scope:** Crawling a URL into a raw markdown file with locally downloaded images.
> **Load when:** User says `ingest <url>` or provides a URL to add to the KB inbox.
> **After ingest:** Report the generated raw file path and downloaded images count. The user can run `compile <file>` when ready.
> **See also:** [write-pipeline.md](write-pipeline.md) | [core-rules.md](core-rules.md)

---

## 1. Execute the Crawl Script

Run the crawl script using the project's virtual environment:

```bash
.kb/scripts/.venv/bin/python .kb/scripts/crawl.py "<URL>"
```

Working directory: the KB project root (the directory containing `AGENTS.md`).

The script will:
- Fetch the page HTML with a realistic browser User-Agent
- Extract main article content using readability (strips nav/ads/footers)
- Download all images to `knowledge_base/raw/assets/<slug>/`
- Convert HTML → markdown with local image paths (`../assets/<slug>/image.png`)
- Save to `knowledge_base/raw/feeds/<slug>.md`

### First-Time Setup (if venv doesn't exist)

If the venv is missing, set it up:

```bash
python3 -m venv .kb/scripts/.venv
.kb/scripts/.venv/bin/pip install -r .kb/scripts/requirements.txt
```

---

## 2. Verify Output

After the script completes successfully, verify:

1. **Raw file exists:** The script prints the raw file path on success — confirm it exists.
2. **Content is substantial:** Open the raw file and confirm it has meaningful content.
3. **Images downloaded:** If the script reports N images, confirm the assets directory contains N image files.
4. **Image references resolve:** Spot-check that `![...](../assets/<slug>/...)` paths in the markdown point to real files.

---

## 3. Error Handling

If the script exits with a non-zero status:

| Error | Action |
|---|---|
| **HTTP 403 / bot protection** | Tell user: *"This page is blocked by bot protection. Use the Obsidian MarkDownload extension to manually crawl it, then place the `.md` file in `knowledge_base/raw/feeds/` and the images in `knowledge_base/raw/assets/<name>/`."* |
| **Empty/short content** | The page is likely JavaScript-rendered (SPA). Same manual fallback as above. |
| **Network/timeout error** | Ask user to verify the URL is correct and accessible. |
| **Missing venv** | Run the first-time setup commands from §1. |

---

## 4. Completion & Summary

Report completion to the user:
- Raw markdown file path: `knowledge_base/raw/feeds/<slug>.md`
- Downloaded assets directory: `knowledge_base/raw/assets/<slug>/`
- Total images/figures saved: `<count>`

Remind the user that the raw feed is ready in `raw/feeds/` and can be processed anytime using `compile <slug>.md`.

---

## 5. Log

Append to `knowledge_base/wiki/log.md`:

```markdown
## [YYYY-MM-DD] ingest | <URL>
- Crawl status: success | failed (<reason>)
- Raw file: <filename>
- Images downloaded: <count>
```
