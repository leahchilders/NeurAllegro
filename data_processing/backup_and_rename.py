# This file goes through all folders in the need_to_be_processed directory, and for each file, it creates a backup in the original_files directory, and parses the file, adding it to the PARSED directory. It also adds a record to the master_score_list table in the database.

import json
import logging
import multiprocessing
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import git
import joblib
from joblib import Parallel, delayed
from parsing_musicxml import parse_multitrack_score
from tqdm import tqdm


# logging
def setup_logging(log_dir="logs"):
    """
    Set up logging configuration for the entire application.
    Creates a new log file with timestamp for each run.

    Args:
        log_dir: Directory where log files will be stored

    Returns:
        A configured logger instance
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_name = f"musicxml_processing_{timestamp}.log"
    log_file = log_path / log_name

    print(f"Logging to: {log_file}")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.handlers:
        root_logger.handlers.clear()
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return logging.getLogger(__name__)


def process_single_file(file_path, composer_name):
    """Process a single MusicXML file and return the parsed data"""
    logger = logging.getLogger(__name__)
    logger.info(f"Processing file: {file_path}")

    try:
        parsed_data = parse_multitrack_score(file_path, composer=composer_name)
        return parsed_data
    except Exception as e:
        logger.exception(f"Error processing file {file_path}: {e}")
        return None


def commit_and_push_to_github(file_path, commit_message):
    # I did this because I reallllllly didn't want to lose any files ever
    logger = logging.getLogger(__name__)

    try:
        # get the repository path (assuming the script is inside the repository)
        repo_path = "/home/leahm/MusicXML/NeurAllegro"

        repo = git.Repo(repo_path)
        relative_path = os.path.relpath(file_path, repo_path)
        logger.info(f"Adding file {relative_path} to git staging")
        repo.git.add(relative_path)
        logger.info(f"Creating commit: {commit_message}")
        repo.git.commit("-m", commit_message)

        logger.info("Pushing to remote repository")
        repo.git.push()

        logger.info("Successfully pushed database to GitHub")
        return True

    except git.GitCommandError as e:
        logger.error(f"Git command error: {e}")
        return False
    except Exception as e:
        logger.exception(f"Error committing to GitHub: {e}")
        return False


@contextmanager
def tqdm_joblib(total=None, desc="Processing", **kwargs):
    """Context manager to patch joblib to report into tqdm progress bar"""

    class TqdmBatchCompletionCallback(joblib.parallel.BatchCompletionCallBack):
        def __call__(self, *args, **kwargs):
            tqdm_object.update(n=self.batch_size)
            return super().__call__(*args, **kwargs)

    # Create the tqdm progress bar!
    tqdm_object = tqdm(total=total, desc=desc, **kwargs)

    old_batch_callback = joblib.parallel.BatchCompletionCallBack
    joblib.parallel.BatchCompletionCallBack = TqdmBatchCompletionCallback

    try:
        yield tqdm_object
    finally:
        joblib.parallel.BatchCompletionCallBack = old_batch_callback
        tqdm_object.close()


def process_musicxml_files():
    logger = logging.getLogger(__name__)
    logger.info("Starting MusicXML processing script")

    try:
        db_path = "score_database.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        base_dir = Path("/home/leahm/MusicXML/NeurAllegro/musicxml_files")
        need_to_be_processed_dir = base_dir / "need_to_be_processed_test"
        processed_original_files_dir = base_dir / "original_files"
        processed_dir = base_dir / "parsed"

        tasks = []

        # iterate over each composer folder
        for composer_folder in need_to_be_processed_dir.iterdir():
            if composer_folder.is_dir():
                composer_name = composer_folder.name
                logger.info(f"Parsing composer: {composer_name}")

                cursor.execute(
                    "SELECT label FROM composer_indices WHERE composer = ?",
                    (composer_name,),
                )
                result = cursor.fetchone()

                if result is None:
                    # if composer doesn't exist in the table, get the maximum label and increment
                    cursor.execute("SELECT MAX(label) FROM composer_indices")
                    max_label_result = cursor.fetchone()
                    max_label = (
                        max_label_result[0] if max_label_result[0] is not None else -1
                    )
                    new_label = max_label + 1

                    cursor.execute(
                        "INSERT INTO composer_indices (composer, label) VALUES (?, ?)",
                        (composer_name, new_label),
                    )
                    conn.commit()
                    logger.info(
                        f"Added composer {composer_name} to composer_indices with label {new_label}"
                    )
                # iterate over each file in the composer folder.
                for score_file in composer_folder.iterdir():
                    if score_file.is_file() and score_file.suffix.lower() in [
                        ".xml",
                        ".musicxml",
                    ]:
                        original_title = score_file.stem
                        cursor.execute(
                            "INSERT INTO master_score_list (new_title, original_title, composer) VALUES (?, ?, ?)",
                            (None, original_title, composer_name),
                        )
                        record_id = cursor.lastrowid
                        conn.commit()

                        backup_composer_dir = (
                            processed_original_files_dir / composer_name
                        )
                        backup_composer_dir.mkdir(parents=True, exist_ok=True)
                        backup_file_path = backup_composer_dir / score_file.name
                        shutil.copy2(score_file, backup_file_path)
                        logger.info(f"Copied {score_file} to backup {backup_file_path}")

                        tasks.append((str(score_file), composer_name, record_id))

        total_files = len(tasks)
        print(f"Found {total_files} MusicXML files to parse")

        n_jobs = min(multiprocessing.cpu_count(), total_files)
        print(f"Using {n_jobs} cores for parallel processing")

        logger.info(f"Starting parallel processing of {total_files} files")

        file_paths = [t[0] for t in tasks]
        composer_names = [t[1] for t in tasks]

        with tqdm_joblib(total=total_files, desc="Parsing files"):
            processed_results = Parallel(
                n_jobs=n_jobs, backend="multiprocessing", verbose=0
            )(
                delayed(process_single_file)(file_path, composer_name)
                for file_path, composer_name in zip(file_paths, composer_names)
            )

        logger.info("Parallel processing completed")
        print("Parsing attempted. Updating database and saving results...")

        successful_files = 0
        failed_files = set()

        for (file_path, composer_name, record_id), processed_file in zip(
            tasks, processed_results
        ):
            if processed_file is None:
                logger.error(
                    f"Processing failed for {file_path}, removing database record"
                )
                try:
                    cursor.execute(
                        "DELETE FROM master_score_list WHERE rowid = ?", (record_id,)
                    )
                    conn.commit()
                    logger.info(
                        f"Removed database record with ID {record_id} for failed file {file_path}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to remove database record with ID {record_id}: {e}"
                    )

                failed_files.add(file_path)
                continue

            cursor.execute(
                "SELECT MAX(index_number) FROM master_score_list WHERE composer = ? AND index_number IS NOT NULL",
                (composer_name,),
            )
            result = cursor.fetchone()
            max_index = result[0] if result and result[0] is not None else -1
            new_index = max_index + 1
            new_file_name = f"{composer_name}{new_index}.json"
            cursor.execute(
                "UPDATE master_score_list SET new_title = ?, index_number = ? WHERE rowid = ?",
                (new_file_name, new_index, record_id),
            )
            conn.commit()

            processed_composer_dir = processed_dir / composer_name
            processed_composer_dir.mkdir(parents=True, exist_ok=True)
            final_processed_file_path = processed_composer_dir / new_file_name

            with open(final_processed_file_path, "w", encoding="utf-8") as f:
                json.dump(processed_file, f, indent=2)

            logger.info(
                f"Saved processed file for {file_path} to {final_processed_file_path}"
            )

            # Only remove successfully processed files, and keep the failed ones in the original location
            original_file_path = Path(file_path)
            if original_file_path.exists():
                original_file_path.unlink()  # Delete the file
                logger.info(f"Removed original file: {original_file_path}")
            else:
                logger.warning(
                    f"Original file not found for removal: {original_file_path}"
                )

            successful_files += 1

        logger.info(
            f"Failed to parse {len(failed_files)} files. These will remain in their original location."
        )
        print(
            f"Parsed {successful_files} files successfully. Failed to parse {len(failed_files)} files."
        )

        logger.info("Cleaning up the need_to_be_processed directory")
        for root, dirs, files in os.walk(need_to_be_processed_dir, topdown=False):
            root_path = Path(root)

            for file in files:
                file_path = root_path / file
                file_path_str = str(file_path)

                # skip files that failed to parse
                if file_path_str in failed_files:
                    logger.info(f"Keeping file that failed to parse: {file_path}")
                    continue

                is_musicxml = file.lower().endswith((".xml", ".musicxml"))

                # If it's not a musicxml file or if it's a musicxml file that was processed successfully, we remove it
                if not is_musicxml or file_path_str not in failed_files:
                    try:
                        file_path.unlink()
                        logger.info(f"Removed file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove file {file_path}: {e}")

        for root, dirs, files in os.walk(need_to_be_processed_dir, topdown=False):
            root_path = Path(root)

            if root_path == need_to_be_processed_dir:
                continue
            if not any(root_path.iterdir()):
                try:
                    root_path.rmdir()
                    logger.info(f"Removed empty directory: {root_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove directory {root_path}: {e}")
        conn.close()

        if successful_files > 0:
            db_absolute_path = os.path.abspath(db_path)
            commit_message = f"Update database after parsing {successful_files} MusicXML files - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            logger.info(f"Committing database to GitHub with message: {commit_message}")
            if commit_and_push_to_github(db_absolute_path, commit_message):
                print("Successfully backed up database to GitHub!")
            else:
                print(
                    "WARNING: Failed to back up database to GitHub. Check logs for details."
                )

        logger.info("Parsing complete.")
        print("Parsing complete!")

    except Exception as e:
        logger.exception(f"An error occurred during parsing: {e}")
        print(f"An error occurred: {e}")
