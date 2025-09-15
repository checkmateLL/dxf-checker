# dxf_checker/logger.py
from pathlib import Path
from datetime import datetime

class DXFLogger:
    def __init__(self, verbose=False, log_dir="logs", report_dir="reports"):
        self.verbose = verbose
        self.log_dir = Path(log_dir)
        self.report_dir = Path(report_dir)
        self.log_file = None
        self.verbose_file = None
        self.verbose_written = False
        self._setup_files()

    def _setup_files(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir.mkdir(exist_ok=True)
        self.report_dir.mkdir(exist_ok=True)

        self.log_file = self.log_dir / f"log_{timestamp}.txt"
        with self.log_file.open("w", encoding="utf-8") as f:
            f.write(f"=== DXF Checker Log ({timestamp}) ===\n\n")

        if self.verbose:
            self.verbose_file = self.report_dir / f"verbose_{timestamp}.txt"
            with self.verbose_file.open("w", encoding="utf-8") as f:
                f.write(f"=== Verbose Report ({timestamp}) ===\n\n")

    def log(self, message, level="INFO"):
        line = f"[{level}] {message}"
        print(line)
        if self.log_file:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def log_verbose(self, message):
        if self.verbose_file:
            with self.verbose_file.open("a", encoding="utf-8") as f:
                f.write(message + "\n")
            self.verbose_written = True

    def cleanup(self):
        # Remove verbose file if nothing was written
        if self.verbose and self.verbose_file and not self.verbose_written:
            try:
                self.verbose_file.unlink()
            except Exception as e:
                self.log(f"Failed to delete unused verbose file: {e}", level="WARNING")