#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import Dict, Tuple, Optional
import re
from neologdn import normalize as neonorm


class TitleExtractor:
    def __init__(
        self: TitleExtractor,
        min_text_len: int = 100,  # 内容の最小文字数
        min_line_len: int = 10,  # １行の最小文字数
        min_text_nlines: int = 3  # 内容の最小行数
    ) -> None:
        self.min_text_len = min_text_len
        self.min_line_len = min_line_len
        self.min_text_nlines = min_text_nlines
        return

    def extract(
        self: TitleExtractor,
        info: Dict[str, str]
    ) -> Tuple[str, str]:
        title = self._extract_title(info=info)
        if title is None or len(title) == 0:
            return ('', '')
        normed_title = neonorm(title)
        normed_title = re.sub(
            r'\(.*\)', '', normed_title
        ).strip()
        if len(normed_title) == 0:
            return ('', '')
        return (title, normed_title)

    def _extract_title(
        self: TitleExtractor,
        info: Dict[str, str]
    ) -> Optional[str]:
        '''ひとつのエンティティ（Wikipediaの一項目）から
        タイトルを抽出する（不適切なものは意図的に読み込まない）

        Args:
            info (Dict[str, str]): エンティティの情報

        Returns:
            Optional[str]: タイトル（不適切な場合は None）
        '''
        # 本文の取得
        sentences = info.get('text')
        if (sentences is None) or (len(sentences) < self.min_text_len):
            # 本文が無かったり短すぎたら無視する
            return None
        # タイトルの取得
        title = info.get('title')
        if title is None:
            # タイトルが無かったら無視する
            return None
        # 本文から余分な文章を削除する
        valid_sentences = list()
        for sentence in sentences.splitlines():
            sentence = neonorm(sentence.strip())
            if sentence == '関連項目.':
                # 関連項目以降はスキップ
                break
            if sentence.endswith('.'):
                # 見出しの文はスキップ
                continue
            if '「」' in sentence:
                # 発音記号などが書かれていて、
                # 壊れている文はスキップ
                continue
            # 括弧は（中身も含めて）すべて削除
            sentence = re.sub(
                r'（.*）', '', sentence
            ).strip()
            if len(sentence) < self.min_line_len:
                # あまりに短い文はスキップ
                continue
            valid_sentences.append(sentence)
        if len(valid_sentences) < self.min_text_nlines:
            # 本文が実質無かったら、スキップ
            return None
        return title
