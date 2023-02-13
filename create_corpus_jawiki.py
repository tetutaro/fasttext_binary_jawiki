#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from __future__ import annotations
import sys
from argparse import ArgumentParser, Namespace
from logging import Logger, getLogger, Formatter, StreamHandler, INFO

from src.downloader import Downloader
from src.extractor import Extractor
from src.tokenizer import Tokenizer


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
        description="create corpus from Japanese Wikipedia"
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        default="none",
        metavar="YYYYMMDD",
        help="Wikipedia version",
    )
    parser.add_argument(
        "-b", "--base", action="store_true", help="use base form"
    )
    args: Namespace = parser.parse_args()
    # download
    downloader: Downloader = Downloader(logger=logger)
    downloader.download(version=args.version)
    # extract
    extractor: Extractor = Extractor(
        filename=downloader.filename,
        extract_dir=downloader.extract_dir,
        logger=logger,
    )
    extractor.extract()
    # tokenize
    tokenizer: Tokenizer = Tokenizer(
        version=downloader.version,
        extract_dir=downloader.extract_dir,
        base=args.base,
        logger=logger,
    )
    tokenizer.tokenize()
    return


if __name__ == "__main__":
    main()
