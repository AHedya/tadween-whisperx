import enum

from tadween_core.broker.base import BrokerListener


class Status(enum.Enum):
    PENDING = "⏳"
    RUNNING = "🏃"
    DONE = "✅"
    FAILED = "❌"
    SKIPPED = "➖"


class ProgressUIListener(BrokerListener):
    """
    Broker listener that tracks the progress of audio files through the pipeline
    and generates a rich render-able for the CLI.
    """

    def __init__(self):

        raise NotImplementedError()
