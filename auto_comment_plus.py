# -*- coding: utf-8 -*-
# @Time : 2022/2/8 20:50
# @Author : @qiu-lzsnmb and @Dimlitter
# @File : auto_comment_plus.py

"""京东自动评价工具 — CLI 入口。

本文件仅保留命令行参数解析、日志初始化、配置读取与主流程编排，
所有业务逻辑已拆分至各功能模块。用户仍通过 ``python auto_comment_plus.py`` 运行。
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

import jieba

import jdspider
from config import (
    CONFIG_PATH,
    ORDINARY_SLEEP_SEC,
    REVIEW_SLEEP_SEC,
    SERVICE_RATING_SLEEP_SEC,
    SUNBW_SLEEP_SEC,
    USER_CONFIG_PATH,
    build_headers,
    load_config,
)
from evaluator import get_evaluation_stats
from handlers import ordinary, review, service_rating
from logger import setup_logging


def main(opts: dict[str, Any], headers: dict[str, Any], headers2: dict[str, Any]) -> None:
    """主函数，执行所有评价流程。

    Args:
        opts: 配置选项字典，需包含 ``"logger"``、``"dry_run"`` 等键。
        headers: GET 请求头。
        headers2: POST 请求头。
    """
    logger = opts.get("logger")

    if logger:
        logger.info("开始京东批量评价！")

    N = get_evaluation_stats(headers, opts)
    if logger:
        logger.debug("N value after executing get_evaluation_stats(): %s", N)

    if not N:
        if logger:
            logger.error("Ck出现错误，请重新抓取！")
        sys.exit(1)

    if logger:
        logger.info(f"已评价：{N.get('已评价', 0)}个")

    # 普通评价
    if N.get("待评价订单", 0) != 0:
        if logger:
            logger.info("1.开始普通评价")
        N = ordinary(N, headers, headers2, opts)
        if logger:
            logger.debug("N value after executing ordinary(): %s", N)
        N = get_evaluation_stats(headers, opts)
        if logger:
            logger.debug("N value after executing get_evaluation_stats(): %s", N)

    # 追评
    if N.get("待追评", 0) != 0:
        if logger:
            logger.info("3.开始批量追评,注意：追评不会自动上传图片")
        N = review(N, headers, headers2, opts)
        if logger:
            logger.debug("N value after executing review(): %s", N)
        N = get_evaluation_stats(headers, opts)
        if logger:
            logger.debug("N value after executing get_evaluation_stats(): %s", N)

    # 服务评价
    if N.get("服务评价", 0) != 0:
        if logger:
            logger.info("4.开始服务评价")
        N = service_rating(N, headers, opts)
        if logger:
            logger.debug("N value after executing service_rating(): %s", N)
        N = get_evaluation_stats(headers, opts)
        if logger:
            logger.debug("N value after executing get_evaluation_stats(): %s", N)

    if logger:
        logger.info("全部完成啦！")

    # 检查是否有未完成的评价，循环重试（Bug 5修复：递归改为while循环，最多3次）
    max_retries = 3
    for retry in range(max_retries):
        has_pending = False
        for key in N:
            if N[key] != 0:
                has_pending = True
                break
        if not has_pending:
            break
        if logger:
            logger.warning("出现了二次错误，跳过了部分，重新尝试（第%d次）", retry + 1)

        # 普通评价
        if N.get("待评价订单", 0) != 0:
            if logger:
                logger.info("1.开始普通评价")
            N = ordinary(N, headers, headers2, opts)
            if logger:
                logger.debug("N value after executing ordinary(): %s", N)
            N = get_evaluation_stats(headers, opts)
            if logger:
                logger.debug("N value after executing get_evaluation_stats(): %s", N)

        # 追评
        if N.get("待追评", 0) != 0:
            if logger:
                logger.info("3.开始批量追评,注意：追评不会自动上传图片")
            N = review(N, headers, headers2, opts)
            if logger:
                logger.debug("N value after executing review(): %s", N)
            N = get_evaluation_stats(headers, opts)
            if logger:
                logger.debug("N value after executing get_evaluation_stats(): %s", N)

        # 服务评价
        if N.get("服务评价", 0) != 0:
            if logger:
                logger.info("4.开始服务评价")
            N = service_rating(N, headers, opts)
            if logger:
                logger.debug("N value after executing service_rating(): %s", N)
            N = get_evaluation_stats(headers, opts)
            if logger:
                logger.debug("N value after executing get_evaluation_stats(): %s", N)


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="京东自动评价工具")
    parser.add_argument(
        "--dry-run",
        help="完整运行但不提交评价（测试模式）",
        action="store_true",
    )
    parser.add_argument(
        "-lv",
        "--log-level",
        help="指定日志级别 (默认: INFO)",
        default="DEBUG",
        choices=["DEBUG", "WARN", "INFO", "ERROR", "FATAL"],
    )
    parser.add_argument(
        "-o", "--log-file", help="指定日志文件路径（默认使用日期命名）", default=None
    )
    args = parser.parse_args()

    # 规范化日志级别
    log_level = args.log_level.upper()

    opts: dict[str, Any] = {
        "dry_run": args.dry_run,
        "log_level": log_level,
        "log_file": args.log_file,
    }

    # 初始化日志系统
    logger = setup_logging(log_level, log_file=args.log_file)
    opts["logger"] = logger

    # 将 jieba / jdspider 的 default_logger 指向 setup_logging 已配置的日志器
    jieba.default_logger = logging.getLogger("jieba")
    jdspider.default_logger = logging.getLogger("spider")

    if logger:
        logger.debug("Successfully set up console logger")
        logger.debug("CLI arguments: %s", args)
        logger.debug("Options passed to functions: %s", opts)
        logger.debug("Builtin constants:")
        logger.debug("  CONFIG_PATH: %s", CONFIG_PATH)
        logger.debug("  USER_CONFIG_PATH: %s", USER_CONFIG_PATH)
        logger.debug("  ORDINARY_SLEEP_SEC: %s", ORDINARY_SLEEP_SEC)
        logger.debug("  SUNBW_SLEEP_SEC: %s", SUNBW_SLEEP_SEC)
        logger.debug("  REVIEW_SLEEP_SEC: %s", REVIEW_SLEEP_SEC)
        logger.debug("  SERVICE_RATING_SLEEP_SEC: %s", SERVICE_RATING_SLEEP_SEC)

    # 读取配置文件
    if logger:
        logger.debug("Reading the configuration file")

    try:
        cfg = load_config()
        if logger:
            logger.debug("Configurations in Python-dict format: %s", cfg)
    except Exception as e:
        if logger:
            logger.error("Failed to read configuration file: %s", e)
        sys.exit(1)

    # 设置Cookie并构建请求头
    ck = cfg["user"]["cookie"]
    jdspider.cookie = ck.encode("utf-8")
    headers, headers2 = build_headers(ck)

    if logger:
        logger.debug("Builtin HTTP request header: %s", headers)
        logger.debug("Starting main processes")

    # 执行主流程
    try:
        main(opts, headers, headers2)
    except RecursionError:
        if logger:
            logger.error("多次出现未完成情况，程序自动退出")
        sys.exit(1)
