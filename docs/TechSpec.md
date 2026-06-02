# StockOracle 技术规格文档（Tech Spec）

> 版本：v1.0  
> 状态：可实现 / 可编码  
> 最后更新：2026-06-02

---

## 1. 技术栈选型

| 层面 | 技术选择 | 理由 |
| --- | --- | --- |
| 开发语言 | Python 3.10+ | 丰富的数据处理库，跨平台成熟生态 |
| GUI 框架 | **PySide6** (Qt6 的 LGPL 绑定) | 跨平台原生外观，组件丰富，开源商业友好 |
| 核心数据处理 | **pandas + numpy** | 向量化计算，全市场筛选速度快 |
| 技术指标 | **ta-lib** 或自实现 | 常用均线/MACD/量能指标 |
| 数据源 | **AkShare**（主） + **efinance**（备） | 免费、全量 A 股、社区活跃 |
| 本地存储 | **SQLite**（Python 标准库内置） | 无需额外安装，单文件数据库，适合桌面 |
| K 线图表 | **pyqtgraph** 或 **matplotlib 嵌入** | pyqtgraph 性能高，适合动态刷新 |
| 配置 / 规则方案 | **JSON** 文件 | 简单、可读、可手动编辑 |
| 实时刷新 | **QThread + QTimer** | Qt 原生多线程，不阻塞 UI |
| 桌面通知 | **plyer**（跨平台） | 统一封装 macOS / Windows 通知 |
| 打包 | **PyInstaller + UPX** | 成熟稳定；Windows 生成 .exe，macOS 生成 .app/.dmg |
| 依赖管理 | **requirements.txt** + **venv** | 简单透明 |

---

## 2. 目录结构

```
StockOracle/
├── docs/
│   ├── PRD.md              # 产品需求文档
│   └── TechSpec.md         # 本文
├── src/
│   └── stock_oracle/
│       ├── __init__.py
│       ├── main.py         # 程序入口（GUI 启动）
│       ├── config.py       # 配置管理（应用路径 / 数据源 / 用户设置）
│       ├── logger.py       # 统一日志
│       ├── data/           # 数据层
│       │   ├── __init__.py
│       │   ├── models.py   # SQLite 表结构定义 + ORM 辅助
│       │   ├── db.py       # 数据库连接/会话/迁移
│       │   ├── providers/  # 数据源抽象 + 实现
│       │   │   ├── __init__.py
│       │   │   ├── base.py         # DataProvider 抽象基类
│       │   │   ├── akshare_provider.py
│       │   │   └── efinance_provider.py
│       │   ├── fetcher.py  # 拉取调度（限速 / 重试 / 缓存）
│       │   └── cache.py    # 缓存命中 / 过期策略
│       ├── indicators/     # 技术指标计算
│       │   ├── __init__.py
│       │   ├── ma.py       # 均线
│       │   ├── macd.py     # MACD
│       │   ├── volume.py   # 量能 / 量比
│       │   └── technical.py# 统一入口
│       ├── screener/       # 选股引擎
│       │   ├── __init__.py
│       │   ├── rules.py    # 预置规则 R1-R4 + 规则注册机制
│       │   ├── custom.py   # 自定义规则（表达式解析）
│       │   ├── schema.py   # 规则方案 JSON Schema
│       │   └── engine.py   # 规则应用 / 评分 / 输出
│       ├── watcher/        # 盯盘引擎
│       │   ├── __init__.py
│       │   ├── monitor.py  # 自选股池实时刷新
│       │   ├── triggers.py # 触发条件评估
│       │   ├── notifier.py # 系统通知 / 声音
│       │   └── log.py      # 触发日志
│       ├── portfolio/      # 自选股 / 分组管理
│       │   ├── __init__.py
│       │   └── manager.py
│       └── ui/             # GUI 层
│           ├── __init__.py
│           ├── app.py          # QApplication 启动
│           ├── main_window.py  # 主窗口 + 标签页
│           ├── widgets/
│           │   ├── __init__.py
│           │   ├── data_center.py
│           │   ├── screener.py
│           │   ├── watcher.py
│           │   ├── quote.py
│           │   └── settings.py
│           └── charts/
│               ├── __init__.py
│               └── kline.py     # pyqtgraph K 线组件
├── tests/
│   ├── test_indicators.py
│   ├── test_rules.py
│   └── test_db.py
├── data/                   # 运行时数据（SQLite db + 缓存），git 忽略
├── user_rules/             # 用户保存的规则方案 JSON
├── user_portfolios/        # 用户自选股 JSON
├── requirements.txt
├── pyproject.toml          # 可选：用于打包元信息
├── build_windows.spec      # PyInstaller spec for Windows
├── build_macos.spec        # PyInstaller spec for macOS
├── README.md
├── .gitignore
└── run.py                  # 开发启动脚本：python run.py
```

---

## 3. 核心模块接口设计

### 3.1 DataProvider 抽象

所有数据源统一抽象，便于未来替换 / 扩展：

```python
# src/stock_oracle/data/providers/base.py
from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd

class DataProvider(ABC):
    name: str = "base"

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """返回 [code, name, market] 列表"""
        ...

    @abstractmethod
    def get_daily(self, code: str, start: Optional[str] = None,
                  end: Optional[str] = None, adjust: str = "qfq") -> pd.DataFrame:
        """返回日线 DataFrame
        columns: [date, open, high, low, close, volume, amount]
        date: 'YYYY-MM-DD'
        """
        ...

    @abstractmethod
    def get_minute(self, code: str, freq: str = "5",
                   days: int = 30) -> pd.DataFrame:
        """返回分钟线
        columns: [datetime, open, high, low, close, volume]
        freq in ["5", "15", "30", "60"]
        """
        ...

    @abstractmethod
    def get_realtime_quote(self, codes: List[str]) -> pd.DataFrame:
        """批量拉取实时行情
        columns: [code, name, price, change_pct, open, high, low,
                  preclose, volume, amount, turnover_rate, volume_ratio]
        """
        ...

    def health_check(self) -> bool:
        """简单健康检查"""
        try:
            self.get_stock_list()
            return True
        except Exception:
            return False
```

数据源注册机制（`data/providers/__init__.py`）：

```python
PROVIDERS = {
    "akshare": AkShareProvider(),
    "efinance": EFinanceProvider(),
}

def get_provider(name: str = "akshare") -> DataProvider:
    return PROVIDERS.get(name) or PROVIDERS["akshare"]
```

### 3.2 Indicators（技术指标层）

所有指标函数是**纯函数**，输入 `pd.Series` / `pd.DataFrame`，输出列。方便写单元测试。

```python
# src/stock_oracle/indicators/ma.py
import pandas as pd

def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()

def ma_cross(close: pd.Series, short: int, long: int) -> pd.Series:
    """返回布尔序列：True 表示当日短均线上穿长均线"""
    s = sma(close, short)
    l = sma(close, long)
    prev_s, prev_l = s.shift(1), l.shift(1)
    return (s > l) & (prev_s <= prev_l)
```

```python
# src/stock_oracle/indicators/macd.py
import pandas as pd

def macd(close: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return dif, dea, hist

def macd_golden_cross(close: pd.Series) -> pd.Series:
    dif, dea, _ = macd(close)
    return (dif > dea) & (dif.shift(1) <= dea.shift(1))
```

### 3.3 Screener Rules（规则）

规则统一接口：

```python
# src/stock_oracle/screener/engine.py
from dataclasses import dataclass, field
from typing import Dict, Any, List, Callable
import pandas as pd

@dataclass
class RuleResult:
    code: str
    name: str
    hit: bool
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)

# 规则函数签名：df(daily) + params -> RuleResult
RuleFn = Callable[[pd.DataFrame, Dict[str, Any]], RuleResult]

class RuleRegistry:
    _rules: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, key: str, fn: RuleFn, default_params: Dict[str, Any],
                 description: str = ""):
        cls._rules[key] = {"fn": fn, "params": default_params, "desc": description}

    @classmethod
    def run(cls, key: str, df: pd.DataFrame, params: Dict[str, Any] = None) -> RuleResult:
        entry = cls._rules[key]
        merged = {**entry["params"], **(params or {})}
        return entry["fn"](df, merged)
```

核心规则 R1（底部横盘缩量 + 放量上涨）实现骨架：

```python
def rule_consolidation_breakout(df: pd.DataFrame, params: dict) -> RuleResult:
    """
    df columns: [date, open, high, low, close, volume, amount]
    需要至少 params["consolidation_days"] + 5 条历史
    """
    ...
    # 伪代码：
    # 1. 窗口切片：最近 N 日（不含今日观察日）
    # 2. 横盘判定：max(high) / min(low) <= 1 + range_pct/100
    # 3. 缩量判定：后 5 日均量 / 前 15 日均量 <= shrink_ratio
    # 4. 今日涨 5%-7%：(close[-1] / close[-2] - 1) 在区间
    # 5. 今日放量：volume[-1] / mean(volume[-N:]) >= expansion
    # 6. 价格 > MA20
    # 7. 打分：score = 涨幅 + 放量倍数 * 2 + (1 - 振幅/15%) * 3
    ...
```

### 3.4 Watcher（盯盘）

- 使用 `QTimer` 每 N 秒拉取实时行情
- 使用 `QThread` 跑 `get_realtime_quote`，结果通过 `pyqtSignal` 回主线程
- 触发条件在主线程评估，命中则调用 `notifier.notify()`

---

## 4. 关键流程

### 4.1 首次启动

```
启动 → 检查 data/oracle.db 是否存在
  ├─ 不存在 → 建表（见 §5）
  ├─ 检查 stock_list 表是否为空 → 调用 provider.get_stock_list() 写入
  └─ 启动 GUI 主窗口
```

### 4.2 盘后选股流程

```
用户点击"运行选股"
  ├─ 校验是否有日线数据（不足则增量拉取）
  ├─ 并行拉取（多进程 / 线程池，限速 0.5-1.5s 间隔）
  ├─ 每只股票：pandas 向量化计算指标
  ├─ 按规则评分，输出 Top-N
  └─ 结果写入临时表 + GUI 表格展示 + 可导出 CSV
```

### 4.3 盯盘流程

```
用户点击"开始盯盘"
  ├─ 每 refresh_interval 秒：
  │   └─ worker 线程请求 get_realtime_quote(自选股池)
  │       └─ 主线程信号触发 → 更新表格
  │                      └─ 逐条评估触发条件
  │                          └─ 命中 → 系统通知 + 日志
  └─ 用户点击"停止" → timer.stop()
```

---

## 5. 数据库表结构

表字段使用 **snake_case**，股票代码使用 `code`（6 位）+ `market`（sh/sz）拼接为符号。

```sql
-- 股票基本信息
CREATE TABLE stock_list (
    code         TEXT PRIMARY KEY,  -- 6 位代码，内部使用
    symbol       TEXT UNIQUE,       -- 如 sh600519 / sz000001
    name         TEXT NOT NULL,
    market       TEXT,              -- sh / sz / bj
    industry     TEXT,
    list_date    TEXT,              -- YYYY-MM-DD
    updated_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 日线（核心数据）
CREATE TABLE kline_daily (
    code        TEXT NOT NULL,
    trade_date  TEXT NOT NULL,       -- YYYY-MM-DD
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      INTEGER,
    amount      REAL,
    adjust      TEXT DEFAULT 'qfq', -- qfq / hfq / none
    PRIMARY KEY (code, trade_date, adjust)
);
CREATE INDEX IF NOT EXISTS idx_kline_daily_code ON kline_daily(code);
CREATE INDEX IF NOT EXISTS idx_kline_daily_date ON kline_daily(trade_date);

-- 分钟线（可选保留，按日期分区）
CREATE TABLE kline_minute (
    code        TEXT NOT NULL,
    ts          TEXT NOT NULL,       -- 'YYYY-MM-DD HH:MM'
    freq        TEXT NOT NULL,       -- 5 / 15 / 30 / 60
    open        REAL, high REAL, low REAL, close REAL,
    volume      INTEGER,
    PRIMARY KEY (code, ts, freq)
);

-- 自选股池
CREATE TABLE portfolio (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,   -- 如 "短线池" / "中长线"
    description TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE portfolio_item (
    portfolio_id INTEGER NOT NULL,
    code         TEXT NOT NULL,
    added_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (portfolio_id, code)
);

-- 盯盘触发日志
CREATE TABLE watch_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    code       TEXT NOT NULL,
    rule_key   TEXT NOT NULL,
    trigger_at TEXT NOT NULL,
    price      REAL,
    change_pct REAL,
    note       TEXT
);

-- 应用设置（key-value）
CREATE TABLE app_config (
    key   TEXT PRIMARY KEY,
    value TEXT
);
```

首次建表通过 `data/db.py` 里的 `init_db()` 完成（使用原生 sqlite3）。

---

## 6. 配置与持久化

### 6.1 应用目录（跨平台）

- **Windows**：`%APPDATA%/StockOracle/` 或用户选择的目录
- **macOS**：`~/Library/Application Support/StockOracle/`
- **开发模式**：项目根目录下的 `data/`

统一通过 `config.py` 的 `get_app_dir()` 解析。

### 6.2 规则方案 JSON 示例

```json
{
  "name": "底部横盘放量",
  "rules": [
    {
      "rule_key": "consolidation_breakout",
      "params": {
        "consolidation_days": 20,
        "consolidation_range_pct": 15,
        "shrink_vol_ratio": 0.7,
        "today_min_pct": 5.0,
        "today_max_pct": 7.0,
        "vol_expansion_ratio": 2.0,
        "price_above_ma20": true
      }
    }
  ],
  "filters": {
    "exclude_st": true,
    "exclude_new_ipo_days": 60,
    "min_price": 2.0,
    "max_price": 100.0,
    "min_mcap_yi": 10,
    "max_mcap_yi": 1000
  }
}
```

---

## 7. GUI 设计要点

### 7.1 主窗口（`main_window.py`）

- 使用 `QMainWindow` + `QTabWidget` 承载 5 个 Tab：数据中心 / 选股中心 / 盯盘中心 / 行情中心 / 设置
- 底部状态栏显示：数据源、当前本地数据版本、最后更新时间
- 顶部菜单：文件（导入/导出/退出）、工具（刷新数据、清空缓存）、帮助（关于）

### 7.2 数据中心 Tab

- 左侧：数据源选择 + 数据统计（本地已存股票数、日线记录数、最后更新时间）
- 中部：进度条 + 按钮组（更新股票列表 / 更新全市场日线 / 仅更新增量 / 清空缓存）
- 右侧：拉取日志滚动区（可关闭）

### 7.3 选股中心 Tab

- 左侧：规则方案列表（树形，分组：预置 / 我的）
- 右上：规则参数编辑面板（动态生成 QLineEdit / QCheckBox / QSpinBox）
- 右下：结果表格（`QTableWidget`，可点击任意行跳转行情中心）

### 7.4 盯盘中心 Tab

- 顶部：自选股池下拉 + 开始/停止按钮 + 刷新频率下拉
- 主区：表格（代码、名称、现价、涨跌幅、量比、换手率、状态），涨跌幅按颜色标红标绿
- 底部：触发日志（滚动，保留最近 500 条）

### 7.5 行情中心 Tab

- 顶部：搜索框（按代码 / 名称搜）
- 左：股票基础信息卡片
- 右：`pyqtgraph` K 线图，叠加 MA5/10/20
- 底部：最近 60 交易日的量能图

### 7.6 设置 Tab

- 数据源选择（单选：AkShare / efinance）
- 数据存储目录（`QFileDialog` 选择）
- 实时行情刷新频率（3s / 5s / 15s / 60s）
- 声音提醒开关（可选择声音文件）
- 代理（可选，HTTP 代理文本框）

---

## 8. 数据流与时序（盘后选股）

```
┌──────────┐   1. 拉取股票列表       ┌─────────────┐
│  Main    │ ──────────────────────▶ │ DataFetcher │
│  Window  │                          └──────┬──────┘
│          │   2. 每只股票拉取日线             │ akshare API
│          │ ◀─────── progress signal ────────┘
│          │
│          │   3. 用户选择规则方案
│          │   4. 点击"运行选股"
│          │                     ┌──────────────┐
│          │ ──────────────────▶ │ Screener     │
│          │                     │ Engine       │
│          │                     │  · pandas 向量化
│          │                     │  · 规则逐股应用
│          │                     │  · 排序 Top-N
│          │ ◀──────────────────  │  · 输出 DataFrame
└──────────┘   5. 刷新表格展示    └──────────────┘
```

---

## 9. 测试策略

| 测试类型 | 覆盖范围 | 工具 |
| --- | --- | --- |
| 单元测试 | indicators / rules / 数据解析 | pytest |
| 集成测试 | DataFetcher（mock provider）+ SQLite 读写 | pytest + 临时数据库 |
| 手工验证 | 与东方财富网页数据抽样对比 5-10 只股票最近 30 日价格 | 人工 |
| 性能测试 | 全市场 5500 只选股运行耗时 | cProfile |
| 冒烟测试 | 冷启动 + 首次全量拉取 | 各平台各一台 |

---

## 10. 打包与发布

### 10.1 requirements.txt

```
PySide6>=6.5
pandas>=2.0
numpy>=1.24
akshare>=1.12
efinance>=0.8
pyqtgraph>=0.13
plyer>=2.1
requests>=2.31
pyinstaller>=6.0
```

### 10.2 PyInstaller 打包命令

Windows（在 Windows 机器执行）：
```
pyinstaller --noconfirm --clean build_windows.spec
```

macOS（在 Mac 机器执行，支持 Universal2）：
```
pyinstaller --noconfirm --clean build_macos.spec
```

`build_*.spec` 要点：
- `--windowed` / `--noconsole`（不显示命令行窗口）
- `--name StockOracle`
- `--icon assets/icon.ico`（对应平台格式）
- `--collect-all PySide6`、`--collect-submodules akshare`（避免隐藏导入遗漏）
- `--upx-dir path/to/upx`（体积优化，可选）
- `datas` 段把 `user_rules/`、`user_portfolios/` 空目录打进资源

---

## 11. 性能与优化清单

- [ ] 使用 pandas `rolling()` 而非循环，选股时间复杂度 O(N × D)，D 为天数常数
- [ ] 全市场拉取使用 `ThreadPoolExecutor`，最大 8 并发，随机 0.3-1.0s 间隔避免被封
- [ ] `kline_daily` 建立 `(code, trade_date)` 索引，避免重复写入
- [ ] 选股时按 pandas 先批量读所有股票到内存（如果受限则分批 1000 只一批）
- [ ] 实时行情使用 `get_realtime_quote` 批量接口（一次请求返回全部），避免逐股请求
- [ ] pyqtgraph 使用 `setData` 更新而非重建

---

## 12. 下一步编码顺序（建议）

1. `src/stock_oracle/config.py` + `logger.py`
2. `src/stock_oracle/data/db.py` + `data/providers/base.py`
3. `src/stock_oracle/data/providers/akshare_provider.py`（最关键）
4. `src/stock_oracle/data/fetcher.py`
5. `src/stock_oracle/indicators/`（ma / macd / volume）
6. `src/stock_oracle/screener/`（rules + engine + R1-R4）
7. CLI 冒烟测试：`python -m stock_oracle.screener --rule r1 --top 30`
8. `src/stock_oracle/ui/app.py` + `main_window.py`（骨架 Tab 壳）
9. 逐个 widget 填充（数据中心 / 选股中心 / 盯盘中心 / 行情中心 / 设置）
10. `src/stock_oracle/watcher/` + 盯盘 Tab 联动
11. 打包 spec + 各平台安装包
12. 自测 + 修复

---

## 13. 常见坑与规避

| 坑 | 规避 |
| --- | --- |
| akshare 接口偶尔改名 / 返回列名变化 | 列名重命名 + 必要字段 assert + 异常降级 |
| 全量拉取时间长，被限速或被封 | 限速 + 随机间隔 + 断点续拉（写入失败记表，下次继续） |
| 非交易日数据缺失（停牌股） | `if df.empty` 统一跳过，不抛异常 |
| Windows / macOS 通知 API 差异 | `plyer.notification` 统一封装，失败降级为 QSystemTrayIcon 弹消息 |
| pandas `SettingWithCopyWarning` | 所有操作使用 `.copy()` / `.loc[..., col] = ...` |
| Qt 子线程修改 UI 崩溃 | 严格使用 `pyqtSignal` 跨线程通信 |

---

**文档结束。** 下一步：进入实现阶段（§12 的编码顺序）。
