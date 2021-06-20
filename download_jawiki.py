#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import annotations
import sys
import os
import shutil
import subprocess
import requests
from bs4 import BeautifulSoup
import logging


class Downloader(object):
    def __init__(self: Downloader, logger: logging.Logger) -> None:
        self.logger = logger
        self._scrape_wikimedia()
        return

    def _scrape_wikimedia(self: Downloader) -> None:
        # scrape jawiki top page
        url = 'https://dumps.wikimedia.org/jawiki/'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        versions = list()
        for a in soup.find_all('a'):
            href = a.get('href')
            if not href.startswith(('.', 'latest')):
                versions.append(href)
        # get latest version
        latest_dir = sorted(versions)[-1]
        self.version = latest_dir.split(os.sep)[0]
        self.filename = (
            f'jawiki-{self.version}'
            '-pages-articles-multistream.xml.bz2'
        )
        self.extract_dir = f'jawiki_{self.version}'
        # scrape latest page
        url += latest_dir
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        fpath = None
        for a in soup.find_all('a'):
            if a.string == self.filename:
                fpath = a.get('href')
                break
        if fpath is None:
            raise ValueError(f'dump file not found: {self.filename}')
        self.file_url = 'https://dumps.wikimedia.org' + fpath
        return

    def download(self: Downloader) -> None:
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

    def extract(self: Downloader) -> None:
        assert os.path.exists(self.filename)
        if os.path.isdir(self.extract_dir):
            self.logger.info('already extracted. skip extracting.')
            return
        try:
            subprocess.run([
                'wikiextractor', self.filename,
                '--json', '--output', self.extract_dir
            ], check=True)
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.isdir(self.extract_dir):
                shutil.rmtree(self.extract_dir)
            raise e
        return


def main() -> None:
    # setup logger
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s')
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # download
    dl = Downloader(logger=logger)
    dl.download()
    # extract
    dl.extract()
    return


if __name__ == '__main__':
    main()
