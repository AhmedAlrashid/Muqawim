"""Tiny runner to demonstrate the crawler logger.

Creates one log entry at INFO and one at WARNING level. Run this to
verify that a timestamped file appears under `Logs/` and messages
also appear on the console.
"""

from be.python.utils import myGetLogger
import logging as lg


def main():
    logger = myGetLogger("muqawim.crawler.demo", level=lg.INFO)
    logger.info("Starting demo crawler run")
    logger.warning("This is a demo warning")


if __name__ == "__main__":
    main()
