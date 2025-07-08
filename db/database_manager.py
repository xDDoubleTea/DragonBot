from typing import Any, Dict, Union, List
import psycopg2
from psycopg2.extras import RealDictCursor, RealDictRow
import asyncpg


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

    def _build_where_clause(self, criteria: Dict[str, Any]) -> tuple[str, tuple]:
        """
        Builds a WHERE clause and a tuple of values from a criteria dict.
        Handles both single values (=) and lists (IN).
        """
        if not criteria:
            return "", ()

        conditions = []
        values: list[Any] = []
        for key, value in criteria.items():
            if isinstance(value, (list, tuple)):
                if not value:
                    # Handle empty list case to prevent SQL errors.
                    # This condition will always be false, correctly returning no rows.
                    conditions.append("1 = 0")
                    continue
                conditions.append(f'"{key}" IN %s')
                values.append(
                    tuple(value)
                )  # psycopg2 expects a tuple for the IN clause
            else:
                conditions.append(f'"{key}" = %s')
                values.append(value)

        where_clause = "WHERE " + " AND ".join(conditions)
        return where_clause, tuple(values)

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
        where_clause, values = self._build_where_clause(criteria)
        sql = f"SELECT * FROM {table_name} {where_clause}"
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

    def insert_many(self, table_name: str, data: List[Dict[str, Any]]):
        """
        Inserts multiple rows into a table in a single transaction.

        Args:
            table_name (str): The table name to insert data.
            data (List[Dict[str, Any]]): The data list to insert.
        """
        if not data:
            return

        columns = data[0].keys()
        columns_sql = ", ".join(columns)
        placeholders_sql = ", ".join(["%s"] * len(columns))

        values_to_insert = [tuple(row[col] for col in columns) for row in data]

        query = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders_sql})"

        try:
            assert self.cursor
            self.cursor.executemany(query, values_to_insert)
        except Exception as e:
            print(f"Error during bulk insert: {e}")
            raise

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
        where_clause, where_values = self._build_where_clause(criteria=criteria)
        sql = f"UPDATE {table_name} SET {set_clause} {where_clause}"
        values = tuple(data.values()) + tuple(where_values)
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
        where_clause, values = self._build_where_clause(criteria=criteria)
        sql = f"DELETE FROM {table_name} {where_clause}"
        self.cursor.execute(sql, values)
        return self.cursor.rowcount


class AsyncDatabaseManager:
    def __init__(self, db_url: str):
        self._db_url = db_url
        self._pool: asyncpg.Pool | None = None

    async def connect(self):
        """Creates the connection pool. Call this once on bot startup."""
        if not self._pool:
            self._pool = await asyncpg.create_pool(self._db_url)
            print("Successfully created async database connection pool.")

    async def close(self):
        """Closes the connection pool. Call this on bot shutdown."""
        if self._pool:
            await self._pool.close()

    def _build_where_clause(
        self, criteria: Dict[str, Any], start_index: int = 1
    ) -> tuple[str, list[Any]]:
        """
        Builds a WHERE clause for asyncpg, using $1, $2, etc. for parameters.
        This is now a synchronous method as it does no I/O.
        """
        if not criteria:
            return "", []

        conditions = []
        values: list[Any] = []
        for i, (key, value) in enumerate(criteria.items(), start=start_index):
            if isinstance(value, (list, tuple)):
                # Note: asyncpg can use `= ANY($n)` for list matching
                conditions.append(f'"{key}" = ANY(${i})')
                values.append(list(value))
            else:
                conditions.append(f'"{key}" = ${i}')
                values.append(value)

        where_clause = "WHERE " + " AND ".join(conditions)
        return where_clause, values

    async def select(
        self, table_name: str, criteria: Dict[str, Any] = dict(), fetch_one=False
    ):
        if not self._pool:
            raise RuntimeError(
                "Database pool is not initialized. Call connect() first."
            )
        where_clause, params = self._build_where_clause(criteria)
        query = f"SELECT * FROM {table_name} {where_clause}"

        async with self._pool.acquire() as connection:
            if fetch_one:
                return await connection.fetchrow(query, *params)
            return await connection.fetch(query, *params)

    async def insert(
        self, table_name: str, data: Dict[str, Any], returning_col: str
    ) -> Any:
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
        if not self._pool:
            raise RuntimeError(
                "Database pool is not initialized. Call connect() first."
            )
        columns = ", ".join([f'"{k}"' for k in data.keys()])
        placeholders = ", ".join([f"${i}" for i in range(1, len(data) + 1)])
        sql = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders}) RETURNING "{returning_col}"'
        async with self._pool.acquire() as connection:
            result = await connection.fetchrow(sql, *data.values())
            if result:
                return result[returning_col]
            return None

    async def insert_many(self, table_name: str, data: List[Dict[str, Any]]):
        """
        Inserts multiple rows into a table in a single transaction.

        Args:
            table_name (str): The table name to insert data.
            data (List[Dict[str, Any]]): The data list to insert.
        """
        if not data:
            return
        if not self._pool:
            raise RuntimeError(
                "Database pool is not initialized. Call connect() first."
            )

        columns = data[0].keys()
        columns_sql = ", ".join(columns)
        placeholders_sql = ", ".join([f"${i}" for i in range(1, len(columns) + 1)])

        values_to_insert = [tuple(row[col] for col in columns) for row in data]

        query = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders_sql})"

        try:
            async with self._pool.acquire() as connection:
                await connection.executemany(query, values_to_insert)
        except Exception as e:
            print(f"Error during bulk insert: {e}")
            raise

    async def update(
        self, table_name: str, data, criteria: Dict[str, Any] = dict()
    ) -> int:
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
        if not self._pool:
            raise RuntimeError(
                "Database pool is not initialized. Call connect() first."
            )

        # Build SET clause
        set_clause = ", ".join(
            [f'"{key}" = ${i + 1}' for i, key in enumerate(data.keys())]
        )

        # Build WHERE clause, starting placeholder index after the SET values
        where_clause, where_values = self._build_where_clause(
            criteria, start_index=len(data) + 1
        )
        sql = f"UPDATE {table_name} SET {set_clause} {where_clause}"
        all_values = tuple(data.values()) + tuple(where_values)
        async with self._pool.acquire() as connection:
            status = await connection.execute(sql, *all_values)
            return int(status.split()[-1])

    async def delete(self, table_name: str, criteria: Dict[str, Any] = dict()):
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
        if not self._pool:
            raise RuntimeError(
                "Database pool is not initialized. Call connect() first."
            )
        where_clause, values = self._build_where_clause(criteria=criteria)
        sql = f"DELETE FROM {table_name} {where_clause}"
        async with self._pool.acquire() as connection:
            status = await connection.execute(sql, *values)
            return int(status.split()[-1])


if __name__ == "__main__":
    print("Nothing was done...")
