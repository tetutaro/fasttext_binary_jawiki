#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import Dict, List, TextIO
import sys
import os
import subprocess
import json
import re
from copy import deepcopy
import shutil
import argparse
import requests
from glob import glob
from bs4 import BeautifulSoup
from html import unescape as unescape
from tqdm import tqdm
from neologdn import normalize as neonorm
import fasttext
from gensim.models import KeyedVectors
from logging import Logger, getLogger, Formatter, StreamHandler, INFO
from src.title_extractor import TitleExtractor
from src.title_parser import TitleParser
from src.title_replacer import TitleReplacer
from src.tokenizer import Tokenizer

USE_TITLE_REPLACER: bool = False


class Processor:
    MIN_TEXT_LEN: int = 100  # 内容の最小文字数
    MIN_LINE_LEN: int = 10  # １行の最小文字数
    MIN_TEXT_NLINES: int = 3  # 内容の最小行数
    MIN_SENTENCE_NWORDS: int = 5  # １行の最小単語数

    def __init__(
        self: Processor,
        version: str,
        dictionary: str,
        original: bool,
        model: str,
        dim: int,
        epoch: int,
        mincount: int,
        logger: Logger
    ) -> None:
        if version == 'none':
            self.version = None
        else:
            self.version = version
        self.mecab_dictionary = dictionary
        self.use_original = original
        self.model = model
        self.dim = dim
        self.epoch = epoch
        self.mincount = mincount
        self.logger = logger
        self.title_dictionary = dict()
        self._scrape_wikimedia()
        return

    def _scrape_wikimedia(self: Processor) -> None:
        '''wikimediaをスクレイピングして、ダンプの最新バージョンを得る
        '''
        # scrape jawiki top page
        url = 'https://dumps.wikimedia.org/jawiki/'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        versions = list()
        for a in soup.find_all('a'):
            href = a.get('href')
            if not href.startswith(('.', 'latest')):
                versions.append(href.split(os.sep)[0])
        # get latest and valid version
        found = False
        for version in sorted(versions, reverse=True):
            if self.version is not None and self.version != version:
                continue
            found = self._scrape_wikimedia_page(version=version)
            if found is True:
                break
        if found is False:
            raise SystemError('valid wikipedia dump version not found')
        return

    def _scrape_wikimedia_page(self: Processor, version: str) -> bool:
        '''wikimediaページをスクレイピングして、ファイルのURLを得る

        Args:
            version (str): Wikipediaのバージョン(YYYYMMDD)
        '''
        self.logger.debug(f'check version: {version}')
        filename = (
            f'jawiki-{version}'
            '-pages-articles-multistream.xml.bz2'
        )
        extract_dir = f'jawiki_{version}'
        # scrape latest page
        url = f'https://dumps.wikimedia.org/jawiki/{version}/'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        fpath = None
        for a in soup.find_all('a'):
            if a.string == filename:
                fpath = a.get('href')
                break
        if fpath is None:
            return False
        self.logger.info(f'latest version: {version}')
        self.version = version
        self.filename = filename
        self.extract_dir = extract_dir
        self.file_url = 'https://dumps.wikimedia.org' + fpath
        return True

    def download(self: Processor) -> None:
        '''日本語Wikipediaのダンプをダウンロードする
        '''
        if os.path.isdir(self.extract_dir):
            self.logger.info('already extracted. skip download.')
            return
        if os.path.isfile(self.filename):
            self.logger.info('already downloaded. skip download.')
            return
        try:
            subprocess.run(
                ['wget', '-O', self.filename, self.file_url], check=True
            )
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.exists(self.filename):
                os.remove(self.filename)
            raise e
        return

    def extract(self: Processor) -> None:
        '''WikiExtractorを使ってWikipediaのダンプをJSONに変換する
        '''
        assert os.path.exists(self.filename)
        if os.path.isdir(self.extract_dir):
            self.logger.info('already extracted. skip extracting.')
            return
        try:
            subprocess.run([
                'WikiExtractor', self.filename,
                '--json', '--links', '--output', self.extract_dir,
                '--quiet'
            ], check=True)
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.isdir(self.extract_dir):
                shutil.rmtree(self.extract_dir)
            raise e
        return

    def _extract_titles(self: Processor) -> None:
        # タイトルを書き出すファイル名
        self.title_fname = f'jawiki_titles_{self.version}.txt'
        if os.path.exists(self.title_fname):
            # ファイルからタイトルを読み込む
            with open(self.title_fname, 'rt') as rf:
                line = rf.readline()
                while line:
                    key, value = line.strip().split(',', 1)
                    self.title_dictionary[key] = value
                    line = rf.readline()
        else:
            # まずはタイトルだけを全部抽出してファイルに書き出し
            extractor = TitleExtractor(
                min_text_len=self.MIN_TEXT_LEN,
                min_line_len=self.MIN_LINE_LEN,
                min_text_nlines=self.MIN_TEXT_NLINES
            )
            self.logger.info('collect titles')
            for fname in tqdm(self.extracted_files):
                self._collect_titles_each_file(fname=fname)
                # １行ずつ読み込む
                with open(fname, 'rt') as rf:
                    line = rf.readline()
                    while line:
                        # JSON の読み込み
                        try:
                            info = json.loads(line.strip())
                        except Exception:
                            line = rf.readline()
                            continue
                        title, normed_title = extractor.extract(info=info)
                        if len(title) > 0:
                            # タイトルの辞書への登録
                            self.title_dictionary[title] = normed_title
                            line = rf.readline()
            with open(self.title_fname, 'wt') as wf:
                for key, value in self.title_dictionary.items():
                    wf.write(f'{key},{value}\n')
                wf.flush()
        return

    def wakati(self: Processor) -> None:
        # WikiExtractor で抽出したファイル群
        self.extracted_files = sorted(glob(f'{self.extract_dir}/*/*'))
        # Wikipedia のタイトルだけを全部読み込む
        self._extract_titles()
        # 学習用データを書き出すファイル
        if self.use_original:
            self.train_fname = f'jawiki_orig_{self.version}.txt'
        else:
            self.train_fname = f'jawiki_{self.version}.txt'
        if os.path.exists(self.train_fname):
            self.logger.info(
                'train data has already created. skip wakati.'
            )
            return
        # 中間ファイル用のTemporary directory
        if self.use_original:
            self.temp_dir = 'temp_orig_' + self.extract_dir
        else:
            self.temp_dir = 'temp_' + self.extract_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        # インスタンス生成
        self.title_parser = TitleParser(
            title_dictionary=self.title_dictionary
        )
        if USE_TITLE_REPLACER:
            self.title_replacer = TitleReplacer(
                title_dictionary=self.title_dictionary
            )
        self.tokenizer = Tokenizer(
            dictionary=self.mecab_dictionary,
            use_original=self.use_original
        )
        # Tokenize してファイルに書き出す
        self._tokenize_sentences()
        # 中間ファイルをまとめてひとつの学習用ファイルにする
        cmd = f'cat {self.temp_dir}/*/* > {self.train_fname}'
        try:
            subprocess.run(cmd, check=True, shell=True, text=True)
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.exists(self.train_fname):
                os.remove(self.train_fname)
            raise e
        shutil.rmtree(self.temp_dir)
        return

    def _tokenize_sentences(self: Processor) -> None:
        '''WikiExtractor で抽出したファイル群を読み込み、
        １行ずつ分かち書きして書き出す
        '''
        self.logger.info('tokenize sentences')
        for fname in tqdm(self.extracted_files):
            self._tokenize_sentences_each_file(fname=fname)
        return

    def _tokenize_sentences_each_file(
        self: Processor,
        fname: str
    ) -> None:
        '''ファイルを１行ずつ読み込み、分かち書きをする

        Args:
            fname (str): ファイルのパス
        '''
        # 中間ファイルのオープン
        paths = fname.split(os.sep)
        dname = os.path.join(self.temp_dir, paths[1])
        if not os.path.isdir(dname):
            os.makedirs(dname, exist_ok=True)
        wname = os.path.join(dname, paths[2])
        wf = open(wname, 'wt')
        # １行ずつ読み込む
        with open(fname, 'rt') as rf:
            line = rf.readline()
            while line:
                # JSON の読み込み
                try:
                    info = json.loads(line.strip())
                except Exception:
                    line = rf.readline()
                    continue
                self._tokenize_sentences_each_entity(info=info, wf=wf)
                line = rf.readline()
        wf.close()
        return

    def _tokenize_sentences_each_entity(
        self: Processor,
        info: Dict[str, str],
        wf: TextIO
    ) -> None:
        '''エンティティの内容を分かち書きする

        Args:
            info (Dict[str, str]): エンティティの情報
            wf (TextIO): 中間ファイルのファイル識別子
        '''
        # 本文の取得
        sentences = info.get('text')
        if (sentences is None) or (len(sentences) < self.MIN_TEXT_LEN):
            # 本文が無かったり短すぎたら無視する
            return
        # 本文から余分な文章を削除する
        valid_sentences = self._eliminate_bad_sentence(
            sentences=sentences
        )
        if len(valid_sentences) < self.MIN_TEXT_NLINES:
            # 本文が実質無かったら、スキップ
            return
        # 一文ずつ処理する
        for sentence in valid_sentences:
            # Wikipedia にリンクを貼る HTML Anchor タグを
            # 正規化したタイトルに置き換え、それをタグとして保持
            tags = list()
            self.title_parser.reset()
            self.title_parser.feed(sentence)
            sentence = deepcopy(self.title_parser.text)
            for tag in self.title_parser.tags:
                tags.append((tag['start'], tag['end']))
            if USE_TITLE_REPLACER:
                # タイトル名でを全文検索し、
                # HTMLタグと被っていなかったら置換
                sentence, tags = self.title_replacer.replace(
                    sentence=sentence,
                    tags=tags
                )
            # 形態素解析し、単語のリストにする
            words = self.tokenizer.parse(
                sentence=sentence,
                tags=tags
            )
            # 空白区切りの分かち書きをファイルに書き込む
            if len(words) > self.MIN_SENTENCE_NWORDS:
                wf.write(' '.join(words) + '\n')
                wf.flush()
        return

    def _eliminate_bad_sentence(
        self: Processor,
        sentences: str
    ) -> List[str]:
        ''' 本文から余分な文章を削除する

        Args:
            sentences (str): 元の本文

        Returns:
            List[str]: 余分な文章を除いた本文
        '''
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
            if len(sentence) < self.MIN_LINE_LEN:
                # あまりに短い文はスキップ
                continue
            # HTMLエスケープを戻して valid_sentencesに入れる
            valid_sentences.append(unescape(sentence))
        return valid_sentences

    def train(self: Processor) -> None:
        '''fastTextでWikipediaを学習する
        '''
        if self.use_original:
            self.fasttext_bin = f'fasttext_jawiki_orig_{self.version}.bin'
            self.fasttext_vec = f'fasttext_jawiki_orig_{self.version}.vec'
        else:
            self.fasttext_bin = f'fasttext_jawiki_{self.version}.bin'
            self.fasttext_vec = f'fasttext_jawiki_{self.version}.vec'
        if (
            os.path.exists(self.fasttext_bin)
        ) and (
            os.path.exists(self.fasttext_vec)
        ):
            self.logger.info('already trained. skip training.')
            return
        # 学習
        ft = fasttext.train_unsupervised(
            self.train_fname, model=self.model,
            dim=self.dim, epoch=self.epoch, minCount=self.mincount
        )
        # モデルのバイナリの書き出し
        ft.save_model(self.fasttext_bin)
        # ベクトルファイルの書き出し
        words = ft.get_words()
        with open(self.fasttext_vec, 'wt') as wf:
            wf.write(
                str(len(words)) + ' ' + str(ft.get_dimension()) + '\n'
            )
            for word in words:
                try:
                    vec = ft.get_word_vector(word)
                    vec_str = ''
                    for v in vec:
                        vec_str += ' ' + str(v)
                    wf.write(word + vec_str + '\n')
                except Exception:
                    continue
        return

    def convert(self: Processor) -> None:
        '''fastTextのバイナリはサイズが大きく使いづらいため、
        gensimのKeyedVecor形式バイナリに変換する
        '''
        if self.use_original:
            self.kv_bin = f'kv_fasttext_jawiki_orig_{self.version}.bin'
        else:
            self.kv_bin = f'kv_fasttext_jawiki_{self.version}.bin'
        kv = KeyedVectors.load_word2vec_format(
            self.fasttext_vec, binary=False
        )
        kv.save_word2vec_format(self.kv_bin, binary=True)
        return


def main() -> None:
    # setup logger
    logger = getLogger(__file__)
    logger.setLevel(INFO)
    formatter = Formatter('%(asctime)s: %(levelname)s: %(message)s')
    handler = StreamHandler(stream=sys.stdout)
    handler.setLevel(INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # get arguments
    parser = argparse.ArgumentParser(
        description='tokenize sentence into morphemes using MeCab'
    )
    parser.add_argument(
        '-v', '--version', type=str, default='none',
        help='indicate version of Wikipedia'
    )
    parser.add_argument(
        '-d', '--dictionary', type=str, default='mecab_ipadic',
        help='path of MeCab dictonary or [ipa|juman|neologd]'
    )
    parser.add_argument(
        '-o', '--original', action='store_true',
        help='use original form'
    )
    parser.add_argument(
        '-m', '--model', type=str, choices=['skipgram', 'cbow'],
        default='skipgram',
        help='data representation model in fastText (default: skipgram)'
    )
    parser.add_argument(
        '--dim', type=int, default=300,
        help='size of word vectors (default: 300)'
    )
    parser.add_argument(
        '--epoch', type=int, default=10,
        help='number of training epochs (default: 10)'
    )
    parser.add_argument(
        '--mincount', type=int, default=20,
        help='minimal number of word occurrences (default: 20)'
    )
    args = parser.parse_args()
    # download
    processor = Processor(**vars(args), logger=logger)
    processor.download()
    # extract
    processor.extract()
    # create train data
    processor.wakati()
    # training
    processor.train()
    # convert
    processor.convert()
    return


if __name__ == '__main__':
    main()
