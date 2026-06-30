"""Recruiting digest CLI.

    python -m recruiting check            # verify Notion token + DB access
    python -m recruiting daily            # send today's digest email
    python -m recruiting daily --dry-run  # print plain-text, don't send
    python -m recruiting preview          # write the HTML to recruiting/preview.html
"""

import sys
from pathlib import Path

from recruiting import config, digest, notion


def _check():
    cfg = config.load_config()
    db_id = cfg["notion"]["database_id"]
    token = cfg["notion"]["token"]
    print(f"NOTION_TOKEN     : set ({token[:7]}…{token[-4:]})")
    print(f"recruiting DB id : {db_id}")
    try:
        meta = notion.db_meta(token, db_id)
        title = "".join(t.get("plain_text", "") for t in meta.get("title", []))
        print(f"DB access        : OK — \"{title or '(untitled)'}\"")
    except notion.NotionAccessError as e:
        print("DB access        : FAILED\n")
        print(e)
        return 1
    n = sum(1 for _ in notion.fetch_candidates(token, db_id))
    print(f"candidates        : {n} rows readable")
    recips = cfg["digest"]["to_emails"] or ["(none — set RECRUITING_DIGEST_TO)"]
    print(f"email recipients  : {', '.join(recips)}")
    print(f"gmail sender      : {cfg['gmail']['email'] or '(none — set GMAIL_EMAIL)'}")
    print("\nall good — `python -m recruiting daily` will send.")
    return 0


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
    elif cmd == "check":
        return _check()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
