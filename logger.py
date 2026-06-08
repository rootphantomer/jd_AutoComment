# -*- coding: utf-8 -*-
"""日志系统模块。

提供带 ANSI 颜色/样式的日志格式化能力，以及统一的日志初始化函数。
"""

from __future__ import annotations

import copy
import logging
import os
import time
from typing import Any

# ---------------------------------------------------------------------------
# ANSI 样式常量
# ---------------------------------------------------------------------------

_COLORS: dict[str, int] = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
}

_RESET_SEQ: str = "\033[0m"
_COLOR_SEQ: str = "\033[1;%dm"
_BOLD_SEQ: str = "\033[1m"
_ITALIC_SEQ: str = "\033[3m"
_UNDERLINED_SEQ: str = "\033[4m"

_FORMATTER_COLORS: dict[str, int] = {
    "DEBUG": _COLORS["blue"],
    "INFO": _COLORS["green"],
    "WARNING": _COLORS["yellow"],
    "ERROR": _COLORS["red"],
    "CRITICAL": _COLORS["red"],
}


# ---------------------------------------------------------------------------
# 样式格式化工具
# ---------------------------------------------------------------------------

def format_style_seqs(msg: str, use_style: bool = True) -> str:
    """格式化日志消息中的样式控制字符。

    将 ``$RESET`` / ``$BOLD`` / ``$ITALIC`` / ``$UNDERLINED`` 占位符
    替换为对应的 ANSI 转义序列（或空字符串）。

    Args:
        msg: 原始消息文本。
        use_style: 是否启用 ANSI 样式。为 False 时清除所有占位符。

    Returns:
        替换后的消息文本。
    """
    if use_style:
        msg = msg.replace("$RESET", _RESET_SEQ)
        msg = msg.replace("$BOLD", _BOLD_SEQ)
        msg = msg.replace("$ITALIC", _ITALIC_SEQ)
        msg = msg.replace("$UNDERLINED", _UNDERLINED_SEQ)
    else:
        msg = msg.replace("$RESET", "")
        msg = msg.replace("$BOLD", "")
        msg = msg.replace("$ITALIC", "")
        msg = msg.replace("$UNDERLINED", "")
    return msg


class StyleFormatter(logging.Formatter):
    """支持按日志级别着色的格式化器。"""

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        use_style: bool = True,
    ) -> None:
        logging.Formatter.__init__(self, fmt, datefmt)
        self.use_style = use_style

    def format(self, record: logging.LogRecord) -> str:
        rcd = copy.copy(record)
        levelname = rcd.levelname
        if self.use_style and levelname in _FORMATTER_COLORS:
            levelname_with_color = "%s%s%s" % (
                _COLOR_SEQ % (30 + _FORMATTER_COLORS[levelname]),
                levelname,
                _RESET_SEQ,
            )
            rcd.levelname = levelname_with_color
        return logging.Formatter.format(self, rcd)


# ---------------------------------------------------------------------------
# 日志初始化
# ---------------------------------------------------------------------------

def _normalize_log_level(log_level: str) -> int:
    """将字符串日志级别转换为 logging 模块的整数常量。

    Args:
        log_level: 日志级别字符串，如 ``"DEBUG"``、``"WARN"``、``"FATAL"``。

    Returns:
        对应的 logging 级别整数。
    """
    level_str = log_level.upper()
    # WARN 是 WARNING 的别名，FATAL 是 CRITICAL 的别名
    level_map: dict[str, int] = {
        "WARN": logging.WARNING,
        "FATAL": logging.CRITICAL,
    }
    if level_str in level_map:
        return level_map[level_str]
    return getattr(logging, level_str, logging.INFO)


def setup_logging(log_level: str, log_file: str | None = None) -> logging.Logger:
    """统一设置日志系统。

    创建主日志器 ``"comment"``，同时为 ``jieba`` 和 ``spider`` 子系统
    配置相同的处理器与级别。

    Args:
        log_level: 日志级别字符串，如 ``"DEBUG"``、``"INFO"``。
        log_file: 日志文件路径。为 None 时自动按日期生成；
                  为 False 时不创建文件日志。

    Returns:
        主日志器实例（名称 ``"comment"``）。
    """
    level = _normalize_log_level(log_level)

    # 主日志器
    logger = logging.getLogger("comment")
    logger.setLevel(level)

    # 格式化器
    formatter = StyleFormatter("%(asctime)s %(levelname)-19s %(message)s")
    rawformatter = StyleFormatter(
        "%(asctime)s %(levelname)-8s %(message)s", use_style=False
    )

    # 控制台处理器
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 文件处理器
    if log_file is not False:  # noqa: E712 — 允许 False 显式禁用文件日志
        try:
            log_dir = "log"
            os.makedirs(log_dir, exist_ok=True)

            if log_file:
                log_file_path = log_file
            else:
                today = time.strftime("%Y-%m-%d")
                log_file_path = os.path.join(log_dir, f"{today}.txt")

            handler = logging.FileHandler(log_file_path, "a", encoding="utf-8")
            handler.setLevel(level)
            handler.setFormatter(rawformatter)
            logger.addHandler(handler)
        except Exception as exc:
            logger.error("Failed to open the file handler")
            logger.error("Error message: %s", exc)

    # 配置 jieba 和 spider 日志器
    jieba_logger = logging.getLogger("jieba")
    jieba_logger.setLevel(level)
    for h in list(logger.handlers):
        jieba_logger.addHandler(h)

    spider_logger = logging.getLogger("spider")
    spider_logger.setLevel(level)
    for h in list(logger.handlers):
        spider_logger.addHandler(h)

    return logger
