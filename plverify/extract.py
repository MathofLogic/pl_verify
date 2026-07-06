"""
plverify.extract — pull checkable claims out of derivation text.
==========================================================================
Two extraction modes, both deliberately CONSERVATIVE — a false extraction
becomes a false refutation, so precision outranks recall here (missed
steps cost coverage; wrong steps cost soundness, and soundness is the
product).

  1. GSM8K-style calculator annotations:  <<16-3-4=9>>
  2. Free-text equations:  "16 - 3 - 4 = 9", "9 * 2 = $18",
     "3 x 4 = 12", fraction and mixed-number claims ("= 1/20",
     "= 3 1/2"), percents normalised as N% -> (N/100).

Truncation guards (each skips extraction rather than risk a false
refutation — every guard below was added because a real GSM8K sentence
defeated the naive pattern; see docs/CALIBRATION.md):

  - a match preceded by a letter, digit, ')', '%', '/', ',' or '.' is a
    fragment of something bigger ("(1/2) 278 + 11 = 150") -> skip
  - a claim followed by more digits is a truncated space-grouped number
    ("$409 500") -> skip
  - a number token with leading zeros ("000") means we started
    mid-number -> skip
  - a digit-attached 'x' ("2x + 4") is a VARIABLE, not multiplication;
    algebra is beyond this instrument's theta -> skip

Everything here is a stipulated theta and says so in the manifest.
"""
from __future__ import annotations
import re

_INT = r"\d[\d,]*"
_NUM = rf"-?\$?{_INT}(?:\.\d+)?%?"
_CLAIM = (rf"-?\$?(?:{_INT} \d+/\d+"
          rf"|{_INT}(?:\.\d+)?(?:/{_INT})?)%?")
_EXPR = rf"{_NUM}(?:[ \t]*[-+*/x×÷\u2013\u2014\u2212][ \t]*\(?[ \t]*{_NUM}[ \t]*\)?)+"
_PART = rf"(?:{_EXPR}|{_CLAIM})"
ANNOT = re.compile(r"<<([^=<>]+)=([^=<>]+)>>")
FREE_EQ = re.compile(rf"({_EXPR})[ \t]*=[ \t]*({_CLAIM})")
FREE_CHAIN = re.compile(rf"({_EXPR})((?:[ \t]*=[ \t]*{_PART})+)")
_SPLIT_EQ = re.compile(r"[ \t]*=[ \t]*")
FINAL_GSM = re.compile(r"####\s*(-?\$?[\d,]+(?:\.\d+)?)")
FINAL_TEXT = re.compile(
    r"(?:answer|total|result)(?:\s+is)?\s*[:=]?\s*(-?\$?[\d,]+(?:\.\d+)?)",
    re.IGNORECASE)

_LEAD_ZERO = re.compile(r"(?<![\d.])0\d")
_VARIABLE_X = re.compile(r"\dx|x\d")


def _norm(s):
    """Currency and thousands-commas dropped, unicode operators mapped,
    spaced-x as multiplication, percents as (N/100), mixed numbers as
    sums."""
    s = s.strip().replace("$", "").replace(",", "")
    s = s.replace("×", "*").replace("÷", "/")
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")   # en/em dash, minus sign
    s = re.sub(r"(?<=[\d\s)])x(?=[\s(])|(?<=[\s)])x(?=[\s\d(])", "*", s)
    s = re.sub(r"(\d+) (\d+)/(\d+)", r"(\1 + \2/\3)", s)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", s)
    return s


def clean_expr(s):
    return _norm(s)


def clean_num(s):
    return _norm(s).rstrip(".")


def _guarded(text, m):
    """True if this free-text match risks truncation — skip it."""
    i = m.start() - 1
    while i >= 0 and text[i] == " ":
        i -= 1
    before = text[i] if i >= 0 else ""
    # an operator, close-paren, digit, or unicode numeric (¾) immediately
    # left of the match means we caught the TAIL of a larger expression
    # ("(1/2) 278 + 11", "3 1/2 - 2", "2x - 4 - 4", "¾ x 3/3") -> skip
    if before and (before in "+-*/x×÷()%,.=\u2013\u2014\u2212" or before.isdigit()
                   or (before.isnumeric() and not before.isascii())):
        return True
    tail = text[m.end():]
    if re.match(r"\s*\d", tail):
        return True
    raw = m.group(0)
    if _LEAD_ZERO.search(raw.replace(",", "")):
        return True
    if _VARIABLE_X.search(raw):
        return True
    return False


def extract_steps(text):
    """Return [(expr, claimed, source, pct_flag)] — annotations first,
    then guarded free-text equations. pct_flag marks a one-sided percent
    (a unit ambiguity the verifier resolves tolerantly or skips)."""
    steps, spans = [], []
    for m in ANNOT.finditer(text):
        e, c = m.group(1), m.group(2)
        steps.append((clean_expr(e), clean_num(c), "annotation",
                      ("%" in e) != ("%" in c)))
        spans.append(m.span())

    def inside(pos):
        return any(a <= pos < b for a, b in spans)

    for m in FREE_CHAIN.finditer(text):
        if inside(m.start()) or _guarded(text, m):
            continue
        parts = [m.group(1)] + [p for p in _SPLIT_EQ.split(m.group(2))
                                if p.strip()]
        # verify the chain PAIRWISE: a = b = c becomes (a,b) and (b,c);
        # one false link refutes, and the chain end links to the final.
        for lhs, rhs in zip(parts, parts[1:]):
            steps.append((clean_expr(lhs), clean_num(rhs), "freetext",
                          ("%" in lhs) != ("%" in rhs)))
    return steps


def extract_final(text):
    m = FINAL_GSM.search(text)
    if m:
        return clean_num(m.group(1))
    hits = FINAL_TEXT.findall(text)
    if hits:
        return clean_num(hits[-1])
    return None


def strip_annotations(text):
    """Turn <<a=b>> into nothing — simulates model output that has no
    calculator annotations."""
    return ANNOT.sub("", text)


def count_prose_sentences(text):
    sents = [s for s in re.split(r"[.\n]+", text) if s.strip()]
    return sum(1 for s in sents
               if not ANNOT.search(s) and not FREE_EQ.search(s))
