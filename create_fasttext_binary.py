#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import Dict, List, Tuple, Optional, TextIO
import sys
import os
import subprocess
import json
import re
import shutil
import argparse
import requests
from glob import glob
from bs4 import BeautifulSoup
from html.parser import HTMLParser
from html import unescape as unescape
from urllib.parse import unquote
from tqdm import tqdm
from neologdn import normalize as neonorm
from MeCab import Tagger
import fasttext
from gensim.models import KeyedVectors
from logging import Logger, getLogger, Formatter, StreamHandler, INFO

DEBUG: bool = True


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
        entities: List[Dict[str, int]],
    ) -> List[str]:
        '''パースする

        Args:
            sentence (str): 文章
            entities (List[Dict[str, int]]): 分割しないエンティティの場所

        Returns:
            List[str]: 文字のリスト
        '''
        words = list()
        nodes = self.tagger.parse(sentence)
        for node in nodes.splitlines():
            node = node.strip()
            if node == 'EOS':
                break
            surface, feature_str = node.split('\t', 1)
            features = feature_str.split(',')
            if self.use_original:
                if len(features) <= self.offset_original:
                    word = surface
                else:
                    word = features[self.offset_original]
            else:
                word = surface
            words.append(word)
        return words


class SentenceParser(HTMLParser):
    '''文章毎にHREFタグの置き換えをして、置き換えたタグを記憶する

    Args:
        dictionary (Dict[str, str]):
            日本語 Wikipedia に収録されているタイトルと
            その表記名の辞書（例："スズキ (会社)" -> "スズキ"）
    '''

    def __init__(
        self: SentenceParser,
        dictionary: Dict[str, str]
    ) -> None:
        super().__init__()
        # 辞書の登録
        self.titles = sorted(list(dictionary.keys()))
        self.dictionary = dictionary
        # 初期化
        self._clean_tag_resources()
        self._clean_ref_resources()
        return

    def _clean_tag_resources(self: SentenceParser) -> None:
        '''タグ情報を初期化
        '''
        self.text = ''
        self.tags = dict()
        self.tag_ranges = list()
        self.pos = 0
        return

    def _clean_ref_resources(self: SentenceParser) -> None:
        '''タグ置き換えのための資源をリセットする
        '''
        self.isin = False
        self.rref = None
        self.surface = None
        return

    def reset(self: SentenceParser) -> None:
        '''HTMLParser の reset() を継承
        '''
        super().reset()
        # 初期化
        self._clean_tag_resources()
        self._clean_ref_resources()
        return

    def handle_starttag(
        self: SentenceParser,
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
        rref = self.dictionary.get(href)
        if rref is None:
            # HREF が 日本語 Wikipedia にない
            # タグ置き換えのための資源をリセットする
            self._clean_ref_resources()
        else:
            # フラグを立て、リンク先を保持
            self.isin = True
            self.rref = rref
            self.surface = None
        return

    def handle_endtag(
        self: SentenceParser,
        tag: str
    ) -> None:
        '''HTMLParser の handle_endtag() を継承
        A タグなら文字をリンク先に置き換える

        Args:
            tag (str): タグの名前
        '''
        if tag != 'a':
            # タグ置き換えのための資源をリセットする
            self._clean_tag_resources()
            return
        # 置き換え
        if self.isin and self.surface is not None:
            self.tags[self.surface] = self.rref
            self.tag_ranges.append({
                'start': self.pos,
                'end': self.pos + len(self.rref)
            })
            self.pos += len(self.rref)
            self.text += self.rref
        # タグ置き換えのための資源をリセットする
        self._clean_ref_resources()
        return

    def handle_data(self: SentenceParser, data: str) -> None:
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
            self.pos += len(data)
            self.text += data
        return


class Processor:
    MIN_TEXT_LEN: int = 100  # 内容の最小文字数
    MIN_LINE_LEN: int = 10  # １行の最小文字数
    MIN_TEXT_NLINES: int = 3  # 内容の最小行数

    def __init__(
        self: Processor,
        dictionary: str,
        original: bool,
        model: str,
        dim: int,
        epoch: int,
        mincount: int,
        logger: Logger
    ) -> None:
        self.wiki_dictionary = dict()
        self.texts = list()
        self.mecab_dictionary = dictionary
        self.use_original = original
        self.model = model
        self.dim = dim
        self.epoch = epoch
        self.mincount = mincount
        self.logger = logger
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

    def wakati(self: Processor) -> None:
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
        # WikiExtractor で抽出したファイル群
        self.extracted_files = sorted(glob(f'{self.extract_dir}/*/*'))
        # まずはタイトルだけを全部抽出
        self._collect_titles()
        # インスタンス生成
        self.parser = SentenceParser(
            dictionary=self.wiki_dictionary
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

    def _collect_titles(self: Processor) -> None:
        '''WikiExtractor で抽出したファイル群を読み込み、
        タイトルの辞書を作る（ここでは for 文だけ）
        '''
        self.logger.info('collect titles')
        for fname in tqdm(self.extracted_files):
            self._collect_titles_each_file(fname=fname)
        return

    def _collect_titles_each_file(self: Processor, fname: str) -> None:
        '''ファイルを１行ずつ読み込み、タイトルを抽出する

        Args:
            fname (str): ファイルのパス
        '''
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
                title = self._collect_titles_each_entity(info=info)
                if title is None:
                    line = rf.readline()
                    continue
                # タイトルの正規化
                normed_title = neonorm(title)
                # 括弧は（中身も含めて）すべて削除
                normed_title = re.sub(
                    r'\(.*\)', '', normed_title
                ).strip()
                # タイトルの辞書への登録
                self.wiki_dictionary[title] = normed_title
                line = rf.readline()
        return

    def _collect_titles_each_entity(
        self: Processor,
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
        if (sentences is None) or (len(sentences) < self.MIN_TEXT_LEN):
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
            if len(sentence) < self.MIN_LINE_LEN:
                # あまりに短い文はスキップ
                continue
            valid_sentences.append(sentence)
        if len(valid_sentences) < self.MIN_TEXT_NLINES:
            # 本文が実質無かったら、スキップ
            return None
        return title

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
        # エンティティ全体のタグ
        entity_tags = dict()
        entity_ranges = list()
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
        # HTMLタグをパースする
        parsed_sentences = list()
        for sentence in valid_sentences:
            self.parser.reset()
            self.parser.feed(sentence)
            parsed_sentences.append(self.parser.text)
            entity_tags |= self.parser.tags
            entity_ranges.append(self.parser.tag_ranges)
        # タグを全文検索し、HTMLタグと被っていなかったら置換
        parsed_sentences, entity_ranges = self._find_and_replace_tags(
            sentences=parsed_sentences,
            tag_dictionary=entity_tags,
            tag_positions=entity_ranges
        )
        for sentence, entities in zip(parsed_sentences, entity_ranges):
            words = self.tokenizer.parse(
                sentence=sentence,
                entities=entities
            )
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
            sentence = sentence.strip()
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

    def _find_and_replace_tags(
        self: Processor,
        sentences: List[str],
        tag_dictionary: Dict[str, str],
        tag_positions: List[List[Dict[str, int]]]
    ) -> Tuple[List[str], List[List[Dict[str, int]]]]:
        '''タグを全文検索し、HTMLタグと被っていなかったら置換

        Args:
            sentences (List[str]): 文章の配列
            tag_dictionary(Dict[str: int]): タグとその更新後の辞書
            tag_positions(List[List[Dict[str, int]]]): タグの場所

        Returns:
            List[str]: 更新した文章の配列
            List[List[Dict[str, int]]]: 更新したタグの場所
        '''
        assert(len(sentences) == len(tag_positions))
        # タグを 1. 文字数が多い順 2. 辞書順に並び替える
        tag_list = sorted(list(tag_dictionary.keys()))
        tag_list = sorted(
            tag_list, key=lambda x: len(x), reverse=True
        )
        for tag in tag_list:
            if len(tag) < 2:
                break
            new_tag = tag_dictionary[tag]
            old_length = len(tag)
            new_length = len(new_tag)
            for i, sentence in enumerate(sentences):
                spans = [
                    m.span() for m in re.finditer(tag, sentence)
                ]
                if len(spans) == 0:
                    continue
                cur_pos = 0
                inc_off = 0
                text = ''
                positions = tag_positions[i].copy()
                new_positions = list()
                for span in spans:
                    if cur_pos < span[0]:
                        text += sentence[cur_pos: span[0]]
                        cur_pos = span[0]
                    is_valid = True
                    for position in positions:
                        if is_valid and span[1] <= position['start']:
                            # spanがrangeと被ってない→span追加
                            new_positions.append({
                                'start': cur_pos + inc_off,
                                'end': cur_pos + inc_off + new_length,
                            })
                            text += new_tag
                            cur_pos += len(old_length)
                            inc_off += new_length - old_length
                            is_valid = False
                        elif position['end'] <= span[0]:
                            # rangeがspanの位置まで来てない→pass
                            pass
                        else:
                            # rangeがspanと重なる→span無効
                            is_valid = False
                        new_positions.append({
                            'start': position['start'] + inc_off,
                            'end': position['end'] + inc_off,
                        })
                    if is_valid:
                        if cur_pos < span[0]:
                            text += sentence[cur_pos: span[0]]
                            cur_pos = span[0]
                        new_positions.append({
                            'start': cur_pos + inc_off,
                            'end': cur_pos + inc_off + new_length,
                        })
                        text += new_tag
                        cur_pos += old_length
                        inc_off += new_length - old_length
                    if cur_pos < len(sentence):
                        text += sentence[cur_pos: len(sentence)]
                    cur_pos = 0
                    inc_off = 0
                    sentence = text
                    text = ''
                    positions = new_positions
                    new_positions = list()
                sentences[i] = sentence
                tag_positions[i] = positions
        if DEBUG:
            print(f'sentences:{sentences}')
            print(f'tag_position:{tag_positions}')
        return sentences, tag_positions

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
            self.train_data, model=self.model,
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
    if DEBUG:
        processor.extract_dir = 'testdata'
    # create train data
    processor.wakati()
    if not DEBUG:
        # training
        processor.train()
        # convert
        processor.convert()
    return


if __name__ == '__main__':
    main()
