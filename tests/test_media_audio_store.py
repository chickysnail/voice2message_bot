import os

from src.bot.storage.media_audio_store import MediaAudioStore


def _audio_file(tmp_path: object, name: str = "a.mp3") -> str:
    path = os.path.join(str(tmp_path), name)
    with open(path, "wb") as fh:
        fh.write(b"id3")
    return path


def test_save_and_get(tmp_path: object) -> None:
    store = MediaAudioStore()
    path = _audio_file(tmp_path)
    store.save(1, 10, path, 42)
    audio = store.get(1, 10)
    assert audio is not None
    assert audio.path == path
    assert audio.duration == 42


def test_get_isolates_users_and_messages(tmp_path: object) -> None:
    store = MediaAudioStore()
    store.save(1, 10, _audio_file(tmp_path), None)
    assert store.get(2, 10) is None
    assert store.get(1, 11) is None


def test_expiry_removes_file(tmp_path: object) -> None:
    store = MediaAudioStore(ttl_seconds=0)
    path = _audio_file(tmp_path)
    store.save(1, 10, path, None)
    assert store.get(1, 10) is None
    assert not os.path.exists(path)


def test_get_returns_none_when_file_vanished(tmp_path: object) -> None:
    store = MediaAudioStore()
    path = _audio_file(tmp_path)
    store.save(1, 10, path, None)
    os.remove(path)
    assert store.get(1, 10) is None


def test_discard_removes_file(tmp_path: object) -> None:
    store = MediaAudioStore()
    path = _audio_file(tmp_path)
    store.save(1, 10, path, None)
    store.discard(1, 10)
    assert store.get(1, 10) is None
    assert not os.path.exists(path)
