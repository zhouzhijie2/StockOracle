"""详细检查数据库"""
import sqlite3
import os

db_path = 'h:/aicoding/StockOracle/data/oracle.db'
print(f"数据库路径: {db_path}")
print(f"文件存在: {os.path.exists(db_path)}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 检查所有表
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()
print("\n数据库中的表:")
for table in tables:
    print(f"  - {table[0]}")

# 检查 stock_list
cur.execute('SELECT COUNT(*) FROM stock_list')
stock_count = cur.fetchone()[0]
print(f"\n股票列表数量: {stock_count}")

# 检查 kline_daily
cur.execute('SELECT COUNT(*) FROM kline_daily')
kline_count = cur.fetchone()[0]
print(f"K线数据数量: {kline_count}")

# 如果有K线数据，显示一些示例
if kline_count > 0:
    cur.execute('SELECT code, trade_date, COUNT(*) as cnt FROM kline_daily GROUP BY code ORDER BY cnt DESC LIMIT 5')
    print("\n前5只股票K线数量:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[2]} 条")
    
    cur.execute('SELECT * FROM kline_daily LIMIT 3')
    print("\nK线数据示例:")
    rows = cur.fetchall()
    cur.execute("PRAGMA table_info(kline_daily)")
    cols = [col[1] for col in cur.fetchall()]
    print(f"  列名: {cols}")
    for row in rows:
        print(f"  {row}")
else:
    print("\n⚠️ K线数据为空！")

conn.close()
