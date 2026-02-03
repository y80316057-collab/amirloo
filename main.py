"""Simple CLI to demonstrate scheduled message sending.

Usage examples:
  example
  spam حمله اطلس 50 3
  reply user123
"""

from __future__ import annotations

import shlex
import sys
import time
from dataclasses import dataclass


@dataclass
class ReplyContext:
    target: str | None = None


def print_help() -> None:
    print(
        """دستورات:
  example
    نمایش نمونه دستور.
  reply <name>
    تعیین نام فردی که پیام‌ها به صورت ریپلای برای او چاپ شوند.
  spam <message> <count> <interval_seconds>
    ارسال پیام با فاصله زمانی مشخص (مثال: spam حمله اطلس 50 3)
  quit
    خروج.
"""
    )


def run_spam(message: str, count: int, interval: float, reply_to: str | None) -> None:
    if count <= 0:
        print("تعداد پیام باید بزرگ‌تر از صفر باشد.")
        return
    if interval <= 0:
        print("فاصله زمانی باید بزرگ‌تر از صفر باشد.")
        return

    for index in range(1, count + 1):
        if reply_to:
            print(f"Reply to {reply_to}: {message} ({index}/{count})")
        else:
            print(f"{message} ({index}/{count})")
        if index < count:
            time.sleep(interval)


def handle_command(command: str, ctx: ReplyContext) -> bool:
    stripped = command.strip()
    if not stripped:
        return True

    if stripped in {"quit", "exit"}:
        return False

    if stripped == "help":
        print_help()
        return True

    if stripped == "example":
        print("مثال: spam حمله اطلس 50 3")
        print("الان هر 3 ثانیه یک پیام 'حمله اطلس' تا 50 بار چاپ می‌شود.")
        return True

    if stripped.startswith("reply "):
        _, _, target = stripped.partition(" ")
        ctx.target = target.strip() or None
        if ctx.target:
            print(f"ریپلای برای {ctx.target} تنظیم شد.")
        else:
            print("نام ریپلای خالی است.")
        return True

    try:
        parts = shlex.split(stripped)
    except ValueError as exc:
        print(f"خطا در پردازش دستور: {exc}")
        return True

    if parts and parts[0] == "spam":
        if len(parts) < 4:
            print("فرمت: spam <message> <count> <interval_seconds>")
            return True
        message = " ".join(parts[1:-2])
        try:
            count = int(parts[-2])
            interval = float(parts[-1])
        except ValueError:
            print("count باید عدد صحیح و interval باید عدد باشد.")
            return True
        run_spam(message, count, interval, ctx.target)
        return True

    print("دستور ناشناخته است. help را بزنید.")
    return True


def main() -> int:
    ctx = ReplyContext()
    print("برای راهنما help را بزنید.")
    while True:
        try:
            command = input("> ")
        except EOFError:
            print("")
            break
        if not handle_command(command, ctx):
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
