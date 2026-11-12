# jd_AutoComment

> 京东自动评价工具：爬取同类商品的真实评论语料，生成更贴合商品的评价内容，并按流程完成普通评价、追评和服务评价。

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [工作原理](#工作原理)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [安装](#安装)
- [配置](#配置)
- [使用](#使用)
- [命令行参数](#命令行参数)
- [日志](#日志)
- [常见问题](#常见问题)
- [分支说明](#分支说明)
- [免责声明](#免责声明)
- [鸣谢](#鸣谢)
- [许可证](#许可证)

## 项目简介

京东自动评价工具会先读取账号下待处理的评价任务，再根据商品名称爬取同类商品的已有评论，从中提取可用语料生成评价内容，最后依次提交普通评价、追评和服务评价。

项目最初用于解决“评价内容与商品不匹配”的问题。评价语料来自商品评论，但生成结果仍具有随机性，请在使用前通过 `--dry-run` 检查完整流程。

## 功能特性

| 功能 | 说明 |
| --- | --- |
| 普通评价 | 自动处理待评价订单，支持下载并上传商品晒图 |
| 追评 | 对已评价订单自动追评，追评不会上传图片 |
| 服务评价 | 自动提交服务评分，评分随机为 4–5 分 |
| 评论语料生成 | 根据商品名称爬取同类商品评论，结合关键词和模板生成内容 |
| 本地缓存 | 同一商品的评论语料和关键词只加载一次，减少重复请求 |
| 自动重试 | 仍有未完成评价时自动重试，最多 3 次 |
| dry-run | 完整执行流程但不提交评价，适合首次验证 |
| 分级日志 | 支持控制台彩色日志、文件日志和自定义日志级别 |

## 工作原理

1. 读取 `config.yml` 或 `config.user.yml` 中的 Cookie，并构建请求头。
2. 查询账号中待评价、待追评和服务评价的数量。
3. 对每个商品爬取同类商品评论，拆分句子并提取商品关键词。
4. 从语料中随机抽取句子，替换 `$` 占位符后生成评价内容。
5. 提交评价；普通评价会尝试下载并重新上传最多两张晒图。
6. 每类任务完成后刷新统计，若仍有未完成项则进入重试流程。

执行顺序固定为：

```text
普通评价 → 追评 → 服务评价 → （必要时）重试
```

## 项目结构

```text
jd_AutoComment/
├── auto_comment_plus.py   # CLI 入口、参数解析和主流程编排
├── config.py              # 常量、配置读取和请求头构建
├── logger.py              # 日志初始化与 ANSI 样式格式化
├── templates.py           # 默认评价与赠品评价模板
├── image_utils.py         # 图片下载、上传和清理
├── comment_generator.py   # 评论语料加载、关键词提取和评价生成
├── evaluator.py           # 评价数量查询与统计
├── handlers.py            # 普通评价、追评和服务评价处理器
├── jdspider.py            # 京东商品评论爬虫
├── config.yml.example     # 配置示例
├── config.yml             # 默认配置文件
├── config.user.yml        # 用户配置文件（优先读取，建议本地使用）
├── requirements.txt       # pip 依赖
├── pyproject.toml         # 项目元数据与依赖
├── uv.lock                # uv 锁文件
└── LICENSE                # MIT 许可证
```

### 模块依赖

```text
config ─────────────── (无项目内依赖)
logger ─────────────── (无项目内依赖)
templates ──────────── (无项目内依赖)
image_utils ────────── (无项目内依赖)
evaluator ──────────── (无项目内依赖)
jdspider ─────────────→ templates
comment_generator ────→ jdspider, templates
handlers ─────────────→ comment_generator, config, image_utils
auto_comment_plus ────→ config, evaluator, handlers, logger, jdspider
```

## 环境要求

- Python 3.9 或更高版本
- 可访问京东网站的网络环境
- 一个已完成登录的京东账号 Cookie

推荐使用 Python 3.10 及以上版本。

## 安装

```bash
git clone https://github.com/rootphantomer/jd_AutoComment.git
cd jd_AutoComment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

Windows 激活虚拟环境：

```powershell
.venv\Scripts\activate
```

也可以使用 `uv`：

```bash
uv sync
uv run python auto_comment_plus.py
```

## 配置

### 1. 获取 Cookie

1. 在浏览器中登录京东账号。
2. 打开 <https://club.jd.com/myJdcomments/myJdcomment.action>。
3. 打开开发者工具，进入 **Network / 网络** 面板。
4. 刷新页面，选择任意 XHR 请求。
5. 在请求头中找到 `Cookie`，复制完整内容。

### 2. 写入配置文件

可以复制配置示例：

```bash
cp config.yml.example config.user.yml
```

然后编辑 `config.user.yml`，把示例值替换为浏览器中复制的完整 Cookie：

```yaml
user:
  cookie: YOUR_JD_COOKIE_HERE
```

配置文件读取优先级：

```text
config.user.yml > config.yml
```

建议把真实 Cookie 放在 `config.user.yml`，避免后续更新覆盖 `config.yml` 中的内容。

> **安全提示：** Cookie 等同于账号登录凭证，请勿提交到 Git、Issue、日志或公开聊天中。

## 使用

首次运行建议先使用 dry-run：

```bash
python auto_comment_plus.py --dry-run
```

dry-run 会完整执行查询、爬取、内容生成和图片处理流程，但不会提交评价。

确认流程正常后正式运行：

```bash
python auto_comment_plus.py
```

只输出到控制台：

```bash
python auto_comment_plus.py --no-log-file
```

指定日志文件：

```bash
python auto_comment_plus.py -o log/my-run.log
```

请根据系统环境使用 `python`、`python3` 或 `py`。

## 命令行参数

```text
usage: auto_comment_plus.py [-h] [--dry-run] [-lv LOG_LEVEL] [-o LOG_FILE]
                            [--no-log-file]

options:
  -h, --help            show this help message and exit
  --dry-run             完整运行但不提交评价（测试模式）
  -lv, --log-level      指定日志级别（默认：DEBUG）
                        可选：DEBUG, INFO, WARN, ERROR, FATAL
  -o, --log-file        指定日志文件路径（默认：log/日期.txt）
  --no-log-file         不写入日志文件，仅输出到控制台
```

| 参数 | 说明 |
| --- | --- |
| `-h`, `--help` | 显示帮助信息 |
| `--dry-run` | 执行完整流程，但不提交评价 |
| `-lv`, `--log-level` | 设置日志级别，默认 `DEBUG` |
| `-o`, `--log-file` | 指定日志文件路径 |
| `--no-log-file` | 禁用文件日志 |

提交 Issue 反馈问题时，建议使用 `DEBUG` 级别并附上脱敏后的日志。

## 日志

默认同时输出到控制台和文件：

```text
log/YYYY-MM-DD.txt
```

日志级别从详细到精简依次为：

```text
DEBUG → INFO → WARN → ERROR → FATAL
```

使用 `--no-log-file` 可以禁用文件日志；使用 `-o` 可以自定义日志路径。

## 常见问题

### Cookie 失效

现象：程序提示 Cookie 错误，或评价统计为空。

处理：重新登录京东，按[配置](#配置)步骤复制最新的完整 Cookie。

### 京东外卖或虚拟商品无法自动评价

这类商品的评价链接可能包含 `javascript`，程序会跳过并输出错误日志。请在京东页面中手动评价。

### 晒图上传失败

图片下载或上传失败时，程序会继续提交不带图片的评价。可以查看 `DEBUG` 日志定位网络或接口问题。

### 请求过于频繁

程序在评价提交和评论爬取之间内置了等待时间。请勿随意删除这些等待逻辑，否则可能触发京东风控。

### 接口或页面结构变化

京东页面和接口可能随时调整。如果订单解析或评价提交失败，请附上脱敏后的 `DEBUG` 日志提交 Issue。

## 分支说明

| 分支 | 说明 |
| --- | --- |
| `main` | 开发版，更新较快，功能较新，但测试可能不完整 |
| `stable` | 稳定版，更新较慢，适合日常使用 |
| `more_cookie` | 多账号批量评价分支，需要多账号环境测试 |

多账号分支会按账号依次执行普通评价、追评和服务评价。账号较多时，后面账号的 Cookie 可能在执行前失效。

## 免责声明

本项目为 Python 学习与技术交流用途的开源非营利项目，仅用于学习自动化请求、网页解析和数据处理。

严禁将本项目用于商业用途或任何盈利活动。使用者应遵守京东用户协议、相关法律法规及平台规则。因使用本项目产生的一切后果由使用者自行承担，项目作者不承担任何责任。

如果本项目对您造成困扰，请联系删除。

## 鸣谢

- [qiu-lzsnmb](https://github.com/qiu-lzsnmb)：原始自动评价脚本
- [Zhang Jiale](https://github.com/2274900)：评论爬虫实现
- [Dimlitter/jd_AutoComment](https://github.com/Dimlitter/jd_AutoComment)：项目上游仓库

相关项目：

- [qiu-lzsnmb/jd_lzsnmb](https://github.com/qiu-lzsnmb/jd_lzsnmb)
- [2274900/JD_comment_spider](https://github.com/2274900/JD_comment_spider)

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
