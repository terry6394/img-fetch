# img-fetch

LLM-powered image fetching skill for e-commerce products.

## 功能

根据 Excel 表格或清单中的商品名称和规格抓取产品图片。

## 安装

```bash
pip install -e .
```

## 使用方法

### 基本用法

```bash
img-fetch <input_file> [options]
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input_file` | 输入文件路径（Excel/CSV/JSON） | 必需 |
| `-o, --output-dir` | 输出目录路径 | `./output` |
| `-b, --brand-field` | 品牌字段名（可选，自动从商品名称提取） | 自动检测 |
| `-n, --name-field` | 商品名称字段名 | `name` |
| `-s, --spec-field` | 商品规格字段名 | `spec` |

### 示例

```bash
# 基本用法
img-fetch products.xlsx

# 指定输出目录和字段
img-fetch products.xlsx -o ./images -n product_name -s specification

# 指定品牌字段
img-fetch products.xlsx -b brand
```

### 输入文件格式

#### Excel 文件 (.xlsx, .xls)

需要包含表头行，支持的列名（大小写不敏感）:
- `name` 或 `product_name`: 商品名称
- `spec` 或 `specification`: 商品规格
- `brand` (可选): 品牌名称

#### CSV 文件 (.csv)

```csv
name,spec,brand
HAGLOFS Alpha Jacket,BLACK-M,HAGLOFS
STONE ISLAND Cotton,RED-L,STONE_ISLAND
```

#### JSON 文件 (.json)

```json
{
  "products": [
    {"name": "HAGLOFS Alpha Jacket", "spec": "BLACK-M", "brand": "HAGLOFS"},
    {"name": "STONE ISLAND Cotton", "spec": "RED-L", "brand": "STONE_ISLAND"}
  ]
}
```

或直接为数组格式:
```json
[
  {"name": "HAGLOFS Alpha Jacket", "spec": "BLACK-M"},
  {"name": "STONE ISLAND Cotton", "spec": "RED-L"}
]
```

### 输出结构

```
output/
└── images/
    └── {BRAND}/
        └── {BRAND}_{NAME}_{SPEC}.jpg
```

## 开发

### 运行测试

```bash
pytest tests/ -v
```

### 代码覆盖率

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

## 项目结构

```
img_fetch/
├── src/img_fetch/
│   ├── main.py           # 入口点
│   ├── config.py         # 配置
│   ├── core/             # 核心模块
│   │   ├── product.py    # 产品数据模型
│   │   ├── brand_extractor.py  # 品牌提取
│   │   └── file_namer.py       # 文件命名
│   ├── readers/          # 文件读取
│   ├── fetchers/         # 图片获取
│   ├── agents/           # LLM代理
│   ├── automation/       # 浏览器自动化
│   ├── writers/          # 文件写入
│   └── utils/            # 工具函数
└── tests/
    ├── unit/             # 单元测试
    └── integration/      # 集成测试
```

## License

MIT
