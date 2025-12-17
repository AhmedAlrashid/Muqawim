import logging as lg
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

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
