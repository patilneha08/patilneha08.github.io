#!/usr/bin/env python3
"""
Blog generator for patilneha08.github.io
-----------------------------------------
Reads .txt files from the /blog folder, generates:
  - posts/<slug>.html  (individual post pages)
  - blog.html          (updated writing index)
  - index.html         (updated "Writing" section cards)

Txt file format (frontmatter + body):
--------------------------------------
title: My Post Title
tags: rag, llms
excerpt: One sentence teaser shown in cards.
date: 2025-06-10
---
Your full post content here.
Paragraphs separated by blank lines.
"""

import os, re, json, shutil
from datetime import datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent          # repo root
BLOG_DIR    = ROOT / "blog"                         # where .txt files live
POSTS_DIR   = ROOT / "posts"                        # generated HTML posts
BLOG_HTML   = ROOT / "blog.html"
INDEX_HTML  = ROOT / "index.html"

POSTS_DIR.mkdir(exist_ok=True)

# ── Tag meta (colour classes that already exist in your CSS) ─────────────────
TAG_CLASS = {
    "rag":    "rag",
    "llms":   "llms",
    "genai":  "genai",
    "agent":  "agent",
    "tools":  "tools",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text

def parse_txt(path: Path) -> dict:
    """Parse frontmatter + body from a .txt file."""
    raw = path.read_text(encoding="utf-8")
    meta = {"title": path.stem, "tags": [], "excerpt": "", "date": ""}
    body = raw

    if "---" in raw:
        fm_block, _, body = raw.partition("---")
        for line in fm_block.strip().splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key, val = key.strip().lower(), val.strip()
                if key == "tags":
                    meta["tags"] = [t.strip().lower() for t in val.split(",") if t.strip()]
                else:
                    meta[key] = val

    # Auto-date from file mtime if not specified
    if not meta["date"]:
        mtime = path.stat().st_mtime
        meta["date"] = datetime.fromtimestamp(mtime).strftime("%B %d, %Y")
    else:
        try:
            meta["date"] = datetime.strptime(meta["date"], "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            pass

    # Auto-excerpt from first paragraph if not specified
    body = body.strip()
    if not meta["excerpt"] and body:
        first_para = body.split("\n\n")[0].strip()
        meta["excerpt"] = first_para[:180] + ("…" if len(first_para) > 180 else "")

    meta["body"] = body
    meta["slug"] = slugify(meta["title"])
    meta["file"] = path.stem
    return meta

def body_to_html(body: str) -> str:
    """Convert plain text body to simple HTML paragraphs."""
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    html_parts = []
    for p in paragraphs:
        # Headings: lines starting with # or ##
        if p.startswith("## "):
            html_parts.append(f'<h2 class="post-h2">{p[3:]}</h2>')
        elif p.startswith("# "):
            html_parts.append(f'<h2 class="post-h2">{p[2:]}</h2>')
        else:
            lines = p.splitlines()
            text = "<br>".join(lines)
            html_parts.append(f"<p>{text}</p>")
    return "\n".join(html_parts)

def tag_badge(tag: str, for_post_page: bool = False) -> str:
    cls = TAG_CLASS.get(tag, "")
    if for_post_page:
        return f'<span class="post-tag {cls}">{tag.upper()}</span>'
    return f'<span class="post-tag {cls}">{tag.upper()}</span>'

# ── Post page template ────────────────────────────────────────────────────────

POST_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title} - Neha Patil</title>
<style>
:root {{
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
  --bg: #ffffff; --bg2: #f5f5f7;
  --text-primary: #1d1d1f; --text-secondary: #6e6e73; --text-tertiary: #86868b;
  --accent: #6e3aff; --accent-soft: #ede8ff; --divider: #d2d2d7;
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.07); --shadow-md: 0 4px 20px rgba(0,0,0,0.10);
  --radius: 18px; --radius-sm: 12px;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{ font-family: var(--font); background: var(--bg); color: var(--text-primary);
        font-size: 17px; line-height: 1.6; -webkit-font-smoothing: antialiased; }}
.page {{ max-width: 980px; margin: 0 auto; padding: 0 22px; }}
.site-nav {{ position: sticky; top: 0; z-index: 100;
  background: rgba(255,255,255,0.85); backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--divider); }}
.nav-inner {{ max-width: 980px; margin: 0 auto; padding: 0 22px;
  display: flex; align-items: center; justify-content: space-between; height: 52px; }}
.nav-logo {{ font-size: 15px; font-weight: 600; color: var(--text-primary); text-decoration: none; }}
.nav-links {{ display: flex; align-items: center; gap: 28px; list-style: none; }}
.nav-links a {{ font-size: 14px; color: var(--text-secondary); text-decoration: none; transition: color .15s; }}
.nav-links a:hover, .nav-links a.active {{ color: var(--accent); font-weight: 500; }}
.post-hero {{ padding: 64px 0 48px; border-bottom: 1px solid var(--divider); }}
.post-tags {{ display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; }}
.post-tag {{ padding: 3px 11px; background: var(--accent-soft); border-radius: 980px;
              font-size: 12px; font-weight: 600; color: var(--accent); }}
.post-tag.rag   {{ background: #e8f9f0; color: #1a9e5c; }}
.post-tag.llms  {{ background: #fff4e6; color: #c0640a; }}
.post-tag.genai {{ background: #fde8f8; color: #9b3faa; }}
.post-tag.agent {{ background: #e8f1ff; color: #1a52c0; }}
.post-tag.tools {{ background: #e8fafb; color: #0a7a8a; }}
.post-title {{ font-size: clamp(2rem, 4vw, 3rem); font-weight: 700;
               letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 16px; }}
.post-meta {{ font-size: 14px; color: var(--text-tertiary); }}
.post-body {{ max-width: 720px; padding: 56px 0 80px; }}
.post-body p {{ font-size: 17px; color: var(--text-secondary); line-height: 1.85;
                margin-bottom: 22px; }}
.post-h2 {{ font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em;
             margin: 44px 0 16px; color: var(--text-primary); }}
.back-link {{ display: inline-flex; align-items: center; gap: 6px;
              font-size: 14px; font-weight: 500; color: var(--accent);
              text-decoration: none; margin-bottom: 32px; }}
.back-link:hover {{ text-decoration: underline; }}
footer {{ background: var(--bg2); border-top: 1px solid var(--divider);
          padding: 44px 0; text-align: center; }}
.footer-name {{ font-size: 17px; font-weight: 600; margin-bottom: 6px; }}
.footer-sub  {{ font-size: 14px; color: var(--text-tertiary); }}
</style>
</head>
<body>
<nav class="site-nav">
  <div class="nav-inner">
    <a href="../index.html" class="nav-logo">Neha Patil</a>
    <ul class="nav-links">
      <li><a href="../index.html">About</a></li>
      <li><a href="../index.html#experience">Experience</a></li>
      <li><a href="../index.html#projects">Projects</a></li>
      <li><a href="../blog.html" class="active">Writing</a></li>
    </ul>
  </div>
</nav>
<div class="post-hero">
  <div class="page">
    <a href="../blog.html" class="back-link">← All posts</a>
    <div class="post-tags">{tag_badges}</div>
    <h1 class="post-title">{title}</h1>
    <div class="post-meta">{date}</div>
  </div>
</div>
<div class="page">
  <div class="post-body">
    {body_html}
  </div>
</div>
<footer>
  <div class="page">
    <div class="footer-name">Neha Patil</div>
    <div class="footer-sub">Writing about AI &nbsp;&middot;&nbsp; neha.patil.tech@gmail.com</div>
  </div>
</footer>
</body>
</html>
"""

# ── blog.html post row ────────────────────────────────────────────────────────

def make_post_row(post: dict) -> str:
    tags_html = "".join(tag_badge(t) for t in post["tags"])
    return f"""\
      <!-- POST: {post['slug']} -->
      <a href="posts/{post['slug']}.html" class="post-row" data-tags="{' '.join(post['tags'])}">
        <div class="post-row-left">
          <div class="post-row-tags">{tags_html}</div>
          <div class="post-row-title">{post['title']}</div>
          <div class="post-row-excerpt">{post['excerpt']}</div>
        </div>
        <div class="post-row-right">
          <div class="post-date">{post['date']}</div>
          <span class="post-arrow">→</span>
        </div>
      </a>"""

# ── index.html blog card ──────────────────────────────────────────────────────

def make_blog_card(post: dict) -> str:
    tag_label = post["tags"][0].upper() if post["tags"] else "AI"
    return f"""\
      <a href="posts/{post['slug']}.html" class="blog-card reveal">
        <div class="blog-card-top"><span class="blog-tag">{tag_label}</span><span class="blog-date">{post['date']}</span></div>
        <div class="blog-title">{post['title']}</div>
        <div class="blog-excerpt">{post['excerpt']}</div>
        <div class="blog-read">Read &rarr;</div>
      </a>"""

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not BLOG_DIR.exists():
        print(f"No blog/ folder found at {BLOG_DIR}. Creating it.")
        BLOG_DIR.mkdir()
        return

    txt_files = sorted(BLOG_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not txt_files:
        print("No .txt files found in blog/. Nothing to do.")
        return

    posts = [parse_txt(f) for f in txt_files]
    print(f"Found {len(posts)} post(s): {[p['slug'] for p in posts]}")

    # 1. Generate individual post HTML pages
    for post in posts:
        tag_badges_html = "".join(tag_badge(t, for_post_page=True) for t in post["tags"])
        body_html = body_to_html(post["body"])
        html = POST_TEMPLATE.format(
            title=post["title"],
            tag_badges=tag_badges_html,
            date=post["date"],
            body_html=body_html,
        )
        out = POSTS_DIR / f"{post['slug']}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  ✓ Written posts/{post['slug']}.html")

    # 2. Rebuild blog.html post list section
    if BLOG_HTML.exists():
        blog_src = BLOG_HTML.read_text(encoding="utf-8")
        rows_html = "\n".join(make_post_row(p) for p in posts)
        new_list = (
            f'    <div class="posts-list" id="postsList">\n'
            f'{rows_html}\n'
            f'    </div>'
        )
        # Replace everything between the posts-list div tags
        blog_src = re.sub(
            r'<div class="posts-list" id="postsList">.*?</div>',
            new_list,
            blog_src,
            flags=re.DOTALL,
        )
        BLOG_HTML.write_text(blog_src, encoding="utf-8")
        print("  ✓ Updated blog.html")

    # 3. Rebuild index.html Writing section (up to 3 latest cards)
    if INDEX_HTML.exists():
        index_src = INDEX_HTML.read_text(encoding="utf-8")
        latest = posts[:3]
        cards_html = "\n".join(make_blog_card(p) for p in latest)
        new_grid = (
            f'    <div class="blog-grid">\n'
            f'{cards_html}\n'
            f'    </div>'
        )
        index_src = re.sub(
            r'<div class="blog-grid">.*?</div>',
            new_grid,
            index_src,
            flags=re.DOTALL,
        )
        INDEX_HTML.write_text(index_src, encoding="utf-8")
        print("  ✓ Updated index.html Writing section (latest 3 cards)")

    print("\nDone! All files updated.")

if __name__ == "__main__":
    main()
