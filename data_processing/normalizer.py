import json
import logging
import os
from pathlib import Path

import music21
import numpy as np

logger = logging.getLogger(__name__)

# Define the directories but change them to yours!
BASE_DIR = Path("/home/leahm/MusicXML/NeurAllegro/musicxml_files")
TEMP_WINDOWS_DIR = BASE_DIR / "temporary_windows"
NORMALIZED_WINDOWS_DIR = BASE_DIR / "normalized_windows"


def pitch_to_midi(pitch_str):
    # Convert 'C4' etc. to a MIDI number.
    try:
        n = music21.note.Note(pitch_str)
        return n.pitch.midi
    except:
        return None


def normalize_window(
    window, pitch_min=21, pitch_max=108, max_events=3000, unknown_id=0
):
    """
    Convert a single window dict into a fixed-size numeric representation.
    1. Flatten all parts' measure_data -> (measure_num, offset, part_name, pitch, duration)
    2. Sort by measure_num, then offset
    3. Map pitch to integer or zero if unknown
    4. Truncate or pad to max_events
    5. Return a numpy array with shape [max_events, feature_dim]
    """
    flattened_events = []
    for part_idx, part in enumerate(window["parts"]):
        part_name = part["part_name"]
        part_id = part_idx
        for measure in part["measure_data"]:
            m_num = measure["measure_num"]
            for ev in measure["events"]:
                offset = ev["offset_in_measure"]
                dur = ev["duration"]
                if ev["element_type"] == "chord":
                    for chord_pitch in ev["pitch"]:
                        flattened_events.append(
                            (m_num, offset, part_id, chord_pitch, dur)
                        )
                else:
                    # note or rest
                    pitch_val = ev["pitch"]  # like "C4" or None (for rest)
                    flattened_events.append((m_num, offset, part_id, pitch_val, dur))
    flattened_events.sort(key=lambda x: (x[0], x[1]))

    numeric_events = []
    for m_num, offset, part_id, pitch_str, dur in flattened_events:
        if pitch_str is None:
            pitch_idx = unknown_id
        else:
            midi_num = pitch_to_midi(pitch_str)
            if midi_num is None or midi_num < pitch_min or midi_num > pitch_max:
                pitch_idx = unknown_id
            else:
                pitch_idx = midi_num - pitch_min + 1
        duration_val = float(dur)
        numeric_events.append(
            (m_num, offset, float(part_id), float(pitch_idx), duration_val)
        )
    feature_dim = 5
    output_array = np.zeros((max_events, feature_dim), dtype=np.float32)
    # Truncate if too long but I hope that doesn't happen
    truncated_events = numeric_events[:max_events]

    for i, evt in enumerate(truncated_events):
        output_array[i, :] = np.array(evt, dtype=np.float32)
    return output_array


def ensure_directories_exist():
    NORMALIZED_WINDOWS_DIR.mkdir(exist_ok=True)
    logger.info(
        f"Ensured normalized_windows directory exists: {NORMALIZED_WINDOWS_DIR}"
    )


def process_window_file(window_file):
    """
    Process a single window file:
    1. Load the JSON
    2. Normalize it
    3. Save as numpy array
    4. Delete the original JSON file

    Returns True if successful, False otherwise
    """
    window_filename = window_file.name
    base_filename = window_file.stem

    try:
        with open(window_file, "r") as f:
            window_data = json.load(f)

        normalized_data = normalize_window(window_data)
        numpy_file = NORMALIZED_WINDOWS_DIR / f"{base_filename}.npy"
        np.save(numpy_file, normalized_data)
        window_file.unlink()

        logger.info(f"Successfully normalized {window_filename}")
        return True

    except Exception as e:
        logger.error(f"Error normalizing {window_filename}: {str(e)}")
        return False


def normalize_windows():
    """
    Main function to normalize all windows in the temporary_windows folder:
    1. Ensure the normalized_windows directory exists
    2. Process each window file
    3. Handle failures by keeping those files
    """
    logger.info("Starting window normalization")

    ensure_directories_exist()

    if not TEMP_WINDOWS_DIR.exists():
        logger.error(f"Temporary windows directory does not exist: {TEMP_WINDOWS_DIR}")
        return

    window_files = list(TEMP_WINDOWS_DIR.glob("*.json"))

    if not window_files:
        logger.warning(f"No window files found in {TEMP_WINDOWS_DIR}")
        return

    logger.info(f"Found {len(window_files)} window files to normalize")

    success_count = 0
    failure_count = 0

    for window_file in window_files:
        if process_window_file(window_file):
            success_count += 1
        else:
            failure_count += 1

    logger.info(
        f"Normalization complete. Successes: {success_count}, Failures: {failure_count}"
    )

    if failure_count > 0:
        failed_files = list(TEMP_WINDOWS_DIR.glob("*.json"))
        logger.info(
            f"Failed files remain in {TEMP_WINDOWS_DIR}: {[f.name for f in failed_files]}"
        )
