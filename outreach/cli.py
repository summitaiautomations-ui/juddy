"""Entry: python -m outreach <flow>."""

import sys

from outreach import birthday, digest, scan

FLOWS = {
    "birthday": birthday.run,
    "scan": scan.run,
    "digest": digest.run,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in FLOWS:
        print(f"usage: python -m outreach <{'|'.join(FLOWS)}>", file=sys.stderr)
        sys.exit(2)
    FLOWS[sys.argv[1]]()
