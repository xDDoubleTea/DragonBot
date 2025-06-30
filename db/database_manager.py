import os
from dotenv import load_dotenv
from typing import Any, Dict, Union, List
import psycopg2
from psycopg2.extras import RealDictCursor, RealDictRow
from config import TicketStatus


class DatabaseManager:
    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("Database URL cannot be empty.")
        self.database_url: str = database_url

        self.cursor = None
        self.conn = None

    def __enter__(self):
        """
        Establishes the database connection.
        """
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            return self
        except psycopg2.Error as e:
            print(f"Database connection error: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the cursor and the connection.
        """
        try:
            assert self.conn is not None and self.cursor is not None
            if exc_type is not None:
                print(f"Exception {exc_val}. Rolling back...")
                self.conn.rollback()
            else:
                self.conn.commit()
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except AssertionError:
            print("Database connection or cursor was not initialized correctly.")
            return True
        finally:
            return False

    def create_table(self, table_name: str, columns: List[tuple] = []):
        assert self.cursor is not None
        if not columns:
            raise ValueError("Columns must be provided to create a table.")
        column_definitions = ", ".join([f'"{name}" {ctype}' for name, ctype in columns])
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions})"
        self.cursor.execute(sql)
        print(f"Table '{table_name}' created or already exists.")

    def select(
        self, table_name: str, criteria: Dict[str, Any] = dict(), fetch_one=False
    ) -> Union[List[RealDictRow], Dict[str, Any], None]:
        assert self.cursor is not None
        sql = f"SELECT * FROM {table_name}"
        values = ()
        if criteria:
            conditions = " AND ".join([f"{k} = %s" for k in criteria.keys()])
            sql += f" WHERE {conditions}"
            values = tuple(criteria.values())
        self.cursor.execute(sql, values)
        if fetch_one:
            return self.cursor.fetchone()
        else:
            return self.cursor.fetchall()

    def insert(self, table_name: str, data: Dict[str, Any], returning_col="id") -> Any:
        """
        Inserts a new record into a table.

        Args:
            table_name (str): The name of the table.
            data (dict): A dictionary where keys are column names and
                         values are the data to insert.
        Returns:
            The value of the specified returning column.
        Raises:
            AssertionError: If the cursor is not initialized.
            ValueError: If data is not provided.
        """
        if not data:
            raise ValueError("Data must be provided for insert operation.")
        assert self.cursor is not None

        columns = ", ".join([f'"{k}"' for k in data.keys()])
        placeholders = ", ".join(["%s"] * len(data))
        sql = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders}) RETURNING "{returning_col}"'
        self.cursor.execute(sql, tuple(data.values()))
        result = self.cursor.fetchone()
        if result:
            return result[returning_col]
        return None

    def update(self, table_name: str, data, criteria: Dict[str, Any] = dict()) -> int:
        """
        Updates records from a table where the criteria match.

        Args:
            table_name (str): The name of the table.
            criteria (dict): (Must be an non-empty dict) The WHERE clause to select records to delete.
        Returns:
            Rows affected (int)
        """
        if not criteria:
            raise ValueError("Criteria must be provided for update operation.")
        assert self.cursor is not None

        set_clause = ", ".join([f'"{key}" = %s' for key in data.keys()])
        where_clause = " AND ".join([f'"{key}" = %s' for key in criteria.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        values = tuple(data.values()) + tuple(criteria.values())
        self.cursor.execute(sql, values)
        return self.cursor.rowcount

    def delete(self, table_name: str, criteria: Dict[str, Any] = dict()):
        """
        Deletes records from a table where the criteria match.

        Args:
            table_name (str): The name of the table.
            criteria (dict): (Must be an non-empty dict) The WHERE clause to select records to delete.
        Returns:
            Rows affected (int)
        """
        if not criteria:
            raise ValueError("Criteria must be provided for delete operation.")
        assert self.cursor is not None
        where_clause = " AND ".join([f'"{key}" = %s' for key in criteria.keys()])
        sql = f"DELETE FROM {table_name} WHERE {where_clause}"
        values = tuple(criteria.values())
        self.cursor.execute(sql, values)
        return self.cursor.rowcount


if __name__ == "__main__":
    load_dotenv()
    db_url = os.getenv("DATABASE_TEST_URL", "")
    with DatabaseManager(db_url) as db_manager:
        ticket_columns = [
            ("id", "SERIAL PRIMARY KEY"),
            ("channel_id", "BIGINT"),
            ("auto_timeout", "INTEGER"),
            ("timed_out", "INTEGER"),
            ("first_msg_id", "BIGINT"),
            ("status", "INTEGER"),
            ("participant_ids", "BIGINT[]"),
        ]
        db_manager.create_table(table_name="tickets", columns=ticket_columns)
        init_usr_data = {
            "channel_id": 10100,
            "auto_timeout": 48,
            "timed_out": 0,
            "first_msg_id": 128182,
            "status": TicketStatus.OPEN,
            "participant_ids": [12374],
        }
        db_manager.insert(table_name="tickets", data=init_usr_data)
        print(
            db_manager.select(
                table_name="tickets", criteria={"status": TicketStatus.OPEN}
            )
        )
