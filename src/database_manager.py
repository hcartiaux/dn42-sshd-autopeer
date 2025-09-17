import logging
import os
import sqlite3
import threading

from src.utils_dn42 import as_maintained_by


class DatabaseManager:
    """
    A manager class for handling interactions with an SQLite database, specifically for managing peering links.

    Attributes:
        db_path (str): The path to the SQLite database file.
        connection (sqlite3.Connection): The connection to the SQLite database.
    """

    def __init__(self, db_path=None):
        """
        Initialize the DatabaseManager with a database path and open the connection.

        Parameters:
            db_path (str, optional): The path to the SQLite database file.
                                     If not provided, it will be taken from the environment variable 'DN42_DB_PATH'.
        """
        self.db_path = db_path or os.environ['DN42_DB_PATH']
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._initialize_database()

    def _initialize_database(self):
        """
        Initialize the database schema by creating the peering_links table if it does not exist.
        """
        with self.connection:
            self.connection.execute("""
            CREATE TABLE IF NOT EXISTS peering_links (
                id INTEGER PRIMARY KEY CHECK(id BETWEEN 1 AND 65535),
                as_num INTEGER UNIQUE NOT NULL,
                wg_pub_key TEXT NOT NULL,
                wg_endpoint_addr TEXT NOT NULL,
                wg_endpoint_port INTEGER NOT NULL CHECK(wg_endpoint_port BETWEEN 1 AND 65535),
                user_link_local TEXT
            )
            """)

    def close(self):
        """
        Close the database connection explicitly.
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_peer_config(self, as_num):
        """
        Get the peer configuration for a specific AS number.

        Parameters:
            as_num (int): The AS number for which to retrieve the peer configuration.

        Returns:
            dict or None: The peer configuration details, or None if not found.
        """
        cursor = self.connection.execute("SELECT * FROM peering_links WHERE as_num = ?", (as_num,))
        row = cursor.fetchone()
        if row:
            # Use user's link-local if provided, otherwise use calculated one
            if row["user_link_local"]:
                peer_address = row["user_link_local"]
            else:
                peer_address = f"{os.environ['DN42_WG_LINK_LOCAL_PREFIX']}2:{hex(row['id'])[2:]}"

            return {
                "id": row["id"],
                "wg_pub_key": row["wg_pub_key"],
                "wg_endpoint_addr": row["wg_endpoint_addr"],
                "wg_endpoint_port": str(row["wg_endpoint_port"]),
                "ll_address": peer_address,
            }
        else:
            return None

    def get_peer_list(self, user):
        """
        Retrieve a list of peers maintained by a user.

        Parameters:
            user (str): The user maintaining the AS numbers.

        Returns:
            dict: A dictionary containing the peer details, keyed by AS number.
        """
        as_nums = as_maintained_by(user)
        peer_list = {}

        for as_num in as_nums:
            peer_config = self.get_peer_config(as_num)
            if peer_config:
                peer_list[str(as_num)] = peer_config

        return peer_list

    def get_peers_asn(self):
        """
        Retrieve a list of all AS numbers from the peering_links table.

        Returns:
            list[int]: A list of integers representing the AS numbers of all peers.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT as_num FROM peering_links;")
        results = cursor.fetchall()
        return [row['as_num'] for row in results]

    def peer_create(self, as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port, user_link_local=None):
        """
        Insert a new peer into the database.

        Parameters:
            as_num (int): The AS number of the peer.
            wg_pub_key (str): The WireGuard public key of the peer.
            wg_endpoint_addr (str): The WireGuard endpoint address of the peer.
            wg_endpoint_port (int): The WireGuard endpoint port of the peer.
            user_link_local (str, optional): The user's custom link-local address.

        Returns:
            bool: True if the peer was successfully inserted, False otherwise.
        """

        # From https://stackoverflow.com/a/907300/1908136
        # We get the first available id, and use a transaction to avoid a potential race conditions
        # The reason is to allow id re-use, the id field must not exceed 65535 (16 bit integer),
        # because it is used to calculate a part of the peering links link-local IPv6
        # It should be enough for a few years given the number of Dn42 participants
        query = """
        WITH unused_id AS (
            SELECT  id
            FROM    (
                    SELECT  1 AS id
                    ) q1
            WHERE   NOT EXISTS
                    (
                    SELECT  1
                    FROM    peering_links
                    WHERE   id = 1
                    )
            UNION ALL
            SELECT  *
            FROM    (
                    SELECT  id + 1
                    FROM    peering_links t
                    WHERE   NOT EXISTS
                            (
                            SELECT  1
                            FROM    peering_links ti
                            WHERE   ti.id = t.id + 1
                            )
                    ORDER BY
                            id
                    LIMIT 1
                    ) q2
            ORDER BY
                    id
            LIMIT 1
        )
        INSERT INTO peering_links (
                                    id,
                                    as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port, user_link_local
                                  )
        VALUES (
                (SELECT id FROM unused_id),
                ?, ?, ?, ?, ?
               );
        """
        try:
            self.connection.execute('BEGIN TRANSACTION')
            self.connection.execute(query, (as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port, user_link_local))
            self.connection.execute('COMMIT')
        except sqlite3.IntegrityError:
            self.connection.execute('ROLLBACK')
            logging.exception(f"[{threading.get_ident()}][DatabaseManager] Error inserting peer")
            return False
        return True

    def peer_remove(self, as_num):
        """
        Remove a peer from the database by AS number.

        Parameters:
            as_num (int): The AS number of the peer to remove.

        Returns:
            bool: True if the peer was successfully removed, False otherwise.
        """
        query = "DELETE FROM peering_links WHERE as_num = ?"
        try:
            with self.connection:
                self.connection.execute(query, (as_num,))
                return True
        except sqlite3.Error:
            logging.exception(f"[{threading.get_ident()}][DatabaseManager] Error Removing peer")
            return False
