#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from typing import Optional
import os


def get_nprocess() -> int:
    cpu_count: Optional[int] = os.cpu_count()
    if cpu_count is None or cpu_count < 3:
        return 1
    return cpu_count - 1
