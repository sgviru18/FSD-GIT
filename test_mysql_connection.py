import MySQLdb

# Fill in your actual MySQL credentials below
MYSQL_SETTINGS = {
    'host': 'localhost',         # e.g., 'localhost' or your DB host
    'user': 'root',  # your MySQL username
    'passwd': 'rajat', # your MySQL password
    'db': 'pbl4',       # your database name
    'port': 3306                # default MySQL port
}

try:
    db = MySQLdb.connect(
        host=MYSQL_SETTINGS['host'],
        user=MYSQL_SETTINGS['user'],
        passwd=MYSQL_SETTINGS['passwd'],
        db=MYSQL_SETTINGS['db'],
        port=MYSQL_SETTINGS['port']
    )
    print("Connection successful!")
    db.close()
except Exception as e:
    print("Connection failed:", e)
