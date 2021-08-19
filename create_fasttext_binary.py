#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import List, Tuple, TextIO
import sys
import os
import shutil
import subprocess
from glob import glob
from collections import defaultdict
from multiprocessing import Process
import requests
from bs4 import BeautifulSoup
import simplejson as json
from MeCab import Tagger
from neologdn import normalize as neonorm
import fasttext
from gensim.models.keyedvectors import KeyedVectors
import argparse
from logging import Logger, getLogger, Formatter, StreamHandler, INFO

MIN_WORDS_PER_SENTENCE: int = 5
MAX_WORDS_PER_SENTENCE: int = 500
REPLACE_PATTERNS: List[Tuple[str, str]] = [
    ('\n', ''),
    ('　', ' '),
    ('、、', '、'),
    ('（、', '（'),
    ('（，', '（'),
    ('、）', '）'),
    ('，)', '）'),
    ('（）', ''),
    ('(,', '('),
    (',)', ')'),
    ('()', ''),
    ('「」', ''),
    ('『』', ''),
    ('、。', '。'),
]


def wakati_each_dir(
    tagger: Tagger,
    wn: str,
    fns: List[str],
    use_original: bool,
    offset_original: int
) -> None:
    # 中間ファイル
    wf = open(wn, 'wt')
    for fn in fns:
        with open(fn, 'rt') as rf:
            line = rf.readline()
            while line:
                # JSONの読み込み
                try:
                    info = json.loads(line.strip())
                except Exception:
                    line = rf.readline()
                    continue
                title = info.get('title')
                text = info.get('text')
                # 改行コード２連続（１行空け）を文章の区切りとする
                sentences = text.split('\n\n')
                for sentence in sentences:
                    if sentence == title:
                        continue
                    _wakati_each_sentence(
                        tagger=tagger,
                        sentence=sentence,
                        wf=wf,
                        use_original=use_original,
                        offset_original=offset_original
                    )
                line = rf.readline()
    wf.close()
    print(f'wakati: {wn} done')
    return


def _wakati_each_sentence(
    tagger: Tagger,
    sentence: str,
    wf: TextIO,
    use_original: bool,
    offset_original: int
) -> None:
    '''文章を正規化し、分かち書きして、ファイルに書き込む
    '''
    # 正規化
    for pattern in REPLACE_PATTERNS:
        sentence = sentence.replace(pattern[0], pattern[1])
    try:
        sentence = neonorm(sentence)
    # 変な文字がある場合はスキップ
    except Exception:
        return
    # 空行はスキップ
    if len(sentence) == 0:
        return
    # 分かち書き
    if use_original:
        # 単語の原型を使う場合
        words = list()
        nodes = tagger.parse(sentence)
        for node in nodes.splitlines():
            node = node.strip()
            if node == 'EOS':
                break
            try:
                surface, features_str = node.split('\t', 1)
            except Exception:
                continue
            features = features_str.split(',')
            if features[offset_original] == '*':
                # 未知語の場合は表層語を用いる
                words.append(surface)
            else:
                words.append(features[offset_original])
        wakatied = ' '.join(words)
    else:
        wakatied = tagger.parse(sentence).strip()
    # あまりにも短い文章、あまりにも長い文章はスキップ
    num_words = len(wakatied.split(' '))
    if (
        num_words < MIN_WORDS_PER_SENTENCE
    ) or (
        num_words > MAX_WORDS_PER_SENTENCE
    ):
        return
    # 書き込み
    wf.write(wakatied + '\n')
    return


class Processor(object):
    INSTALLED_DICTIONARIES: List[str] = [
        'ipa', 'juman', 'neologd'
    ]

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
        self.dictionary = dictionary
        self.use_original = original
        self.model = model
        if dim < 100:
            raise ValueError(f'size of word vectors is too small: {dim}')
        if dim > 300:
            raise ValueError(f'size of word vectors is too big: {dim}')
        self.dim = dim
        if epoch < 1:
            raise ValueError(f'epoch should be > 0: {epoch}')
        self.epoch = epoch
        if mincount < 1:
            raise ValueError(f'mincount should be > 0: {mincount}')
        self.mincount = mincount
        self.logger = logger
        self._download_wikiextractor()
        self._scrape_wikimedia()
        self._load_mecab()
        return

    def _download_wikiextractor(self: Processor) -> None:
        '''WikiExtractor.pyをダウンロードする
        '''
        if not os.path.exists('WikiExtractor.py'):
            subprocess.run([
                'wget', '-O', 'WikiExtractor.py',
                'https://raw.githubusercontent.com/zaemyung/'
                'wikiextractor/master/WikiExtractor.py'
            ], check=True)
        return

    def _load_mecab(self: Processor) -> None:
        if os.path.isdir(self.dictionary):
            # load local dictionary
            self.logger.info(f'loading local dictionary: {self.dictionary}')
            if self.use_original:
                self.tagger = Tagger(f'-d {self.dictionary}')
            else:
                self.tagger = Tagger(f'-O wakati -d {self.dictionary}')
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
        self.logger.info(f'loading installed dictionary: {self.dictionary}')
        if self.use_original:
            self.tagger = Tagger(f'-d {dic_path}')
        else:
            self.tagger = Tagger(f'-O wakati -d {dic_path}')
        if self.dictionary == 'juman':
            self.offset_original = 4
        else:
            self.offset_original = 6
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
                'python', 'WikiExtractor.py', self.filename,
                '--json', '--output', self.extract_dir, '--quiet'
            ], check=True)
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.isdir(self.extract_dir):
                shutil.rmtree(self.extract_dir)
            raise e
        return

    def wakati(self: Processor) -> None:
        '''WikipediaのJSONファイルを１行１文章で
        単語（形態素）毎に分かち書きし、
        fastTextの学習用データにする
        '''
        # 学習用データ
        if self.use_original:
            self.train_data = f'jawiki_orig_{self.version}.txt'
        else:
            self.train_data = f'jawiki_{self.version}.txt'
        if os.path.exists(self.train_data):
            self.logger.info('train data has already created. skip wakati.')
            return
        # 中間ファイル用のTemporary directory
        if self.use_original:
            self.temp_dir = 'temp_orig_' + self.extract_dir
        else:
            self.temp_dir = 'temp_' + self.extract_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        # WikiExtractorが出力したファイルを、ディレクトリ毎にまとめる
        json_files = glob(f'{self.extract_dir}/*/*')
        json_dir_files = defaultdict(list)
        for fn in json_files:
            json_dir_files[fn.split(os.sep)[1]].append(fn)
        del json_files
        # ファイルの変換
        if sys.version_info.major == 3 and sys.version_info.minor > 7:
            # Python 3.8 以降はmultiprocessingがうまく動かない
            # （Taggerの共有をなんとかする必要がある）ので
            # 逐次的に処理する
            for dn, fns in json_dir_files.items():
                wn = os.path.join(self.temp_dir, f'{dn}.txt')
                wakati_each_dir(
                    tagger=self.tagger,
                    wn=wn,
                    fns=fns,
                    use_original=self.use_original,
                    offset_original=self.offset_original
                )
        else:
            # Python 3.7 までだと何とかなってしまうので
            # multiprocessing.Processで簡易的な並列化
            processes = list()
            for dn, fns in json_dir_files.items():
                wn = os.path.join(self.temp_dir, f'{dn}.txt')
                process = Process(
                    target=wakati_each_dir,
                    kwargs={
                        'tagger': self.tagger,
                        'wn': wn,
                        'fns': fns,
                        'use_original': self.use_original,
                        'offset_original': self.offset_original,
                    }
                )
                process.start()
                processes.append(process)
            for process in processes:
                process.join()
        # 中間ファイルをまとめてひとつのfastText学習量ファイルにする
        cmd = f'cat {self.temp_dir}/* > {self.train_data}'
        try:
            subprocess.run(cmd, check=True, shell=True, text=True)
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.exists(self.train_data):
                os.remove(self.train_data)
            raise e
        shutil.rmtree(self.temp_dir)
        return

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
    # create train data
    processor.wakati()
    # training
    processor.train()
    # convert
    processor.convert()
    return


if __name__ == '__main__':
    main()
