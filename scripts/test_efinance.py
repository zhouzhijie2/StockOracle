"""测试 efinance 数据源"""
import sys
sys.path.insert(0, 'h:/aicoding/StockOracle/src')

from stock_oracle.data.providers.efinance_provider import EFinanceProvider

provider = EFinanceProvider()

print("测试 efinance 获取日线数据...")
try:
    df = provider.get_daily("000001")
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
