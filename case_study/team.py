"""Four editable team profiles, persisted locally in SQLite."""

from datetime import datetime, timezone
from contextlib import closing
import io
import os
from pathlib import Path
import sqlite3
import warnings

from PIL import Image, ImageOps

from .config import TEAM_DATABASE


def database_path():
    return Path(os.environ.get("PHISHERIES_TEAM_DB", TEAM_DATABASE))


def connect(path=None):
    path = Path(path) if path else database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS team (
        id INTEGER PRIMARY KEY CHECK (id BETWEEN 1 AND 4),
        name TEXT NOT NULL DEFAULT '', register_number TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT '', photo BLOB, updated_at TEXT
    )""")
    connection.executemany("INSERT OR IGNORE INTO team(id) VALUES (?)", [(i,) for i in range(1, 5)])
    connection.commit()
    return connection


def members(path=None):
    with closing(connect(path)) as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM team ORDER BY id")]


def prepare_photo(blob):
    if not blob or len(blob) > 3 * 1024 * 1024:
        raise ValueError("Choose a PNG or JPEG photo smaller than 3 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(blob)) as original:
                if original.format not in {"PNG", "JPEG"} or original.width * original.height > 12_000_000:
                    raise ValueError("Use a PNG or JPEG of at most 12 megapixels.")
                image = ImageOps.exif_transpose(original).convert("RGB")
                image.thumbnail((720, 900))
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=88)
                return output.getvalue()
    except (OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("The uploaded file could not be read as a valid photo.") from error


def save_member(member_id, name, register_number="", role="", photo=None, remove_photo=False, path=None):
    if member_id not in range(1, 5):
        raise ValueError("There are exactly four team-member sections.")
    values = [str(name).strip(), str(register_number).strip(), str(role).strip()]
    if any(len(value) > limit for value, limit in zip(values, [100, 64, 100])):
        raise ValueError("Keep names and roles within 100 characters, and register numbers within 64.")
    prepared = prepare_photo(photo) if photo is not None and not remove_photo else None
    with closing(connect(path)) as connection:
        existing = connection.execute("SELECT photo FROM team WHERE id=?", (member_id,)).fetchone()[0]
        stored_photo = None if remove_photo else prepared if photo is not None else existing
        connection.execute("UPDATE team SET name=?, register_number=?, role=?, photo=?, updated_at=? WHERE id=?",
                           (*values, stored_photo, datetime.now(timezone.utc).isoformat(), member_id))
        connection.commit()
    return next(member for member in members(path) if member["id"] == member_id)
