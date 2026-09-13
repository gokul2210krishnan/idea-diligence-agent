"""
Data Sanitizer — Untrusted web content isolation.

This is the THIRD defense boundary. All text returned from external web
requests is processed through this module before reaching any agent's
context window.

Sanitization steps:
  1. Strip <script>, <style>, HTML comments, and invisible Unicode chars
  2. Truncate to a safe length
  3. Wrap in an inert XML envelope: <untrusted_external_evidence source="...">

The envelope acts as a semantic fence — the agent prompts instruct the LLM
to treat everything inside these tags as external data, not instructions.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_CONTENT_LENGTH = 15_000  # chars after sanitization
_ENVELOPE_TAG = "untrusted_external_evidence"

# Patterns to strip from raw HTML
_STRIP_PATTERNS = [
    # <script>...</script> blocks (including content)
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    # <style>...</style> blocks (including content)
    re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL),
    # HTML comments
    re.compile(r"<!--.*?-->", re.DOTALL),
    # HTML tags (but keep text content)
    re.compile(r"<[^>]+>"),
]

# Invisible / zero-width Unicode characters that could be used for steganography
_INVISIBLE_UNICODE = re.compile(
    "["
    "\u200b"  # zero-width space
    "\u200c"  # zero-width non-joiner
    "\u200d"  # zero-width joiner
    "\u200e"  # left-to-right mark
    "\u200f"  # right-to-left mark
    "\u2060"  # word joiner
    "\u2061"  # function application
    "\u2062"  # invisible times
    "\u2063"  # invisible separator
    "\u2064"  # invisible plus
    "\ufeff"  # zero-width no-break space (BOM)
    "\ufff9"  # interlinear annotation anchor
    "\ufffa"  # interlinear annotation separator
    "\ufffb"  # interlinear annotation terminator
    "]"
)

# Collapse runs of whitespace
_WHITESPACE_COLLAPSE = re.compile(r"\s{3,}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitize_web_content(raw_content: str, source_url: str) -> str:
    """Sanitize external web content and wrap in an inert envelope.

    Args:
        raw_content: The raw HTML/text returned from a web request.
        source_url: The URL the content was fetched from (for attribution).

    Returns:
        Sanitized text wrapped in <untrusted_external_evidence> tags.
    """
    text = raw_content

    # --- Step 1: Strip dangerous HTML elements ---
    for pattern in _STRIP_PATTERNS:
        text = pattern.sub("", text)

    # --- Step 2: Remove invisible Unicode ---
    text = _INVISIBLE_UNICODE.sub("", text)

    # --- Step 3: Collapse excessive whitespace ---
    text = _WHITESPACE_COLLAPSE.sub("\n\n", text)
    text = text.strip()

    # --- Step 4: Truncate ---
    if len(text) > _MAX_CONTENT_LENGTH:
        text = text[:_MAX_CONTENT_LENGTH] + "\n\n[Content truncated for safety]"

    # --- Step 5: Wrap in inert envelope ---
    # Escape any existing closing tags to prevent envelope escape
    safe_url = source_url.replace('"', "&quot;")
    text = text.replace(f"</{_ENVELOPE_TAG}>", "")

    return (
        f'<{_ENVELOPE_TAG} source="{safe_url}">\n'
        f"{text}\n"
        f"</{_ENVELOPE_TAG}>"
    )


def strip_envelope(wrapped_content: str) -> str:
    """Remove the security envelope tags (for testing/debugging).

    Args:
        wrapped_content: Content previously wrapped by sanitize_web_content.

    Returns:
        The inner text without envelope tags.
    """
    pattern = re.compile(
        rf"<{_ENVELOPE_TAG}[^>]*>\n?(.*?)\n?</{_ENVELOPE_TAG}>",
        re.DOTALL,
    )
    match = pattern.search(wrapped_content)
    return match.group(1) if match else wrapped_content
