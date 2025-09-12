import os
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")
VERBOSE_DIR = Path("reports")

log_file = None
verbose_written = False
verbose_file = None


def setup_logging(verbose=False):
    global log_file, verbose_file

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(exist_ok=True)
    VERBOSE_DIR.mkdir(exist_ok=True)

    log_file = LOG_DIR / f"log_{timestamp}.txt"
    verbose_file = VERBOSE_DIR / f"verbose_{timestamp}.txt" if verbose else None

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"=== DXF Checker Log ({timestamp}) ===\n\n")

    if verbose and verbose_file:
        with open(verbose_file, "w", encoding="utf-8") as f:
            f.write(f"=== Verbose Report ({timestamp}) ===\n\n")


def log(message: str, level: str = "INFO"):
    """Write to main log and console"""
    line = f"[{level}] {message}"
    print(line)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def log_verbose(message: str):
    """Write to verbose log only"""
    global verbose_written
    if verbose_file:
        with open(verbose_file, "a", encoding="utf-8") as f:
            f.write(message + "\n")
        verbose_written = True
