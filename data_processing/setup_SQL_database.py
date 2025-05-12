#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path


def setup_database():
    # Set up the SQLite database and create the necessary tables for the MusicXML processing system.
    db_path = "score_database.db"

    # Check if database already exists and warn if it does
    if os.path.exists(db_path):
        print(
            f"Warning: Database {db_path} already exists. Running this script will reset it."
        )
        response = input("Do you want to continue? (y/n): ")
        if response.lower() != "y":
            print("Database setup canceled.")
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the master_score_list table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS master_score_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_title TEXT NOT NULL,
        new_title TEXT,
        composer TEXT NOT NULL,
        index_number INTEGER,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processing_status TEXT DEFAULT 'pending'
    )
    """)

    # Create directory structure
    base_dir = Path("/home/leahm/MusicXML/NeurAllegro/musicxml_files")
    dirs_to_create = [
        base_dir,
        base_dir
        / "need_to_be_processed_test",  # Where unprocessed files will be placed
        base_dir / "original_files",  # backup of original files
        base_dir / "PARSED",  # Where processed JSON files will go
    ]

    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

    conn.commit()
    conn.close()

    print(f"Database setup complete. Created database at {db_path}")
    print("Directory structure created.")
    print("\nNext steps:")
    print("1. Place your MusicXML files in composer-named subdirectories under:")
    print(f"   {dirs_to_create[1]}")
    print("2. Run the main processing script to process the files")


if __name__ == "__main__":
    setup_database()
