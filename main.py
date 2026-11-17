"""Command-line interface. Dry-run is the default; add --live for a real browser."""
import argparse
import getpass
import logging
import os
import random
import sys

from bot import InstagramBot
from captions import draft_caption, validate_caption
from safety import DEFAULT_LIMITS, RateLimiter, in_active_hours
from session import run_session

LIVE_LOG, DRY_LOG = "action_log.json", "action_log_dryrun.json"


def load_env(path=".env"):
    """Tiny .env reader (KEY=VALUE lines) so we need no extra dependency."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)


def make_bot(args):
    limiter = RateLimiter(path=LIVE_LOG if args.live else DRY_LOG)
    user = os.getenv("INSTAGRAM_USERNAME")
    pwd = os.getenv("INSTAGRAM_PASSWORD")
    if args.live:
        print("LIVE mode acts on a real account and may violate Instagram's Terms of Use.")
        if input("Type YES to continue: ") != "YES":
            sys.exit("Cancelled.")
        if not in_active_hours() and not args.ignore_hours:
            sys.exit("Outside active hours (09:00-22:00). Use --ignore-hours to override.")
        user = user or input("Username: ")
        pwd = pwd or getpass.getpass("Password: ")
    sleep = (lambda s: None) if not args.live else __import__("time").sleep
    return InstagramBot(user, pwd, dry_run=not args.live, limiter=limiter,
                        delay_range=(args.min_delay, args.max_delay), sleep=sleep)


def cmd_draft(args):
    print(draft_caption(args.topic, args.tone, args.keywords))


def cmd_run(args):
    bot = make_bot(args)
    try:
        bot.start()
        if not bot.login():
            sys.exit("Login failed.")
        summary = run_session(bot, args.hashtag, args.likes, args.comments, args.follows)
        print("Session summary:", summary)
    finally:
        bot.close()


def cmd_upload(args):
    caption = validate_caption(args.caption)
    bot = make_bot(args)
    try:
        bot.start()
        if bot.login():
            bot.upload_post(args.image, caption)
    finally:
        bot.close()


def cmd_status(args):
    limiter = RateLimiter(path=LIVE_LOG if args.live else DRY_LOG)
    print(f"{'Action':<10}{'Used':>6}{'Limit':>7}")
    for action in DEFAULT_LIMITS:
        print(f"{action:<10}{limiter.used(action):>6}{limiter.limits[action]:>7}")


def build_parser():
    p = argparse.ArgumentParser(description="Instagram automation bot (dry-run by default).")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--live", action="store_true", help="use a real browser/account")
        sp.add_argument("--ignore-hours", action="store_true")
        sp.add_argument("--min-delay", type=float, default=4.0)
        sp.add_argument("--max-delay", type=float, default=12.0)

    d = sub.add_parser("draft", help="draft a caption")
    d.add_argument("--topic", required=True)
    d.add_argument("--tone", default="friendly")
    d.add_argument("--keywords", nargs="*")
    d.set_defaults(func=cmd_draft)

    r = sub.add_parser("run", help="hashtag search + like/comment/follow session")
    r.add_argument("--hashtag", required=True)
    r.add_argument("--likes", type=int, default=5)
    r.add_argument("--comments", type=int, default=2)
    r.add_argument("--follows", type=int, default=2)
    common(r)
    r.set_defaults(func=cmd_run)

    u = sub.add_parser("upload", help="upload an image post")
    u.add_argument("--image", required=True)
    u.add_argument("--caption", required=True)
    common(u)
    u.set_defaults(func=cmd_upload)

    s = sub.add_parser("status", help="show today's action counts")
    s.add_argument("--live", action="store_true")
    s.set_defaults(func=cmd_status)
    return p


def main():
    load_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")])
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (ValueError, FileNotFoundError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
