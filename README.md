# StockOracle 📈

面向 A 股个人投资者的跨平台桌面智能选股工具。基于 Python + PySide6，本地 SQLite 存储，免费数据接口（AkShare / efinance）。

## ✨ 核心能力

| 模块 | 功能 |
|---|---|
| 数据中心 | 拉取 A 股股票列表；增量/全量更新日线数据；本地 SQLite 缓存 |
| 选股中心 | 预置 5 条规则：底部横盘放量、均线金叉、MACD 金叉、放量创新高、涨停板；自定义参数；导出 CSV |
| 盯盘中心 | 自选股分组；多条件并行监控（涨跌幅、量比、换手率）；系统通知桌面提醒 |
| 行情中心 | 个股实时行情 + K线图（MA5/MA10/MA20）；双击其它 Tab 跳转 |
| 设置 | 数据源切换；刷新间隔；提示音；代理配置 |

## 🚀 快速开始

```bash
# 1. 克隆并安装依赖
git clone <this-repo>
cd StockOracle
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt

# 2. 启动 GUI
python run.py

# 3. 或使用 CLI 跑一次选股（便于自动化）
python run.py --cli --rule consolidation_breakout --top 30
```

## 📦 打包为桌面可执行程序

需要在目标平台上运行打包命令：

### Windows（生成本机 .exe）
```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name StockOracle \
  --collect-all PySide6 --collect-all akshare --collect-all efinance \
  --hidden-import pyqtgraph --hidden-import plyer \
  run.py
# 生成的文件位于 dist/StockOracle/StockOracle.exe
```

### macOS（生成本机 .app）
```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name StockOracle \
  --collect-all PySide6 --collect-all akshare --collect-all efinance \
  --hidden-import pyqtgraph --hidden-import plyer \
  run.py
# 生成的文件位于 dist/StockOracle.app
```

## 📖 目录结构

```
StockOracle/
├── docs/                    # 产品需求与技术规格文档
│   ├── PRD.md              # 产品需求文档
│   └── TechSpec.md         # 技术规格
├── src/stock_oracle/       # 主代码包
│   ├── config.py           # 应用配置
│   ├── logger.py           # 日志
│   ├── data/               # 数据层（数据源抽象 + Fetcher）
│   ├── indicators/         # 技术指标
│   ├── screener/           # 选股引擎（规则 + 注册表）
│   ├── watcher/            # 盯盘引擎（通知 + 触发）
│   ├── portfolio/          # 自选股管理
│   └── ui/                 # PySide6 GUI 层
├── tests/                  # 测试（pytest）
├── run.py                  # 入口脚本
└── requirements.txt
```

## 🧪 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## 📝 合规声明

本产品**不提供证券投资咨询服务，不做买卖建议，不涉及任何自动交易**。所有数据筛选与指标展示仅供用户自行研究参考。

## 🔖 许可证

MIT
