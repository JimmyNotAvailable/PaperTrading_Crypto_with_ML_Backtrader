import sqlite3

conn = sqlite3.connect('data/trading_logs.db')
cur = conn.cursor()

# Count trades
cur.execute('SELECT COUNT(*) FROM trades')
print(f'✅ Total trades logged: {cur.fetchone()[0]}')

# Latest trades
cur.execute('SELECT symbol, action, price, amount, reason, ml_confidence FROM trades ORDER BY timestamp DESC LIMIT 5')
print('\n📊 Latest 5 trades:')
for row in cur.fetchall():
    print(f'  {row[1]:4} {row[0]:8} @ ${row[2]:>10,.2f} x {row[3]:>10.6f} | {row[5]:.2%} | {row[4]}')

# Equity snapshots
cur.execute('SELECT COUNT(*) FROM equity')
print(f'\n💰 Equity snapshots: {cur.fetchone()[0]}')

# Positions
cur.execute('SELECT COUNT(*) FROM positions')
print(f'📈 Position snapshots: {cur.fetchone()[0]}')

conn.close()
print('\n✅ Database check complete!')
