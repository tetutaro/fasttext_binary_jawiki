#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from __future__ import annotations
from typing import List, NamedTuple, Optional
import os
from glob import glob
import subprocess
from multiprocessing import (
    Process,
    Queue,
    JoinableQueue,
    SimpleQueue,
    get_logger,
)
from logging import Logger, Formatter
from logging.handlers import QueueHandler, QueueListener

from tqdm import tqdm

from src.tokenize_gnome import TokenizeGnome
from src.utils import get_nprocess


class TaskRequest(NamedTuple):
    fname: str
    oname: str
    base: bool


class TaskResponse(NamedTuple):
    oname: str


def gnome_worker(
    index: int,
    req_queue: JoinableQueue,
    res_queue: SimpleQueue,
    log_queue: Queue,
    log_level: int,
) -> None:
    logger: Logger = get_logger()
    logger.setLevel(log_level)
    formatter: Formatter = Formatter(f"[GNOME{index:02}] %(message)s")
    handler: QueueHandler = QueueHandler(log_queue)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    gnome: TokenizeGnome = TokenizeGnome(logger=logger)
    # Main loop
    while True:
        req: Optional[TaskRequest] = req_queue.get(block=True)
        if req is None:
            req_queue.put(None)
            break
        gnome.tokenize(fname=req.fname, oname=req.oname, base=req.base)
        res = TaskResponse(oname=req.oname)
        res_queue.put(res)
        req_queue.task_done()
    return


class Tokenizer:
    version: str
    extract_dir: str
    base: bool
    train_fname: str
    temp_dir: str
    nprocess: int
    logger: Logger

    def __init__(
        self: Tokenizer,
        version: str,
        extract_dir: str,
        base: bool,
        logger: Logger,
    ) -> None:
        self.version = version
        self.extract_dir = extract_dir
        self.base = base
        if base:
            self.train_fname = f"jawiki_base_{version}.txt"
            self.temp_dir = "temp_base_" + extract_dir
        else:
            self.train_fname = f"jawiki_{version}.txt"
            self.temp_dir = "temp_" + extract_dir
        self.nprocess = get_nprocess()
        self.logger = logger
        return

    def tokenize(self: Tokenizer) -> None:
        if os.path.exists(self.train_fname):
            self.logger.info("train data has already created. skip wakati.")
            return
        # Create temporary directories
        os.makedirs(self.temp_dir, exist_ok=True)
        fnames: List[str] = glob(f"{self.extract_dir}/*/*")
        mdirs: List[str] = list(set([x.split(os.sep)[-2] for x in fnames]))
        for mdir in mdirs:
            os.makedirs(os.path.join(self.temp_dir, mdir), exist_ok=True)
        # Tokenize
        self._tokenize(fnames=fnames)
        # Summarize results
        cmd = f"cat {self.temp_dir}/*/* > {self.train_fname}"
        try:
            subprocess.run(cmd, check=True, shell=True, text=True)
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            if os.path.exists(self.train_fname):
                os.remove(self.train_fname)
            raise e
        return

    def _tokenize(self: Tokenizer, fnames: List[str]) -> None:
        # Register tasks
        request_queue: JoinableQueue = JoinableQueue()
        result_queue: SimpleQueue = SimpleQueue()
        task_remains: int = 0
        fnames = glob(f"{self.extract_dir}/*/*")
        for fname in fnames:
            oname: str = os.path.join(self.temp_dir, *fname.split(os.sep)[1:])
            request_queue.put(
                TaskRequest(
                    fname=fname,
                    oname=oname,
                    base=self.base,
                )
            )
            task_remains += 1
        message_queue: Queue = Queue()
        listener: QueueListener = QueueListener(
            message_queue,
            *self.logger.handlers,
            respect_handler_level=True,
        )
        listener.start()
        # Kick gnomes
        procs: List[Process] = list()
        for i in range(self.nprocess):
            proc: Process = Process(
                target=gnome_worker,
                args=(
                    i + 1,
                    request_queue,
                    result_queue,
                    message_queue,
                    self.logger.level,
                ),
            )
            procs.append(proc)
            proc.start()
        # Show progress bar
        pbar = tqdm(total=task_remains)
        while task_remains > 0:
            _ = result_queue.get()
            pbar.update()
            task_remains -= 1
        pbar.close()
        # Wait for gnomes exit
        request_queue.join()
        request_queue.put(None)
        for proc in procs:
            proc.join()
        listener.stop()
        message_queue.close()
        request_queue.close()
        result_queue.close()
        return
