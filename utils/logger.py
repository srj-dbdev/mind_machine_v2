import logging
import os
from datetime import datetime


# ---------------------------------------------------
# Global logger instance
# ---------------------------------------------------

_logger = None


def setup_logger():
    """
    Sets up a logger that writes to both console and a
    timestamped log file under logs/.

    Creates a new log file for every pipeline run.

    Returns the logger instance.
    """

    global _logger

    if _logger is not None:
        return _logger

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join("logs", f"pipeline_{timestamp}.log")

    # Create logger
    logger = logging.getLogger("mind_machine")
    logger.setLevel(logging.DEBUG)

    # ---------------------------------------------------
    # File handler — full DEBUG level, all details
    # ---------------------------------------------------
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # ---------------------------------------------------
    # Console handler — INFO level, clean output
    # ---------------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(message)s"
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _logger = logger

    logger.info(f"Logger initialized — writing to: {log_file}")

    return logger


def get_logger():
    """
    Returns the existing logger or creates one if not set up yet.
    """
    global _logger
    if _logger is None:
        return setup_logger()
    return _logger