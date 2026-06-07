"""检查数据库数据"""
import sqlite3

conn = sqlite3.connect('h:/aicoding/StockOracle/data/oracle.db')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM stock_list')
print('股票列表数量:', cur.fetchone()[0])

cur.execute('SELECT COUNT(*) FROM kline_daily')
print('K线数据数量:', cur.fetchone()[0])

cur.execute('SELECT code, COUNT(*) as cnt FROM kline_daily GROUP BY code ORDER BY cnt DESC LIMIT 5')
print('前5只股票K线数量:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]} 条')

conn.close()
