import sqlite3

Class Source:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
    
    def execute(self, query):
        self.cursor.execute(query)
        self.conn.commit()