#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from __future__ import annotations
import os
import subprocess
import shutil
from logging import Logger

from src.utils import get_nprocess


class Extractor:
    filename: str
    extract_dir: str
    logger: Logger

    def __init__(
        self: Extractor,
        filename: str,
        extract_dir: str,
        logger: Logger,
    ) -> None:
        self.filename = filename
        self.extract_dir = extract_dir
        self.logger = logger
        return

    def extract(self: Extractor) -> None:
        """WikiExtractorを使ってWikipediaのダンプをJSONに変換する"""
        assert os.path.exists(self.filename)
        if os.path.isdir(self.extract_dir):
            self.logger.info("already extracted. skip extracting.")
            return
        try:
            subprocess.run(
                [
                    "wikiextractor",
                    self.filename,
                    "--json",
                    "--quiet",
                    "--no-templates",
                    "--processes",
                    str(get_nprocess()),
                    "--output",
                    self.extract_dir,
                ],
                check=True,
            )
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.isdir(self.extract_dir):
                shutil.rmtree(self.extract_dir)
            raise e
        return
