# img-fetch

LLM-powered image fetching skill for e-commerce products.

根据 Excel 表格或清单中的商品名称和规格，自动从品牌官网、电商平台抓取产品图片。

## 快速开始

```bash
# 方式1: 使用 Python 模块
PYTHONPATH=src python3 -m img_fetch.main products.xlsx -o output -n "商品名称" -s "商品规格"

# 方式2: Claude Code Skill
/img-fetch products.xlsx
```

## 文档

- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构和工作流程详解
- [REVIEW.md](REVIEW.md) - 需求分析和设计决策
- [CLAUDE.md](CLAUDE.md) - 开发规范

## 功能特性

- 多源图片抓取: 品牌官网 > 电商平台 > Youzan
- 浏览器自动化: Selenium Chrome 真实浏览器抓取
- 人类行为模拟: 随机延迟、反爬虫规避
- 图片验证: 自动识别并拒绝骨架占位图
- 断点续传: manifest.json 记录处理进度
- Excel报告: 生成可读的 report.xlsx

## 输入文件格式

### Excel (.xlsx)

| 列名 | 说明 |
|------|------|
| 商品名称 | 产品名称 |
| 商品规格 | 规格/颜色/尺寸 |
| 商品链接 | 有赞商品链接 (可选) |

### JSON (.json)

```json
{
  "products": [
    {"name": "HAGLOFS Alpha Jacket", "spec": "BLACK-M"}
  ]
}
```

## 输出

```
output/
├── images/
│   └── {BRAND}/
│       └── {BRAND}_{NAME}_{SPEC}.jpg
├── manifest.json   # 处理进度
└── report.xlsx     # Excel报告
```

## 开发

```bash
# 安装依赖
pip install -e .

# 运行测试
python3 -m pytest tests/ -v

# 带覆盖率
python3 -m pytest tests/ --cov=src --cov-report=term-missing
```

## License

MIT
