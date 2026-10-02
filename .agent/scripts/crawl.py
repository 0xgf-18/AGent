#!/usr/bin/env python3
"""
crawl.py — Portable web crawler for the Android RE Knowledge Base.

Fetches a URL, extracts main article content, downloads all images locally,
and produces a raw markdown file ready for the KB compile pipeline.

Usage:
    python crawl.py <URL> [--output-dir <path>]

Output:
    knowledge_base/raw/feeds/<slug>.md
    knowledge_base/raw/assets/<slug>/<image-files>

Dependencies (install via .kb/scripts/requirements.txt):
    requests, beautifulsoup4, markdownify, readability-lxml, lxml
"""

import argparse
import hashlib
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
import base64

import requests
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md, MarkdownConverter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

PAGE_TIMEOUT = 30       # seconds for the main page fetch
IMAGE_TIMEOUT = 15      # seconds per image download
MIN_IMAGE_SIZE = 1024   # skip images smaller than 1KB (tracking pixels)
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # skip images larger than 50MB

# Known image extensions
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".bmp", ".ico", ".tiff", ".tif", ".avif",
}

# Content-Type → extension mapping for when URL has no extension
CONTENT_TYPE_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/x-icon": ".ico",
    "image/tiff": ".tiff",
    "image/avif": ".avif",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(text: str, max_length: int = 80) -> str:
    """Convert a string to a filesystem-safe slug."""
    # Remove HTML entities and decode
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    # Replace non-alphanum with hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    text = re.sub(r"-+", "-", text).strip("-")
    # Truncate
    if len(text) > max_length:
        text = text[:max_length].rsplit("-", 1)[0]
    return text.lower() or "untitled"


def sanitize_filename(name: str) -> str:
    """Make a filename filesystem-safe while preserving extension."""
    # Decode URL encoding
    name = unquote(name)
    # Get basename
    name = os.path.basename(name)
    # Split name and extension
    stem, ext = os.path.splitext(name)
    # Sanitize the stem
    stem = re.sub(r"[^\w\s.-]", "_", stem)
    stem = re.sub(r"\s+", "_", stem).strip("_")
    # Truncate long names
    if len(stem) > 60:
        stem = stem[:60]
    return f"{stem}{ext}" if stem else f"image{ext}"


def get_image_extension(url: str, content_type: str | None = None) -> str:
    """Determine image file extension from URL or Content-Type."""
    # Try URL path first
    parsed = urlparse(url)
    path_ext = os.path.splitext(parsed.path)[1].lower()
    if path_ext in IMAGE_EXTENSIONS:
        return path_ext

    # Try Content-Type
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in CONTENT_TYPE_TO_EXT:
            return CONTENT_TYPE_TO_EXT[ct]

    # Fallback
    return ".png"


def extract_data_uri(data_uri: str) -> tuple[bytes, str] | None:
    """Decode a base64 data URI into (bytes, extension)."""
    match = re.match(r"data:(image/[^;]+);base64,(.*)", data_uri, re.DOTALL)
    if not match:
        return None
    mime_type = match.group(1)
    try:
        data = base64.b64decode(match.group(2))
    except Exception:
        return None
    ext = CONTENT_TYPE_TO_EXT.get(mime_type, ".png")
    return data, ext


# ---------------------------------------------------------------------------
# Custom MarkdownConverter — preserves code blocks and tables better
# ---------------------------------------------------------------------------


class KBMarkdownConverter(MarkdownConverter):
    """Custom converter with better code block and table handling."""

    def convert_pre(self, el, text, convert_as_inline):
        """Preserve <pre> blocks as fenced code blocks."""
        # Try to detect language from class
        code_el = el.find("code")
        lang = ""
        if code_el:
            classes = code_el.get("class", [])
            if isinstance(classes, list):
                for cls in classes:
                    if cls.startswith(("language-", "lang-", "highlight-")):
                        lang = cls.split("-", 1)[1]
                        break
                    # Some sites use just the language name as class
                    if cls in (
                        "javascript", "python", "java", "c", "cpp", "bash",
                        "shell", "json", "xml", "html", "css", "asm",
                        "arm", "aarch64", "smali", "kotlin", "swift",
                        "objc", "objective-c", "typescript", "rust", "go",
                    ):
                        lang = cls
                        break
            # Get the raw text from code element
            text = code_el.get_text()
        else:
            text = el.get_text()

        # Clean up but preserve content
        text = text.strip("\n")

        return f"\n\n```{lang}\n{text}\n```\n\n"


def convert_html_to_markdown(html: str) -> str:
    """Convert HTML to markdown using our custom converter."""
    return md(
        html,
        heading_style="ATX",
        code_language_callback=None,
        strip=["script", "style", "nav", "footer", "header", "noscript",
               "iframe", "form", "button", "input", "select", "textarea"],
        bullets="-",
        newline_style="backslash",
    )


# ---------------------------------------------------------------------------
# Core: Fetch, Extract, Download Images, Convert
# ---------------------------------------------------------------------------


def fetch_page(url: str) -> tuple[str, str]:
    """
    Fetch a URL and return (html_content, final_url).
    final_url accounts for redirects.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }
    resp = requests.get(url, headers=headers, timeout=PAGE_TIMEOUT, allow_redirects=True)
    resp.raise_for_status()

    # Detect encoding
    resp.encoding = resp.apparent_encoding or resp.encoding

    return resp.text, resp.url


def extract_title(html: str, readability_title: str) -> str:
    """
    Extract the best article title from HTML.
    Priority: og:title > first h1 > readability title > <title> tag.
    """
    soup = BeautifulSoup(html, "lxml")

    # Try first h1 (cleanest for article pages)
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(strip=True)
        if h1_text and len(h1_text) > 5:
            return h1_text

    # Try og:title (usually reliable, but may include site name)
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content", "").strip():
        og_text = og_title["content"].strip()
        # Strip common site name patterns: "Title - Site" or "Title | Site"
        cleaned = re.split(r"\s*[|–—]\s*", og_text, maxsplit=1)[0].strip()
        if cleaned and len(cleaned) > 5:
            return cleaned
        return og_text

    # Try readability title (often includes site name suffix)
    if readability_title:
        # Strip common site name patterns: "Title - Site" or "Title | Site"
        cleaned = re.split(r"\s*[|–—-]\s*", readability_title, maxsplit=1)[0].strip()
        if cleaned and len(cleaned) > 5:
            return cleaned
        return readability_title

    # Fallback to <title> tag
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)

    return "Untitled"


def extract_article(html: str, url: str) -> tuple[str, str]:
    """
    Use readability to extract main article content.
    Returns (article_html, title).
    """
    doc = Document(html, url=url)
    readability_title = doc.title()
    title = extract_title(html, readability_title)
    content_html = doc.summary(html_partial=True)
    return content_html, title


def extract_figures_from_original(
    original_html: str, article_soup: BeautifulSoup,
    base_url: str, assets_dir: Path, slug: str
) -> tuple[int, int]:
    """
    Scan original HTML for <figure> elements containing <img> or <svg>
    that readability may have stripped. Re-inject them into the article soup
    and save SVGs as .svg files.

    Returns (images_recovered, svgs_saved).
    """
    original_soup = BeautifulSoup(original_html, "lxml")
    images_recovered = 0
    svgs_saved = 0

    # Find the main content area in the article soup to append to
    body = article_soup.find("body") or article_soup

    # Collect all image URLs already in the article (for dedup)
    existing_srcs = set()
    for img in article_soup.find_all("img"):
        src = img.get("src", "")
        if src:
            existing_srcs.add(urljoin(base_url, src))

    # Process figures from original HTML
    for fig in original_soup.find_all("figure"):
        fig_id = fig.get("id", "")
        fig_class = " ".join(fig.get("class", []))

        # Skip decorative/layout figures (usually have position-absolute, etc.)
        if any(skip in fig_class for skip in ["position-absolute", "hero", "banner"]):
            continue

        # Case 1: Figure contains SVG (inline diagrams/disassembly)
        svg = fig.find("svg")
        if svg:
            svg_str = str(svg)
            # Skip tiny SVGs (likely decorative icons)
            if len(svg_str) < 200:
                continue

            # Save SVG to assets
            svg_hash = hashlib.md5(svg_str[:500].encode()).hexdigest()[:8]
            svg_name = f"figure_{fig_id or svg_hash}.svg" if fig_id else f"figure_{svg_hash}.svg"
            svg_name = sanitize_filename(svg_name)
            svg_path = assets_dir / svg_name
            if not svg_path.exists():
                svg_path.write_text(svg_str, encoding="utf-8")

            # Get caption if any
            caption_el = fig.find("figcaption")
            caption = caption_el.get_text(strip=True) if caption_el else fig_id or ""

            # Create an img reference in the article soup
            new_tag = article_soup.new_tag("p")
            img_tag = article_soup.new_tag(
                "img",
                src=f"../assets/{slug}/{svg_name}",
                alt=caption or f"Figure: {svg_name}"
            )
            new_tag.append(img_tag)
            if caption:
                cap_tag = article_soup.new_tag("em")
                cap_tag.string = f" — {caption}"
                new_tag.append(cap_tag)
            body.append(new_tag)
            svgs_saved += 1
            continue

        # Case 2: Figure contains <img> not already in article
        img = fig.find("img")
        if img:
            src = img.get("src", "") or img.get("data-src", "")
            if not src:
                continue
            abs_src = urljoin(base_url, src)
            if abs_src in existing_srcs:
                continue  # Already in article

            # Clone the img into the article
            new_tag = article_soup.new_tag("p")
            img_tag = article_soup.new_tag(
                "img",
                src=src,
                alt=img.get("alt", "")
            )
            new_tag.append(img_tag)
            caption_el = fig.find("figcaption")
            if caption_el:
                cap_tag = article_soup.new_tag("em")
                cap_tag.string = f" — {caption_el.get_text(strip=True)}"
                new_tag.append(cap_tag)
            body.append(new_tag)
            existing_srcs.add(abs_src)
            images_recovered += 1

    return images_recovered, svgs_saved


def download_image(
    img_url: str, save_dir: Path, session: requests.Session
) -> str | None:
    """
    Download a single image. Returns the local filename or None on failure.
    """
    try:
        resp = session.get(img_url, timeout=IMAGE_TIMEOUT, stream=True)
        resp.raise_for_status()

        # Check content type
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            return None

        # Check size from headers
        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) < MIN_IMAGE_SIZE:
            return None
        if content_length and int(content_length) > MAX_IMAGE_SIZE:
            return None

        # Read content
        content = resp.content
        if len(content) < MIN_IMAGE_SIZE:
            return None

        # Determine filename
        ext = get_image_extension(img_url, content_type)
        url_basename = os.path.basename(urlparse(img_url).path)
        if url_basename and os.path.splitext(url_basename)[1].lower() in IMAGE_EXTENSIONS:
            filename = sanitize_filename(url_basename)
        else:
            # Generate name from URL hash
            url_hash = hashlib.md5(img_url.encode()).hexdigest()[:10]
            filename = f"image_{url_hash}{ext}"

        # Handle duplicates
        save_path = save_dir / filename
        counter = 1
        while save_path.exists():
            stem, ext_part = os.path.splitext(filename)
            save_path = save_dir / f"{stem}_{counter}{ext_part}"
            counter += 1

        save_path.write_bytes(content)

        # Automatically convert .webp images to .png for model compatibility
        if save_path.suffix.lower() == ".webp":
            converted_path = ensure_png_format(save_path)
            return converted_path.name

        return save_path.name

    except Exception as e:
        print(f"  [WARN] Failed to download image {img_url}: {e}", file=sys.stderr)
        return None


def ensure_png_format(file_path: Path) -> Path:
    """
    Convert a .webp image to .png using native macOS `sips` tool or PIL.
    Returns the new PNG Path (or original Path if conversion fails).
    """
    if file_path.suffix.lower() != ".webp":
        return file_path

    png_path = file_path.with_suffix(".png")

    # Try native macOS sips command
    try:
        import subprocess
        res = subprocess.run(
            ["sips", "-s", "format", "png", str(file_path), "--out", str(png_path)],
            capture_output=True
        )
        if res.returncode == 0 and png_path.exists():
            file_path.unlink(missing_ok=True)
            return png_path
    except Exception:
        pass

    # Try PIL fallback
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            img.convert("RGB").save(png_path, "PNG")
        file_path.unlink(missing_ok=True)
        return png_path
    except Exception:
        pass

    return file_path


def process_images(
    soup: BeautifulSoup, base_url: str, assets_dir: Path, slug: str
) -> int:
    """
    Find all <img> tags, download images, rewrite src to local paths.
    Returns count of successfully downloaded images.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Referer": base_url,
    })

    downloaded = 0
    seen_urls = {}  # url → local_filename (deduplication)

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue

        # Skip images already pointing to local assets (placed by figure recovery)
        if src.startswith("../assets/"):
            continue

        # Handle data URIs
        if src.startswith("data:image/"):
            result = extract_data_uri(src)
            if result:
                data, ext = result
                if len(data) < MIN_IMAGE_SIZE:
                    continue
                url_hash = hashlib.md5(data[:256]).hexdigest()[:10]
                filename = f"data_image_{url_hash}{ext}"
                save_path = assets_dir / filename
                if not save_path.exists():
                    save_path.write_bytes(data)
                local_path = f"../assets/{slug}/{filename}"
                img["src"] = local_path
                downloaded += 1
            continue

        # Skip non-http URLs
        if src.startswith(("javascript:", "mailto:", "#")):
            continue

        # Resolve relative URLs
        abs_url = urljoin(base_url, src)

        # Check dedup
        if abs_url in seen_urls:
            local_path = f"../assets/{slug}/{seen_urls[abs_url]}"
            img["src"] = local_path
            continue

        # Download
        filename = download_image(abs_url, assets_dir, session)
        if filename:
            seen_urls[abs_url] = filename
            local_path = f"../assets/{slug}/{filename}"
            img["src"] = local_path
            downloaded += 1
            # Brief pause between downloads to be polite
            time.sleep(0.1)
        else:
            # Keep original URL if download failed (agent can still see it)
            pass

    return downloaded


def crawl(url: str, kb_root: Path) -> dict:
    """
    Main crawl pipeline.

    Returns a dict with:
        - slug: article slug
        - title: article title
        - raw_file: path to the generated markdown
        - assets_dir: path to the downloaded images directory
        - image_count: number of images downloaded
        - success: bool
        - error: error message if failed
    """
    result = {
        "slug": "",
        "title": "",
        "raw_file": "",
        "assets_dir": "",
        "image_count": 0,
        "success": False,
        "error": "",
    }

    # --- Step 1: Fetch ---
    print(f"[1/5] Fetching {url} ...")
    try:
        html, final_url = fetch_page(url)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            result["error"] = (
                f"HTTP 403 Forbidden — page likely has bot protection. "
                f"Use Obsidian MarkDownload extension to manually crawl this URL."
            )
        else:
            result["error"] = f"HTTP error: {e}"
        return result
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection error: {e}"
        return result
    except requests.exceptions.Timeout:
        result["error"] = f"Timeout after {PAGE_TIMEOUT}s fetching {url}"
        return result
    except Exception as e:
        result["error"] = f"Fetch failed: {e}"
        return result

    # --- Step 2: Extract main content ---
    print("[2/5] Extracting article content ...")
    try:
        article_html, title = extract_article(html, final_url)
    except Exception as e:
        result["error"] = f"Content extraction failed: {e}"
        return result

    if not article_html or len(article_html.strip()) < 100:
        result["error"] = (
            "Extracted content is empty or too short. "
            "Page may be JavaScript-rendered. "
            "Use Obsidian MarkDownload extension to manually crawl this URL."
        )
        return result

    slug = slugify(title)
    result["slug"] = slug
    result["title"] = title

    # --- Step 3: Download images + recover figures ---
    print("[3/5] Downloading images ...")
    assets_dir = kb_root / "knowledge_base" / "raw" / "assets" / slug
    assets_dir.mkdir(parents=True, exist_ok=True)
    result["assets_dir"] = str(assets_dir)

    soup = BeautifulSoup(article_html, "lxml")

    # Recover figures (SVGs, images) that readability stripped
    imgs_recovered, svgs_saved = extract_figures_from_original(
        html, soup, final_url, assets_dir, slug
    )
    if imgs_recovered > 0 or svgs_saved > 0:
        print(f"  Recovered {imgs_recovered} images + {svgs_saved} SVG figures from original HTML")

    # Download remote images (including recovered ones)
    image_count = process_images(soup, final_url, assets_dir, slug)
    image_count += svgs_saved  # SVGs already saved by extract_figures
    result["image_count"] = image_count
    print(f"  Total images/figures: {image_count}")

    # Clean up empty assets dir if no images
    if image_count == 0:
        try:
            assets_dir.rmdir()
            result["assets_dir"] = ""
        except OSError:
            pass  # directory not empty (maybe .DS_Store)

    # --- Step 4: Convert to markdown ---
    print("[4/5] Converting to markdown ...")
    # Get the modified HTML (with local image paths)
    modified_html = str(soup)
    markdown_content = convert_html_to_markdown(modified_html)

    # Clean up excessive whitespace
    markdown_content = re.sub(r"\n{4,}", "\n\n\n", markdown_content)

    # --- Step 5: Write output ---
    print("[5/5] Writing raw markdown ...")
    raw_dir = kb_root / "knowledge_base" / "raw" / "feeds"
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_file = raw_dir / f"{slug}.md"

    # Handle existing files — don't overwrite
    if raw_file.exists():
        counter = 1
        while raw_file.exists():
            raw_file = raw_dir / f"{slug}_{counter}.md"
            counter += 1

    # Prepend metadata header
    crawl_date = time.strftime("%Y-%m-%d")
    header = (
        f"<!-- source_url: {url} -->\n"
        f"<!-- crawl_date: {crawl_date} -->\n"
        f"<!-- images_downloaded: {image_count} -->\n\n"
        f"# {title}\n\n"
    )

    raw_file.write_text(header + markdown_content, encoding="utf-8")
    result["raw_file"] = str(raw_file)
    result["success"] = True

    return result


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Crawl a URL into a raw markdown file for the Reverse Engineering KB."
    )
    parser.add_argument("url", help="The URL to crawl")
    parser.add_argument(
        "--kb-root",
        default=None,
        help="Path to the KB project root (default: auto-detect from script location)",
    )
    args = parser.parse_args()

    # Determine KB root
    if args.kb_root:
        kb_root = Path(args.kb_root).resolve()
    else:
        # Script is at .kb/scripts/crawl.py → KB root is ../../
        kb_root = Path(__file__).resolve().parent.parent.parent

    # Verify KB structure
    if not (kb_root / "knowledge_base" / "raw").is_dir():
        print(
            f"ERROR: KB root not found at {kb_root}. "
            f"Expected knowledge_base/raw/ directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"KB root: {kb_root}")
    print(f"URL: {args.url}")
    print("---")

    result = crawl(args.url, kb_root)

    print("\n---")
    if result["success"]:
        print(f"SUCCESS")
        print(f"  Title: {result['title']}")
        print(f"  Slug: {result['slug']}")
        print(f"  Raw file: {result['raw_file']}")
        print(f"  Images downloaded: {result['image_count']}")
        if result["assets_dir"]:
            print(f"  Assets dir: {result['assets_dir']}")
        print(f"\nReady for: compile {Path(result['raw_file']).name}")
    else:
        print(f"FAILED: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
