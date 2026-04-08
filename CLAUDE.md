# img_fetch 项目规范

## 项目管理
- **分支策略**: Git Flow (main/develop/feature/*)
- **包管理**: uv (Python包管理器)
- **测试**: pytest + pytest-cov，核心模块覆盖率 > 80%

## 开发原则

### 1. 可测试性
- 所有核心模块必须有单元测试
- 使用依赖注入便于Mock测试
- 测试文件放在 `tests/` 目录

### 2. 可扩展性
- 使用抽象基类定义接口（如 `BaseReader`, `BaseFetcher`）
- 插件式架构，新增Reader/Fetcher只需实现接口
- 配置外部化，避免硬编码

### 3. GitHub管理
- 所有变更通过 Pull Request 合并
- feature 分支从 develop 创建
- commit message 遵循 Conventional Commits

## 技术栈
- Python 3.11+ / uv
- Selenium + Chrome (浏览器自动化)
- pytest (测试)
- openpyxl (Excel处理)
- anthropic SDK (LLM调用)
