import sqlite3
from passlib.hash import sha256_crypt

hasher = sha256_crypt.using(rounds=30000)
def make_hash(password):
    return hasher.hash(password)

def check_hash(password, hash):
    return hasher.verify(password, hash)


class DatabaseWorker:
    def __init__(self, name:str):
        self.name_db = name
        # Step 1: create a connection to the file
        self.connection = sqlite3.connect(self.name_db)
        self.cursor = self.connection.cursor()

    def run_query(self, query:str):
        self.cursor.execute(query)  # run query
        self.connection.commit()  # save changes

    def insert(self, query:str):
        self.run_query(query)

    def search(self, query:str, multiple=False):
        results = self.cursor.execute(query)
        if multiple:
            return results.fetchall()  # return multiple rows
        return results.fetchone()  # return a single value

    def create(self, table_name: str):
        query = f"""CREATE TABLE if not exists {table_name}(
                id INTEGER PRIMARY KEY,
                email text NOT NULL unique,
                password VARCHAR(256),
                username text NOT NULL)"""
        self.run_query(query)

    def close(self):
        self.connection.close()