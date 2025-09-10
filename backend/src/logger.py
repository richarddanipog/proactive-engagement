import logging
import sys

logger = logging.getLogger("proactive-engagement")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(console_formatter)

if not logger.handlers:
    logger.addHandler(console_handler)

__all__ = ["logger"]
