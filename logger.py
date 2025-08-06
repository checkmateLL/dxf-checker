import logging
import os
from datetime import datetime

LOGS_DIR = "logs"
REPORTS_DIR = "reports"

# These will be set by init_logger
log_file = None
report_file = None

def init_logger(verbose=False):
    global log_file, report_file

    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOGS_DIR, f"log_{timestamp}.txt")
    report_file = os.path.join(REPORTS_DIR, f"report_{timestamp}.txt")

    # Configure default logger for errors/info
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler()  # still show on console
        ]
    )

    # Create empty report file if verbose is on
    if verbose:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"Verbose Report - {timestamp}\n{'='*50}\n\n")

def log_info(message: str):
    logging.info(message)

def log_warning(message: str):
    logging.warning(message)

def log_error(message: str):
    logging.error(message)

def log_verbose(message: str):
    if report_file:
        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(message + "\n")
