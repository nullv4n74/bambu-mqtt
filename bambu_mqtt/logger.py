"""Configure application-wide colored logging."""

import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Format log records with colors based on severity."""

    RESET = "\033[0m"
    COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[1;31m",  # Bold red
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with a colored level name."""
        original_levelname = record.levelname
        color = self.COLORS.get(record.levelno, self.RESET)

        record.levelname = f"{color}{original_levelname}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname


def configure_logging(level: int = logging.INFO) -> None:
    """Configure colored console logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColoredFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
