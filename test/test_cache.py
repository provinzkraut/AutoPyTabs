import pytest

from auto_pytabs.core import Cache


@pytest.fixture(autouse=True)
def purge_cache():
    Cache.clear_all()
    yield
    Cache.clear_all()


def test_get_not_found() -> None:
    assert Cache.get("foo") is None


def test_get() -> None:
    Cache.cache_dir.mkdir(exist_ok=True)
    Cache.cache_dir.joinpath("foo").write_text("bar")

    assert Cache.get("foo") == "bar"
    assert Cache._cache["foo"] == "bar"


def test_set() -> None:
    Cache.set("foo", "bar")

    assert Cache.get("foo") == "bar"
    assert Cache._cache["foo"] == "bar"
    assert Cache.cache_dir.joinpath("foo").exists()
    assert Cache.cache_dir.joinpath("foo").read_text() == "bar"


def test_clean() -> None:
    Cache.cache_dir.mkdir(exist_ok=True)
    test_file_one = Cache.cache_dir.joinpath("one")
    test_file_two = Cache.cache_dir.joinpath("two")
    test_file_one.write_text("foo")
    test_file_two.write_text("bar")

    Cache.get("two")
    Cache.set("three", "baz")

    Cache.evict_unused()

    assert not test_file_one.exists()
    assert Cache.cache_dir.joinpath("two").exists()
    assert Cache.cache_dir.joinpath("three").exists()
    assert Cache.get("one") is None
    assert "one" not in Cache._cache
