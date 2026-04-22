import re

import regex
from pydantic import BaseModel, SkipValidation, model_validator
from tadween_core.handler import BaseHandler
from typing_extensions import TypedDict


class SegmentLike(TypedDict, total=False):
    text: str


class NormalizerInput(BaseModel):
    # skip copy on validate. Hold reference, and validate manually
    segments: SkipValidation[list[SegmentLike]]
    allowed_chars: int = 3
    max_word_len: int = 20
    allowed_words: int = 2

    @model_validator(mode="before")
    @classmethod
    def check_segments_type(cls, data):
        segments = (
            data.get("segments")
            if isinstance(data, dict)
            else getattr(data, "segments", None)
        )
        if not isinstance(segments, list):
            raise ValueError("`segments` must be a list")
        return data


class NormalizeHandler(BaseHandler[NormalizerInput, NormalizerInput]):
    def warmup(self):
        pass

    def shutdown(self):
        pass

    def __init__(
        self, allowed_chars: int = 3, max_word_len: int = 20, allowed_words: int = 2
    ):
        self._allowed_chars = allowed_chars
        self._allowed_words = allowed_words
        self._max_word_len = max_word_len

    def run(self, inputs):
        for seg in inputs.segments:
            seg["text"] = collapse_phrase_opt(
                seg["text"],
                self._allowed_words,
                self._allowed_chars,
                self._max_word_len,
            )
        return inputs


def collapse_chars_opt(
    word: str, chars_allowed: int = 2, max_word_len: int = 20
) -> str:
    if not word:
        return ""
    word = word[:max_word_len]

    pattern = r"(\X+?)\1+"

    def replacement(m):
        return m.group(1) * min(
            len(m.group(0)) // len(m.group(1)),  # actual repeat count
            chars_allowed,
        )

    return regex.sub(pattern, replacement, word)


def collapse_phrase_opt(
    phrase: str, chars_allowed: int = 2, words_allowed: int = 2, max_word_len: int = 20
) -> str:
    if not phrase:
        return ""

    words = [collapse_chars_opt(w, chars_allowed, max_word_len) for w in phrase.split()]

    sentinel = "\x00"
    joined = sentinel.join(words)
    word_pattern = r"((?:[^\x00]+\x00)*?[^\x00]+?)(?:\x00\1)+"

    def replacement(m):
        return sentinel.join(
            [m.group(1)]
            * min((len(m.group(0)) + 1) // (len(m.group(1)) + 1), words_allowed)
        )

    result = re.sub(word_pattern, replacement, joined)
    return " ".join(result.split(sentinel))
