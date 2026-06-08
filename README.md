# jd_AutoComment

## 鸣谢

感谢[qiu-lzsnmb](https://github.com/qiu-lzsnmb)大佬的脚本和[Zhang Jiale](https://github.com/2274900)大佬的评论爬虫

源库链接：[自动评价](https://github.com/qiu-lzsnmb/jd_lzsnmb)
[评论爬虫](https://github.com/2274900/JD_comment_spider)

### 本脚本只是对以上两位的结合以及魔改，用于解决评论文不对题的问题。经测试，本脚本能初步解决这一问题

## 思路

由爬虫先行对商品的既有评价进行爬取，在此基础上进行自己的评价

## 项目结构

```
jd_AutoComment/
├── auto_comment_plus.py   # CLI 入口 & 主流程编排
├── config.py              # 常量定义 + 配置文件读取 + Headers 构建
├── logger.py              # 日志初始化 & ANSI 样式格式化
├── templates.py           # 评论文本模板（DEFAULT_COMMENTS / GIFT_COMMENTS）
├── image_utils.py         # 图片下载 / 上传 / 清理
├── comment_generator.py   # 评论生成（generation）
├── evaluator.py           # 评价统计（get_evaluation_stats / all_evaluate）
├── handlers.py            # 三大评价处理器（ordinary / review / service_rating）
├── jdspider.py            # 京东商品评论爬虫
├── config.yml             # 默认配置文件
└── requirements.txt       # Python 依赖
```

### 模块依赖关系

```
config ────── (无项目内依赖)
logger ────── (无项目内依赖)
templates ─── (无项目内依赖)
image_utils ─ (无项目内依赖)
jdspider ────→ templates
comment_generator → jdspider, templates
evaluator ─── (无项目内依赖)
handlers ────→ comment_generator, config, image_utils
auto_comment_plus → config, evaluator, handlers, logger, jdspider
```

## 用法

> 请先确保python版本为3.9+，最好是python3.10+。

### 分支说明

main分支为开发版，更新较快，但由于开发者cookie数量远远不足以满足开发需求，测试不够完备，可能存在bug。

stable分支为稳定版，更新较慢，基本可以稳定使用，但功能可能存在欠缺。

more_cookie分支是有需要多账号进行批量评论诞生的分支。
> 由于作者只有一个 jd 账号，因此该more_cookie分支，需要有多账号的朋友进行测试。
目前代码逻辑是 先普通评价-》再追评-》再第二个账号继续执行前面的顺序。所以你多账号可能要历史追评结束后才会执行，cookie 可能会失效，如果很多个 jd 账号话。可能实际上效果没那么好。

### 快速使用

在终端中执行：

```bash
git clone https://github.com/Dimlitter/jd_AutoComment.git
cd jd_AutoComment
pip install -r requirements.txt
```

`https://club.jd.com/myJdcomments/myJdcomment.action`打开该链接，登录账号后获取 xhr 请求下的 `cookie`，`全部`填入配置文件。可以选择填入默认配置文件 `config.yml` ；也可以填入用户配置文件 `config.user.yml` （需要新建后将 `config.yml` 中的内容复制到该文件中），避免后续的更新覆盖 `config.yml` 中的内容。

需要填入如下内容：

```yml
user:
  cookie: '<Cookie>'
```

例如，若获取得到的ck为 `a=1; b=2; c=3` ，则配置文件中填入：

```yml
user:
  cookie: 'a=1; b=2; c=3'
```

最后运行 `auto_comment_plus.py` ：

```bash
python3 auto_comment_plus.py
```

**注意:** 请根据设备环境换用不同的解释器路径，如 `python`、`py`。

### 命令行参数

本程序支持命令行参数：

```text
usage: auto_comment_plus.py [-h] [--dry-run] [-lv LOG_LEVEL] [-o LOG_FILE]

optional arguments:
  -h, --help            show this help message and exit
  --dry-run             完整运行但不提交评价（测试模式）
  -lv, --log-level      指定日志级别 (默认: DEBUG)
                        可选: DEBUG, INFO, WARN, ERROR, FATAL
  -o, --log-file        指定日志文件路径（默认使用日期命名）
```

**`-h`, `--help`:**

显示帮助文本。

**`--dry-run`:**

完整地运行程序，但不实际提交评论。适合首次使用时验证流程是否正常。

**`-lv`, `--log-level`:**

设置输出日志的等级。默认为 `DEBUG`。可选等级为 `DEBUG`、`INFO`、`WARN`、`ERROR`、`FATAL`，输出内容量依次递减。

**注意:** 若你需要提交 issue 来报告一个 bug ，请将该选项设置为 `DEBUG`。

**`-o`, `--log-file`:**

设置输出日志文件的路径。若无此选项，则不输出到文件。

### 功能说明

| 功能 | 说明 |
|------|------|
| 普通评价 | 自动评价待评价订单，支持晒图 |
| 追评 | 对已评价订单进行追评，不支持晒图 |
| 服务评价 | 自动进行服务评分（随机 4-5 分） |
| 重试机制 | 若存在未完成评价，自动重试（最多 3 次） |
| dry-run 模式 | 完整运行流程但不提交，用于测试验证 |

执行顺序：**普通评价 → 追评 → 服务评价**，若仍有未完成项则循环重试。

## 声明

本项目为Python学习交流的开源非营利项目，仅作为程序员之间相互学习交流之用。

严禁用于商业用途，禁止使用本项目进行任何盈利活动。

使用者请遵从相关政策。对一切非法使用所产生的后果，我们概不负责。

本项目对您如有困扰请联系我们删除。

## 证书

![AUR](https://img.shields.io/badge/license-MIT%20License%202.0-green.svg)
