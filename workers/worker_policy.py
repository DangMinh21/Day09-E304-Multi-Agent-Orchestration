"""
Compatibility wrapper for M3 guide naming.

Guide references worker_policy.py while the repo implementation lives in
workers/policy_tool.py. This wrapper keeps both names available without
changing other teammates' imports.
"""

import logging

try:
    # Thử import theo kiểu relative (nếu chạy trong package)
    from .policy_tool import WORKER_NAME, analyze_policy, run
except (ImportError, ValueError):
    try:
        # Thử import trực tiếp (nếu chạy script độc lập)
        from policy_tool import WORKER_NAME, analyze_policy, run
    except ImportError as e:
        logging.error(f"Critical Error: Không tìm thấy policy_tool.py để wrap. {e}")
        raise

__all__ = ["WORKER_NAME", "analyze_policy", "run"]
