#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""Livedoor ニュースコーパスをダウンロードして整形するツール。

http://www.rondhuit.com/download.html#ldcc
"""
from typing import List, TextIO
import os
import subprocess
import shutil
import glob
import json
from neologdn import normalize
from pydantic import BaseModel
from datetime import datetime

ARCHIVE_FNAME: str = "ldcc-20140209.tar.gz"
EXTRACT_DIR: str = "ldcc"
JSONL_FNAME: str = "ldcc.jsonl"


class News(BaseModel):
    """Livedoor ニュースコーパスをパースした各記事の中身。

    Attributes:
        url (str): 記事の URL
        created (datetime): 記事を公開した日時
        title (str): 記事のタイトル
        contents (List[str]): 記事の内容
    """

    url: str
    created: datetime
    title: str
    contents: List[str]


def check_and_download_archive() -> None:
    """Livedoor ニュースコーパスをダウンロードする。

    Raises:
        SystemError: ダウンロードに失敗した
    """
    if os.path.exists(ARCHIVE_FNAME):
        return
    try:
        subprocess.run(
            [
                "wget",
                "-q",
                "https://www.rondhuit.com/download/ldcc-20140209.tar.gz",
            ],
            check=True,
        )
    except Exception:
        if os.path.exists(ARCHIVE_FNAME):
            os.remove(ARCHIVE_FNAME)
        raise SystemError("Downloading the Livedoor News Corpus is failed.")
    return


def check_and_unpack_archive() -> None:
    """Livedoor ニュースコーパスを解凍する。

    Raises:
        SystemError: 解凍に失敗した
    """
    if os.path.isdir(EXTRACT_DIR):
        return
    try:
        shutil.unpack_archive(
            filename=ARCHIVE_FNAME, extract_dir=EXTRACT_DIR, format="gztar"
        )
    except Exception:
        if os.path.isdir(EXTRACT_DIR):
            shutil.rmtree(EXTRACT_DIR, ignore_errors=True)
        raise SystemError("Unpacking the Livedoor News Corpus is failed.")
    return


def normalize_sentence(sentence: str) -> str:
    """文章を正規化する。

    Args:
        sentence (str): 正規化したい文章

    Returns:
        str: 正規化後の文章
    """
    return normalize(sentence.strip().replace("“", "”"))


def read_news(fname: str, label: str) -> News:
    """各記事のファイルを読んで内容を展開する。

    Args:
        fname (str): ファイル名
        label (str): 記事の媒体名

    Returns:
        News: 記事の内容
    """
    with open(fname, "rt") as rf:
        lines: List[str] = rf.read().splitlines()
    url: str = lines[0].strip()
    created: datetime = datetime.strptime(
        lines[1].strip(), "%Y-%m-%dT%H:%M:%S%z"
    )
    title: str = normalize_sentence(sentence=lines[2])
    contents = list()
    for line in lines[3:]:
        sentence: str = normalize_sentence(sentence=line)
        if len(sentence) == 0:
            # 長さが短かったらその行を読み飛ばす
            continue
        if sentence.startswith("Amazon.co.jp で詳細を見る"):
            # Amazon.co.jp へのリンクだったらその行を読み飛ばす
            continue
        if sentence.startswith(("http", "・http")):
            # URLだったら読み飛ばす
            continue
        if (
            ("関連記事" in sentence)
            or ("関連情報" in sentence)
            or ("関連リンク" in sentence)
        ) and (len(line) < 20):
            # 関連情報以降は読み込まない
            if label == "topic-news":
                continue
            else:
                break
        contents.append(sentence)
    return News(url=url, created=created, title=title, contents=contents)


def main() -> None:
    """main 関数"""
    check_and_download_archive()
    check_and_unpack_archive()
    fnames: List[str] = sorted(
        glob.glob(os.path.join(EXTRACT_DIR, "text", "*", "*.txt"))
    )
    wf: TextIO = open(JSONL_FNAME, "wt")
    for fname in fnames:
        if "LICENSE" in fname:
            continue
        bnames: List[str] = fname.split(os.sep)
        label: str = bnames[-2]
        did: str = os.path.splitext(bnames[-1])[0].split("-")[-1]
        news: News = read_news(fname=fname, label=label)
        wf.write(
            json.dumps(
                {
                    "did": did,
                    "label": [label],
                    "name": news.title,
                    "contents": news.contents,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        wf.flush()
    wf.close()
    os.remove(ARCHIVE_FNAME)
    shutil.rmtree(EXTRACT_DIR)
    return


if __name__ == "__main__":
    main()
