#!/usr/bin/env python3
"""
Thin wrapper to run the QA Agent from scripts entrypoint.

Preserves pyproject and Makefile entrypoint compatibility.
"""

import sys

import run_qa_agent as app


def main():  # noqa: D401
    """Delegate to root-level run_qa_agent.main()"""
    return app.main()


if __name__ == "__main__":
    sys.exit(main())
