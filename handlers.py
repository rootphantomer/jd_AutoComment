# -*- coding: utf-8 -*-
"""评价处理器模块。

包含普通评价、追评和服务评价三个核心业务处理函数。
所有网络请求所需的 headers 均通过函数参数显式传入。
"""

from __future__ import annotations

import random
import time
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlsplit

import requests
from lxml import etree

from comment_generator import generation
from config import ORDINARY_SLEEP_SEC, REVIEW_SLEEP_SEC, SERVICE_RATING_SLEEP_SEC
from image_utils import generate_unique_filename, download_image, upload_image

ORDER_URL = "https://club.jd.com/myJdcomments/myJdcomment.action"
SAVE_COMMENT_URL = "https://club.jd.com/myJdcomments/saveProductComment.action"
SAVE_REVIEW_URL = "https://club.jd.com/afterComments/saveAfterCommentAndShowOrder.action"
SURVEY_URL = "https://club.jd.com/myJdcomments/insertRestSurvey.action"
IMAGE_LIST_URL = "https://club.jd.com/discussion/getProductPageImageCommentList.action"
UPLOADED_IMAGE_BASE = "//img20.360buyimg.com/shaidan/s645x515_"


def _fetch_order_rows(
    sort: int,
    pending: int,
    headers: dict[str, Any],
    opts: dict[str, Any],
    primary_xpath: str,
    fallback_xpath: str,
    label: str,
) -> list[Any]:
    """分页抓取订单列表，并按主/备用 XPath 提取订单节点。"""
    logger = opts.get("logger")
    pages: list[Any] = []
    page_count = pending // 20 + 1

    if logger:
        logger.debug("Fetching %s pages, total loop times: %d", label, page_count)

    for page in range(1, page_count + 1):
        url = f"{ORDER_URL}?sort={sort}&page={page}"
        if logger:
            logger.debug("URL: %s", url)

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            if logger:
                logger.warning("Failed to fetch %s page %d: %s", label, page, exc)
            continue

        pages.append(etree.HTML(response.text))

    def collect(xpath: str) -> list[Any]:
        rows: list[Any] = []
        for html_tree in pages:
            rows.extend(html_tree.xpath(xpath))
        return rows

    rows = collect(primary_xpath)
    if len(rows) != pending:
        if logger:
            logger.debug(
                "%s count %d != expected %d, retrying with fallback XPath",
                label,
                len(rows),
                pending,
            )
        rows = collect(fallback_xpath)

    if logger:
        logger.info("当前共有 %d 个%s任务。", pending, label)
    return rows


def _extract_pid(href: str) -> str:
    """从商品链接中提取纯数字商品 ID。"""
    href = href.strip()
    if "javascript" in href:
        return href

    path = urlsplit(href).path
    name = path.rsplit("/", 1)[-1]
    return name[:-5] if name.endswith(".html") else name


def _parse_review_ids(href: str) -> tuple[str, str]:
    """从追评链接中解析商品 ID 与订单 ID。"""
    params = parse_qs(urlsplit(href).query)
    pid = params.get("sku", [""])[0].strip()
    oid = params.get("orderId", [""])[0].strip()
    if not pid or not oid:
        raise ValueError(f"无法从链接解析商品/订单 ID: {href}")
    return pid, oid


def _upload_comment_images(
    pid: str,
    headers: dict[str, Any],
    logger: Any = None,
) -> str:
    """下载并重新上传商品晒图，返回京东图片 URL（最多两张）。"""
    params = {"productId": pid, "isShadowSku": "0", "page": "1", "pageSize": "10"}
    url = f"{IMAGE_LIST_URL}?{urlencode(params)}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        imgdata = response.json()
    except (requests.RequestException, ValueError) as exc:
        if logger:
            logger.warning("获取晒图数据失败: %s", exc)
        return ""

    if not isinstance(imgdata, dict):
        if logger:
            logger.warning("晒图接口返回了非预期格式")
        return ""

    img_list = (imgdata.get("imgComments") or {}).get("imgList") or []
    if not img_list:
        if logger:
            logger.warning("这单没有图片数据，将不晒图")
        return ""

    session = requests.Session()
    uploaded: list[str] = []
    for index, item in enumerate(img_list[:2], start=1):
        source_url = item.get("imageUrl", "") if isinstance(item, dict) else ""
        if not source_url:
            continue

        if logger:
            logger.info("imgurl%d url: %s", index, source_url)

        filename = generate_unique_filename()
        local_path = download_image(source_url, filename, logger=logger)
        if not local_path:
            continue

        upload_response = upload_image(
            filename,
            local_path,
            session,
            headers,
            logger=logger,
        )
        if (
            upload_response is not None
            and upload_response.status_code == 200
            and ".jpg" in upload_response.text
        ):
            uploaded.append(f"{UPLOADED_IMAGE_BASE}{upload_response.text}")
        elif logger:
            logger.info("上传图片%d失败", index)

    return ",".join(uploaded)


def ordinary(
    N: dict[str, int],
    headers: dict[str, Any],
    headers2: dict[str, Any],
    opts: dict[str, Any] | None = None,
) -> dict[str, int]:
    """处理普通评价（含晒图）。

    Args:
        N: 评价数量统计字典。
        headers: GET 请求头（含 Cookie）。
        headers2: POST 请求头（含 Cookie 及完整 UA）。
        opts: 配置选项，需包含 ``"logger"`` 和 ``"dry_run"`` 键。

    Returns:
        更新后的评价数量统计字典。
    """
    time.sleep(3)
    opts = opts or {}
    logger = opts.get("logger")

    pending = N.get("待评价订单", 0)
    Order_data = _fetch_order_rows(
        sort=0,
        pending=pending,
        headers=headers,
        opts=opts,
        primary_xpath='//*[@id="main"]/div[2]/div[2]/table/tbody',
        fallback_xpath='//*[@id="main"]/div[2]/div[2]/table',
        label="评价",
    )

    if logger:
        logger.debug("Commenting on items")

    # 处理每个订单
    for i, Order in enumerate(Order_data):
        try:
            oid = Order.xpath('tr[@class="tr-th"]/td/span[3]/a/text()')[0]
            oname_data = Order.xpath('tr[@class="tr-bd"]/td[1]/div[1]/div[2]/div/a/text()')
            pid_data = Order.xpath('tr[@class="tr-bd"]/td[1]/div[1]/div[2]/div/a/@href')

            if logger:
                logger.debug("oid: %s", oid)
                logger.debug("oname_data: %s", oname_data)
                logger.debug("pid_data: %s", pid_data)
        except IndexError:
            if logger:
                logger.warning(f"第{i + 1}个订单未查找到商品，跳过。")
            continue

        loop_times1 = min(len(oname_data), len(pid_data))
        if logger:
            logger.debug("Commenting on orders")
            logger.debug("Total loop times: %d", loop_times1)

        for idx, (oname, pid) in enumerate(zip(oname_data, pid_data)):
            if logger:
                logger.debug("Loop: %d / %d", idx + 1, loop_times1)

            pid = _extract_pid(pid)
            if logger:
                logger.debug("pid: %s", pid)

            if "javascript" in pid:
                if logger:
                    logger.error(
                        "pid_data: %s,这个订单估计是京东外卖的，会导致此次评价失败，请把该 %s 商品手工评价后再运行程序。",
                        pid, oname
                    )
                continue

            if logger:
                logger.info(f"\t{i}.开始评价订单\t{oname}[{oid}]并晒图")

            # 生成评价内容
            xing, Str = generation(oname, opts=opts)
            if logger:
                logger.info(f"\t\t评价内容,星级{xing}：" + Str)

            # 获取并上传晒图
            if logger:
                logger.info("\t\t开始获取图片")
            imgurl = _upload_comment_images(pid, headers, logger)
            if logger:
                logger.info("\t\t图片url=%s", imgurl)

            # 准备评价数据
            Str_encoded = quote(Str, safe="/")
            Comment_data: dict[str, Any] = {
                "orderId": oid,
                "productId": pid,
                "score": str(xing),
                "content": Str_encoded,
                "saveStatus": "1",
                "anonymousFlag": "1",
            }

            if imgurl:
                Comment_data["imgs"] = imgurl

            if logger:
                logger.debug("Data: %s", Comment_data)

            # 发送评价请求
            if not opts.get("dry_run"):
                if logger:
                    logger.debug("Sending comment request")

                try:
                    Comment_resp = requests.post(
                        SAVE_COMMENT_URL,
                        headers=headers2,
                        data=Comment_data,
                        timeout=30,
                    )
                    if logger:
                        logger.info(
                            "发送请求后的状态码:%d,text:%s",
                            Comment_resp.status_code,
                            Comment_resp.text,
                        )

                    if Comment_resp.status_code == 200 and Comment_resp.json().get("success"):
                        if logger:
                            logger.info(f"\t{i}.评价订单\t{oname}[{oid}]评论成功")
                    else:
                        if logger:
                            logger.warning(f"\t{i}.评价订单\t{oname}[{oid}]评论失败")
                except requests.RequestException as e:
                    if logger:
                        logger.error(f"Failed to submit comment: {e}")
                except (ValueError, KeyError) as e:
                    if logger:
                        logger.error(f"Failed to parse response: {e}")
            else:
                if logger:
                    logger.debug("Skipped sending comment request in dry run")

            if logger:
                logger.debug("Sleep time (s): %.1f", ORDINARY_SLEEP_SEC)
            time.sleep(ORDINARY_SLEEP_SEC)

    if Order_data:
        N["待评价订单"] = max(0, N.get("待评价订单", 0) - 1)
    return N


def review(
    N: dict[str, int],
    headers: dict[str, Any],
    headers2: dict[str, Any],
    opts: dict[str, Any] | None = None,
) -> dict[str, int]:
    """处理追评。

    Args:
        N: 评价数量统计字典。
        headers: GET 请求头（含 Cookie）。
        headers2: POST 请求头（含 Cookie 及完整 UA）。
        opts: 配置选项，需包含 ``"logger"`` 和 ``"dry_run"`` 键。

    Returns:
        更新后的评价数量统计字典。
    """
    opts = opts or {}
    logger = opts.get("logger")

    pending = N.get("待追评", 0)
    Order_data = _fetch_order_rows(
        sort=3,
        pending=pending,
        headers=headers,
        opts=opts,
        primary_xpath='//*[@id="main"]/div[2]/div[2]/table/tr[@class="tr-bd"]',
        fallback_xpath='//*[@id="main"]/div[2]/div[2]/table/tbody/tr[@class="tr-bd"]',
        label="追评",
    )

    if logger:
        logger.debug("Commenting on items")

    # 处理每个订单
    for i, Order in enumerate(Order_data):
        try:
            oname = Order.xpath("td[1]/div/div[2]/div/a/text()")[0]
            _id = Order.xpath("td[3]/div/a/@href")[0]
        except IndexError as e:
            if logger:
                logger.warning(f"Failed to extract order info for item {i+1}: {e}")
            continue

        if logger:
            logger.info(f"\t开始追评第{i+1}，{oname}")
            logger.debug("_id: %s", _id)

        if logger:
            logger.debug("URL: %s", SAVE_REVIEW_URL)

        try:
            pid, oid = _parse_review_ids(_id)
        except ValueError as e:
            if logger:
                logger.error(f"Failed to parse product ID and order ID: {e}")
            continue

        if logger:
            logger.debug("pid: %s", pid)
            logger.debug("oid: %s", oid)

        if "javascript" in pid:
            if logger:
                logger.error(
                    "pid_data: %s,这个订单估计是京东外卖的，会导致此次评价失败，请把该 %s 商品手工评价后再运行程序。",
                    pid, oname
                )
            continue

        # 生成追评内容
        _, context = generation(oname, _type=0, opts=opts)
        if logger:
            logger.info(f"\t\t追评内容：{context}")

        context_encoded = quote(context, safe="/")
        data1: dict[str, Any] = {
            "orderId": oid,
            "productId": pid,
            "content": context_encoded,
            "anonymousFlag": 1,
            "score": 5,
            "imgs": "",
        }

        if logger:
            logger.debug("Data: %s", data1)

        # 发送追评请求
        if not opts.get("dry_run"):
            if logger:
                logger.debug("Sending comment request")

            try:
                pj1 = requests.post(
                    SAVE_REVIEW_URL,
                    headers=headers2,
                    data=data1,
                    timeout=30,
                )
                if logger:
                    logger.debug(
                        "发送请求后的状态码:%d,text:%s",
                        pj1.status_code,
                        pj1.text,
                    )
            except requests.RequestException as e:
                if logger:
                    logger.error(f"Failed to submit review: {e}")
        else:
            if logger:
                logger.debug("Skipped sending comment request in dry run")

        if logger:
            logger.info("完成")
            logger.debug("Sleep time (s): %.1f", REVIEW_SLEEP_SEC)

        time.sleep(REVIEW_SLEEP_SEC)
        N["待追评"] = max(0, N.get("待追评", 0) - 1)

    return N


def service_rating(
    N: dict[str, int],
    headers: dict[str, Any],
    opts: dict[str, Any] | None = None,
) -> dict[str, int]:
    """处理服务评价（原 Service_rating 函数）。

    Args:
        N: 评价数量统计字典。
        headers: HTTP 请求头（含 Cookie）。
        opts: 配置选项，需包含 ``"logger"`` 和 ``"dry_run"`` 键。

    Returns:
        更新后的评价数量统计字典。
    """
    opts = opts or {}
    logger = opts.get("logger")

    pending = N.get("服务评价", 0)
    Order_data = _fetch_order_rows(
        sort=4,
        pending=pending,
        headers=headers,
        opts=opts,
        primary_xpath='//*[@id="main"]/div[2]/div[2]/table/tbody/tr[@class="tr-bd"]',
        fallback_xpath='//*[@id="main"]/div[2]/div[2]/table/tr[@class="tr-bd"]',
        label="服务评价",
    )

    if logger:
        logger.debug("Commenting on items")

    # 处理每个订单
    for i, Order in enumerate(Order_data):
        try:
            oname = Order.xpath("td[1]/div[1]/div[2]/div/a/text()")[0]
            oid = Order.xpath("td[4]/div/a[1]/@oid")[0]
        except IndexError as e:
            if logger:
                logger.warning(f"Failed to extract order info for item {i+1}: {e}")
            continue

        if logger:
            logger.info(f"\t开始第一次评论，{i+1}，{oname}")
            logger.debug("oid: %s", oid)

        url1 = f"{SURVEY_URL}?voteid=145&ruleid={oid}"
        if logger:
            logger.debug("URL: %s", url1)

        data1: dict[str, Any] = {
            "oid": oid,
            "gid": "32",
            "sid": "186194",
            "stid": "0",
            "tags": "",
            "ro591": f"591A{random.randint(4, 5)}",  # 商品符合度
            "ro592": f"592A{random.randint(4, 5)}",  # 店家服务态度
            "ro593": f"593A{random.randint(4, 5)}",  # 快递配送速度
            "ro899": f"899A{random.randint(4, 5)}",  # 快递员服务
            "ro900": f"900A{random.randint(4, 5)}",  # 快递员服务
        }

        if logger:
            logger.debug("Data: %s", data1)

        # 发送服务评价请求
        if not opts.get("dry_run"):
            if logger:
                logger.debug("Sending comment request")

            try:
                pj1 = requests.post(url1, headers=headers, data=data1, timeout=30)
                if logger:
                    logger.info("\t\t %s", pj1.text)
            except requests.RequestException as e:
                if logger:
                    logger.error(f"Failed to submit service rating: {e}")
        else:
            if logger:
                logger.debug("Skipped sending comment request in dry run")

        if logger:
            logger.debug("Sleep time (s): %.1f", SERVICE_RATING_SLEEP_SEC)

        time.sleep(SERVICE_RATING_SLEEP_SEC)
        N["服务评价"] = max(0, N.get("服务评价", 0) - 1)

    return N
