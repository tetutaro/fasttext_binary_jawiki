#!/usr/bin/env python
# -*- coding:utf-8 -*-
from typing import List, Tuple, Optional
import os
from argparse import ArgumentParser, Namespace
from gensim.models.keyedvectors import KeyedVectors


def load_kvs(version: str, base: bool) -> KeyedVectors:
    # find the latest binary
    kv_bins: List[Tuple[str, str]] = list()
    if version != "none":
        if base:
            entry: str = f"kv_fasttext_jawiki_base_{version}.bin"
        else:
            entry: str = f"kv_fasttext_jawiki_{version}.bin"
        if os.path.exists(entry):
            kv_bins.append((entry, version))
    else:
        for fullentry in os.listdir(path="."):
            entry: str = os.path.basenanme(fullentry)
            if not entry.endswith(".bin"):
                continue
            prefix: str = "kv_fasttext_jawiki_"
            prefix_base: str = "kv_fasttext_jawiki_base_"
            if not entry.startswith(prefix):
                continue
            if (not base) and entry.startswith(prefix_base):
                continue
            if base and (not entry.startswith(prefix_base)):
                continue
            version = os.path.splitext(entry)[0].split("_")[-1]
            kv_bins.append((entry, version))
    if len(kv_bins) == 0:
        raise SystemError("KeyedVectors binary not found")
    bin_fn = sorted(kv_bins, key=lambda x: x[1], reverse=True)[0][0]
    print(bin_fn)
    return KeyedVectors.load_word2vec_format(bin_fn, binary=True)


def find_similar(
    pos: List[str],
    neg: Optional[List[str]],
    version: str,
    topn: int,
    base: bool,
) -> None:
    kvs: KeyedVectors = load_kvs(version=version, base=base)
    positives: List[str] = list()
    for p in pos:
        try:
            _ = kvs.get_vector(p)
        except Exception:
            print(f"「{p}」は学習済みの語彙にありません")
        else:
            positives.append(p)
    if len(positives) == 0:
        raise ValueError("no valid positive word")
    negatives: Optional[List[str]]
    if neg is None:
        negatives = None
    else:
        negatives = list()
        for n in neg:
            try:
                _ = kvs.get_vector(n)
            except Exception:
                print(f"「{n}」は学習済みの語彙にありません")
            else:
                negatives.append(p)
        if len(negatives) == 0:
            negatives = None
    rets: List[Tuple(str, float)] = kvs.most_similar(
        positive=positives,
        negative=negatives,
        topn=topn,
    )
    print("【結果】")
    for i, ret in enumerate(rets):
        print(f"{i + 1}. {ret[0]} : {ret[1]}")
    return


def main() -> None:
    parser: ArgumentParser = ArgumentParser(
        description="find the word that have similar meanings"
    )
    parser.add_argument(
        "pos",
        nargs="+",
        type=str,
        help="word[s] that contribute positively",
    )
    parser.add_argument(
        "-n",
        "--neg",
        nargs="*",
        type=str,
        help="word[s] that contribute negatively",
    )
    parser.add_argument(
        "-v",
        "--version",
        default="none",
        help="version of trained binary",
    )
    parser.add_argument(
        "--topn",
        type=int,
        default=5,
        help="number of top-N words to display (default: 5)",
    )
    parser.add_argument(
        "-b",
        "--base",
        action="store_true",
        help="use base form",
    )
    args: Namespace = parser.parse_args()
    find_similar(**vars(args))
    return


if __name__ == "__main__":
    main()
