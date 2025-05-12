# Music XML Processing Pipeline
#
# This script coordinates the complete processing workflow:
# 1. Parse MusicXML files and backup originals
# 2. Apply windowing to the JSON files
# 3. Normalize the windowed data


from backup_and_rename import process_musicxml_files, setup_logging
from normalizer import normalize_windows
from windowser import make_windows

if __name__ == "__main__":
    setup_logging()
    print("=== Starting MusicXML Parsing ===")
    process_musicxml_files()
    print("=== MusicXML Parsing Completed ===")
    make_windows()
    print("=== Windowing Completed ===")
    normalize_windows()
    print("=== Normalization Completed ===")
    print("=== MusicXML Processing Pipeline Completed ===")
