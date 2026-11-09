#!/usr/bin/env python3
"""Prepare private Prometheus inputs from the monitoring repository's .env."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"SUPABASE_URL", "SUPABASE_SECRET_KEY"}


def read_settings(path):
    settings = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or name not in REQUIRED:
            continue
        try:
            parts = shlex.split(value, comments=True, posix=True)
        except ValueError:
            raise ValueError(f"Invalid quoting for {name}") from None
        if len(parts) != 1:
            raise ValueError(f"Provide one nonempty value for {name}")
        settings[name] = parts[0]

    if not REQUIRED.issubset(settings):
        raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY are required")

    url = urlsplit(settings["SUPABASE_URL"])
    if (
        url.scheme != "https"
        or not re.fullmatch(r"[a-z0-9]+\.supabase\.co", url.netloc)
        or url.path not in ("", "/")
        or url.query
        or url.fragment
    ):
        raise ValueError("SUPABASE_URL must be https://<project-ref>.supabase.co")
    key = settings["SUPABASE_SECRET_KEY"]
    if not key or any(character.isspace() for character in key):
        raise ValueError("SUPABASE_SECRET_KEY must be a nonempty single-line key")
    return url.netloc, key


def write_private(path, content, reader_uid):
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chown(temporary, reader_uid, -1)
        os.chmod(temporary, 0o400)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--reader-uid", type=int, required=True,
                        help="UID reported by docker exec monitoring-prometheus id -u")
    args = parser.parse_args()
    if os.name != "posix" or os.geteuid() != 0:
        parser.error("Run this preparation command with sudo on the Oracle VM")
    if args.reader_uid < 0:
        parser.error("--reader-uid must be nonnegative")

    try:
        host, key = read_settings(args.env_file)
        directory = ROOT.parent / "monitoring-private-secrets" / "prometheus"
        if directory.is_symlink():
            raise ValueError("Private output directory must not be a symlink")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chown(directory, args.reader_uid, -1)
        os.chmod(directory, 0o500)

        targets = [{
            "targets": [host + ":443"],
            "labels": {
                "service": "matchwise_database",
                "project": host.split(".")[0],
            },
        }]
        write_private(directory / "supabase-api-key", key, args.reader_uid)
        write_private(
            directory / "supabase-targets.json",
            json.dumps(targets, indent=2) + "\n",
            args.reader_uid,
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"Preparation failed: {error}\n")

    print("Supabase Prometheus input files prepared.")
    print("Target:", host + ":443")
    print("Reader UID:", args.reader_uid)
    print("Private directory:", directory)


if __name__ == "__main__":
    main()
