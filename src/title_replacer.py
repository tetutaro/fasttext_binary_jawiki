#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import Dict, List, Tuple
import re


class TitleReplacer:
    def __init__(
        self: TitleReplacer,
        title_dictionary: Dict[str, str],
        min_word_len: int = 3
    ) -> None:
        self.title_dictionary = dict()
        title_list = sorted(list(title_dictionary.keys()))
        title_list = sorted(
            title_list, key=lambda x: len(x), reverse=True
        )
        for title in title_list:
            if len(title) < min_word_len:
                break
            bad_chars = ['(', ')', '+', '?', '!', '\\', '*']
            continue_flag = False
            for bad_char in bad_chars:
                if bad_char in title:
                    continue_flag = True
                    break
            if continue_flag:
                continue
            self.title_dictionary[title] = title_dictionary[title]
        return

    def replace(
        self: TitleReplacer,
        sentence: str,
        tags: List[Tuple[int, int]]
    ) -> Tuple[str, List[Tuple[int, int]]]:
        # Wikipedia にリンクを貼る HTML Anchor タグを
        # 正規化したタイトルに置き換え、それをタグとして保持
        for old_title, new_title in self.title_dictionary.items():
            key = old_title.replace('(', '\\(').replace(')', '\\)')
            spans = [
                m.span() for m in re.finditer(key, sentence)
            ]
            if len(spans) == 0:
                continue
            diff_len = len(new_title) - len(old_title)
            sum_len = 0
            for span in spans:
                span = (span[0] + sum_len, span[1] + sum_len)
                # span と tag の重なりを調べる
                # 重なったらその span は無視
                is_overlapped = False
                for tag in tags:
                    if tag[1] <= span[0]:
                        # span は tag の前にある
                        continue
                    elif span[1] <= tag[0]:
                        # span は tag の後ろにある
                        break
                    else:
                        # span と tag は重なっている
                        is_overlapped = True
                        break
                if is_overlapped:
                    continue
                # old_title と new_title を置き換えた sentence を作る
                new_sentence = sentence[:span[0]]
                new_sentence += new_title
                new_sentence += sentence[span[1]:]
                # span を入れ、span 以降は位置をずらした tags を作る
                new_tags = list()
                new_tags.append((span[0], span[0] + len(new_title)))
                for tag in tags:
                    if tag[1] <= span[0]:
                        new_tags.append((tag[0], tag[1]))
                    elif span[1] <= tag[0]:
                        new_tags.append((
                            tag[0] + diff_len,
                            tag[1] + diff_len
                        ))
                # 新しいものに入れ替える
                sentence = new_sentence
                tags = sorted(new_tags, key=lambda x: x[0])
                sum_len += diff_len
        return (sentence, tags)
