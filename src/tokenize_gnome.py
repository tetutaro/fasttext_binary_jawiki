#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import Dict, List, Optional, TextIO
import os
import re
import json
from logging import Logger

from fugashi import GenericTagger
from neologdn import normalize as neonorm


class TokenizeGnome:
    # parameters
    MIN_TEXT_LEN: int = 100  # 内容の最小文字数
    MIN_LINE_LEN: int = 10  # １行の最小文字数
    MIN_TEXT_NLINES: int = 3  # 内容の最小行数
    MIN_SENTENCE_NWORDS: int = 5  # １行の最小単語数
    # variables
    dic_dir: str
    dic_rc: str
    dic_version: str
    tagger: GenericTagger
    logger: Logger

    def __init__(self: TokenizeGnome, logger: Logger) -> None:
        self._load_tagger()
        self.logger = logger
        return

    def _load_tagger(self: TokenizeGnome) -> None:
        import unidic_cwj

        self.dic_dir = unidic_cwj.dicdir
        self.dic_rc = os.path.join(os.getcwd(), "dicrc")
        self.dic_version = unidic_cwj.__version__
        arg: str = f"-d {self.dic_dir} -r {self.dic_rc}"
        self.tagger = GenericTagger(arg)
        return

    def tokenize(
        self: TokenizeGnome,
        fname: str,
        oname: str,
        base: bool,
    ) -> None:
        # １行ずつ読み込む
        with open(fname, "rt") as rf, open(oname, "wt") as wf:
            line = rf.readline()
            while line:
                # JSON の読み込み
                try:
                    info = json.loads(line.strip())
                except Exception:
                    line = rf.readline()
                    continue
                self._tokenize_entity(info=info, base=base, wf=wf)
                line = rf.readline()
        return

    def _tokenize_entity(
        self: TokenizeGnome,
        info: Dict[str, str],
        base: bool,
        wf: TextIO,
    ) -> None:
        """エンティティの内容を分かち書きする

        Args:
            info (Dict[str, str]): エンティティの情報
            wf (TextIO): 中間ファイルのファイル識別子
        """
        # 本文の取得
        text: Optional[str] = info.get("text")
        if (text is None) or (len(text) < self.MIN_TEXT_LEN):
            # 本文が無かったり短すぎたら無視する
            return
        # 本文から余分な文章を削除する
        sentences: List[str] = self._text2sentences(text=text)
        if len(sentences) < self.MIN_TEXT_NLINES:
            # 本文が実質無かったら、スキップ
            return
        # 一文ずつ処理する
        for sentence in sentences:
            words: List[str] = list()
            nodes: List[str] = self.tagger.parse(sentence).strip().splitlines()
            for node in nodes:
                node = node.strip()
                if node == "EOS":
                    break
                try:
                    surface, baseform = node.split("\t", 1)
                except Exception:
                    self.logger.debug(f"node={node}")
                    surface = node
                    baseform = ""
                if base and baseform not in ["", "UNK"]:
                    words.append(baseform)
                else:
                    words.append(surface)
            if len(words) >= self.MIN_SENTENCE_NWORDS:
                wf.write(" ".join(words) + "\n")
                wf.flush()
        return

    @staticmethod
    def _sub_link(text: str) -> str:
        """マークアップされたWikipedia内リンクを置き換える
        （タイトルと本文中表記が異なる場合）
        """
        while True:
            match = re.search(r"\s*\[\[([^[\]].+?)\|[^[[\]].+?\]\]\s*", text)
            if match is None:
                break
            title = match.groups()[0]
            normed_title = re.sub(r"\s*\([^()].+?\)\s*", "", title).strip()
            text = text[: match.start()] + normed_title + text[match.end() :]
        return text

    @staticmethod
    def _sub_entity(text: str) -> str:
        """マークアップされたWikipedia内リンクを置き換える
        （タイトルと本文中表記が同じ場合）
        """
        while True:
            match = re.search(r"\s*\[\[([^[\]].+?)\]\]\s*", text)
            if match is None:
                break
            entity = match.groups()[0]
            normed_entity = re.sub(r"\s*\([^()].+?\)\s*", "", entity).strip()
            text = text[: match.start()] + normed_entity + text[match.end() :]
        return text

    @staticmethod
    def _sub_kuten(text: str) -> str:
        while True:
            match = re.search(r"「[^「」]+(。).*」", text)
            if match is None:
                break
            text = text[: match.start(1)] + "．" + text[match.end(1) :]
        return text

    def _text2sentences(self: TokenizeGnome, text: str) -> List[str]:
        """text を正規化して文章に分割する"""
        # 文章の正規化
        text = neonorm(text.strip())
        # 文章のクレンジング
        # マークアップの除去（[[...]]の形）
        # [[:言語:その言語での表記]] など
        text = re.sub(r"\s*\[\[:[^[\]]+?\]\]\s*", "", text)
        # [[Category:カテゴリー]] など
        text = re.sub(r"\s*\[\[[^:[\]]+?:[^[\]]+?\]\]\s*", "", text)
        # [[Wikipediaのタイトル|実際の表記]] など
        text = self._sub_link(text=text)
        # [[Wikipediaのタイトルと実際の表記が同じ場合]] など
        text = self._sub_entity(text=text)
        # 空の２重brancketの削除
        text = re.sub(r"\s*\[\[\]\]\s*", "", text)
        # アノテーションの除去（[...]の形）
        # [要出典] など
        text = re.sub(r"\s*\[要[^[\]]+?\]\s*", "", text)
        text = re.sub(r"\[[^[\]]*?\?\]", "", text)  # [疑問?]
        # 空括弧の削除
        text = re.sub(r"\s*\(\)\s*", "", text)
        text = re.sub(r"\s*〈〉\s*", "", text)
        text = re.sub(r"\s*『』\s*", "", text)
        text = re.sub(r"\s*「」\s*", "", text)
        text = re.sub(r"\s*（）\s*", "", text)
        text = re.sub(r"\s*（[^（）]*?）\s*", "", text)
        # 空白の重複の削除
        text = re.sub(r"\s+", " ", text).strip()
        # 鉤括弧の中の句点をピリオドに変換
        text = self._sub_kuten(text=text)

        is_break: bool = False
        sentences: List[str] = list()
        for line in text.splitlines():
            sents: List[str] = line.split("。")
            lsent = len(sents)
            for i, sentence in enumerate(sents):
                sentence = sentence.strip()
                # あまりに短い文はスキップ
                if len(sentence) < self.MIN_LINE_LEN:
                    continue
                # 以降は読むのをやめるもの
                if sentence == "関連項目.":  # 関連項目セクション
                    is_break = True
                    break
                # 文全体を読み飛ばすもの
                if sentence.endswith("."):  # 見出し
                    continue
                if re.match(r"^\[\d+?\]", sentence):  # 脚注
                    continue
                sentence = sentence.replace("．", "。")
                if i < lsent - 1:
                    sentence += "。"
                sentences.append(sentence)
            if is_break:
                break
        return sentences
