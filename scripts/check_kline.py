import sqlite3

conn = sqlite3.connect('h:/aicoding/StockOracle/data/oracle.db')
cur = conn.cursor()

# 直接执行SQL
cur.execute("SELECT COUNT(*) FROM kline_daily")
result = cur.fetchone()
print(f"K线数量: {result[0]}")

cur.execute("SELECT * FROM kline_daily LIMIT 1")
row = cur.fetchone()
if row:
    print("第一条数据:", row)
else:
    print("表为空")

conn.close()
