from typing_extensions import TypedDict


class SingleWordSegment(TypedDict):
    """
    A single word of a speech.
    """

    word: str
    start: float
    end: float
    score: float


class SingleCharSegment(TypedDict):
    """
    A single char of a speech.
    """

    char: str
    start: float
    end: float
    score: float


class SingleSegment(TypedDict):
    """
    A single segment (up to multiple sentences) of a speech.
    """

    start: float
    end: float
    text: str


class SingleAlignedSegment(TypedDict, total=False):
    """
    A single segment (up to multiple sentences) of a speech with word alignment.
    """

    start: float
    end: float
    text: str
    words: list[SingleWordSegment]
    chars: list[SingleCharSegment] | None
