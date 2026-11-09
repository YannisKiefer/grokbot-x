"""Guard: the kit stays niche-agnostic and carries no company/person leaks.

Fails if any tracked file (outside the carve-outs below):

1. mentions a real company or person from this repo's history
   (ecombrain/EcomBrain, Yannis, Dawid, Kiefer, swissvogue, and the
   handles/domains found in git history: kieferyannis, yanniskiefer,
   ecombrain.io), or
2. contains ecommerce-specific vocabulary
   (checkout, sku, refund, Shopify, merchant, DTC, storefront, pixel).

Carve-outs:
- docs/analysis/ : working documents, deliberately out of scope.
- examples/profiles/ : user-niche example profiles; an ecommerce profile
  is a legitimate user niche there.
- README.md, site/, docs/brand/ : EcomBrain branding surfaces. Owner
  order 11-08 keeps them untouched; they may carry EcomBrain branding,
  links and the YannisKiefer GitHub URL. They are still checked for
  ecommerce vocabulary unless allowlisted below.

Remaining legitimate exceptions live in ALLOWLIST with a reason each.
Keep it short; new entries need a reason nobody has to guess at.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# --- 1. real company / person names from this repo's history ----------------
# Lowercase substrings (matched case-insensitively, word-ish boundaries).
# "kiefer" also catches "Kieferyannis"; "yanniskiefer" covers the GitHub
# handle; "ecombrain" covers "EcomBrain" and "ecombrain.io".
NAME_PATTERNS = [
    r"ecombrain",
    r"yannis",
    r"dawid",
    r"kiefer",
    r"swissvogue",
]

# --- 2. ecommerce-specific vocabulary ---------------------------------------
# Word boundaries; singular and plural. "pixel(s)" needs the allowlist for
# image-dimension uses.
VOCAB_PATTERN = (
    r"\b(checkouts?|skus?|refunds?|shopify|merchants?|dtc|storefronts?|pixels?)\b"
)

# Paths (posix, repo-rooted) exempt from the NAME check: branding surfaces,
# plus this file itself (it must spell out the names it guards against).
NAME_EXEMPT_PREFIXES = ("site/", "docs/brand/")
NAME_EXEMPT_FILES = {"README.md", "tests/test_generic.py"}

# Paths exempt from the VOCAB check: working docs, user-niche example
# profiles. Plus this file: its pattern string spells the vocabulary out.
EXEMPT_PREFIXES = ("docs/analysis/", "examples/profiles/")
EXEMPT_FILES = {"tests/test_generic.py"}

# Explicit, small allowlist: (posix path, matched term lowercase, reason).
ALLOWLIST = [
    # EcomBrain branding text kept per owner order 11-08 (site/ untouched).
    ("site/index.html", "shopify",
     "EcomBrain footer copy listing platforms it works inside; owner order keeps site/ as-is"),
    ("site/llms.txt", "shopify",
     "EcomBrain entity-schema text naming its platforms; owner order keeps site/ as-is"),
    # "pixels" as an image unit in the brand image-size spec, not ad tracking.
    ("docs/brand/IMAGE-PROMPTS.md", "pixel",
     "image dimensions in pixels (a unit), not an ad pixel"),
    # GitHub Actions step names, not ecommerce terms.
    (".github/workflows/ci.yml", "checkout",
     "actions/checkout step name, not a checkout flow"),
    (".github/workflows/pages.yml", "checkout",
     "actions/checkout step name, not a checkout flow"),
]

BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf"}


def tracked_files() -> list[Path]:
    """All tracked files, via git, with a plain filesystem fallback."""
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout
        return [REPO / line for line in out.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
        return [
            p
            for p in REPO.rglob("*")
            if p.is_file() and not (skip & set(p.relative_to(REPO).parts[:-1]))
        ]


def read_text(path: Path) -> str | None:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def allowlisted(rel: str, term: str) -> bool:
    return any(rel == path and term == allowed for path, allowed, _ in ALLOWLIST)


def test_no_company_or_person_mentions():
    pattern = re.compile("|".join(NAME_PATTERNS), re.IGNORECASE)
    hits = []
    for path in tracked_files():
        rel = path.relative_to(REPO).as_posix()
        if rel in NAME_EXEMPT_FILES or rel.startswith(NAME_EXEMPT_PREFIXES):
            continue
        text = read_text(path)
        if text is None:
            continue
        for m in pattern.finditer(text):
            if not allowlisted(rel, m.group(0).lower()):
                hits.append(f"{rel}: ...{text[max(0, m.start() - 30):m.end() + 30]!r}...")
    assert not hits, "Real company/person mentions outside branding surfaces:\n" + "\n".join(hits)


def test_no_ecommerce_vocabulary_outside_examples():
    pattern = re.compile(VOCAB_PATTERN, re.IGNORECASE)
    hits = []
    for path in tracked_files():
        rel = path.relative_to(REPO).as_posix()
        if rel in EXEMPT_FILES or rel.startswith(EXEMPT_PREFIXES):
            continue
        text = read_text(path)
        if text is None:
            continue
        for m in pattern.finditer(text):
            if not allowlisted(rel, m.group(0).lower().rstrip("s")):
                hits.append(f"{rel}: ...{text[max(0, m.start() - 30):m.end() + 30]!r}...")
    assert not hits, "Ecommerce vocabulary outside examples/profiles:\n" + "\n".join(hits)


def test_allowlist_entries_still_exist():
    """Every allowlist entry must still match its file, or be pruned."""
    stale = []
    for path, term, _reason in ALLOWLIST:
        text = read_text(REPO / path)
        if text is None or not re.search(rf"\b{term}s?\b", text, re.IGNORECASE):
            stale.append(f"{path}: term {term!r} no longer present; drop the entry")
    assert not stale, "Stale allowlist entries:\n" + "\n".join(stale)
