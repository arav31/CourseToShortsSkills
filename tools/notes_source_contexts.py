"""Select strong, note-ready source excerpts for a course concept."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


_CONNECTORS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "to", "using", "via", "with",
}
_WEAK_TOKENS = {
    "algorithm", "analysis", "application", "course", "example", "function",
    "introduction", "method", "model", "problem", "system", "theory",
}
_BAD_TITLE = re.compile(
    r"\b(?:calendar|syllabus|assignment|problem[ -]?set|homework|exam|quiz|"
    r"related resources|course home|navigation|schedule)\b",
    re.I,
)
_BAD_BLOCK = re.compile(
    r"\b(?:browse course material|skip to main content|course info|instructors?|"
    r"download course|problem set \d+|homework \d+|due date|office hours|"
    r"lecture calendar|weekly schedule|browser (?:is |may be )?out of date|"
    r"update (?:your )?browser|download (?:video|audio|transcript)|"
    r"transcript player|video player|playback speed|closed captions?|"
    r"previous lecture|next lecture)\b",
    re.I,
)
_CITATION_LINE = re.compile(
    r"^\s*(?:sources?|references?|bibliography|further reading|cite this|"
    r"https?://|www\.|doi:|isbn:)\b",
    re.I,
)
_FOOTNOTE_LINE = re.compile(
    r"^\s*(?:footnotes?\b|endnotes?\b|notes\s*$|\[\^?\d+\]|\^\d+\b|"
    r"\d{1,3}[.)]\s+(?:see|cf\.|ibid\b|https?://|[A-Z][\w'-]+,))",
    re.I,
)
_PAGE_BOUNDARY = re.compile(
    r"^\s*(?:\f+|[-=_ ]*page\s+\d+(?:\s+of\s+\d+)?[-=_ ]*|"
    r"[-=_]{3,}\s*(?:page\s+\d+)?\s*[-=_]{3,})\s*$",
    re.I,
)
_SOURCE_METADATA_LINE = re.compile(
    r"^\s*(?:source[_ -]?(?:digest|hash|id|metadata|record)|material[_ -]?id|"
    r"content[_ -]?(?:digest|hash)|sha(?:1|224|256|384|512))\s*[:=]",
    re.I,
)
_CONTINUATION = re.compile(
    r"^\s*(?:this|that|these|those|such|therefore|thus|consequently|as a result|"
    r"the\s+(?:relationship|result|conclusion|method|process|quantity|value|"
    r"bound|estimate|path|proof|derivation))\b",
    re.I,
)
_CONTENT_STOPWORDS = _CONNECTORS | _WEAK_TOKENS | {
    "also", "are", "be", "been", "being", "can", "could", "does", "each",
    "has", "have", "it", "its", "may", "more", "not", "one", "only", "other",
    "our", "same", "such", "than", "that", "their", "then", "there", "these",
    "they", "this", "those", "through", "thus", "was", "we", "were", "when",
    "which", "while", "will", "would", "you",
}
_HEADING = re.compile(
    r"^\s*(?:#{1,6}\s+|(?:chapter|lecture|section|unit|topic)\s+\d+[\w.:-]*\s*)?"
    r"([^.!?]{3,100})\s*$",
    re.I,
)
_INLINE_URL = re.compile(r"(?:https?://|www\.)\S+", re.I)
_MIN_SUBSTANTIVE_WORDS = 45


@dataclass(frozen=True)
class _Candidate:
    score: float
    material_index: int
    section_index: int
    text: str


def _normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _concept_terms(concept: str) -> tuple[str, list[str]]:
    words = [word for word in _normalized_words(concept) if word not in _CONNECTORS]
    phrase = " ".join(words)
    useful = [word for word in words if len(word) > 2 and word not in _WEAK_TOKENS]
    return phrase, useful or [word for word in words if len(word) > 2]


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 110 or _CITATION_LINE.match(stripped):
        return False
    if stripped.startswith("#"):
        return True
    if re.match(r"^(?:chapter|lecture|section|unit|topic)\b", stripped, re.I):
        return True
    return bool(_HEADING.match(stripped) and not re.search(r"[,;]", stripped) and len(stripped.split()) <= 12)


def _sections(text: str) -> Iterable[tuple[str, str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    heading = ""
    body: list[str] = []
    suppressed: str | None = None

    def flush() -> tuple[str, str] | None:
        nonlocal body
        if not body:
            return None
        section = (heading, "\n".join(body))
        body = []
        return section

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if _PAGE_BOUNDARY.match(line):
            section = flush()
            if section:
                yield section
            heading = ""
            suppressed = None
            continue
        if _FOOTNOTE_LINE.match(line) or _CITATION_LINE.match(line):
            section = flush()
            if section:
                yield section
            heading = ""
            suppressed = "references" if _CITATION_LINE.match(line) else "footnote"
            continue
        if _SOURCE_METADATA_LINE.match(line):
            section = flush()
            if section:
                yield section
            continue
        if _is_heading(line):
            section = flush()
            if section:
                yield section
            heading = re.sub(r"^#{1,6}\s*", "", line).strip()
            suppressed = None
        elif line:
            if suppressed:
                continue
            if _BAD_BLOCK.search(line):
                # Scraped transcript UI and lecture prose are frequently
                # flattened onto one line. Remove UI labels without discarding
                # the substantive sentences around them.
                line = _BAD_BLOCK.sub(" ", line)
                line = _INLINE_URL.sub(" ", line)
                line = re.sub(r"\s+", " ", line).strip(" .:-")
                if not line:
                    section = flush()
                    if section:
                        yield section
                    continue
            body.append(line)
        elif body:
            section = flush()
            if section:
                yield section
        elif suppressed == "footnote":
            suppressed = None
    section = flush()
    if section:
        yield section


def _term_span(words: list[str], terms: list[str]) -> int | None:
    positions = [[i for i, word in enumerate(words) if word == term] for term in terms]
    if not positions or any(not found for found in positions):
        return None
    return min(max(choice) - min(choice) for choice in _nearby_choices(positions))


def _nearby_choices(positions: list[list[int]]) -> Iterable[tuple[int, ...]]:
    """Yield only combinations near each possible anchor, avoiding a full product."""
    for anchor in positions[0]:
        yield tuple([anchor] + [min(group, key=lambda value: (abs(value - anchor), value)) for group in positions[1:]])


def _quality_score(title: str, heading: str, body: str, phrase: str, terms: list[str]) -> float | None:
    if _BAD_TITLE.search(title) or _BAD_TITLE.search(heading):
        return None
    clean = re.sub(r"\s+", " ", body).strip()
    words = _normalized_words(clean)
    if len(words) < 45 or _BAD_BLOCK.search(clean[:500]):
        return None
    sentences = re.findall(r"[^.!?]+[.!?]", clean)
    if len(sentences) < 2 or sum(ch.isalpha() for ch in clean) / max(len(clean), 1) < .55:
        return None

    normalized_body = " ".join(words)
    normalized_heading = " ".join(_normalized_words(heading))
    exact = phrase and phrase in normalized_body
    heading_exact = phrase and phrase in normalized_heading
    span = _term_span(words, terms)
    heading_span = _term_span(_normalized_words(heading), terms)
    if not exact and span is None and heading_span is None:
        return None
    # Broad terms are evidence only when tightly grouped or supported by a heading.
    if not exact and heading_span is None and (span is None or span > max(14, len(terms) * 5)):
        return None

    score = 10.0 if exact else 0.0
    score += 9.0 if heading_exact else 0.0
    score += 6.0 if heading_span is not None else 0.0
    score += max(0.0, 6.0 - (span or 0) / 4) if span is not None else 0.0
    score += min(3.0, len(sentences) / 3)
    score += 2.0 if re.search(r"\b(?:is defined|means|therefore|because|where|implies|equation|theorem)\b", clean, re.I) else 0.0
    return score


def _content_words(text: str) -> set[str]:
    return {
        word for word in _normalized_words(text)
        if len(word) > 2 and word not in _CONTENT_STOPWORDS
    }


def _sentence_relevance(sentence: str, terms: list[str]) -> int:
    words = _normalized_words(sentence)
    return sum(words.count(term) for term in terms)


def _is_noise(text: str) -> bool:
    stripped = text.strip()
    return bool(
        not stripped
        or _CITATION_LINE.match(stripped)
        or _FOOTNOTE_LINE.match(stripped)
        or _PAGE_BOUNDARY.match(stripped)
        or _SOURCE_METADATA_LINE.match(stripped)
        or _BAD_BLOCK.search(stripped)
        or re.search(r"https?://|\bdoi:\s*|\bsha256\s*[:=]", stripped, re.I)
    )


def _visible_excerpt(heading: str, body: str, terms: list[str]) -> str:
    # Newlines remain meaningful: PDF pages, HTML paragraphs, and transcript UI
    # frequently arrive as adjacent text with no machine-readable metadata.
    sentences: list[str] = []
    for block in body.splitlines():
        if _is_noise(block):
            continue
        sentences.extend(
            part.strip()
            for part in re.findall(r"[^.!?]+[.!?]|[^.!?]+$", block)
            if part.strip() and not _is_noise(part)
        )
    if not sentences:
        return ""

    relevance = [_sentence_relevance(sentence, terms) for sentence in sentences]
    anchor = max(range(len(sentences)), key=lambda index: (relevance[index], -index))
    start = max(0, anchor - 1)
    chosen = sentences[start:anchor + 1]
    focus = _content_words(" ".join([heading, sentences[anchor]]))
    pending_bridge: str | None = None
    for sentence in sentences[anchor + 1:]:
        words = _content_words(sentence)
        related = (
            bool(words & focus)
            or _sentence_relevance(sentence, terms) > 0
            or bool(_CONTINUATION.match(sentence))
        )
        if related:
            if pending_bridge:
                chosen.append(pending_bridge)
                focus.update(_content_words(pending_bridge))
                pending_bridge = None
            focus.update(words)
        else:
            # Keep one bridge sentence; two consecutive lexically disconnected
            # sentences are a reliable topic boundary in scraped course prose.
            if pending_bridge is not None:
                # Do not throw away an otherwise strong excerpt for falling a
                # word or two below the substantive-source gate. The first
                # bridge still belongs to the neighboring lecture prose; the
                # second disconnected sentence marks the topic boundary.
                if sum(len(item.split()) for item in chosen) < _MIN_SUBSTANTIVE_WORDS:
                    chosen.append(pending_bridge)
                break
            pending_bridge = sentence
            continue
        chosen.append(sentence)
        if sum(len(item.split()) for item in chosen) >= 150:
            break
    excerpt = " ".join(chosen)
    if heading and not _BAD_TITLE.search(heading):
        excerpt = f"{heading}. {excerpt}"
    return re.sub(r"\s+", " ", excerpt).strip()[:1800].rstrip()


def notes_source_contexts(pack: dict[str, object], concept: str, limit: int = 3) -> list[str]:
    """Return deterministic, substantive excerpts close to the requested concept."""
    if limit <= 0:
        return []
    phrase, terms = _concept_terms(concept)
    if not terms:
        return []
    materials = pack.get("materials")
    if not isinstance(materials, list):
        return []

    candidates: list[_Candidate] = []
    for material_index, material in enumerate(materials):
        if not isinstance(material, dict):
            continue
        title = str(material.get("title", ""))
        text = str(material.get("text", ""))
        for section_index, (heading, body) in enumerate(_sections(text)):
            score = _quality_score(title, heading, body, phrase, terms)
            if score is None:
                continue
            excerpt = _visible_excerpt(heading, body, terms)
            if len(excerpt.split()) >= _MIN_SUBSTANTIVE_WORDS:
                candidates.append(_Candidate(score, material_index, section_index, excerpt))

    ordered = sorted(candidates, key=lambda item: (-item.score, item.material_index, item.section_index, item.text))
    result: list[str] = []
    seen: set[str] = set()
    for candidate in ordered:
        fingerprint = " ".join(_normalized_words(candidate.text)[:80])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        result.append(candidate.text)
        if len(result) == limit:
            break
    if not result:
        # Some source packs contain only an authoritative calendar/index entry for
        # a unit, not prose suitable for quotation.  Preserve that weaker evidence
        # honestly instead of pretending it is a conceptual explanation.
        concept_words = _normalized_words(concept)
        normalized_phrase = " ".join(concept_words)
        phrase_pattern = re.compile(
            r"\b" + r"[^a-z0-9]+".join(re.escape(word) for word in concept_words) + r"\b",
            re.I,
        ) if concept_words else None
        for material in materials:
            if not isinstance(material, dict):
                continue
            clean_lines = []
            for raw_line in str(material.get("text", "")).splitlines():
                line = _BAD_BLOCK.sub(" ", raw_line)
                line = _INLINE_URL.sub(" ", line)
                line = re.sub(r"\s+", " ", line).strip(" .:-")
                if line and not _is_noise(line):
                    clean_lines.append(line)
            text = re.sub(r"\s+", " ", " ".join(clean_lines)).strip()
            if _CITATION_LINE.match(text) or _FOOTNOTE_LINE.match(text):
                continue
            normalized_text = " ".join(_normalized_words(text))
            if not normalized_phrase or normalized_phrase not in normalized_text or phrase_pattern is None:
                continue
            match = phrase_pattern.search(text)
            if match:
                result.append(match.group(0).strip())
            break
    return result
