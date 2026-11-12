# -*- coding: utf-8 -*-
"""图片工具模块。

提供评价流程中需要的图片下载、上传与清理功能。
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

import requests

_logger = logging.getLogger("comment.image_utils")


def _get_logger(logger: logging.Logger | None) -> logging.Logger:
    return logger or _logger


def _normalize_image_url(img_url: str) -> str:
    """补全图片 URL 的协议头。"""
    img_url = img_url.strip()
    if img_url.startswith("//"):
        return f"https:{img_url}"
    if img_url.startswith(("http://", "https://")):
        return img_url
    return f"https://{img_url.lstrip('/')}"


def generate_unique_filename() -> str:
    """生成唯一的 JPG 文件名。

    使用时间戳末5位 + UUID 前5位组合为 10 位文件名。

    Returns:
        形如 ``"1234567890.jpg"`` 的唯一文件名字符串。
    """
    timestamp = str(int(time.time()))[-5:]
    unique_id = str(uuid.uuid4().int)[:5]
    unique_filename = f"{timestamp}{unique_id}.jpg"
    return unique_filename


def download_image(
    img_url: str,
    file_name: str,
    logger: logging.Logger | None = None,
) -> str | None:
    """下载图片到本地 ``img/`` 目录。

    Args:
        img_url: 不含协议头的图片 URL（如 ``"//img.jd.com/xxx.jpg"``）。
        file_name: 保存的文件名。

    Returns:
        保存后的本地文件路径；下载失败时返回 None。
    """
    log = _get_logger(logger)
    full_url = _normalize_image_url(img_url)
    try:
        response = requests.get(full_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        log.warning("下载图片失败: %s", e)
        return None

    if not response.content:
        log.warning("图片内容为空: %s", full_url)
        return None

    directory = "img"
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, file_name)

    try:
        with open(file_path, "wb") as file:
            file.write(response.content)
    except OSError as e:
        log.warning("保存图片失败: %s", e)
        return None

    return file_path


def upload_image(
    filename: str,
    file_path: str,
    session: requests.Session,
    headers: dict[str, Any],
    logger: logging.Logger | None = None,
) -> requests.Response | None:
    """上传图片到京东接口。

    Args:
        filename: 文件名。
        file_path: 本地文件路径。
        session: requests 会话对象。
        headers: 请求头。

    Returns:
        上传成功的响应对象；上传失败时返回 None。
    """
    log = _get_logger(logger)
    try:
        with open(file_path, "rb") as file:
            files = {
                "name": (None, filename),
                "Filedata": (file_path, file, "image/jpeg"),
            }
            response = session.post(
                "https://club.jd.com/myJdcomments/ajaxUploadImage.action",
                headers=headers,
                files=files,
                timeout=30,
            )
        return response
    except (OSError, requests.RequestException) as e:
        log.warning("上传图片失败: %s", e)
        return None


def delete_jpg(logger: logging.Logger | None = None) -> None:
    """删除当前目录及 img 子目录下的所有 JPG 图片。"""
    current_directory = os.getcwd()
    for directory in [current_directory, os.path.join(current_directory, "img")]:
        try:
            if not os.path.isdir(directory):
                continue
            file_list = os.listdir(directory)
            for file_name in file_list:
                if file_name.lower().endswith(".jpg"):
                    file_path = os.path.join(directory, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        except OSError as e:
            _get_logger(logger).warning("删除 %s 下的 JPG 失败: %s", directory, e)
