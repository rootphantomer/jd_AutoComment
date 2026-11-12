# -*- coding: utf-8 -*-
"""评论生成模块。

根据商品名称生成评价内容，依赖京东爬虫、jieba 关键词提取
以及 templates 中的默认/赠品评价模板。
"""

from __future__ import annotations

import logging
import random
from functools import lru_cache
from typing import Any

import jieba  # noqa: F401 — 确保 jieba.analyse 可用
import jieba.analyse

import jdspider
from templates import DEFAULT_COMMENTS, GIFT_COMMENTS

logger = logging.getLogger("comment.comment_generator")

_GIFT_KEYWORDS = ("赠品", "非实物", "增值服务")
_EXCLUDE_KEYWORDS = {"男士", "女士", "男", "女", "一对", "一个", "一件"}


@lru_cache(maxsize=128)
def _comment_pool(pname: str) -> tuple[str, ...]:
    """加载并缓存商品可用的评价语料，避免同一商品重复爬取。"""
    if any(keyword in pname for keyword in _GIFT_KEYWORDS):
        return tuple(GIFT_COMMENTS)

    try:
        comments = jdspider.JDSpider(pname).get_data(2, 3)
    except Exception as exc:
        logger.warning("爬取评论失败: %s，使用默认评价模板", exc)
        return tuple(DEFAULT_COMMENTS)

    return tuple(comments) if comments else tuple(DEFAULT_COMMENTS)


@lru_cache(maxsize=512)
def _extract_name(pname: str) -> str:
    """提取商品名中的核心关键词，并缓存结果。"""
    try:
        all_keywords = jieba.analyse.textrank(pname, topK=10, allowPOS="n")
    except Exception as exc:
        logger.warning('jieba 关键词提取失败: %s，商品名回退为“宝贝”', exc)
        return "宝贝"

    filtered = [
        keyword
        for keyword in all_keywords
        if keyword not in _EXCLUDE_KEYWORDS and len(keyword) > 1
    ]
    if filtered:
        return filtered[0]
    return all_keywords[0] if all_keywords else "宝贝"


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
    call_logger = opts.get("logger")

    if call_logger:
        call_logger.debug("Current item: %s", pname)

    name = _extract_name(pname)
    if call_logger:
        call_logger.debug("Name: %s", name)

    if _class == 1:
        return name

    result = _comment_pool(pname)
    num = min(6 if _type == 1 else 4, len(result))
    comments = "".join(random.sample(result, num)) if num else ""

    if call_logger:
        call_logger.debug("_type: %d, num: %d", _type, num)
        call_logger.debug("Raw comments: %s", comments)

    return 5, comments.replace("$", name)
