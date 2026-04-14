"""
Compatibility wrapper for M3 guide naming.

Guide references worker_policy.py while the repo implementation lives in
workers/policy_tool.py. This wrapper keeps both names available without
changing other teammates' imports.
"""

try:
    from .policy_tool import WORKER_NAME, analyze_policy, run
except ImportError:
    from policy_tool import WORKER_NAME, analyze_policy, run


__all__ = ["WORKER_NAME", "analyze_policy", "run"]
