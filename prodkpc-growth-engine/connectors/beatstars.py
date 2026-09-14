"""
BeatStars connector — manual / CSV, on purpose.

BeatStars has no public API. Rather than ship fragile scraping that breaks (and
risks your account), this module tracks the numbers you enter yourself — either
in the BeatStars page of the app, or by dropping a CSV at data/beatstars.csv
with columns: beat_title,plays,downloads,sales,revenue

If BeatStars ever ships an API, this file is the only thing that changes:
implement collect() to hit it and everything downstream keeps working.
"""
import os
import csv
from .base import Connector
from data import store


class BeatStarsConnector(Connector):
    id = "beatstars"
    name = "BeatStars"
    kind = "manual"

    def is_configured(self):
        return True  # always available — it's manual

    def csv_path(self, db_path):
        return os.path.join(os.path.dirname(db_path), "beatstars.csv")

    def collect(self, db_path):
        path = self.csv_path(db_path)
        if not os.path.exists(path):
            return {"source": self.id, "ok": True,
                    "msg": "manual module — no CSV found, use the BeatStars page to log numbers"}
        n = 0
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                store.add_beatstars_entry(
                    db_path, row.get("beat_title", ""),
                    int(row.get("plays", 0) or 0), int(row.get("downloads", 0) or 0),
                    int(row.get("sales", 0) or 0), float(row.get("revenue", 0) or 0),
                )
                n += 1
        return {"source": self.id, "ok": True, "msg": f"imported {n} rows from CSV"}
