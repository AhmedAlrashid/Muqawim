import logging as lg
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from hashlib import sha256
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "utils.env", override=True)

raw = os.getenv("LOGS_DIR")
if raw is None:
    raise RuntimeError("LOGS_DIR is not set (check utils.env path and contents).")

logs_dir = Path(raw.strip('\'"')).expanduser().resolve()
logs_dir.mkdir(parents=True, exist_ok=True)
print("Logs directory:", logs_dir)

def myGetLogger():
    logger = lg.getLogger(__name__)
    logger.setLevel(lg.DEBUG)

    # Only configure once
    if logger.handlers:
        return logger

    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = lg.Formatter(fmt, datefmt=datefmt)

    # Per-run folder
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir = logs_dir / f"crawl_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=False)

    # Console handler
    sh = lg.StreamHandler()
    sh.setLevel(lg.DEBUG)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # File handler (inside run folder)
    logfile = run_dir / "crawler.log"
    fh = lg.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(lg.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.debug(f"Logger initialized. Writing to {logfile}")
    return logger

logger = myGetLogger()
logger.info("I told you so")
logger.warning("hell no")


def get_urlhash(url):
    parsed = urlparse(url)
    # everything other than scheme.
    return sha256(
        f"{parsed.netloc}/{parsed.path}/{parsed.params}/"
        f"{parsed.query}/{parsed.fragment}".encode("utf-8")).hexdigest()

def normalize(url):
    if url.endswith("/"):
        return url.rstrip("/")
    return url


def log_warning(logger, url, status_code, msg, **extra):
    """Log a structured warning about a failed or problematic request.
    
    Args:
        logger: Logger instance
        url: URL that had the issue
        status_code: HTTP status code
        msg: Description of the issue
        **extra: Additional fields (e.g. headers, retries)
    """
    details = {"url": url, "status_code": status_code}
    details.update(extra)
    logger.warning(f"Scrape warning: {msg} | {details}")


def log_success(logger, url, items_scraped=0, duration_sec=None, **extra):
    """Log a structured success entry for a completed scrape.
    
    Args:
        logger: Logger instance
        url: Successfully scraped URL
        items_scraped: Number of items extracted
        duration_sec: Time taken in seconds
        **extra: Additional metadata
    """
    details = {"url": url, "items_scraped": items_scraped}
    if duration_sec is not None:
        details["duration_sec"] = round(duration_sec, 3)
    details.update(extra)
    logger.info(f"Scrape success | {details}")
