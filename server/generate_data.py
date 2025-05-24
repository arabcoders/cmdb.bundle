#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import glob
import hashlib
import json
import os
import re

parser = argparse.ArgumentParser(
    description="Generate data.json for your series.",
    epilog="Example: python3 generate_data.py /path/to/your/series -o /path/to/your/data.json -p jp -l 5",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    "path", type=str, help="Path to where your series stored.", default=os.getcwd()
)

parser.add_argument(
    "-o", "--output", type=str, help="Store json data into this file.", default="-"
)

parser.add_argument("-p", "--prefix", type=str, help="Shows ID prefix.", default="jp")

parser.add_argument("-l", "--length", type=int, help="Hash length", default=5)

args = parser.parse_args()


def natural_sort(items):
    def convert(text):
        return int(text) if text.isdigit() else text.lower()

    def alphanum_key(key):
        return [convert(c) for c in re.split("([0-9]+)", key)]

    return sorted(items, key=alphanum_key)


def clean_up_string(s: str) -> str:
    s = s.replace("&", "and")
    s = re.sub(r"\[[^)]*\]", "", s)
    s = re.sub(r'[!"#$%&\'()*+,-./:;<=>?@\[\]^_`{|}~]', " ", s)
    s = s.lower()
    s = re.sub(r"^(the|a) ", "", s)
    s = re.sub(r"[ ]+", " ", s)
    return s.strip()


def makeId(dir: str, prefix: str, length: int = 5) -> str:
    return f"{prefix}-{hashlib.shake_256(dir.encode('utf-8')).hexdigest(length)}"


shows: list = []

if not os.path.exists(args.path):
    raise FileNotFoundError(f"Path '{args.path}' not found.")

path = os.path.abspath(args.path)

for dir in natural_sort(glob.iglob(f"{path}/*")):
    if not os.path.isdir(dir):
        continue

    base_dir = os.path.basename(dir)
    shows.append(
        {
            "id": makeId(dir=base_dir, prefix=args.prefix, length=args.length),
            "title": base_dir,
            "match": [clean_up_string(base_dir)],
        }
    )

data = json.dumps(shows, indent=4, ensure_ascii=False)
if args.output == "-":
    print(data)
else:
    with open(args.output, "w") as f:
        f.write(data)
