# -*- coding: utf-8 -*-
"""配置加载与常量定义模块。

本模块集中管理京东自动评价工具的所有配置常量与配置文件读取逻辑，
消除原先散落在各处的全局 headers 隐式依赖。
"""

from __future__ import annotations

import os
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

CONFIG_PATH: str = "./config.yml"
"""默认配置文件路径"""

USER_CONFIG_PATH: str = "./config.user.yml"
"""用户自定义配置文件路径（优先于默认配置）"""

ORDINARY_SLEEP_SEC: int = 10
"""普通评价提交后的休眠秒数"""

SUNBW_SLEEP_SEC: int = 5
"""晒单评价提交后的休眠秒数"""

REVIEW_SLEEP_SEC: int = 10
"""追评提交后的休眠秒数"""

SERVICE_RATING_SLEEP_SEC: int = 15
"""服务评价提交后的休眠秒数"""


# ---------------------------------------------------------------------------
# 配置读取
# ---------------------------------------------------------------------------

def load_config() -> dict[str, Any]:
    """读取 YAML 配置文件并返回字典。

    优先读取 ``USER_CONFIG_PATH``；若不存在则回退到 ``CONFIG_PATH``。

    Returns:
        解析后的配置字典。

    Raises:
        FileNotFoundError: 配置文件不存在时。
        yaml.YAMLError: 配置文件格式错误时。
    """
    if os.path.exists(USER_CONFIG_PATH):
        cfg_path = USER_CONFIG_PATH
    else:
        cfg_path = CONFIG_PATH

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    return cfg


# ---------------------------------------------------------------------------
# Headers 构建
# ---------------------------------------------------------------------------

def build_headers(cookie: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """根据 Cookie 字符串构建两组 HTTP 请求头。

    Args:
        cookie: 用户 Cookie 字符串。

    Returns:
        (headers, headers2) 二元组。
        - headers: 精简请求头，用于普通 GET 请求。
        - headers2: 完整请求头，用于 POST 提交评价等操作。
    """
    ck = cookie.encode("utf-8")

    headers2: dict[str, Any] = {
        "Cookie": ck,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36"
        ),
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://club.jd.com/",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    headers: dict[str, Any] = {
        "Cookie": ck,
        "User-Agent": (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0 '
            'Sec-Ch-Ua: "Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"'
        ),
        "DNT": "1",
    }

    return headers, headers2
