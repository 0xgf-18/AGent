#!/usr/bin/env python3
"""
Knowledge Base Graph Generator & Visualizer Launcher

Parses all Markdown files in vault/articles/, extracts Obsidian links [[wiki/...]],
builds a node-edge graph, saves it to vault/visualizer/graph_data.js,
and optionally opens the web visualizer in the default browser.
"""

import os
import re
import sys
import json
import argparse
import webbrowser
from pathlib import Path

# Try parsing YAML frontmatter cleanly if PyYAML is installed, fallback to regex
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def extract_frontmatter_and_content(file_path: Path):
    """Reads markdown file and extracts YAML frontmatter and body."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return {}, ""

    frontmatter = {}
    content = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_str = parts[1].strip()
            content = parts[2]
            if HAS_YAML:
                try:
                    frontmatter = yaml.safe_load(fm_str) or {}
                except Exception:
                    pass
            if not frontmatter:
                # Basic regex fallback for key-value extraction
                for line in fm_str.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        frontmatter[k.strip()] = v.strip().strip('"').strip("'")

    return frontmatter, content


def parse_title(frontmatter: dict, content: str, file_path: Path) -> str:
    """Extracts H1 header or title from frontmatter or filename."""
    if "title" in frontmatter and frontmatter["title"]:
        return str(frontmatter["title"])
    
    # Check for H1 header in content
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
            
    # Fallback to file name without extension
    stem = file_path.stem
    if stem.startswith("_"):
        return stem.replace("_", "").title() + " Index"
    return stem.replace("-", " ").title()


def parse_topic(file_path: Path, wiki_dir: Path) -> str:
    """Determines topic category based on relative directory path."""
    rel = file_path.relative_to(wiki_dir)
    parts = rel.parts
    if len(parts) > 1:
        return parts[0]
    return "general"


def extract_links(content: str) -> list:
    """Extracts obsidian [[wiki/...]] links and markdown file links."""
    links = []
    
    # 1. Obsidian links: [[wiki/path/file|alias]] or [[wiki/path/file]]
    obsidian_matches = re.findall(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]", content)
    for target in obsidian_matches:
        target = target.strip()
        if not target.startswith("wiki/"):
            target = f"wiki/{target}"
        links.append(target)

    # 2. Markdown relative links: [label](path.md)
    md_matches = re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", content)
    for target in md_matches:
        if not target.startswith("http") and not target.startswith("#"):
            links.append(target)

    return links


def normalize_node_id(path_str: str) -> str:
    """Standardizes path strings into canonical node IDs."""
    path_str = path_str.replace("\\", "/").strip()
    if path_str.startswith("./"):
        path_str = path_str[2:]
    if not path_str.startswith("wiki/"):
        path_str = f"wiki/{path_str}"
    if path_str.endswith(".md"):
        path_str = path_str[:-3]
    return path_str.lower()


def build_graph(wiki_dir: Path):
    """Scans all markdown files in wiki_dir and returns nodes and links."""
    md_files = list(wiki_dir.rglob("*.md"))
    
    node_map = {}
    raw_edges = []
    
    # Topic colors mapping for UI rendering
    topic_colors = {
        "_root": "#a855f7",
        "packers": "#f97316",
        "techniques": "#10b981",
        "experiments": "#3b82f6",
        "success-traces": "#22d3ee",
        "apks": "#f59e0b",
        "tool-registry": "#64748b",
        "patterns": "#ec4899",
        "knowledge-diffs": "#84cc16",
        "rasp": "#ef4444",
        "protectors": "#f59e0b",
        "arch": "#3b82f6",
        "frida": "#10b981",
        "challenges": "#ec4899",
        "general": "#6b7280"
    }

    # Volatile / host-specific strings that must never surface in the graph UI
    # (device serials, Windows usernames, absolute host paths - device state is
    # runtime-only and never persisted; method knowledge keeps relative paths)
    VOLATILE_RX = [
        re.compile(r"[A-Za-z]:\\[^\s\"'`)\]]+"),     # windows absolute paths
        re.compile(r"\bF A H A D\b"),                # local Windows username
        re.compile(r"\b(?:NW2665880108060)\b"),      # known device serials
    ]

    def scrub(text: str) -> str:
        for rx in VOLATILE_RX:
            text = rx.sub("[redacted]", text)
        return text

    # Pass 1: Discover all Nodes
    for file_path in md_files:
        rel_path = file_path.relative_to(wiki_dir)
        # volatile topics (device state) never render in the graph
        if rel_path.parts and rel_path.parts[0] == "environments":
            continue
        node_id = f"wiki/{rel_path.as_posix()[:-3]}" if str(rel_path).endswith(".md") else f"wiki/{rel_path.as_posix()}"
        node_id_norm = normalize_node_id(node_id)
        
        fm, content = extract_frontmatter_and_content(file_path)
        title = parse_title(fm, content, file_path)
        topic = parse_topic(file_path, wiki_dir)
        
        if file_path.name == "_master-index.md":
            topic = "_root"

        node_type = fm.get("type", "concept" if "_index" in file_path.name else "article")
        complexity = fm.get("complexity", "intermediate")
        summary = scrub(str(fm.get("llm_summary", "")))
        content = scrub(content)
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        node_map[node_id_norm] = {
            "id": node_id_norm,
            "display_id": node_id,
            "title": scrub(title),
            "rel_path": f"vault/articles/{rel_path.as_posix()}",
            "topic": topic,
            "color": topic_colors.get(topic, "#8b5cf6"),
            "type": str(node_type),
            "complexity": str(complexity),
            "summary": str(summary) if summary else "No summary provided.",
            "tags": tags if isinstance(tags, list) else [],
            "content": content[:1500] + ("..." if len(content) > 1500 else ""),
            "val": 1  # Base weight for visualization radius
        }

        # Extract links
        extracted = extract_links(content)
        for target in extracted:
            target_norm = normalize_node_id(target)
            raw_edges.append((node_id_norm, target_norm))

    # Pass 2: Filter and Build Edges
    links = []
    edge_set = set()

    for source_id, target_id in raw_edges:
        if source_id in node_map:
            # Handle potential index fallbacks
            resolved_target = target_id
            if target_id not in node_map:
                if f"{target_id}/_index" in node_map:
                    resolved_target = f"{target_id}/_index"
                elif f"{target_id}/index" in node_map:
                    resolved_target = f"{target_id}/index"

            if resolved_target in node_map and source_id != resolved_target:
                edge_key = (source_id, resolved_target)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    links.append({
                        "source": source_id,
                        "target": resolved_target
                    })
                    # Increase node weights based on connection degree
                    node_map[source_id]["val"] += 0.8
                    node_map[resolved_target]["val"] += 1.2

    nodes = list(node_map.values())
    return {"nodes": nodes, "links": links}


def main():
    parser = argparse.ArgumentParser(description="Generate Knowledge Base Graph Visualizer.")
    parser.add_argument("--open", action="store_true", help="Automatically open visualizer in default browser")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    kb_root = script_dir.parent.parent
    wiki_dir = kb_root / "vault" / "articles"
    graph_dir = kb_root / "vault" / "visualizer"

    if not wiki_dir.is_dir():
        print(f"Error: {wiki_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    graph_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning wiki at: {wiki_dir}")
    graph_data = build_graph(wiki_dir)

    # Write JS file for local browser access (avoids CORS restrictions with local file://)
    js_output_path = graph_dir / "graph_data.js"
    js_content = f"window.GRAPH_DATA = {json.dumps(graph_data, indent=2)};"
    js_output_path.write_text(js_content, encoding="utf-8")

    print(f"Successfully generated graph: {len(graph_data['nodes'])} nodes, {len(graph_data['links'])} edges.")
    print(f"Data saved to: {js_output_path}")

    html_path = graph_dir / "index.html"
    print(f"Visualizer ready at: file://{html_path}")

    if args.open:
        print("Opening visualizer in browser...")
        webbrowser.open(f"file://{html_path.resolve()}")


if __name__ == "__main__":
    main()
