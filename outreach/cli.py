"""Entry: python -m outreach <flow>."""

import sys

from outreach import birthday

FLOWS = {
    "birthday": birthday.run,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in FLOWS:
        print(f"usage: python -m outreach <{'|'.join(FLOWS)}>", file=sys.stderr)
        sys.exit(2)
    FLOWS[sys.argv[1]]()
