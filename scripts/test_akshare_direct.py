"""直接测试 akshare"""
import akshare as ak

print("测试 akshare 获取日线数据...")
try:
    df = ak.stock_zh_a_hist(
        symbol="sz000001",
        period="daily",
        start_date="",
        end_date="",
        adjust="qfq",
    )
    print(f"获取到 {len(df)} 条数据")
    if not df.empty:
        print(df.head())
        print("\n列名:", df.columns.tolist())
    else:
        print("数据为空!")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
