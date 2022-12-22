#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import List, Tuple
import os
import subprocess
from MeCab import Tagger


class Tokenizer:
    '''形態素解析するクラス

    Args:
        dictionary (str):
            MeCab 辞書のディレクトリ名
            もしくは "ipa", "juman", "neologd" のどれか
        use_original (bool):
            原型に戻すか否か
    '''
    INSTALLED_DICTIONARIES: List[str] = ['ipa', 'juman', 'neologd']

    def __init__(
        self: Tokenizer,
        dictionary: str,
        use_original: bool
    ) -> None:
        super().__init__()
        self.dictionary = dictionary
        self.use_original = use_original
        self._load_mecab()
        return

    def _load_mecab(self: Tokenizer) -> None:
        '''MeCab をロードする
        '''
        if os.path.isdir(self.dictionary):
            # load local dictionary
            self.tagger = Tagger(f'-d {self.dictionary}')
            # original dictionary is based on IPA
            self.offset_original = 6
            return
        elif self.dictionary not in self.INSTALLED_DICTIONARIES:
            raise ValueError(f'dictionary not found: {self.dictionary}')
        # load installed dictionary
        mecab_config_path = None
        # retrive the directory of dictionary
        mecab_config_cands = [
            '/usr/bin/mecab-config', '/usr/local/bin/mecab-config'
        ]
        for c in mecab_config_cands:
            if os.path.exists(c):
                mecab_config_path = c
                break
        if mecab_config_path is None:
            raise SystemError(
                'mecab-config not found. check mecab is really installed'
            )
        dic_dir = subprocess.run(
            [mecab_config_path, '--dicdir'],
            check=True, stdout=subprocess.PIPE, text=True
        ).stdout.rstrip()
        # retrive the dictonary
        dic_path = None
        if self.dictionary == 'ipa':
            dic_cands = ['ipadic-utf8', 'ipadic']
        elif self.dictionary == 'juman':
            dic_cands = ['juman-utf8', 'jumandic']
        else:  # self.dictionary == 'neologd'
            dic_cands = ['mecab-ipadic-neologd']
        for c in dic_cands:
            tmpdir = os.path.join(dic_dir, c)
            if os.path.isdir(tmpdir):
                dic_path = tmpdir
                break
        if dic_path is None:
            raise SystemError(
                f'installed dictionary not found: {self.dictionary}'
            )
        # create tagger
        self.tagger = Tagger(f'-d {dic_path}')
        if self.dictionary == 'juman':
            self.offset_original = 4
        else:
            self.offset_original = 6
        return

    def parse(
        self: Tokenizer,
        sentence: str,
        tags: List[Tuple[int, int]],
    ) -> List[str]:
        '''パースする

        Args:
            sentence (str): 文章
            entities (List[Tuple[int, int]]): 分割しないタグの場所

        Returns:
            List[str]: 単語のリスト
        '''
        # オフセットと単語の Tuple のリスト
        offs_words = list()
        # タグの単語を予め入れておく
        for tag in tags:
            word = sentence[tag[0]: tag[1]]
            offs_words.append((tag[0], word, word))
        cur_pos = 0
        nodes = self.tagger.parse(sentence)
        for node in nodes.splitlines():
            node = node.strip()
            if node == 'EOS':
                break
            # このノードで出力する単語
            try:
                surface, feature_str = node.split('\t', 1)
            except Exception:
                continue
            word = self._get_word(
                surface=surface,
                feature_str=feature_str
            )
            # タグとの交差判定
            area = (cur_pos, cur_pos + len(surface))
            overlapped = False
            for tag in tags:
                if tag[1] <= area[0]:
                    continue
                elif area[1] <= tag[0]:
                    break
                else:
                    overlapped = True
                    break
            if overlapped:
                # 交差してる
                if area[0] < tag[0]:
                    p_sentence = sentence[area[0]: tag[0]]
                    p_offs_words = self._parse_gap(sentence=p_sentence)
                    for p_ow in p_offs_words:
                        offs_words.append((
                            cur_pos + p_ow[0], p_ow[1], p_ow[2]
                        ))
                if tag[1] < area[1]:
                    p_sentence = sentence[tag[1]: area[1]]
                    p_offs_words = self._parse_gap(sentence=p_sentence)
                    for p_ow in p_offs_words:
                        offs_words.append((
                            cur_pos + (tag[1] - area[0]) + p_ow[0],
                            p_ow[1], p_ow[2]
                        ))
            else:
                # 交差してない
                offs_words.append((cur_pos, surface, word))
            cur_pos = self._next_position(
                cur_pos=cur_pos, surface=surface, sentence=sentence
            )
        # オフセット順に並べ替え
        offs_words = sorted(offs_words, key=lambda x: x[0])
        # 単語のリストにして返す
        return [x[2] for x in offs_words]

    def _get_word(
        self: Tokenizer,
        surface: str,
        feature_str: str
    ) -> str:
        '''出力したい単語を得る

        Args:
            surface (str): 表層系（文章に出てきたそのままの単語）
            feature_str (str): MeCabで得られた単語の特徴（カンマ区切り）

        Returs:
            str: 出力したい単語
        '''
        features = [x.strip() for x in feature_str.strip().split(',')]
        if self.use_original:
            if (
                len(features) <= self.offset_original
            ) or (
                features[self.offset_original] == '*'
            ):
                # Unknown
                word = surface[:]
            else:
                word = features[self.offset_original]
        else:
            word = surface[:]
        return word

    def _parse_gap(
        self: Tokenizer,
        sentence: str,
    ) -> List[Tuple[int, str, str]]:
        '''重なり合っていない隙間をパースする

        Args:
            sentence (str): 文章

        Returns:
            List[Tuple[int, str, str]]: start, surface, word のリスト
        '''
        offs_words = list()
        cur_pos = 0
        nodes = self.tagger.parse(sentence)
        for node in nodes.splitlines():
            node = node.strip()
            if node == 'EOS':
                break
            # このノードで出力する単語
            try:
                surface, feature_str = node.split('\t', 1)
            except Exception:
                continue
            word = self._get_word(
                surface=surface,
                feature_str=feature_str
            )
            offs_words.append((cur_pos, surface, word))
            cur_pos = self._next_position(
                cur_pos=cur_pos, surface=surface, sentence=sentence
            )
        return offs_words

    def _next_position(
        self: Tokenizer,
        cur_pos: int,
        surface: str,
        sentence: str
    ) -> int:
        '''次のポジションを返す

        Args:
            cur_pos (int): current position
            surface (str): 表層系（文章に出てきたそのままの単語）
            sentence (str): 元の文章

        Returns:
            int: 次のポジション
        '''
        next_pos = cur_pos + len(surface)
        while next_pos < len(sentence) and sentence[next_pos] == ' ':
            next_pos += 1
        return next_pos
