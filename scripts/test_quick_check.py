"""测试快速判断功能"""
import sys
sys.path.insert(0, 'h:/aicoding/StockOracle/src')

from stock_oracle.data.fetcher import DataFetcher

fetcher = DataFetcher()

print("测试 get_all_last_dates()...")
last_dates = fetcher.get_all_last_dates()
print(f"获取到 {len(last_dates)} 只股票的最后更新日期")

if last_dates:
    # 显示前5个
    count = 0
    for code, date in last_dates.items():
        print(f"  {code}: {date}")
        count += 1
        if count >= 5:
            break
else:
    print("⚠️ 没有找到任何股票的最后更新日期！")

# 检查今天日期
from datetime import datetime
today = datetime.now().date()
print(f"\n今天日期: {today}")
