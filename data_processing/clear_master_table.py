# clears all rows because I had to test this stuff a lot

import logging
import os
import sqlite3
from datetime import datetime

import git


def setup_logging():
    """Configure logging for the script"""
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/clear_master_score_list_{timestamp}.log"

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)

    print(f"Logging to: {log_file}")


def commit_to_github(db_path):
    try:
        repo_path = "/home/leahm/MusicXML/NeurAllegro"
        repo = git.Repo(repo_path)
        relative_path = os.path.relpath(db_path, repo_path)
        logging.info(f"Adding {relative_path} to git staging")
        repo.git.add(relative_path)

        commit_message = f"Clear master_score_list table - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        logging.info(f"Creating commit: {commit_message}")
        repo.git.commit("-m", commit_message)

        logging.info("Pushing to remote repository")
        repo.git.push()

        logging.info("Successfully pushed database to GitHub")
        return True
    except Exception as e:
        logging.error(f"Failed to commit to GitHub: {e}")
        return False


def clear_master_score_list():
    db_path = "score_database.db"
    if not os.path.exists(db_path):
        logging.error(f"Database file {db_path} not found!")
        return False

    try:
        logging.info(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM master_score_list")
        row_count = cursor.fetchone()[0]
        logging.info(f"Current row count in master_score_list: {row_count}")

        logging.info("Deleting all rows from master_score_list table...")
        cursor.execute("DELETE FROM master_score_list")

        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM master_score_list")
        new_count = cursor.fetchone()[0]
        logging.info(f"New row count in master_score_list: {new_count}")

        conn.close()
        logging.info("Database connection closed")

        # Backup to GitHub!!
        if commit_to_github(db_path):
            print("Successfully backed up the cleared database to GitHub!")
        else:
            print(
                "WARNING: Failed to back up database to GitHub. Check logs for details."
            )

        print(f"Successfully cleared {row_count} rows from master_score_list table!")
        return True

    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return False


if __name__ == "__main__":
    setup_logging()
    logging.info("=== Starting master_score_list table clearing script ===")

    # Ask for confirmation since this is a destructive operation
    confirm = input(
        "This will DELETE ALL ROWS from the master_score_list table. Type 'YES' to confirm: "
    )
    if confirm != "YES":
        print("Operation cancelled.")
        logging.info("Operation cancelled by user")
    else:
        clear_master_score_list()

    logging.info("=== Script execution completed ===")
