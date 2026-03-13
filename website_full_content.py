"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          FULL WEBSITE CRAWLER → STRUCTURED PDF GENERATOR                   ║
║          Expert-grade BFS Crawler + ReportLab PDF Engine                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

REQUIRED INSTALLATION:
    pip install requests beautifulsoup4 reportlab lxml

USAGE:
    python website_full_content.py
    ── or ──
    python website_full_content.py --url https://drmcet.ac.in
    python website_full_content.py --url https://drmcet.ac.in --max-pages 500
    python website_full_content.py --url https://drmcet.ac.in --delay 1.0

OUTPUT:
    website_full_content.pdf  (saved in the same folder as this script)
"""

# ─────────────────────────────────────────────────────────────────────────────
#  STANDARD LIBRARY
# ─────────────────────────────────────────────────────────────────────────────
import sys
import os
import re
import time
import argparse
import logging
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
#  THIRD-PARTY  (pip install requests beautifulsoup4 reportlab lxml)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("❌  'requests' not found.  Run:  pip install requests")

try:
    from bs4 import BeautifulSoup, Comment, NavigableString, Tag
except ImportError:
    sys.exit("❌  'beautifulsoup4' not found.  Run:  pip install beautifulsoup4 lxml")

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        HRFlowable, Table, TableStyle, KeepTogether
    )
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    sys.exit("❌  'reportlab' not found.  Run:  pip install reportlab")


# ═════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION  — tweak these as needed
# ═════════════════════════════════════════════════════════════════════════════

DEFAULT_MAX_PAGES   = 2000       # upper safety ceiling  (0 = unlimited)
DEFAULT_DELAY       = 0.5        # seconds between requests
REQUEST_TIMEOUT     = 20         # seconds per request
MAX_RETRIES         = 3          # automatic retry count for failed requests
MAX_CONTENT_CHARS   = 15_000     # max chars extracted per page before truncation
OUTPUT_FILENAME     = "website_full_content.pdf"

# Tags whose entire subtree is junk
STRIP_TAGS = {
    "script", "style", "noscript", "iframe", "embed", "object",
    "svg", "canvas", "video", "audio", "map", "track",
    "head", "meta", "link",
}

# Tags that are structural noise (nav, header, footer, sidebar …)
NOISE_TAGS = {"nav", "header", "footer", "aside", "form"}

# Class / ID substrings that signal noise elements
NOISE_RE = re.compile(
    r"(nav(bar|igation)?|breadcrumb|menu|sidebar|side[-_]?bar|"
    r"footer|header|topbar|toolbar|masthead|"
    r"cookie|gdpr|consent|popup|modal|overlay|lightbox|"
    r"advertisement|advert|ad[-_]|banner|sponsor|promo|"
    r"social[-_]|share[-_]|follow[-_]|"
    r"comment|disqus|livechat|"
    r"widget|carousel|slider|ticker|marquee|"
    r"login|signin|signup|register|subscribe|newsletter|"
    r"search[-_]bar|search[-_]box|pagination|pager|"
    r"print[-_]|no[-_]print|skip[-_]link)",
    re.IGNORECASE,
)

# URL patterns to skip
SKIP_URL_RE = re.compile(
    r"(login|logout|signin|signup|register|cart|checkout|"
    r"account|profile|password|reset|forgot|"
    r"\.pdf$|\.jpg$|\.jpeg$|\.png$|\.gif$|\.svg$|\.webp$|"
    r"\.zip$|\.rar$|\.exe$|\.doc$|\.docx$|\.xls$|\.xlsx$|"
    r"\.mp3$|\.mp4$|\.avi$|\.mov$|\.wmv$|"
    r"javascript:|mailto:|tel:|fax:|whatsapp:|"
    r"facebook\.com|twitter\.com|instagram\.com|linkedin\.com|"
    r"youtube\.com|t\.me|wa\.me|pinterest\.com)",
    re.IGNORECASE,
)

# ─────────────────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("crawler")


# ═════════════════════════════════════════════════════════════════════════════
#  URL UTILITIES
# ═════════════════════════════════════════════════════════════════════════════

def normalise_url(raw: str) -> str:
    """Add scheme if missing, strip fragment, normalise trailing slash."""
    raw = raw.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    p = urlparse(raw)
    # Remove fragment, normalise path
    clean = urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/") or "/",
                        p.params, p.query, ""))
    return clean


def get_base_domain(url: str) -> str:
    """Return netloc (lowercased) without leading 'www.'."""
    return urlparse(url).netloc.lower().lstrip("www.")


def is_internal(url: str, base_domain: str) -> bool:
    """True if url belongs to base_domain (including subdomains)."""
    host = urlparse(url).netloc.lower().lstrip("www.")
    return host == base_domain or host.endswith("." + base_domain)


def should_skip(url: str) -> bool:
    """True if the URL matches known junk patterns."""
    return bool(SKIP_URL_RE.search(url))


# ═════════════════════════════════════════════════════════════════════════════
#  HTTP SESSION
# ═════════════════════════════════════════════════════════════════════════════

def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=0.5,
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods={"GET", "HEAD"},
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    return session


def fetch(url: str, session: requests.Session) -> tuple[str, str]:
    """
    Fetch url.  Returns (html_text, final_url) or ("", url) on failure.
    """
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        final_url = resp.url
        ct = resp.headers.get("Content-Type", "")
        if resp.status_code != 200:
            log.debug("  HTTP %d  %s", resp.status_code, url)
            return "", final_url
        if "text/html" not in ct:
            log.debug("  Non-HTML (%s)  %s", ct.split(";")[0], url)
            return "", final_url
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text, final_url
    except requests.exceptions.TooManyRedirects:
        log.warning("  Too many redirects: %s", url)
    except requests.exceptions.SSLError:
        log.warning("  SSL error: %s", url)
    except requests.exceptions.ConnectionError:
        log.warning("  Connection error: %s", url)
    except requests.exceptions.Timeout:
        log.warning("  Timeout: %s", url)
    except Exception as exc:
        log.warning("  Unexpected error (%s): %s", type(exc).__name__, url)
    return "", url


# ═════════════════════════════════════════════════════════════════════════════
#  HTML CONTENT EXTRACTION
# ═════════════════════════════════════════════════════════════════════════════

def _safe_attrs(tag) -> tuple[str, str]:
    """Safely get class string and id from a BS4 tag."""
    if tag is None or not isinstance(tag, Tag):
        return "", ""
    attrs = tag.attrs if tag.attrs else {}
    cls_list = attrs.get("class", [])
    if isinstance(cls_list, list):
        cls = " ".join(cls_list)
    else:
        cls = str(cls_list)
    tid = attrs.get("id", "") or ""
    if not isinstance(tid, str):
        tid = " ".join(tid) if isinstance(tid, list) else str(tid)
    return cls, tid


def _is_noise(tag) -> bool:
    """Return True if this element looks like navigation / ads / junk."""
    cls, tid = _safe_attrs(tag)
    combined = cls + " " + tid
    return bool(NOISE_RE.search(combined))


def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """Strip all noise from the parsed tree in-place and return soup."""
    # 1. Remove comment nodes
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # 2. Remove pure-junk tags by name
    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()

    # 3. Remove structural noise tags (nav, footer, header, aside, form)
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    # 4. Remove elements whose class/id match noise patterns
    #    Iterate over a stable copy to avoid mutation-during-iteration
    for tag in list(soup.find_all(True)):
        try:
            if _is_noise(tag):
                tag.decompose()
        except Exception:
            pass

    return soup


def extract_table_text(table_tag) -> list[str]:
    """Convert an HTML table into a list of row strings."""
    rows_text = []
    for row in table_tag.find_all("tr"):
        cells = row.find_all(["th", "td"])
        cell_texts = []
        for cell in cells:
            ct = cell.get_text(" ", strip=True)
            ct = re.sub(r"\s+", " ", ct)
            if ct:
                cell_texts.append(ct)
        if cell_texts:
            rows_text.append("  |  ".join(cell_texts))
    return rows_text


def extract_page_content(html: str, page_url: str) -> dict:
    """
    Parse HTML and return:
        title   (str)
        blocks  (list of dicts: {type, text})
        links   (list of str)
    Block types: h1 h2 h3 h4 para bullet table_row
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # ── Title ────────────────────────────────────────────────────────────────
    title_tag = soup.find("title")
    og_title  = soup.find("meta", property="og:title")
    if title_tag and title_tag.get_text(strip=True):
        title = title_tag.get_text(strip=True)
    elif og_title and og_title.get("content", "").strip():
        title = og_title["content"].strip()
    else:
        title = page_url

    # ── Collect links BEFORE cleaning ────────────────────────────────────────
    raw_links = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        abs_url = normalise_url(urljoin(page_url, href))
        if abs_url.startswith("http"):
            raw_links.append(abs_url)

    # ── Clean soup ───────────────────────────────────────────────────────────
    clean_soup(soup)

    # ── Find best content container ──────────────────────────────────────────
    main = (
        soup.find("main") or
        soup.find("article") or
        soup.find(id=re.compile(r"^(content|main[-_]content|page[-_]content|"
                                r"primary|post[-_]content|entry[-_]content)$",
                                re.I)) or
        soup.find(class_=re.compile(r"^(content|main[-_]content|page[-_]content|"
                                    r"primary|post[-_]content|entry[-_]content)$",
                                    re.I)) or
        soup.find("div", id=re.compile(r"content|main|body|wrapper", re.I)) or
        soup.find("div", class_=re.compile(r"content|main|body|wrapper", re.I)) or
        soup.find("body") or
        soup
    )

    # ── Extract structured blocks ─────────────────────────────────────────────
    blocks = []
    seen_texts = set()

    def add_block(btype: str, text: str):
        text = re.sub(r"[ \t]+", " ", text).strip()
        text = re.sub(r"\n{2,}", "\n", text)
        if not text or len(text) < 4:
            return
        key = text[:120].lower()
        if key in seen_texts:
            return
        seen_texts.add(key)
        blocks.append({"type": btype, "text": text})

    TAG_MAP = {
        "h1": "h1", "h2": "h2", "h3": "h3",
        "h4": "h4", "h5": "h4", "h6": "h4",
        "p": "para",
        "li": "bullet",
        "dt": "para", "dd": "para",
        "blockquote": "para",
        "pre": "para", "code": "para",
    }

    total_chars = 0
    for element in main.find_all(list(TAG_MAP.keys()) + ["table"]):
        if total_chars >= MAX_CONTENT_CHARS:
            add_block("para", "[… content truncated for length …]")
            break

        tag_name = element.name

        if tag_name == "table":
            for row_text in extract_table_text(element):
                add_block("table_row", row_text)
                total_chars += len(row_text)
            continue

        btype = TAG_MAP.get(tag_name, "para")
        text  = element.get_text(" ", strip=True)
        text  = re.sub(r"\s+", " ", text).strip()
        if text:
            add_block(btype, text)
            total_chars += len(text)

    return {"title": title, "blocks": blocks, "links": raw_links}


# ═════════════════════════════════════════════════════════════════════════════
#  BFS CRAWLER
# ═════════════════════════════════════════════════════════════════════════════

def crawl(start_url: str, max_pages: int, delay: float) -> list[dict]:
    """
    BFS crawl.  Returns list of page dicts: {url, title, blocks}.
    """
    start_url   = normalise_url(start_url)
    base_domain = get_base_domain(start_url)
    session     = build_session()

    visited  = set()          # normalised URLs already processed
    queued   = {start_url}    # normalised URLs already in queue
    queue    = deque([start_url])
    results  = []

    total_links_found = 0

    print()
    print("═" * 70)
    print(f"  WEBSITE CRAWLER  —  {start_url}")
    print(f"  Domain     : {base_domain}")
    print(f"  Max pages  : {'unlimited' if max_pages == 0 else max_pages}")
    print(f"  Delay      : {delay}s between requests")
    print("═" * 70)
    print()

    while queue:
        if max_pages and len(results) >= max_pages:
            log.info("Reached max-page limit (%d).", max_pages)
            break

        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        if should_skip(url):
            log.debug("  SKIP (pattern)  %s", url)
            continue

        page_num = len(results) + 1
        log.info("[%04d]  Fetching: %s", page_num, url)

        html, final_url = fetch(url, session)

        # If the server redirected to an external domain, discard
        if not is_internal(final_url, base_domain):
            log.debug("  Redirected out of domain → skip")
            continue

        if not html:
            continue

        data = extract_page_content(html, final_url)

        # ── Enqueue new internal links ────────────────────────────────────
        new_count = 0
        for link in data["links"]:
            nl = normalise_url(link)
            if (nl not in visited
                    and nl not in queued
                    and is_internal(nl, base_domain)
                    and not should_skip(nl)):
                queue.append(nl)
                queued.add(nl)
                new_count += 1
                total_links_found += 1

        block_count = len(data["blocks"])
        char_count  = sum(len(b["text"]) for b in data["blocks"])
        log.info("         ↳ \"%s\"", data["title"][:65])
        log.info("         ↳ %d content blocks  |  %d chars  |  +%d links queued",
                 block_count, char_count, new_count)

        if block_count > 0:
            results.append({
                "url":    final_url,
                "title":  data["title"],
                "blocks": data["blocks"],
            })

        if delay > 0:
            time.sleep(delay)

    print()
    print("═" * 70)
    print(f"  Crawl complete")
    print(f"  Pages visited   : {len(visited)}")
    print(f"  Pages with text : {len(results)}")
    print(f"  Total links found: {total_links_found}")
    print("═" * 70)
    print()
    return results


# ═════════════════════════════════════════════════════════════════════════════
#  PDF STYLES
# ═════════════════════════════════════════════════════════════════════════════

PAGE_W, PAGE_H = A4          # 595.27 × 841.89 pts
MARGIN_L = MARGIN_R = 2.2 * cm
MARGIN_T = MARGIN_B = 2.5 * cm
USABLE_W = PAGE_W - MARGIN_L - MARGIN_R


def build_styles():
    base = getSampleStyleSheet()

    def S(name, parent_name="Normal", **kw):
        p = base[parent_name] if parent_name in base else base["Normal"]
        return ParagraphStyle(name, parent=p, **kw)

    # ── Colours ──────────────────────────────────────────────────────────────
    NAVY    = colors.HexColor("#0d1b4b")
    INDIGO  = colors.HexColor("#283593")
    STEEL   = colors.HexColor("#37474f")
    SILVER  = colors.HexColor("#90a4ae")
    ACCENT  = colors.HexColor("#1565c0")
    LIGHT   = colors.HexColor("#e8eaf6")
    WHITE   = colors.white
    BLACK   = colors.HexColor("#212121")

    styles = {
        # Cover
        "cover_site":   S("cover_site",  "Title",
                           fontSize=30, textColor=NAVY,
                           alignment=TA_CENTER, spaceAfter=8, spaceBefore=0),
        "cover_sub":    S("cover_sub",   "Normal",
                           fontSize=13, textColor=STEEL,
                           alignment=TA_CENTER, spaceAfter=5),
        "cover_meta":   S("cover_meta",  "Normal",
                           fontSize=10, textColor=SILVER,
                           alignment=TA_CENTER, spaceAfter=3),

        # TOC
        "toc_title":    S("toc_title",   "Heading1",
                           fontSize=18, textColor=NAVY, spaceAfter=10),
        "toc_entry":    S("toc_entry",   "Normal",
                           fontSize=9,  textColor=INDIGO,
                           leading=14,  leftIndent=8),

        # Section headings
        "sec_heading":  S("sec_heading", "Heading1",
                           fontSize=15, textColor=NAVY,
                           spaceBefore=2, spaceAfter=4, leading=20),
        "sec_url":      S("sec_url",     "Normal",
                           fontSize=7.5, textColor=SILVER,
                           spaceAfter=5),
        "h1":           S("xh1",         "Heading2",
                           fontSize=13, textColor=INDIGO,
                           spaceBefore=8, spaceAfter=4),
        "h2":           S("xh2",         "Heading3",
                           fontSize=11.5, textColor=INDIGO,
                           spaceBefore=6, spaceAfter=3),
        "h3":           S("xh3",         "Heading4",
                           fontSize=10.5, textColor=STEEL,
                           spaceBefore=5, spaceAfter=2),
        "h4":           S("xh4",         "Normal",
                           fontSize=10, textColor=STEEL,
                           fontName="Helvetica-Bold",
                           spaceBefore=4, spaceAfter=2),

        # Body
        "para":         S("xpara",       "Normal",
                           fontSize=9.5, textColor=BLACK,
                           leading=15, spaceAfter=5,
                           alignment=TA_JUSTIFY),
        "bullet":       S("xbullet",     "Normal",
                           fontSize=9.5, textColor=BLACK,
                           leading=14, spaceAfter=3,
                           leftIndent=14, firstLineIndent=0),
        "table_row":    S("xtable_row",  "Normal",
                           fontSize=8.5, textColor=BLACK,
                           leading=13, spaceAfter=2,
                           leftIndent=6,
                           backColor=colors.HexColor("#f5f5f5")),

        # Page number footer
        "footer":       S("footer",      "Normal",
                           fontSize=8, textColor=SILVER,
                           alignment=TA_CENTER),

        # Summary
        "summary_h":    S("summary_h",   "Heading2",
                           fontSize=14, textColor=NAVY, spaceAfter=6),
        "summary_b":    S("summary_b",   "Normal",
                           fontSize=10, leading=16),
    }
    return styles


# ═════════════════════════════════════════════════════════════════════════════
#  PDF BUILDER
# ═════════════════════════════════════════════════════════════════════════════

_XML_ESC = str.maketrans({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
})

def _e(text: str) -> str:
    """XML-escape a string for use inside a Paragraph."""
    return str(text).translate(_XML_ESC)


def _para(text: str, style) -> Paragraph:
    return Paragraph(_e(text), style)


class _NumberedCanvas:
    """Mixin-style canvas wrapper that adds page numbers + header rule."""
    # We use a SimpleDocTemplate + onPage callback instead; see below.
    pass


def _on_page(canvas, doc):
    """Called for every page — draws header rule and footer page number."""
    canvas.saveState()
    # Top rule
    canvas.setStrokeColor(colors.HexColor("#0d1b4b"))
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN_L, PAGE_H - MARGIN_T + 4 * mm,
                PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 4 * mm)
    # Footer page number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#90a4ae"))
    canvas.drawCentredString(
        PAGE_W / 2,
        MARGIN_B - 10,
        f"Page {doc.page}"
    )
    canvas.restoreState()


def _on_first_page(canvas, doc):
    """Cover page — no header rule / footer."""
    pass


def build_pdf(pages: list[dict], output_path: str, site_url: str) -> int:
    """
    Build the PDF from crawled page data.
    Returns the number of PDF pages generated.
    """
    styles = build_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title=f"Full Website Content — {site_url}",
        author="Website Full Content Crawler",
        subject=f"Extracted on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    story = []
    NAVY  = colors.HexColor("#0d1b4b")
    LIGHT = colors.HexColor("#e8eaf6")

    # ──────────────────────────────────────────────────────────────────────────
    # COVER PAGE
    # ──────────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3.5 * cm))

    # Decorative top bar (Table trick for coloured background)
    bar_data = [[""]]
    bar_tbl  = Table(bar_data, colWidths=[USABLE_W], rowHeights=[10])
    bar_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    story.append(bar_tbl)
    story.append(Spacer(1, 0.8 * cm))

    story.append(_para("FULL WEBSITE CONTENT REPORT", styles["cover_site"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_para(site_url, styles["cover_sub"]))
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width=USABLE_W, thickness=1.5, color=NAVY))
    story.append(Spacer(1, 0.5 * cm))
    story.append(_para(f"Total pages crawled: {len(pages)}", styles["cover_meta"]))
    story.append(_para(
        f"Generated: {datetime.now().strftime('%d %B %Y  %H:%M')}",
        styles["cover_meta"]
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width=USABLE_W, thickness=0.5,
                             color=colors.HexColor("#90a4ae")))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE OF CONTENTS
    # ──────────────────────────────────────────────────────────────────────────
    story.append(_para("Table of Contents", styles["toc_title"]))
    story.append(HRFlowable(width=USABLE_W, thickness=0.5, color=NAVY))
    story.append(Spacer(1, 0.3 * cm))

    for idx, page in enumerate(pages, 1):
        title_short = page["title"][:90] + ("…" if len(page["title"]) > 90 else "")
        story.append(_para(f"{idx:04d}.  {title_short}", styles["toc_entry"]))

    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # ONE SECTION PER CRAWLED PAGE
    # ──────────────────────────────────────────────────────────────────────────
    for idx, page in enumerate(pages, 1):
        sec_items = []

        # Section header row (coloured background)
        hdr_text = f"{idx}.  {page['title'][:95]}"
        hdr_para = Paragraph(_e(hdr_text), styles["sec_heading"])
        hdr_data  = [[hdr_para]]
        hdr_tbl   = Table(hdr_data, colWidths=[USABLE_W])
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), LIGHT),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW",    (0, 0), (-1, -1), 1.2, NAVY),
        ]))
        sec_items.append(hdr_tbl)
        sec_items.append(_para(page["url"], styles["sec_url"]))
        sec_items.append(Spacer(1, 0.15 * cm))

        if not page["blocks"]:
            sec_items.append(
                _para("⚠ No readable content was extracted from this page.",
                      styles["para"])
            )
        else:
            TYPE_STYLE = {
                "h1":        styles["h1"],
                "h2":        styles["h2"],
                "h3":        styles["h3"],
                "h4":        styles["h4"],
                "para":      styles["para"],
                "bullet":    styles["bullet"],
                "table_row": styles["table_row"],
            }
            for block in page["blocks"]:
                btype = block["type"]
                btext = block["text"]
                sty   = TYPE_STYLE.get(btype, styles["para"])

                if btype == "bullet":
                    sec_items.append(Paragraph("• " + _e(btext), sty))
                elif btype == "table_row":
                    sec_items.append(Paragraph("▸  " + _e(btext), sty))
                else:
                    sec_items.append(Paragraph(_e(btext), sty))

        sec_items.append(Spacer(1, 0.6 * cm))

        # Keep heading + first few items together to avoid orphan headers
        try:
            story.append(KeepTogether(sec_items[:4]))
            story.extend(sec_items[4:])
        except Exception:
            story.extend(sec_items)

        if idx < len(pages):
            story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────────────
    # SUMMARY PAGE
    # ──────────────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 1 * cm))
    story.append(_para("Crawl Summary", styles["summary_h"]))
    story.append(HRFlowable(width=USABLE_W, thickness=1, color=NAVY))
    story.append(Spacer(1, 0.4 * cm))

    summary_lines = [
        f"Website URL      : {site_url}",
        f"Total pages      : {len(pages)}",
        f"Generated on     : {datetime.now().strftime('%d %B %Y at %H:%M:%S')}",
        f"Output file      : {output_path}",
    ]
    for line in summary_lines:
        story.append(_para(line, styles["summary_b"]))

    story.append(Spacer(1, 1 * cm))
    story.append(_para(
        "All content was extracted automatically by the Website Full Content Crawler. "
        "Content is organised page-by-page and reflects publicly accessible text "
        "found on the website at the time of crawling.",
        styles["para"]
    ))

    # ──────────────────────────────────────────────────────────────────────────
    # BUILD — track page count via a list
    # ──────────────────────────────────────────────────────────────────────────
    page_counts = []

    class _CountingCanvas:
        pass

    # Use a simple pageCountCollector via the doc.build callback
    pdf_pages = [0]

    def _on_page_normal(canvas, doc):
        _on_page(canvas, doc)
        pdf_pages[0] = doc.page

    log.info("Building PDF …  (%d sections)", len(pages))

    doc.build(
        story,
        onFirstPage=_on_first_page,
        onLaterPages=_on_page_normal,
    )

    return pdf_pages[0]


# ═════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Crawl a website and export all content to a structured PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--url",       default=None,
                        help="Starting URL  (e.g. https://drmcet.ac.in)")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                        help=f"Max pages to crawl (0 = unlimited, default {DEFAULT_MAX_PAGES})")
    parser.add_argument("--delay",     type=float, default=DEFAULT_DELAY,
                        help=f"Delay in seconds between requests (default {DEFAULT_DELAY})")
    parser.add_argument("--output",    default=OUTPUT_FILENAME,
                        help=f"Output PDF filename (default: {OUTPUT_FILENAME})")
    args = parser.parse_args()

    # ── Get URL ───────────────────────────────────────────────────────────────
    start_url = args.url
    if not start_url:
        print()
        print("╔══════════════════════════════════════════╗")
        print("║    WEBSITE FULL CONTENT → PDF CRAWLER   ║")
        print("╚══════════════════════════════════════════╝")
        print()
        start_url = input("  Enter website URL  (e.g. https://drmcet.ac.in): ").strip()
        if not start_url:
            print("No URL provided. Exiting.")
            sys.exit(1)

    start_url = normalise_url(start_url)

    # ── Crawl ─────────────────────────────────────────────────────────────────
    t0    = time.time()
    pages = crawl(start_url, args.max_pages, args.delay)

    if not pages:
        print()
        print("⚠  No content was collected.")
        print("   Possible reasons:")
        print("   • The site blocks automated scrapers (returns 403/429)")
        print("   • JavaScript rendering is required (static crawler can't help)")
        print("   • The domain is unreachable or SSL errors occurred")
        print()
        sys.exit(1)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    output_path = args.output
    print(f"Building PDF: {output_path}")
    print(f"Sections to write: {len(pages)}")
    print()

    try:
        pdf_page_count = build_pdf(pages, output_path, start_url)
    except Exception as exc:
        log.exception("PDF generation failed: %s", exc)
        sys.exit(1)

    elapsed = time.time() - t0
    file_kb = os.path.getsize(output_path) // 1024

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║                    COMPLETE ✅                       ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Website pages crawled : {len(pages):<28}║")
    print(f"║  PDF pages generated   : {pdf_page_count:<28}║")
    print(f"║  Output file           : {output_path:<28}║")
    print(f"║  File size             : ~{file_kb} KB{' '*(26-len(str(file_kb)))}║")
    print(f"║  Total time            : {elapsed:.1f}s{' '*(27-len(f'{elapsed:.1f}'))}║")
    print("╚══════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
