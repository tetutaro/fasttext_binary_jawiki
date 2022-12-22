#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
import pytest  # noqa: F401
from src.tokenizer import Tokenizer


class TestTokenizer:
    sentence = (
        '奴隷制に反対するエイブラハム・リンカーンなどは、'
        '北部連邦とジオンとルシスを勝利へ導いた。'
    )
    tests = [
        {
            'dictionary': 'mecab_ipadic',
            'use_original': False,
            'tags': [
                (8, 20),
                (29, 32),
            ],
            'desired_words': [
                '奴隷制', 'に', '反対', 'する',
                'エイブラハム・リンカーン', 'など', 'は', '、',
                '北部', '連邦', 'と', 'ジオン', 'と', 'ルシス', 'を',
                '勝利', 'へ', '導い', 'た', '。'
            ],
        },
        {
            'dictionary': 'mecab_ipadic',
            'use_original': True,
            'tags': [
                (8, 20),
                (29, 32),
            ],
            'desired_words': [
                '奴隷制', 'に', '反対', 'する',
                'エイブラハム・リンカーン', 'など', 'は', '、',
                '北部', '連邦', 'と', 'ジオン', 'と', 'ルシス', 'を',
                '勝利', 'へ', '導く', 'た', '。'
            ],
        },
        {
            'dictionary': 'mecab_ipadic',
            'use_original': False,
            'tags': [
                (7, 20),
                (28, 32),
            ],
            'desired_words': [
                '奴隷制', 'に', '反対', 'す',
                'るエイブラハム・リンカーン', 'など', 'は', '、',
                '北部', '連邦', 'とジオン', 'と', 'ルシス', 'を',
                '勝利', 'へ', '導い', 'た', '。'
            ],
        },
        {
            'dictionary': 'mecab_ipadic',
            'use_original': False,
            'tags': [
                (8, 21),
                (29, 33),
            ],
            'desired_words': [
                '奴隷制', 'に', '反対', 'する',
                'エイブラハム・リンカーンな', 'ど', 'は', '、',
                '北部', '連邦', 'と', 'ジオンと', 'ルシス', 'を',
                '勝利', 'へ', '導い', 'た', '。'
            ],
        },
        {
            'dictionary': 'mecab_ipadic',
            'use_original': False,
            'tags': [
                (8, 21),
                (29, 34),
            ],
            'desired_words': [
                '奴隷制', 'に', '反対', 'する',
                'エイブラハム・リンカーンな', 'ど', 'は', '、',
                '北部', '連邦', 'と', 'ジオンとル', 'シス', 'を',
                '勝利', 'へ', '導い', 'た', '。'
            ],
        },
    ]

    def test_init(self: TestTokenizer) -> None:
        _ = Tokenizer(dictionary='ipa', use_original=False)
        _ = Tokenizer(dictionary='ipa', use_original=True)
        _ = Tokenizer(dictionary='juman', use_original=False)
        _ = Tokenizer(dictionary='juman', use_original=True)
        _ = Tokenizer(dictionary='neologd', use_original=False)
        _ = Tokenizer(dictionary='neologd', use_original=True)
        with pytest.raises(ValueError):
            _ = Tokenizer(dictionary='hogehoge', use_original=True)
        return

    def test_parse(self: TestTokenizer) -> None:
        for test in self.tests:
            tokenizer = Tokenizer(
                dictionary=test['dictionary'],
                use_original=test['use_original']
            )
            words = tokenizer.parse(
                sentence=self.sentence,
                tags=test['tags']
            )
            desired_words = test['desired_words']
            assert(len(words) == len(desired_words))
            for i, word in enumerate(words):
                assert(word == desired_words[i])
        return

    def test_space(self: TestTokenizer) -> None:
        tokenizer = Tokenizer(
            dictionary='mecab_ipadic',
            use_original=True
        )
        words = tokenizer.parse(
            sentence='この BASIC 系列では文字列として使用される。',
            tags=[(3, 8), (13, 16)]
        )
        desired_words = [
            'この', 'BASIC', '系列', 'で', 'は',
            '文字列', 'として', '使用', 'する', 'れる', '。',
        ]
        assert(len(words) == len(desired_words))
        for i, word in enumerate(words):
            assert(word == desired_words[i])
        return
