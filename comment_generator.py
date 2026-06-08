# -*- coding: utf-8 -*-
"""评论生成模块。

根据商品名称生成评价内容，依赖京东爬虫、jieba 关键词提取
以及 templates 中的默认/赠品评价模板。
"""

from __future__ import annotations

import random
from typing import Any

import jieba  # just for linting
import jieba.analyse

import jdspider
from templates import DEFAULT_COMMENTS, GIFT_COMMENTS


def generation(
    pname: str,
    _class: int = 0,
    _type: int = 1,
    opts: dict[str, Any] | None = None,
) -> tuple[int, str] | str:
    """生成评价内容。

    Args:
        pname: 商品名称。
        _class: 返回类型。0 — 返回 (星级, 评价内容) 元组；
                1 — 仅返回商品名关键词字符串。
        _type: 评价类型。0 — 追评；1 — 普通评价。
        opts: 配置选项，需包含 ``"logger"`` 键。

    Returns:
        - 当 ``_class == 1`` 时，返回商品名关键词 (str)。
        - 当 ``_class == 0`` 时，返回 (星级, 评价内容) 元组。
    """
    opts = opts or {}
    logger = opts.get("logger")

    items = [pname]
    if logger:
        logger.debug("Items: %s", items)
        logger.debug("Total loop times: %d", len(items))

    result: list[str] = []
    for item in items:
        if logger:
            logger.debug("Current item: %s", item)

        try:
            spider = jdspider.JDSpider(item)
            if logger:
                logger.debug("Successfully created a JDSpider instance")
        except Exception as e:
            if logger:
                logger.warning("Failed to create JDSpider: %s", e)
            result = DEFAULT_COMMENTS[:]
            break

        # 增加对增值服务的评价鉴别
        if any(keyword in pname for keyword in ["赠品", "非实物", "增值服务"]):
            result = GIFT_COMMENTS[:]
        else:
            try:
                result = spider.get_data(2, 3)
            except Exception as e:
                if logger:
                    logger.warning("Failed to get data from spider: %s, using default comments", e)
                result = DEFAULT_COMMENTS[:]

        if logger:
            logger.debug("Result: %s", result)

    # 提取商品名关键词
    try:
        # 先尝试提取所有名词
        all_keywords = jieba.analyse.textrank(pname, topK=10, allowPOS="n")

        # 过滤掉不合适的关键词（性别、数量词等）
        exclude_keywords = {"男士", "女士", "男", "女", "一对", "一个", "一件"}
        filtered_keywords = [kw for kw in all_keywords if kw not in exclude_keywords and len(kw) > 1]

        # 如果有过滤后的关键词，使用第一个；否则使用原始的第一个
        name = filtered_keywords[0] if filtered_keywords else (all_keywords[0] if all_keywords else "宝贝")

        if logger:
            logger.debug("Name: %s", name)
    except Exception as e:
        if logger:
            logger.warning('jieba textrank analysis error: %s, name fallback to "宝贝"', e)
        name = "宝贝"

    if _class == 1:
        if logger:
            logger.debug("_class is 1. Directly return name")
        return name

    # 生成评价内容
    num = 6 if _type == 1 else 4
    num = min(num, len(result))
    comments = "".join(random.sample(result, num))

    if logger:
        logger.debug("_type: %d", _type)
        logger.debug("num: %d", num)
        logger.debug("Raw comments: %s", comments)

    return 5, comments.replace("$", name)
