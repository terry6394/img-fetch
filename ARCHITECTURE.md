# img-fetch 系统架构文档

## 概述

`img-fetch` 是一个 Claude Code Skill，用于根据 Excel 表格中的商品名称和规格，自动从多个来源抓取产品图片。

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户触发 /img-fetch                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. 读取输入文件 (Excel/CSV/JSON)                               │
│     - 提取: 商品名称、商品规格、商品编码、商品链接                │
│     - 识别字段: name_field, spec_field, url_field               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 品牌提取                                                    │
│     - 从商品名称第一段提取品牌                                   │
│     - 例: "STONE ISLAND Ribbed Soft Cotton" → "STONE_ISLAND"   │
│     - 特殊映射: CANADA→CANADA_GOOSE, HELLY→HELLY_HANSEN 等    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 图片抓取 (多源fallback策略)                                 │
│                                                                 │
│     优先级: 品牌官网 > 电商平台 > Youzan(最后手段)            │
│                                                                 │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ 3.1 品牌官网 (BrandFetcher)                           │  │
│     │     - 启动 Chrome 浏览器 (Selenium)                   │  │
│     │     - 访问品牌官网搜索产品                             │  │
│     │     - 支持: Canada Goose, HAGLOFS, Helly Hansen,     │  │
│     │              Stone Island, L.I.M                      │  │
│     │     - 人类行为模拟 (随机延迟、滚动、鼠标移动)          │  │
│     └──────────────────────────────────────────────────────┘  │
│                              │ 失败                             │
│                              ▼                                  │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ 3.2 电商平台 (EcommerceFetcher)                       │  │
│     │     - 亚马逊 (amazon.com)                            │  │
│     │     - 京东 (jd.com)                                   │  │
│     │     - 淘宝 (taobao.com)                               │  │
│     └──────────────────────────────────────────────────────┘  │
│                              │ 失败                             │
│                              ▼                                  │
│     ┌──────────────────────────────────────────────────────┐  │
│     │ 3.3 Youzan (有赞) - 最后手段                          │  │
│     │     - 从Excel中的商品链接直接获取                       │  │
│     │     - 注意: 通常只返回骨架占位图                       │  │
│     └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 图片验证                                                    │
│     - 文件大小 < 5KB → 拒绝 (骨架图)                          │
│     - 尺寸 < 200x200 → 拒绝 (缩略图)                         │
│     - 尺寸 > 10000x10000 → 拒绝 (无效)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. 保存图片 & 生成报告                                          │
│                                                                 │
│     输出目录:                                                    │
│     output/                                                     │
│     ├── images/                                                 │
│     │   └── {BRAND}/                                           │
│     │       └── {BRAND}_{NAME}_{SPEC}.jpg                      │
│     ├── manifest.json     # 处理进度记录                        │
│     └── report.xlsx       # Excel报告                          │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. readers/ - 文件读取

| 模块 | 说明 |
|------|------|
| `excel_reader.py` | 读取 Excel 文件，支持中文列名映射 |
| `csv_reader.py` | 读取 CSV 文件 |
| `json_reader.py` | 读取 JSON 文件 |
| `factory.py` | Reader 工厂，自动发现合适的 Reader |

### 2. core/ - 核心逻辑

| 模块 | 说明 |
|------|------|
| `product.py` | Product 数据模型，包含 ImageMetadata, FetchAttempt |
| `brand_extractor.py` | 从商品名称提取品牌 |
| `file_namer.py` | 规范化文件名，生成安全的文件路径 |

### 3. fetchers/ - 图片抓取

| 模块 | 说明 |
|------|------|
| `base.py` | Fetcher 抽象基类 |
| `brand_fetcher.py` | 品牌官网抓取 (Selenium Chrome) |
| `ecommerce_fetcher.py` | 电商平台抓取 (Amazon/JD/Taobao) |
| `youzan_fetcher.py` | 有赞平台抓取 (直接HTTP请求) |

### 4. automation/ - 浏览器自动化

| 模块 | 说明 |
|------|------|
| `browser.py` | Selenium WebDriver 控制，反检测配置 |
| `human_behavior.py` | 人类行为模拟，随机延迟/滚动/鼠标移动 |

### 5. writers/ - 输出模块

| 模块 | 说明 |
|------|------|
| `manifest_writer.py` | manifest.json 进度记录，支持断点续传 |
| `report_writer.py` | report.xlsx Excel 报告生成 |
| `image_saver.py` | 图片下载和保存 |

## 图片来源优先级

```
1. 品牌官网 (最高优先级)
   ├── canadagoose.com
   ├── haglofs.com
   ├── hellyhansen.com
   ├── stoneisland.com
   └── limitstorem.com

2. 电商平台
   ├── amazon.com
   ├── jd.com
   └── taobao.com

3. Youzan 有赞 (最后手段)
   └── 从Excel中的商品链接获取
```

## 输出文件说明

### manifest.json

```json
{
  "version": "1.0",
  "task_status": "completed",
  "total_products": 578,
  "success_count": 450,
  "failed_count": 128,
  "products": [
    {
      "excel_row": 2,
      "name": "STONE ISLAND Ribbed Soft Cotton",
      "spec": "BLACK-M",
      "brand": "STONE_ISLAND",
      "status": "success",
      "image_path": "output/images/STONE_ISLAND/...",
      "tried_sources": ["brand:STONE_ISLAND", "youzan"],
      "attempts": [
        {
          "source": "brand:STONE_ISLAND",
          "status": "failed",
          "error": "Anti-bot detected"
        },
        {
          "source": "youzan",
          "status": "success",
          "url": "https://..."
        }
      ]
    }
  ]
}
```

### report.xlsx

包含两个 Sheet:
1. **Product Images** - 所有商品的图片信息
2. **Statistics** - 统计汇总

列: excel_row, 商品名称, 商品规格, 品牌, status, image_path, source_domain, source_url, source_page_title, page_description, ...

## 配置文件

`src/img_fetch/config.py`:

```python
# 品牌官网URL
BRAND_WEBSITES = {
    "CANADA_GOOSE": "https://www.canadagoose.com",
    "HAGLOFS": "https://www.haglofs.com",
    "HELLY_HANSEN": "https://www.hellyhansen.com",
    "STONE_ISLAND": "https://www.stoneisland.com",
    "L.I.M": "https://www.limitstorem.com",
}

# 限速 (请求/分钟)
RATE_LIMITS = {
    "canadagoose.com": 2,
    "amazon.com": 10,
    "youzan.com": 30,
}
```

## 使用示例

```bash
# 基本用法
PYTHONPATH=src python3 -m img_fetch.main products.xlsx -o output

# 指定字段
PYTHONPATH=src python3 -m img_fetch.main products.xlsx \
  -o output \
  -n "商品名称" \
  -s "商品规格"

# 查看帮助
PYTHONPATH=src python3 -m img_fetch.main --help
```

## 已知问题

1. **品牌官网反爬虫**: 大多数品牌官网有严格的反爬虫机制
2. **Youzan占位图**: 有赞商品链接通常只返回骨架占位图，需通过其他来源获取真实图片
3. **浏览器驱动**: 需要安装 Chrome 和 ChromeDriver

## 开发

```bash
# 运行测试
python3 -m pytest tests/ -v

# 运行特定测试
python3 -m pytest tests/unit/test_brand_extractor.py -v

# 带覆盖率
python3 -m pytest tests/ --cov=src --cov-report=term-missing
```
