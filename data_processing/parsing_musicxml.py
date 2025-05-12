# This file is part of a MusicXML processing system that parses MusicXML files, extracts relevant data, and stores it in a structured format. The script also includes logging functionality to track the processing status of each file.

# This file contains one function which parses one musicxml file at a time, and returns a JSON object with the parsed data.

import json
import logging
import os
from datetime import datetime

import music21
import numpy as np
import pandas as pd
from music21 import chord, converter, key, meter, note, stream, tempo


def parse_multitrack_score(xml_path, composer=None):
    logger = logging.getLogger(__name__)

    try:
        music21.environment.set("autoDownload", "deny")

        logger.info(f"Starting to parse {xml_path}")
        score = converter.parse(xml_path)
        parts = score.parts if len(score.parts) > 0 else [score]
        parts_data = []

        for part_index, part in enumerate(parts):
            part_name = None
            instrument_objs = part.getInstruments(returnDefault=False, recurse=True)
            if len(instrument_objs) > 0:
                part_name = instrument_objs[0].instrumentName
            if not part_name:
                part_name = f"Part_{part_index + 1}"

            measure_data_list = []
            measures = part.getElementsByClass(stream.Measure)

            for measure in measures:
                measure_num = measure.measureNumber
                tsigs = measure.getElementsByClass(meter.TimeSignature)
                time_signatures = [t.ratioString for t in tsigs] if tsigs else []

                key_signatures = []
                try:
                    local_key = measure.analyze("key")
                    if local_key:
                        key_signatures.append(local_key.name)
                except Exception:
                    pass

                events = []
                for elem in measure.notesAndRests:
                    if isinstance(elem, note.Note):
                        events.append(
                            {
                                "element_type": "note",
                                "pitch": elem.nameWithOctave,
                                "duration": float(elem.quarterLength),
                                "offset_in_measure": float(elem.offset),
                            }
                        )
                    elif isinstance(elem, chord.Chord):
                        chord_notes = [n.nameWithOctave for n in elem.pitches]
                        events.append(
                            {
                                "element_type": "chord",
                                "pitch": chord_notes,
                                "duration": float(elem.quarterLength),
                                "offset_in_measure": float(elem.offset),
                            }
                        )
                    else:
                        events.append(
                            {
                                "element_type": "rest",
                                "pitch": None,
                                "duration": float(elem.quarterLength),
                                "offset_in_measure": float(elem.offset),
                            }
                        )

                measure_data_list.append(
                    {
                        "measure_num": measure_num,
                        "time_signatures": time_signatures,
                        "key_signatures": key_signatures,
                        "events": events,
                    }
                )

            tempos = part.getElementsByClass(tempo.MetronomeMark)
            tempo_value = tempos[0].number if tempos else None

            part_dict = {
                "part_name": part_name,
                "tempo": tempo_value,
                "measure_data": measure_data_list,
            }
            parts_data.append(part_dict)

        file_data = {
            "file_name": os.path.basename(xml_path),
            "composer": composer,
            "parts": parts_data,
        }

        logger.info(f"Successfully parsed {xml_path}")
        return file_data

    except Exception as e:
        logger.exception(f"Error parsing {xml_path}: {e}")
        return None
