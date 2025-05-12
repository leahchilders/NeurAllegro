import json
import logging
import os
import shutil
from pathlib import Path

# get logger from root logger configured in main
logger = logging.getLogger(__name__)

BASE_DIR = Path(
    "/home/leahm/MusicXML/NeurAllegro/musicxml_files"
)  # Assumes script is run from parent directory containing all folders, and you should change this to your own
PARSED_DIR = BASE_DIR / "parsed"
BACKUP_DIR = BASE_DIR / "parsed_backup"
TEMP_WINDOWS_DIR = BASE_DIR / "temporary_windows"


def make_window(score_data, window_size=10, overlap=5):
    logger.info("Creating windows with size %d and overlap %d", window_size, overlap)

    min_measure = None
    max_measure = None
    for part in score_data["parts"]:
        for measure_dict in part["measure_data"]:
            measure_num = measure_dict["measure_num"]
            if min_measure is None or measure_num < min_measure:
                min_measure = measure_num
            if max_measure is None or measure_num > max_measure:
                max_measure = measure_num
    if min_measure is None or max_measure is None:
        return []

    step = window_size - overlap
    windows = []
    start_measure = min_measure
    while True:
        end_measure = start_measure + window_size - 1
        if end_measure > max_measure:
            break

        window_parts = []
        for part in score_data["parts"]:
            window_measure_data = []
            for measure_dict in part["measure_data"]:
                m_num = measure_dict["measure_num"]
                if start_measure <= m_num <= end_measure:
                    window_measure_data.append(measure_dict)
            part_dict = {
                "part_name": part["part_name"],
                "tempo": part["tempo"],
                "measure_data": window_measure_data,
            }
            window_parts.append(part_dict)

        window_record = {
            "original_file_name": score_data["file_name"],
            "composer": score_data["composer"],
            "start_measure": start_measure,
            "end_measure": end_measure,
            "parts": window_parts,
        }
        windows.append(window_record)

        start_measure += step

    return windows


def ensure_directories_exist():
    BACKUP_DIR.mkdir(exist_ok=True)
    TEMP_WINDOWS_DIR.mkdir(exist_ok=True)

    logger.info(f"Ensured directories exist: {BACKUP_DIR}, {TEMP_WINDOWS_DIR}")


def backup_parsed_files():
    logger.info("Starting backup of parsed files")

    if not PARSED_DIR.exists():
        logger.error(f"PARSED directory does not exist: {PARSED_DIR}")
        return False

    composer_dirs = [d for d in PARSED_DIR.iterdir() if d.is_dir()]

    if not composer_dirs:
        logger.warning(f"No composer directories found in {PARSED_DIR}")
        return True

    for composer_dir in composer_dirs:
        composer_name = composer_dir.name
        backup_composer_dir = BACKUP_DIR / composer_name

        backup_composer_dir.mkdir(exist_ok=True)

        json_files = list(composer_dir.glob("*.json"))
        for json_file in json_files:
            backup_path = backup_composer_dir / json_file.name
            shutil.copy2(json_file, backup_path)
            logger.info(f"Backed up {json_file} to {backup_path}")

    logger.info("Backup completed successfully")
    return True


def process_windows():
    logger.info("Starting window processing")

    if not PARSED_DIR.exists():
        logger.error(f"PARSED directory does not exist: {PARSED_DIR}")
        return False

    composer_dirs = [d for d in PARSED_DIR.iterdir() if d.is_dir()]

    if not composer_dirs:
        logger.warning(f"No composer directories found in {PARSED_DIR}")
        return True

    for composer_dir in composer_dirs:
        composer_name = composer_dir.name
        logger.info(f"Processing composer: {composer_name}")

        json_files = list(composer_dir.glob("*.json"))
        for json_file in json_files:
            file_stem = json_file.stem  # such as "Mozart0"

            logger.info(f"Processing file: {json_file}")

            try:
                with open(json_file, "r") as f:
                    score_data = json.load(f)

                if "file_name" not in score_data:
                    score_data["file_name"] = json_file.stem

                windows = make_window(score_data, window_size=10, overlap=5)

                # save each window to a separate file (that's why this doesn't work with the old classifier)
                for i, window in enumerate(windows):
                    # create window filename (such as "Mozart0_0.json")
                    window_filename = f"{file_stem}_{i}.json"
                    window_path = TEMP_WINDOWS_DIR / window_filename

                    with open(window_path, "w") as f:
                        json.dump(window, f)

                    logger.info(f"Saved window {i} to {window_path}")

                json_file.unlink()
                logger.info(f"Deleted original file: {json_file}")

            except Exception as e:
                logger.error(f"Error processing {json_file}: {str(e)}")

    clean_empty_directories()

    logger.info("Window processing completed")
    return True


def clean_empty_directories():
    logger.info("Cleaning up empty directories")

    composer_dirs = [d for d in PARSED_DIR.iterdir() if d.is_dir()]

    for composer_dir in composer_dirs:
        if not any(composer_dir.iterdir()):
            composer_dir.rmdir()
            logger.info(f"Removed empty directory: {composer_dir}")


def make_windows():
    """Main function to orchestrate the entire windowing process."""
    logger.info("Starting window processing pipeline")
    ensure_directories_exist()

    if not backup_parsed_files():
        logger.error("Backup failed, aborting window processing")
        return

    process_windows()

    logger.info("Window processing pipeline completed")
