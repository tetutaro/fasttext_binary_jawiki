#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from typing import List, Dict
import os
import sys
import json
from glob import glob
import shutil
from argparse import ArgumentParser, Namespace
from logging import getLogger, Logger, Formatter, StreamHandler, INFO

from tqdm import tqdm


def convert(version: str, logger: Logger) -> None:
    extracted_dir: str = f"jawiki_{version}"
    extracting_dir: str = f"jawiki_{version}_ja"
    if not os.path.isdir(extracted_dir):
        raise SystemError(f"version {version} is not extracted")
    if os.path.isdir(extracting_dir):
        shutil.rmtree(extracting_dir)
    os.makedirs(extracting_dir)
    extracted_files = sorted(glob(f"{extracted_dir}/*/*"))
    for fname in tqdm(extracted_files):
        fpathes: List[str] = fname.split(os.path.sep)
        fdir: str = fpathes[-2]
        fbase: str = fpathes[-1]
        wdir: str = f"{extracting_dir}/{fdir}"
        if not os.path.isdir(wdir):
            os.makedirs(wdir, exist_ok=True)
        wname: str = f"{extracting_dir}/{fdir}/{fbase}"
        with open(fname, "rt") as rf, open(wname, "wt") as wf:
            for line in rf:
                try:
                    info: Dict[str, str] = json.loads(line.strip())
                except Exception:
                    continue
                wf.write(json.dumps(info, ensure_ascii=False) + "\n")
            wf.flush()
    return


def main() -> None:
    # setup logger
    logger: Logger = getLogger(__file__)
    logger.setLevel(INFO)
    formatter: Formatter = Formatter("%(asctime)s: %(levelname)s: %(message)s")
    handler: StreamHandler = StreamHandler(stream=sys.stdout)
    handler.setLevel(INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # get arguments
    parser: ArgumentParser = ArgumentParser(
        description="tokenize sentence into morphemes using MeCab"
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        default="none",
        required=True,
        help="Wikipedia version (YYYYMMDD)",
    )
    args: Namespace = parser.parse_args()
    convert(**vars(args), logger=logger)
    return


if __name__ == "__main__":
    main()
