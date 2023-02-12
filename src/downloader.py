#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import List, Optional
import os
import subprocess
from logging import Logger

import requests
from requests.models import Response
from bs4 import BeautifulSoup


class Downloader:
    version: Optional[str] = None
    filename: str
    extract_dir: str
    file_url: str
    logger: Logger

    def __init__(
        self: Downloader,
        logger: Logger,
    ) -> None:
        self.logger = logger
        return

    def download(self: Downloader, version: str) -> None:
        if version != "none":
            self.version = version
        self._scrape_wikimedia()
        if os.path.isdir(self.extract_dir):
            self.logger.info("already extracted. skip download.")
            return
        if os.path.isfile(self.filename):
            self.logger.info("already downloaded. skip download.")
            return
        try:
            subprocess.run(
                ["wget", "-O", self.filename, self.file_url], check=True
            )
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.exists(self.filename):
                os.remove(self.filename)
            raise e
        return

    def _scrape_wikimedia(self: Downloader) -> None:
        """wikimediaをスクレイピングして、
        ダンプの最新バージョンもしくは指定されたバージョンを得る
        """
        # scrape jawiki top page
        url: str = "https://dumps.wikimedia.org/jawiki/"
        r: Response = requests.get(url)
        soup: BeautifulSoup = BeautifulSoup(r.text, "html.parser")
        versions: List[str] = list()
        for a in soup.find_all("a"):
            href: str = a.get("href")
            if not href.startswith((".", "latest")):
                versions.append(href.split(os.sep)[0])
        # get latest and valid version
        found: bool = False
        if self.version is None:
            for version in sorted(versions, reverse=True):
                found = self._scrape_wikimedia_page(version=version)
                if found is True:
                    break
        else:
            for version in sorted(versions, reverse=True):
                if self.version == version:
                    found = self._scrape_wikimedia_page(version=version)
        if found is False:
            raise SystemError("valid wikipedia dump version is not found")
        return

    def _scrape_wikimedia_page(self: Downloader, version: str) -> bool:
        """wikimediaページをスクレイピングして、ファイルのURLを得る

        Args:
            version (str): Wikipediaのバージョン(YYYYMMDD)
        """
        self.logger.debug(f"check version: {version}")
        fname: str = f"jawiki-{version}-pages-articles-multistream.xml.bz2"
        extract_dir: str = f"jawiki_{version}"
        # scrape latest page
        url: str = f"https://dumps.wikimedia.org/jawiki/{version}/"
        r: Response = requests.get(url)
        soup: BeautifulSoup = BeautifulSoup(r.text, "html.parser")
        fpath: Optional[str] = None
        for a in soup.find_all("a"):
            if a.string == fname:
                fpath = a.get("href")
                break
        if fpath is None:
            return False
        self.logger.info(f"latest version: {version}")
        self.version = version
        self.filename = fname
        self.extract_dir = extract_dir
        self.file_url = "https://dumps.wikimedia.org" + fpath
        return True
