import pytest

from auto_pytabs.core import Cache


@pytest.fixture()
def cache() -> Cache:
    cache = Cache()
    cache.clear_all()
    yield cache
    cache.clear_all()


def test_get_not_found(cache) -> None:
    assert cache.get("foo") is None


def test_get(cache) -> None:
    cache.cache_dir.mkdir(exist_ok=True)
    cache.cache_dir.joinpath("foo").write_text("bar")
    cache._load()

    assert cache.get("foo") == "bar"
    assert cache._cache["foo"] == "bar"


def test_set(cache) -> None:
    cache.set("foo", "bar")

    assert cache.get("foo") == "bar"
    assert cache._cache["foo"] == "bar"
    assert cache.cache_dir.joinpath("foo").exists()
    assert cache.cache_dir.joinpath("foo").read_text() == "bar"


def test_clean(cache) -> None:
    cache.cache_dir.mkdir(exist_ok=True)
    test_file_one = cache.cache_dir.joinpath("one")
    test_file_two = cache.cache_dir.joinpath("two")
    test_file_one.write_text("foo")
    test_file_two.write_text("bar")
    cache._load()

    cache.get("two")
    cache.set("three", "baz")

    cache.evict_unused()

    assert not test_file_one.exists()
    assert cache.cache_dir.joinpath("two").exists()
    assert cache.cache_dir.joinpath("three").exists()
    assert cache.get("one") is None
    assert "one" not in cache._cache
