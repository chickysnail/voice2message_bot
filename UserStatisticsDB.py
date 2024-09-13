import sqlite3

class UserStatisticsDB:
    def __init__(self, db_name):
        self.connection = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        """Create the user statistics table if it doesn't exist."""
        with self.connection:
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS user_statistics (
                    username TEXT PRIMARY KEY,
                    message_count INTEGER DEFAULT 0,
                    total_duration INTEGER DEFAULT 0
                )
            ''')

    def add_user(self, username):
        """Add a new user to the database or initialize stats if not exists."""
        with self.connection:
            self.connection.execute('''
                INSERT OR IGNORE INTO user_statistics (username)
                VALUES (?)
            ''', (username,))

    def update_statistics(self, username, message_duration):
        """Update the message count and total duration for a user."""
        with self.connection:
            self.connection.execute('''
                UPDATE user_statistics
                SET message_count = message_count + 1,
                    total_duration = total_duration + ?
                WHERE username = ?
            ''', (message_duration, username))

    def get_statistics(self, username):
        """Retrieve the statistics for a specific user."""
        with self.connection:
            result = self.connection.execute('''
                SELECT message_count, total_duration
                FROM user_statistics
                WHERE username = ?
            ''', (username,)).fetchone()
            
        return result if result else (0, 0)

    def close(self):
        """Close the database connection."""
        self.connection.close()
