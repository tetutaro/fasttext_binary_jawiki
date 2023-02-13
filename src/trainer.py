#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
import os
from logging import Logger

import fasttext
import numpy as np
from gensim.models import KeyedVectors


class Trainer:
    file: str
    model: str
    dim: int
    epoch: int
    mincount: int
    base: bool
    version: str
    logger: Logger

    def __init__(
        self: Trainer,
        file: str,
        model: str,
        dim: int,
        epoch: int,
        mincount: int,
        logger: Logger,
    ) -> None:
        self.file = file
        self.model = model
        self.dim = dim
        self.epoch = epoch
        self.mincount = mincount
        if "base" in file:
            self.base = True
        else:
            self.base = False
        self.version = os.path.splitext(file)[0].split("_")[-1]
        self.logger = logger
        return

    def train(self: Trainer) -> None:
        """fastTextでWikipediaを学習する"""
        if self.base:
            self.fasttext_bin = f"fasttext_jawiki_base_{self.version}.bin"
            self.fasttext_vec = f"fasttext_jawiki_base_{self.version}.vec"
            self.kv_bin = f"kv_fasttext_jawiki_base_{self.version}.bin"
        else:
            self.fasttext_bin = f"fasttext_jawiki_{self.version}.bin"
            self.fasttext_vec = f"fasttext_jawiki_{self.version}.vec"
            self.kv_bin = f"kv_fasttext_jawiki_{self.version}.bin"
        if os.path.exists(self.fasttext_bin):
            self.logger.info("already trained. skip training.")
            return
        self._train()
        kv = KeyedVectors.load_word2vec_format(self.fasttext_vec, binary=False)
        kv.save_word2vec_format(self.kv_bin, binary=True)
        return

    def _train(self: Trainer) -> None:
        ft = fasttext.train_unsupervised(
            self.file,
            model=self.model,
            dim=self.dim,
            epoch=self.epoch,
            minCount=self.mincount,
        )
        ft.save_model(self.fasttext_bin)
        words = ft.get_words()
        with open(self.fasttext_vec, "wt") as wf:
            wf.write(str(len(words)) + " " + str(ft.get_dimension()) + "\n")
            for word in words:
                try:
                    vec = ft.get_word_vector(word)
                    # normalize
                    vec /= np.linalg.norm(vec, ord=2)
                    vec_str = ""
                    for v in vec:
                        vec_str += " " + str(v)
                    wf.write(word + vec_str + "\n")
                except Exception:
                    continue
        return
