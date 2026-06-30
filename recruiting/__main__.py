"""Recruiting digest CLI.

    python -m recruiting daily            # send today's digest email
    python -m recruiting daily --dry-run  # print plain-text, don't send
    python -m recruiting preview          # write the HTML to recruiting/preview.html
"""

import sys
from pathlib import Path

from recruiting import digest


def _preview():
    subject, html, plain, a, _cfg = digest.build()
    out = Path(__file__).resolve().parent / "preview.html"
    out.write_text(html, encoding="utf-8")
    print(plain)
    print(f"\nsubject: {subject}")
    print(f"wrote {out}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "daily"
    dry = "--dry-run" in argv or "-n" in argv

    if cmd == "daily":
        digest.run(dry_run=dry)
    elif cmd == "preview":
        _preview()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
