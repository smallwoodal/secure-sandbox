"""
Pipeline orchestrator — runs all configured pipelines.

Add your pipeline functions here as you build them.
Each pipeline should:
  1. Fetch or read input data
  2. Validate against a schema
  3. Transform/aggregate
  4. Write output
"""

import sys


def main():
    print("No pipelines configured yet.")
    print("Use Claude Code to build your first pipeline:")
    print('  "Create a scraper for <site> that extracts <fields>"')
    print('  "Read data/inbox/holdings.xlsx and produce a summary CSV"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
