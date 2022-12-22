#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
import pytest  # noqa: F401
from typing import Dict
from src.title_extractor import TitleExtractor


class TestTitleExtractor:
    sample: Dict[str, str] = {
        'title': 'エイブラハム・リンカーン (人名)',
        'text': '''エイブラハム・リンカーンは、アメリカ合衆国最初の共和党所属の大統領である。
そして、アメリカ合衆国大統領を務めた個々の人物の業績をランクづけするために実施された政治学における調査結果「歴代アメリカ合衆国大統領のランキング」において、しばしば、「もっとも偉大な大統領」の1人に挙げられている。
文章３.
「」
テス
また、1863年11月9日、ゲティスバーグ国立戦没者墓地の開会式において行われた世界的に有名な演説である「ゲティスバーグ演説」において、戦没者を追悼して「人民の人民による人民のための政治を地上から決して絶滅させないために、われわれがここで固く決意することである」という民主主義の基礎を主張したことや、アメリカ合衆国南部における奴隷解放、南北戦争による国家分裂の危機を乗り越えた政治的業績、リーダーシップなどが、歴史的に高く評価されている。
関連項目.
''',
        'short_text': (
            'エイブラハム・リンカーンは、アメリカ合衆国最初の共和党所属の大統領である。'
            'そして、アメリカ合衆国大統領を務めた個々の人物の業績をランクづけするために実施された'
            '政治学における調査結果「歴代アメリカ合衆国大統領のランキング」において、'
            'しばしば、「もっとも偉大な大統領」の1人に挙げられている。'
        ),
    }

    def test_normal(self: TestTitleExtractor) -> None:
        info = self.sample
        extractor = TitleExtractor()
        ret = extractor.extract(info=info)
        assert(len(ret) == 2)
        assert(ret[0] == 'エイブラハム・リンカーン (人名)')
        assert(ret[1] == 'エイブラハム・リンカーン')
        return

    def test_no_text(self: TestTitleExtractor) -> None:
        info = {'title': 'hoge'}
        extractor = TitleExtractor()
        ret = extractor.extract(info=info)
        assert(len(ret) == 2)
        assert(ret[0] == '')
        assert(ret[1] == '')
        return

    def test_text_too_short(self: TestTitleExtractor) -> None:
        info = {'title': 'hoge', 'text': 'hoge'}
        extractor = TitleExtractor()
        ret = extractor.extract(info=info)
        assert(len(ret) == 2)
        assert(ret[0] == '')
        assert(ret[1] == '')
        return

    def test_no_title(self: TestTitleExtractor) -> None:
        info = {'text': self.sample['text']}
        extractor = TitleExtractor()
        ret = extractor.extract(info=info)
        assert(len(ret) == 2)
        assert(ret[0] == '')
        assert(ret[1] == '')
        return

    def test_no_normed_title(self: TestTitleExtractor) -> None:
        info = {'title': ' (人名) ', 'text': self.sample['text']}
        extractor = TitleExtractor()
        ret = extractor.extract(info=info)
        assert(len(ret) == 2)
        assert(ret[0] == '')
        assert(ret[1] == '')
        return

    def test_contents_too_short(self: TestTitleExtractor) -> None:
        info = {
            'title': self.sample['title'],
            'text': self.sample['short_text'],
        }
        extractor = TitleExtractor()
        ret = extractor.extract(info=info)
        assert(len(ret) == 2)
        assert(ret[0] == '')
        assert(ret[1] == '')
        return
