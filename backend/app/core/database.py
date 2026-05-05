"""
File-backed JSON Database (no MongoDB, no Docker required)
===========================================================
Mimics the async Motor API used throughout the codebase so
zero other files need changing.

Data is stored in  backend/data/sessions.json  and
backend/data/iterations.json  so server reloads triggered
by uvicorn --reload  do NOT wipe your sessions.
"""

from __future__ import annotations
import json
from pathlib import Path

# ── Storage directory ────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_DATA_DIR.mkdir(exist_ok=True)
_SESSIONS_FILE   = _DATA_DIR / "sessions.json"
_ITERATIONS_FILE = _DATA_DIR / "iterations.json"


# ── JSON helpers ─────────────────────────────────────────────

def _load_sessions() -> dict[str, dict]:
    if _SESSIONS_FILE.exists():
        try:
            return json.loads(_SESSIONS_FILE.read_text())
        except Exception:
            pass
    return {}


def _load_iterations() -> list[dict]:
    if _ITERATIONS_FILE.exists():
        try:
            return json.loads(_ITERATIONS_FILE.read_text())
        except Exception:
            pass
    return []


def _save_sessions() -> None:
    _SESSIONS_FILE.write_text(json.dumps(_sessions, default=str, indent=2))


def _save_iterations() -> None:
    _ITERATIONS_FILE.write_text(json.dumps(_iterations, default=str, indent=2))


# ── Live tables (loaded from disk at import time) ────────────
_sessions: dict[str, dict] = _load_sessions()
_iterations: list[dict]    = _load_iterations()


# ── Minimal async collection wrappers ────────────────────────

class _SessionsCollection:
    """Wraps the sessions dict with an async Motor-compatible API."""

    async def insert_one(self, doc: dict) -> None:
        _sessions[doc["session_id"]] = doc
        _save_sessions()

    async def update_one(self, filter_: dict, update: dict) -> None:
        sid = filter_.get("session_id")
        if sid and sid in _sessions:
            _sessions[sid].update(update.get("$set", {}))
            _save_sessions()

    async def delete_one(self, filter_: dict) -> "_DeleteResult":
        sid = filter_.get("session_id")
        if sid and sid in _sessions:
            del _sessions[sid]
            _save_sessions()
            return _DeleteResult(1)
        return _DeleteResult(0)

    async def find_one(self, filter_: dict) -> dict | None:
        sid = filter_.get("session_id")
        if sid:
            return _sessions.get(sid)
        for doc in _sessions.values():
            if all(doc.get(k) == v for k, v in filter_.items()):
                return doc
        return None

    def find(self, filter_: dict = {}, projection: dict = {}) -> "_Cursor":
        docs = list(_sessions.values())
        if filter_:
            docs = [d for d in docs if all(d.get(k) == v for k, v in filter_.items())]
        return _Cursor(docs)

    async def create_index(self, *args, **kwargs) -> None:
        pass


class _IterationsCollection:
    """Wraps the iterations list with an async Motor-compatible API."""

    async def insert_one(self, doc: dict) -> None:
        _iterations.append(doc)
        _save_iterations()

    async def update_one(self, filter_: dict, update: dict) -> None:
        for doc in _iterations:
            if all(doc.get(k) == v for k, v in filter_.items()):
                doc.update(update.get("$set", {}))
                _save_iterations()
                break

    async def delete_many(self, filter_: dict) -> None:
        to_remove = [
            d for d in _iterations
            if all(d.get(k) == v for k, v in filter_.items())
        ]
        for d in to_remove:
            _iterations.remove(d)
        if to_remove:
            _save_iterations()

    async def find_one(self, filter_: dict) -> dict | None:
        for doc in _iterations:
            if all(doc.get(k) == v for k, v in filter_.items()):
                return doc
        return None

    def find(self, filter_: dict = {}, projection: dict = {}) -> "_Cursor":
        docs = list(_iterations)
        if filter_:
            docs = [d for d in docs if all(d.get(k) == v for k, v in filter_.items())]
        return _Cursor(docs)

    async def create_index(self, *args, **kwargs) -> None:
        pass


class _Cursor:
    def __init__(self, docs: list[dict]):
        self._docs    = docs
        self._sort_key: str | None = None
        self._sort_dir = 1
        self._skip_n   = 0
        self._limit_n  = 0

    def sort(self, key: str | list, direction: int = 1) -> "_Cursor":
        if isinstance(key, list):
            self._sort_key = key[0][0]
            self._sort_dir = key[0][1]
        else:
            self._sort_key = key
            self._sort_dir = direction
        return self

    def skip(self, n: int) -> "_Cursor":
        self._skip_n = n
        return self

    def limit(self, n: int) -> "_Cursor":
        self._limit_n = n
        return self

    def _results(self) -> list[dict]:
        docs = list(self._docs)
        if self._sort_key:
            docs = sorted(
                docs,
                key=lambda d: str(d.get(self._sort_key, "")),
                reverse=(self._sort_dir == -1),
            )
        if self._skip_n:
            docs = docs[self._skip_n:]
        if self._limit_n:
            docs = docs[:self._limit_n]
        return docs

    def __aiter__(self):
        self._iter = iter(self._results())
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class _DeleteResult:
    def __init__(self, count: int):
        self.deleted_count = count


class _DB:
    @property
    def sessions(self) -> _SessionsCollection:
        return _SessionsCollection()

    @property
    def iterations(self) -> _IterationsCollection:
        return _IterationsCollection()


_db_instance = _DB()


async def connect_db() -> None:
    print(f"[DB] File-backed store ready → {_DATA_DIR}")
    print(f"[DB] Loaded {len(_sessions)} sessions, {len(_iterations)} iterations")


async def disconnect_db() -> None:
    print("[DB] All data saved to disk")


def get_db() -> _DB:
    return _db_instance
