"""Deterministic CJK bigram + ASCII tokenizer.

Strategy: cjk_bigram_ascii_v1
- Extract CJK and ASCII alphanumeric segments via regex
- CJK segments length>=2 → sliding bigrams; length==1 → single char
- ASCII segments → lowercase whole segment
- Other characters are separators; no cross-segment merging
- No stop words, synonym, normalization, or pinyin handling
"""

from __future__ import annotations

import re

_TOKENIZER_VERSION = "cjk_bigram_ascii_v1"

# Match CJK unified ideographs or ASCII alphanumeric runs
_SEGMENT_RE = re.compile(r"[一-鿿]+|[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Tokenize text into CJK bigrams and lowercase ASCII tokens.

    Args:
        text: Input string.

    Returns:
        Ordered list of tokens.

    Raises:
        ValueError: If text is not a str.
    """
    if not isinstance(text, str):
        raise ValueError("text 必须是字符串")

    tokens: list[str] = []
    for match in _SEGMENT_RE.finditer(text):
        seg = match.group()
        # Check if segment is CJK or ASCII
        if "一" <= seg[0] <= "鿿":
            # CJK segment
            if len(seg) == 1:
                tokens.append(seg)
            else:
                for i in range(len(seg) - 1):
                    tokens.append(seg[i : i + 2])
        else:
            # ASCII alphanumeric segment
            tokens.append(seg.lower())
    return tokens
