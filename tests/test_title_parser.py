#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
import pytest  # noqa: F401
from typing import Callable
from src.title_parser import TitleParser


class TestTitleParser:
    def setup_method(
        self: TestTitleParser,
        method: Callable
    ) -> None:
        '''
        辞書の準備
        '''
        self.title_dictionary = {
            'スズキ (会社)': 'スズキ',
            'リンカーン': 'エイブラハム・リンカーン',
            'マグロ': 'マグロ',
            'BASIC': 'BASIC',
            '文字列': '文字列',
        }
        return

    def test_suzuki(self: TestTitleParser) -> None:
        text = '日本の<a href="スズキ (会社)">ある会社</a>はバイクを作る'
        desired_text = '日本のスズキはバイクを作る'
        desired_tags = [{
            'start': 3,
            'end': 6,
            'href': 'スズキ (会社)',
            'word': 'スズキ',
            'surface': 'ある会社',
        }]
        parser = TitleParser(title_dictionary=self.title_dictionary)
        parser.reset()
        parser.feed(text)
        assert(parser.text == desired_text)
        assert(len(parser.tags) == len(desired_tags))
        for i in range(len(parser.tags)):
            for key in ['start', 'end', 'href', 'word', 'surface']:
                parser.tags[i][key] == desired_tags[i][key]
        return

    def test_lincolin(self: TestTitleParser) -> None:
        text = '<p><a href="リンカーン">偉人</a>が</p>木を切る'
        desired_text = 'エイブラハム・リンカーンが木を切る'
        desired_tags = [{
            'start': 0,
            'end': 12,
            'href': 'リンカーン',
            'word': 'エイブラハム・リンカーン',
            'surface': '偉人',
        }]
        parser = TitleParser(title_dictionary=self.title_dictionary)
        parser.reset()
        parser.feed(text)
        assert(parser.text == desired_text)
        assert(len(parser.tags) == len(desired_tags))
        for i in range(len(parser.tags)):
            for key in ['start', 'end', 'href', 'word', 'surface']:
                parser.tags[i][key] == desired_tags[i][key]
        return

    def test_tuna(self: TestTitleParser) -> None:
        text = '<a href="スズキ (会社)">アレ</a>は会社</br><a href="マグロ">コレ</a>は魚'
        desired_text = 'スズキは会社マグロは魚'
        desired_tags = [
            {
                'start': 0,
                'end': 3,
                'href': 'スズキ (会社)',
                'word': 'スズキ',
                'surface': 'アレ',
            },
            {
                'start': 6,
                'end': 9,
                'href': 'マグロ',
                'word': 'マグロ',
                'surface': 'コレ',
            },
        ]
        parser = TitleParser(title_dictionary=self.title_dictionary)
        parser.reset()
        parser.feed(text)
        assert(parser.text == desired_text)
        assert(len(parser.tags) == len(desired_tags))
        for i in range(len(parser.tags)):
            for key in ['start', 'end', 'href', 'word', 'surface']:
                parser.tags[i][key] == desired_tags[i][key]
        return

    def test_no_href(self: TestTitleParser) -> None:
        text = '<a href="">アレ</a>は会社</br><a href="マグロ">コレ</a>は魚'
        desired_text = 'アレは会社マグロは魚'
        desired_tags = [
            {
                'start': 6,
                'end': 9,
                'href': 'マグロ',
                'word': 'マグロ',
                'surface': 'コレ',
            },
        ]
        parser = TitleParser(title_dictionary=self.title_dictionary)
        parser.reset()
        parser.feed(text)
        assert(parser.text == desired_text)
        assert(len(parser.tags) == len(desired_tags))
        for i in range(len(parser.tags)):
            for key in ['start', 'end', 'href', 'word', 'surface']:
                parser.tags[i][key] == desired_tags[i][key]
        return

    def test_no_attr(self: TestTitleParser) -> None:
        text = '<a>アレ</a>は会社</br><a href="マグロ">コレ</a>は魚'
        desired_text = 'アレは会社マグロは魚'
        desired_tags = [
            {
                'start': 6,
                'end': 9,
                'href': 'マグロ',
                'word': 'マグロ',
                'surface': 'コレ',
            },
        ]
        parser = TitleParser(title_dictionary=self.title_dictionary)
        parser.reset()
        parser.feed(text)
        assert(parser.text == desired_text)
        assert(len(parser.tags) == len(desired_tags))
        for i in range(len(parser.tags)):
            for key in ['start', 'end', 'href', 'word', 'surface']:
                parser.tags[i][key] == desired_tags[i][key]
        return

    def test_invalid_href(self: TestTitleParser) -> None:
        text = '<a href="hogehoge">アレ</a>は会社</br><a href="マグロ">コレ</a>は魚'
        desired_text = 'アレは会社マグロは魚'
        desired_tags = [
            {
                'start': 6,
                'end': 9,
                'href': 'マグロ',
                'word': 'マグロ',
                'surface': 'コレ',
            },
        ]
        parser = TitleParser(title_dictionary=self.title_dictionary)
        parser.reset()
        parser.feed(text)
        assert(parser.text == desired_text)
        assert(len(parser.tags) == len(desired_tags))
        for i in range(len(parser.tags)):
            for key in ['start', 'end', 'href', 'word', 'surface']:
                parser.tags[i][key] == desired_tags[i][key]
        return

    def test_basic(self: TestTitleParser) -> None:
        text = 'この <a href="BASIC">BASIC</a> 系列では<a href="文字列">文字列</a>として使用される。'
        desired_text = 'この BASIC 系列では文字列として使用される。'
        desired_tags = [
            {
                'start': 3,
                'end': 8,
                'href': 'BASIC',
                'word': 'BASIC',
                'surface': 'BASIC',
            },
            {
                'start': 13,
                'end': 16,
                'href': '文字列',
                'word': '文字列',
                'surface': '文字列',
            },
        ]
        parser = TitleParser(title_dictionary=self.title_dictionary)
        parser.reset()
        parser.feed(text)
        assert(parser.text == desired_text)
        assert(len(parser.tags) == len(desired_tags))
        for i in range(len(parser.tags)):
            for key in ['start', 'end', 'href', 'word', 'surface']:
                parser.tags[i][key] == desired_tags[i][key]
        return
