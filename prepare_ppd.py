#!/usr/bin/env python3
"""Prepare a separate URF-only PDF route from a compatible CUPS 2.x PPD.

This program never contacts CUPS, installs a driver, or submits a print job.
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path
import re
import sys


class UnsupportedPPD(ValueError):
    """The input is outside the deliberately narrow supported PPD layout."""


FILTER = re.compile(
    rb'^\*cupsFilter2:[ \t]*"([^\s"]+)[ \t]+([^\s"]+)[ \t]+'
    rb'([0-9]+)[ \t]+([^"\r\n]+)"[ \t]*$'
)
PDF_SOURCES = {b"application/pdf", b"application/vnd.cups-pdf"}
URF = (b"image/urf", b"image/urf", b"-")
JPEG = (b"image/jpeg", b"image/jpeg", b"-")
COMMENT = b"*% Local workaround: render PDF through the existing URF raster route."


def prepare(data: bytes) -> tuple[bytes, int]:
    """Remove only native PDF pass-through rules; preserve all other bytes."""
    if not data.startswith(b"*PPD-Adobe:"):
        raise UnsupportedPPD("Not a PPD file: missing PPD-Adobe header.")
    lines = data.splitlines(keepends=True)
    remove: set[int] = set()
    remaining: list[tuple[bytes, bytes, bytes]] = []
    for index, line in enumerate(lines):
        if not line.startswith(b"*cupsFilter2:"):
            continue
        match = FILTER.fullmatch(line.rstrip(b"\r\n"))
        if match is None:
            raise UnsupportedPPD("Unrecognized cupsFilter2 syntax; no output created.")
        source, destination, _cost, program = match.groups()
        program = program.strip()
        if source in PDF_SOURCES and destination == b"application/pdf" and program == b"-":
            remove.add(index)
        else:
            remaining.append((source, destination, program))
    if not remove:
        raise UnsupportedPPD("No supported native PDF pass-through rule found.")
    if URF not in remaining:
        raise UnsupportedPPD("No existing image/urf pass-through route; use a device-specific solution.")
    if any(rule not in {URF, JPEG} for rule in remaining):
        raise UnsupportedPPD(
            "Additional output routes or custom filters found; inspect the filter graph manually."
        )
    for index in remove:
        old = lines[index]
        ending = b"\r\n" if old.endswith(b"\r\n") else b"\n" if old.endswith(b"\n") else b"\r" if old.endswith(b"\r") else b""
        lines[index] = COMMENT + ending
    return b"".join(lines), len(remove)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Your own saved CUPS PPD")
    parser.add_argument("output", type=Path, nargs="?", help="New output file; must not exist")
    parser.add_argument("--check", action="store_true", help="Check compatibility without writing a file")
    args = parser.parse_args(argv)
    if args.check and args.output is not None:
        parser.error("--check does not take an output path")
    if not args.check and args.output is None:
        parser.error("provide an output path, or use --check")
    try:
        original = args.input.read_bytes()
        prepared, count = prepare(original)
        if args.check:
            print(f"Compatible layout: {count} native PDF rule(s), existing URF route.")
            return 0
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Input and output must be different files.")
        # Exclusive creation also prevents replacing an existing symlink.
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(prepared)
        # Zero context avoids printing nearby device URLs or other PPD identifiers.
        sys.stdout.writelines(difflib.unified_diff(
            original.decode("utf-8", errors="replace").splitlines(keepends=True),
            prepared.decode("utf-8", errors="replace").splitlines(keepends=True),
            fromfile="original.ppd", tofile="raster.ppd", n=0,
        ))
        print(f"Prepared {count} change(s). No CUPS configuration or print jobs were changed.")
        return 0
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
