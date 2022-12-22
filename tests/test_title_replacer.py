#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
import pytest  # noqa: F401
from typing import Dict
from src.title_replacer import TitleReplacer


class TestTitleReplacer:
    '''
    辞書の準備
    '''
    title_dictionary: Dict[str, str] = {
        'エイブラハム・リンカーン (人名)': 'エイブラハム・リンカーン',
        'エイブラハム・エイブ・リンカーン': 'エイブラハム・リンカーン',
        'カジキマグロ': 'カジキクロマグロ',
        'ホゲ': 'ホゲ',
    }
    # normal (& multiple) replace
    data1 = {
        'sentence': (
            'エイブラハム・リンカーンは大統領に当選した。'
            'エイブラハム・エイブ・リンカーンは初めて暗殺された。'
            'エイブラハム・エイブ・リンカーンは初めて暗殺された。'
            'エイブラハム・エイブ・リンカーンは初めて暗殺された。'
            'エイブラハム・リンカーンは大統領に当選した。'
        ),
        'tags': [
            (0, 12),
            (100, 112),
        ],
        'desired_sentence': (
            'エイブラハム・リンカーンは大統領に当選した。'
            'エイブラハム・リンカーンは初めて暗殺された。'
            'エイブラハム・リンカーンは初めて暗殺された。'
            'エイブラハム・リンカーンは初めて暗殺された。'
            'エイブラハム・リンカーンは大統領に当選した。'
        ),
        'desired_tags': [
            (0, 12),
            (22, 34),
            (44, 56),
            (66, 78),
            (88, 100),
        ],
    }
    # normal (& multiple) replace 2
    data2 = {
        'sentence': (
            'カジキマグロを海で釣る'
            '海で釣るカジキマグロ'
        ),
        'tags': [
        ],
        'desired_sentence': (
            'カジキクロマグロを海で釣る'
            '海で釣るカジキクロマグロ'
        ),
        'desired_tags': [
            (0, 8),
            (17, 25),
        ],
    }
    # overlapped 1
    data3 = {
        'sentence': (
            '私はカジキマグロを海で釣る'
        ),
        'tags': [
            (1, 5),
        ],
        'desired_sentence': (
            '私はカジキマグロを海で釣る'
        ),
        'desired_tags': [
            (1, 5),
        ],
    }
    # overlapped 2
    data4 = {
        'sentence': (
            '私はカジキマグロを海で釣る'
        ),
        'tags': [
            (5, 9),
        ],
        'desired_sentence': (
            '私はカジキマグロを海で釣る'
        ),
        'desired_tags': [
            (5, 9),
        ],
    }
    # overlapped 3
    data5 = {
        'sentence': (
            '私はカジキマグロを海で釣る'
        ),
        'tags': [
            (1, 9),
        ],
        'desired_sentence': (
            '私はカジキマグロを海で釣る'
        ),
        'desired_tags': [
            (1, 9),
        ],
    }
    # overlapped 4
    data6 = {
        'sentence': (
            '私はカジキマグロを海で釣る'
        ),
        'tags': [
            (3, 7),
        ],
        'desired_sentence': (
            '私はカジキマグロを海で釣る'
        ),
        'desired_tags': [
            (3, 7),
        ],
    }

    def test_data(self: TestTitleReplacer) -> None:
        replacer = TitleReplacer(
            title_dictionary=self.title_dictionary
        )
        datas = [
            self.data1, self.data2,
            self.data3, self.data4, self.data5, self.data6,
        ]
        for data in datas:
            ret = replacer.replace(
                sentence=data['sentence'],
                tags=data['tags']
            )
            assert(data['desired_sentence'] == ret[0])
            assert(len(data['desired_tags']) == len(ret[1]))
            for orig, pred in zip(data['desired_tags'], ret[1]):
                assert(orig[0] == pred[0])
                assert(orig[1] == pred[1])
        return
