import os
import time
from pathlib import Path
from datetime import datetime, timedelta


def cleanup_old_logs(log_dir="logs", report_dir="reports", days_old=7, verbose=False):
    """
    Clean up log and report files older than specified number of days.
    
    Args:
        log_dir (str): Directory containing log files
        report_dir (str): Directory containing report files  
        days_old (int): Files older than this many days will be deleted
        verbose (bool): Print details about cleanup process
    
    Returns:
        dict: Summary of cleanup results
    """
    results = {
        'logs_deleted': 0,
        'reports_deleted': 0,
        'errors': []
    }
    
    cutoff_time = time.time() - (days_old * 24 * 60 * 60)
    cutoff_date = datetime.fromtimestamp(cutoff_time).strftime('%Y-%m-%d %H:%M:%S')
    
    if verbose:
        print(f"Cleaning up files older than {days_old} days (before {cutoff_date})")
    
    # Clean log directory
    log_path = Path(log_dir)
    if log_path.exists():
        results['logs_deleted'] = _clean_directory(log_path, cutoff_time, "log", verbose, results['errors'])
    
    # Clean report directory  
    report_path = Path(report_dir)
    if report_path.exists():
        results['reports_deleted'] = _clean_directory(report_path, cutoff_time, "report", verbose, results['errors'])
    
    if verbose:
        print(f"Cleanup complete: {results['logs_deleted']} logs, {results['reports_deleted']} reports deleted")
        if results['errors']:
            print(f"Errors encountered: {len(results['errors'])}")
    
    return results


def _clean_directory(directory, cutoff_time, file_type, verbose, error_list):
    """Clean files in a specific directory."""
    deleted_count = 0
    
    try:
        for file_path in directory.iterdir():
            if file_path.is_file():
                try:
                    file_mtime = file_path.stat().st_mtime
                    
                    if file_mtime < cutoff_time:
                        if verbose:
                            file_date = datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')
                            print(f"Deleting old {file_type}: {file_path.name} (modified: {file_date})")
                        
                        file_path.unlink()
                        deleted_count += 1
                        
                except OSError as e:
                    error_msg = f"Could not delete {file_path}: {e}"
                    error_list.append(error_msg)
                    if verbose:
                        print(f"Error: {error_msg}")
                        
    except OSError as e:
        error_msg = f"Could not access directory {directory}: {e}"
        error_list.append(error_msg)
        if verbose:
            print(f"Error: {error_msg}")
    
    return deleted_count