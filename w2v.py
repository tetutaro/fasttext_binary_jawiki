#!/usr/bin/env python
# -*- coding:utf-8 -*-
from typing import List, Optional
import os
import argparse
from gensim.models.keyedvectors import KeyedVectors


def load_kvs(version: Optional[str], use_original: bool) -> KeyedVectors:
    # find the latest binary
    kv_bins = list()
    if version is not None:
        if use_original:
            entry = f'kv_fasttext_jawiki_orig_{version}.bin'
        else:
            entry = f'kv_fasttext_jawiki_{version}.bin'
        if os.path.exists(entry):
            kv_bins.append((entry, version))
    else:
        for entry in os.listdir(path='.'):
            name, ext = os.path.splitext(os.path.basename(entry))
            if use_original:
                if name.startswith('kv_fasttext_jawiki_orig_'):
                    version = name.split('_')[-1]
                    kv_bins.append((entry, version))
            else:
                if ((
                    not name.startswith('kv_fasttext_jawiki_orig_')
                ) and name.startswith('kv_fasttext_jawiki_')):
                    version = name.split('_')[-1]
                    kv_bins.append((entry, version))
    if len(kv_bins) == 0:
        raise SystemError('KeyedVectors binary not found')
    bin_fn = sorted(kv_bins, key=lambda x: x[1], reverse=True)[0][0]
    print(bin_fn)
    return KeyedVectors.load_word2vec_format(bin_fn, binary=True)


def find_similar(
    pos: List[str],
    neg: Optional[List[str]],
    version: str,
    topn: int,
    original: bool
) -> None:
    if version == 'none':
        version = None
    kvs = load_kvs(version=version, use_original=original)
    positives = list()
    for p in pos:
        try:
            _ = kvs.get_vector(p)
        except Exception:
            print(f'「{p}」は学習済みの語彙にありません')
        else:
            positives.append(p)
    if len(positives) == 0:
        raise ValueError('no valid positive word')
    if neg is None:
        negatives = None
    else:
        negatives = list()
        for n in neg:
            try:
                _ = kvs.get_vector(n)
            except Exception:
                print(f'「{n}」は学習済みの語彙にありません')
            else:
                negatives.append(p)
        if len(negatives) == 0:
            negatives = None
    rets = kvs.most_similar(
        positive=positives, negative=negatives, topn=topn
    )
    print('【結果】')
    for i, ret in enumerate(rets):
        print(f'{i + 1}. {ret[0]} : {ret[1]}')
    return


def main() -> None:
    parser = argparse.ArgumentParser(
        description='find the word that have similar meanings'
    )
    parser.add_argument(
        'pos', nargs='+',
        help='word[s] that contribute positively'
    )
    parser.add_argument(
        '-n', '--neg', nargs='*',
        help='word[s] that contribute negatively'
    )
    parser.add_argument(
        '-v', '--version', default='none',
        help='version of trained binary'
    )
    parser.add_argument(
        '--topn', type=int, default=5,
        help='number of top-N words to display (default: 5)'
    )
    parser.add_argument(
        '-o', '--original', action='store_true',
        help='use original form'
    )
    args = parser.parse_args()
    find_similar(**vars(args))
    return


if __name__ == '__main__':
    main()
