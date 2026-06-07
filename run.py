"""StockOracle 命令行入口（开发期运行脚本）。

用法:
    python run.py            # 启动 GUI
    python run.py --cli      # CLI 模式：按默认规则跑一次选股，打印 Top N
"""
import argparse
import sys
import os

lib_path = os.path.join(os.path.dirname(__file__), 'lib')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)

src_path = os.path.join(os.path.dirname(__file__), 'src')
if os.path.exists(src_path):
    sys.path.insert(0, src_path)

import site
user_site = site.getusersitepackages()
if os.path.exists(user_site):
    sys.path.insert(0, user_site)


def main():
    parser = argparse.ArgumentParser(prog="StockOracle")
    parser.add_argument("--cli", action="store_true", help="仅跑 CLI，不启动 GUI")
    parser.add_argument("--rule", default="consolidation_breakout", help="规则 key")
    parser.add_argument("--top", type=int, default=30, help="返回 Top N")
    args = parser.parse_args()

    if args.cli:
        _run_cli(args)
    else:
        from stock_oracle.ui.app import run
        run()


def _run_cli(args):
    from stock_oracle.data import db
    from stock_oracle.data.fetcher import DataFetcher
    from stock_oracle.indicators.technical import enrich
    from stock_oracle.screener.engine import run_rule, results_to_dataframe

    db.init_db()
    fetcher = DataFetcher()
    df = fetcher.get_local_stock_list()
    if df.empty:
        print("未找到本地股票数据，正在尝试拉取列表...")
        fetcher.update_stock_list()
        df = fetcher.get_local_stock_list()
    if df.empty:
        print("无法获取股票列表，请检查网络。")
        sys.exit(1)

    print(f"共 {len(df)} 只股票，开始按规则 {args.rule} 筛选...")
    codes = df["code"].tolist()
    names = dict(zip(df["code"], df["name"]))

    results = []
    for i, code in enumerate(codes):
        kline = fetcher.get_local_daily(code)
        if kline.empty or len(kline) < 25:
            continue
        data = enrich(kline)
        r = run_rule(args.rule, data, params={}, code=code, name=names.get(code, ""))
        if r.hit:
            results.append(r)
        if (i + 1) % 500 == 0:
            print(f"  已扫描 {i + 1}/{len(codes)} 只, 命中 {len(results)} 只")

    results.sort(key=lambda x: x.score, reverse=True)
    top = results[: args.top]
    df_out = results_to_dataframe(top)
    print("\n=== 结果 ===")
    print(df_out.to_string(index=False))


if __name__ == "__main__":
    main()
