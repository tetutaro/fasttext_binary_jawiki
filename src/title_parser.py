#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import Dict, List, Tuple
from html.parser import HTMLParser
from urllib.parse import unquote


class TitleParser(HTMLParser):
    '''文章毎にHREFタグの置き換えをして、置き換えたタグを記憶する

    Args:
        dictionary (Dict[str, str]):
            日本語 Wikipedia に収録されているタイトルと
            その表記名の辞書（例："スズキ (会社)" -> "スズキ"）
    '''

    def __init__(
        self: TitleParser,
        title_dictionary: Dict[str, str]
    ) -> None:
        super().__init__()
        # 辞書の登録
        self.titles = sorted(list(title_dictionary.keys()))
        self.title_dictionary = title_dictionary
        # 初期化
        self._clean_tag_resources()
        self._clean_ref_resources()
        return

    def _clean_tag_resources(self: TitleParser) -> None:
        '''タグ情報を初期化
        '''
        self.text = ''
        self.tags = list()
        self.pos = 0
        return

    def _clean_ref_resources(self: TitleParser) -> None:
        '''タグ置き換えのための資源をリセットする
        '''
        self.isin = False
        self.href = None
        self.normed = None
        self.surface = None
        self.start = None
        return

    def reset(self: TitleParser) -> None:
        '''HTMLParser の reset() を継承
        '''
        super().reset()
        # 初期化
        self._clean_tag_resources()
        self._clean_ref_resources()
        return

    def handle_starttag(
        self: TitleParser,
        tag: str,
        attrs: List[Tuple[str, str]]
    ) -> None:
        '''HTMLParser の handle_starttag() を継承
        A タグなら、HREF を unquote して保存し、フラグを立てる

        Args:
            tag (str): タグの名前
            atts (List[Tuple[str, str]]): タグの属性
        '''
        if tag != 'a':
            # A タグじゃない
            # タグ置き換えのための資源をリセットする
            self._clean_ref_resources()
            return
        # リンク先を取得
        href = None
        for key, value in attrs:
            if key == 'href':
                href = value
        if href is None:
            # HREF が取れない
            # タグ置き換えのための資源をリセットする
            self._clean_ref_resources()
            return
        # URL quotation を元に戻す
        href = unquote(href)
        # 対応する表記名を取得
        normed = self.title_dictionary.get(href)
        if normed is None:
            # HREF が 日本語 Wikipedia にない
            # タグ置き換えのための資源をリセットする
            self._clean_ref_resources()
        else:
            # フラグを立て、リンク先を保持
            self.isin = True
            self.href = href
            self.normed = normed
            self.start = self.pos
        return

    def handle_endtag(
        self: TitleParser,
        tag: str
    ) -> None:
        '''HTMLParser の handle_endtag() を継承
        A タグなら文字をリンク先に置き換える

        Args:
            tag (str): タグの名前
        '''
        if tag != 'a':
            # タグ置き換えのための資源をリセットする
            self._clean_ref_resources()
            return
        # 置き換え
        if self.isin:
            self.tags.append({
                'start': self.pos,
                'end': self.pos + len(self.normed),
                'href': self.href,
                'word': self.normed,
                'surface': self.surface,
            })
            self.text += self.normed
            self.pos += len(self.normed)
        # タグ置き換えのための資源をリセットする
        self._clean_ref_resources()
        return

    def handle_data(self: TitleParser, data: str) -> None:
        '''HTMLParser の handle_data() を継承
        A タグの中の文字であれば、それを表層として登録
        それ以外であれば普通に text に追加

        Args:
            data (str): 出てきた文字
        '''
        if self.isin:
            # 表層として登録
            self.surface = data
        else:
            # text に追加
            self.text += data
            self.pos += len(data)
        return
