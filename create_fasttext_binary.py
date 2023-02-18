#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from __future__ import annotations
import sys
from argparse import ArgumentParser, Namespace
from logging import Logger, getLogger, Formatter, StreamHandler, INFO

from src.trainer import Trainer


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
        description="train the corpus and create word2vec format binary"
    )
    parser.add_argument(
        "file",
        type=str,
        metavar="CORPUS",
        help="curpus file",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        choices=["skipgram", "cbow"],
        default="skipgram",
        help="data representation model in fastText (default: skipgram)",
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=300,
        help="size of word vectors (default: 300)",
    )
    parser.add_argument(
        "--epoch",
        type=int,
        default=10,
        help="number of training epochs (default: 10)",
    )
    parser.add_argument(
        "--mincount",
        type=int,
        default=20,
        help="minimal number of word occurrences (default: 20)",
    )
    args: Namespace = parser.parse_args()
    trainer: Trainer = Trainer(**vars(args), logger=logger)
    trainer.train()
    return


if __name__ == "__main__":
    main()
