import mysql.connector

host = '1'
user = '1'
password = '1'
database = '1'

class MySqlDataBase:
    class SqlInfo:
        def __init__(self, host, user, password, database):
            self.host = host
            self.user = user
            self.password = password
            self.database = database
    
    def __init__(self):
        self.SqlInfo.host = host
        self.SqlInfo.user = user
        self.SqlInfo.password = password
        self.SqlInfo.database = database

    def connect_to_db(self):
        db = mysql.connector.connect(
            host = self.SqlInfo.host,
            user = self.SqlInfo.user,
            password = self.SqlInfo.password,
            database = self.SqlInfo.database
            )
        return db 

    def get_db_data(self, sql_cmd:str, values:tuple = ()):
        db = self.connect_to_db()
        cursor = db.cursor()
        cursor.execute(sql_cmd, values)
        return cursor.fetchall()

    def insert_data(self, sql_cmd:str, values:tuple):
        db = self.connect_to_db()
        cursor = db.cursor()
        cursor.execute(sql_cmd, values)
        return db.commit()

    def del_data(self, sql_cmd:str, values):
        db = self.connect_to_db()
        cursor = db.cursor()
        cursor.execute(sql_cmd, values)
        return db.commit()
    
    def update_data(self, sql_cmd:str, values:tuple):
        db = self.connect_to_db()
        cursor = db.cursor()
        cursor.execute(sql_cmd, values)
        return db.commit()