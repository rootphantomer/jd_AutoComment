# -*- coding: utf-8 -*-
"""评价查询与统计模块。

提供查询京东各类评价数量以及获取评价统计摘要的能力。
所有网络请求所需的 headers 均通过函数参数显式传入，
不再依赖全局变量。
"""

from __future__ import annotations

from typing import Any

import requests
from lxml import etree


def all_evaluate(
    headers: dict[str, Any],
    opts: dict[str, Any] | None = None,
) -> dict[str, int]:
    """查询各类评价数量。

    Args:
        headers: HTTP 请求头（包含 Cookie）。
        opts: 配置选项，需包含 ``"logger"`` 键。

    Returns:
        评价类型与对应数量的字典，如 ``{"待评价订单": 3, "已评价": 10}``。
    """
    opts = opts or {}
    logger = opts.get("logger")
    n: dict[str, int] = {}

    url = "https://club.jd.com/myJdcomments/myJdcomment.action?"
    if logger:
        logger.info("URL: %s", url)
        logger.debug("Fetching website data")

    try:
        req = requests.get(url, headers=headers, timeout=30)
        req.raise_for_status()
        if logger:
            logger.debug("Successfully accepted the response with status code %d", req.status_code)
    except requests.RequestException as e:
        if logger:
            logger.error("Failed to fetch evaluate data: %s", e)
        return n

    try:
        req_et = etree.HTML(req.text)
        if logger:
            logger.debug("Successfully parsed an XML tree")

        evaluate_data = req_et.xpath('//*[@id="main"]/div[2]/div[1]/div/ul/li')
        if logger:
            logger.debug("Total loop times: %d", len(evaluate_data))

        for ev in evaluate_data:
            na = ev.xpath("a/text()")[0]
            if logger:
                logger.debug("na: %s", na)
            try:
                num = ev.xpath("b/text()")[0]
                if logger:
                    logger.debug("num: %s", num)
            except IndexError:
                if logger:
                    logger.info("Can't find num content in XPath, fallback to 0")
                num = 0
            n[na] = int(num)
    except Exception as e:
        if logger:
            logger.error("Error parsing evaluate data: %s", e)

    return n


def get_evaluation_stats(
    headers: dict[str, Any],
    opts: dict[str, Any] | None = None,
) -> dict[str, int]:
    """获取评价统计信息（原 No() 函数）。

    调用 :func:`all_evaluate` 获取数据后打印摘要日志。

    Args:
        headers: HTTP 请求头（包含 Cookie）。
        opts: 配置选项，需包含 ``"logger"`` 键。

    Returns:
        评价数量统计字典。
    """
    opts = opts or {}
    logger = opts.get("logger")

    n = all_evaluate(headers, opts)
    if logger:
        s = "----".join([f"{i} {n[i]}" for i in n])
        logger.info(s)

    return n
