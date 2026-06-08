# -*- coding: utf-8 -*-
"""图片工具模块。

提供评价流程中需要的图片下载、上传与清理功能。
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

import requests


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


def download_image(img_url: str, file_name: str) -> str | None:
    """下载图片到本地 ``img/`` 目录。

    Args:
        img_url: 不含协议头的图片 URL（如 ``"//img.jd.com/xxx.jpg"``）。
        file_name: 保存的文件名。

    Returns:
        保存后的本地文件路径；下载失败时返回 None。
    """
    full_url = f"https:{img_url}"
    try:
        response = requests.get(full_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to download image: {e}")
        return None

    directory = "img"
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, file_name)

    with open(file_path, "wb") as file:
        file.write(response.content)

    return file_path


def upload_image(
    filename: str,
    file_path: str,
    session: requests.Session,
    headers: dict[str, Any],
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
    files: dict[str, Any] | None = None
    try:
        files = {
            "name": (None, filename),
            "Filedata": (file_path, open(file_path, "rb"), "image/jpeg"),
        }

        response = session.post(
            "https://club.jd.com/myJdcomments/ajaxUploadImage.action",
            headers=headers,
            files=files,
            timeout=30,
        )
        return response
    except requests.RequestException as e:
        print(f"Failed to upload image: {e}")
        return None
    finally:
        # 确保文件被关闭
        if files is not None:
            files["Filedata"][1].close()


def delete_jpg() -> None:
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
            print(f"Error deleting jpg files in {directory}: {e}")
