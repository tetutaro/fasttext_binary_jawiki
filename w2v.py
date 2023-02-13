#!/usr/bin/env python
# -*- coding:utf-8 -*-
from typing import List, Tuple, Optional
import os
from argparse import ArgumentParser, Namespace

from fugashi import GenericTagger
from gensim.models.keyedvectors import KeyedVectors


def load_tagger() -> GenericTagger:
    import unidic_cwj

    dic_dir: str = unidic_cwj.dicdir
    dic_rc: str = os.path.join(os.getcwd(), "dicrc")
    arg: str = f"-d {dic_dir} -r {dic_rc}"
    tagger: GenericTagger = GenericTagger(arg)
    return tagger


def load_kvs(version: str, file: str, base: bool) -> KeyedVectors:
    # find the latest binary
    kv_bins: List[Tuple[str, str]] = list()
    if file != "none":
        if os.path.exists(file):
            kv_bins.append((file, ""))
    elif version != "none":
        if base:
            entry: str = f"kv_fasttext_jawiki_base_{version}.bin"
        else:
            entry: str = f"kv_fasttext_jawiki_{version}.bin"
        if os.path.exists(entry):
            kv_bins.append((entry, version))
    else:
        for fullentry in os.listdir(path="."):
            entry: str = os.path.basename(fullentry)
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
    bin_fn: str = sorted(kv_bins, key=lambda x: x[1], reverse=True)[0][0]
    kvs: KeyedVectors = KeyedVectors.load_word2vec_format(bin_fn, binary=True)
    cnt: int = len(kvs)
    dim: int = kvs[0].shape[0]
    print(f"{bin_fn}: {dim} dimension {cnt} vectors")
    return kvs


def get_words(tagger: GenericTagger, word: str, base: bool) -> List[str]:
    words: List[str] = list()
    for node in tagger.parse(word).splitlines():
        if node == "EOS":
            break
        try:
            surface, baseform = node.split("\t", 1)
        except Exception:
            surface = node
            baseform = ""
        if base and baseform not in ["", "UNK"]:
            words.append(baseform)
        else:
            words.append(surface)
    return words


def find_similar(
    pos: List[str],
    neg: Optional[List[str]],
    version: str,
    file: str,
    topn: int,
    base: bool,
) -> None:
    tagger: GenericTagger = load_tagger()
    kvs: KeyedVectors = load_kvs(version=version, file=file, base=base)
    positives: List[str] = list()
    for p in pos:
        ps = get_words(tagger=tagger, word=p, base=base)
        for pps in ps:
            try:
                _ = kvs.get_vector(pps)
            except Exception:
                print(f"「{pps}」は学習済みの語彙にありません")
            else:
                positives.append(pps)
    if len(positives) == 0:
        raise ValueError("no valid positive word")
    negatives: Optional[List[str]]
    if neg is None:
        negatives = None
    else:
        negatives = list()
        for n in neg:
            ns = get_words(tagger=tagger, word=n, base=base)
            for nns in ns:
                try:
                    _ = kvs.get_vector(nns)
                except Exception:
                    print(f"「{nns}」は学習済みの語彙にありません")
                else:
                    negatives.append(nns)
        if len(negatives) == 0:
            negatives = None
    rets: List[Tuple(str, float)] = kvs.most_similar(
        positive=positives,
        negative=negatives,
        topn=topn,
    )
    print(f"positives: {positives}, negatives: {negatives}")
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
        metavar="POS",
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
        metavar="YYYYMMDD",
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
    parser.add_argument(
        "-f",
        "--file",
        default="none",
        type=str,
        help="directly indicate trained binary",
    )
    args: Namespace = parser.parse_args()
    find_similar(**vars(args))
    return


if __name__ == "__main__":
    main()
