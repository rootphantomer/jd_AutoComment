# -*- coding: utf-8 -*-
"""评价处理器模块。

包含普通评价、追评和服务评价三个核心业务处理函数。
所有网络请求所需的 headers 均通过函数参数显式传入。
"""

from __future__ import annotations

import random
import time
import urllib.parse
from typing import Any

import requests
from lxml import etree

from comment_generator import generation
from config import ORDINARY_SLEEP_SEC, REVIEW_SLEEP_SEC, SERVICE_RATING_SLEEP_SEC
from image_utils import generate_unique_filename, download_image, upload_image


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

    Order_data: list[Any] = []
    req_et_list: list[Any] = []
    imgCommentCount_bool = True
    loop_times = N.get("待评价订单", 0) // 20

    if logger:
        logger.debug("Fetching website data")
        logger.debug("Total loop times: %d", loop_times)

    # 获取所有订单页面
    for i in range(loop_times + 1):
        url = f"https://club.jd.com/myJdcomments/myJdcomment.action?sort=0&page={i + 1}"
        if logger:
            logger.debug("URL: %s", url)

        try:
            req = requests.get(url, headers=headers, timeout=30)
            req.raise_for_status()
            if logger:
                logger.debug("Successfully accepted the response with status code %d", req.status_code)
        except requests.RequestException as e:
            if logger:
                logger.warning("Failed to fetch page %d: %s", i + 1, e)
            continue

        req_et_list.append(etree.HTML(req.text))
        if logger:
            logger.debug("Successfully parsed an XML tree")

    # 提取订单数据
    if logger:
        logger.debug("Fetching data from XML trees")
        logger.debug("Total loop times: %d", len(req_et_list))

    for idx, html_tree in enumerate(req_et_list):
        if logger:
            logger.debug("Loop: %d / %d", idx + 1, len(req_et_list))
            logger.debug("Fetching order data in the default XPath")

        elems = html_tree.xpath('//*[@id="main"]/div[2]/div[2]/table/tbody')
        if logger:
            logger.debug("Count of fetched order data: %d", len(elems))
        Order_data.extend(elems)

    # 如果第一次提取失败，尝试备用XPath
    if len(Order_data) != N.get("待评价订单", 0):
        if logger:
            logger.debug('Count of fetched order data doesn\'t equal N["待评价订单"]')
            logger.debug("Clear the list Order_data")
        Order_data = []

        if logger:
            logger.debug("Total loop times: %d", len(req_et_list))

        for idx, html_tree in enumerate(req_et_list):
            if logger:
                logger.debug("Loop: %d / %d", idx + 1, len(req_et_list))
                logger.debug("Fetching order data in another XPath")

            elems = html_tree.xpath('//*[@id="main"]/div[2]/div[2]/table')
            if logger:
                logger.debug("Count of fetched order data: %d", len(elems))
            Order_data.extend(elems)

    if logger:
        logger.info(f"当前共有{N.get('待评价订单', 0)}个评价。")
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

            pid = pid.replace("//item.jd.com/", "").replace(".html", "")
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

            # 获取图片
            if logger:
                logger.info(f"\t\t开始获取图片")

            img_url = f"https://club.jd.com/discussion/getProductPageImageCommentList.action?productId={pid}"
            if logger:
                logger.debug("URL: %s", img_url)

            try:
                img_resp = requests.get(img_url, headers=headers, timeout=30)
                img_resp.raise_for_status()
                if logger:
                    logger.debug("Successfully accepted the response with status code %d", img_resp.status_code)
            except requests.RequestException as e:
                if logger:
                    logger.warning("Failed to fetch images: %s", e)
                imgCommentCount_bool = False
                imgurl = ""
            else:
                if logger:
                    logger.info("imgdata_url:" + img_url)

                imgdata = img_resp.json()
                if logger:
                    logger.debug("Image data: %s", imgdata)

                if imgdata["imgComments"]["imgCommentCount"] == 0:
                    if logger:
                        logger.warning("这单没有图片数据，所以直接默认五星好评！！")
                    imgCommentCount_bool = False
                    imgurl = ""
                elif imgdata["imgComments"]["imgCommentCount"] > 0:
                    imgList = imgdata["imgComments"]["imgList"]
                    # 初始化上传后的URL变量（Bug 3修复）
                    imgurl1t = ""
                    imgurl2t = ""

                    # 根据实际图片数量安全获取源URL（Bug 2修复）
                    imgurl1 = imgList[0]["imageUrl"] if len(imgList) >= 1 else ""
                    imgurl2 = imgList[1]["imageUrl"] if len(imgList) >= 2 else ""

                    if logger:
                        logger.info("imgurl1 url: %s", imgurl1)
                        logger.info("imgurl2 url: %s", imgurl2)

                    session = requests.Session()
                    imgBasic = "//img20.360buyimg.com/shaidan/s645x515_"

                    # 下载并上传第一张图片
                    if imgurl1:
                        imgName1 = generate_unique_filename()
                        if logger:
                            logger.debug(f"Image :{imgName1}")

                        downloaded_file1 = download_image(imgurl1, imgName1)
                        if downloaded_file1:
                            imgPart1 = upload_image(imgName1, downloaded_file1, session, headers)
                            if imgPart1 and imgPart1.status_code == 200 and ".jpg" in imgPart1.text:
                                imgurl1t = f"{imgBasic}{imgPart1.text}"
                            else:
                                if logger:
                                    logger.info("上传图片1失败")

                    # 下载并上传第二张图片
                    if imgurl2:
                        imgName2 = generate_unique_filename()
                        if logger:
                            logger.debug(f"Image :{imgName2}")

                        downloaded_file2 = download_image(imgurl2, imgName2)
                        if downloaded_file2:
                            imgPart2 = upload_image(imgName2, downloaded_file2, session, headers)
                            if imgPart2 and imgPart2.status_code == 200 and ".jpg" in imgPart2.text:
                                imgurl2t = f"{imgBasic}{imgPart2.text}"
                            else:
                                if logger:
                                    logger.info("上传图片2失败")

                    # 使用上传后的URL拼接imgurl，排除上传失败的图片（Bug 1修复）
                    uploaded_urls = [u for u in [imgurl1t, imgurl2t] if u]
                    imgurl = ",".join(uploaded_urls)
                    if logger:
                        logger.debug("Image URL: %s", imgurl)
                        logger.info(f"\t\t图片url={imgurl}")
                else:
                    imgurl = ""

            # 准备评价数据
            Str_encoded = urllib.parse.quote(Str, safe="/", encoding=None, errors=None)
            Comment_data: dict[str, Any] = {
                "orderId": oid,
                "productId": pid,
                "score": str(xing),
                "content": Str_encoded,
                "saveStatus": "1",
                "anonymousFlag": "1",
            }

            if imgCommentCount_bool and imgurl:
                Comment_data["imgs"] = imgurl

            if logger:
                logger.debug("Data: %s", Comment_data)

            # 发送评价请求
            if not opts.get("dry_run"):
                if logger:
                    logger.debug("Sending comment request")

                try:
                    Comment_resp = requests.post(
                        "https://club.jd.com/myJdcomments/saveProductComment.action",
                        headers=headers2,
                        data=Comment_data,
                        timeout=30
                    )
                    if logger:
                        logger.info(
                            "发送请求后的状态码:{},text:{}".format(
                                Comment_resp.status_code, Comment_resp.text
                            )
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

    req_et_list: list[Any] = []
    Order_data: list[Any] = []
    loop_times = N.get("待追评", 0) // 20

    if logger:
        logger.debug("Fetching website data")
        logger.debug("Total loop times: %d", loop_times)

    # 获取所有页面
    for i in range(loop_times + 1):
        if logger:
            logger.debug("Loop: %d / %d", i + 1, loop_times)

        url = f"https://club.jd.com/myJdcomments/myJdcomment.action?sort=3&page={i + 1}"
        if logger:
            logger.debug("URL: %s", url)

        try:
            req = requests.get(url, headers=headers, timeout=30)
            req.raise_for_status()
            if logger:
                logger.debug("Successfully accepted the response with status code %d", req.status_code)
        except requests.RequestException as e:
            if logger:
                logger.warning("Failed to fetch page %d: %s", i + 1, e)
            continue

        req_et_list.append(etree.HTML(req.text))
        if logger:
            logger.debug("Successfully parsed an XML tree")

    # 提取订单数据
    if logger:
        logger.debug("Fetching data from XML trees")
        logger.debug("Total loop times: %d", len(req_et_list))

    for idx, html_tree in enumerate(req_et_list):
        if logger:
            logger.debug("Loop: %d / %d", idx + 1, len(req_et_list))
            logger.debug("Fetching order data in the default XPath")

        elems = html_tree.xpath('//*[@id="main"]/div[2]/div[2]/table/tr[@class="tr-bd"]')
        if logger:
            logger.debug("Count of fetched order data: %d", len(elems))
        Order_data.extend(elems)

    # 如果第一次提取失败，尝试备用XPath
    if len(Order_data) != N.get("待追评", 0):
        if logger:
            logger.debug('Count of fetched order data doesn\'t equal N["待追评"]')

        if logger:
            logger.debug("Total loop times: %d", len(req_et_list))

        for idx, html_tree in enumerate(req_et_list):
            if logger:
                logger.debug("Loop: %d / %d", idx + 1, len(req_et_list))
                logger.debug("Fetching order data in another XPath")

            elems = html_tree.xpath('//*[@id="main"]/div[2]/div[2]/table/tbody/tr[@class="tr-bd"]')
            if logger:
                logger.debug("Count of fetched order data: %d", len(elems))
            Order_data.extend(elems)

    if logger:
        logger.info(f"当前共有 {N.get('待追评', 0)} 个需要追评。")
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

        url1 = "https://club.jd.com/afterComments/saveAfterCommentAndShowOrder.action"
        if logger:
            logger.debug("URL: %s", url1)

        try:
            pid, oid = _id.replace(
                "http://club.jd.com/afterComments/productPublish.action?sku=", ""
            ).split("&orderId=")
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

        context_encoded = urllib.parse.quote(context, safe="/", encoding=None, errors=None)
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
                pj1 = requests.post(url1, headers=headers2, data=data1, timeout=30)
                if logger:
                    logger.debug("发送请求后的状态码:{},text:{}".format(pj1.status_code, pj1.text))
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

    Order_data: list[Any] = []
    req_et_list: list[Any] = []
    loop_times = N.get("服务评价", 0) // 20

    if logger:
        logger.debug("Fetching website data")
        logger.debug("Total loop times: %d", loop_times)

    # 获取所有页面
    for i in range(loop_times + 1):
        if logger:
            logger.debug("Loop: %d / %d", i + 1, loop_times)

        url = f"https://club.jd.com/myJdcomments/myJdcomment.action?sort=4&page={i + 1}"
        if logger:
            logger.debug("URL: %s", url)

        try:
            req = requests.get(url, headers=headers, timeout=30)
            req.raise_for_status()
            if logger:
                logger.debug("Successfully accepted the response with status code %d", req.status_code)
        except requests.RequestException as e:
            if logger:
                logger.warning("Failed to fetch page %d: %s", i + 1, e)
            continue

        req_et_list.append(etree.HTML(req.text))
        if logger:
            logger.debug("Successfully parsed an XML tree")

    # 提取订单数据
    if logger:
        logger.debug("Fetching data from XML trees")
        logger.debug("Total loop times: %d", len(req_et_list))

    for idx, html_tree in enumerate(req_et_list):
        if logger:
            logger.debug("Loop: %d / %d", idx + 1, len(req_et_list))
            logger.debug("Fetching order data in the default XPath")

        elems = html_tree.xpath('//*[@id="main"]/div[2]/div[2]/table/tbody/tr[@class="tr-bd"]')
        if logger:
            logger.debug("Count of fetched order data: %d", len(elems))
        Order_data.extend(elems)

    # 如果第一次提取失败，尝试备用XPath
    if len(Order_data) != N.get("服务评价", 0):
        if logger:
            logger.debug('Count of fetched order data doesn\'t equal N["服务评价"]')
            logger.debug("Clear the list Order_data")
        Order_data = []

        if logger:
            logger.debug("Total loop times: %d", len(req_et_list))

        for idx, html_tree in enumerate(req_et_list):
            if logger:
                logger.debug("Loop: %d / %d", idx + 1, len(req_et_list))
                logger.debug("Fetching order data in another XPath")

            elems = html_tree.xpath('//*[@id="main"]/div[2]/div[2]/table/tr[@class="tr-bd"]')
            if logger:
                logger.debug("Count of fetched order data: %d", len(elems))
            Order_data.extend(elems)

    if logger:
        logger.info(f"当前共有{N.get('服务评价', 0)}个需要第一次服务评价。")
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

        url1 = f"https://club.jd.com/myJdcomments/insertRestSurvey.action?voteid=145&ruleid={oid}"
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
                    logger.info("\t\t " + pj1.text)
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
