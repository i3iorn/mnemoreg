import threading

import pytest

from mnemoreg import AlreadyRegisteredError, NotRegisteredError, Registry

pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnhandledThreadExceptionWarning"
)


def _writer(reg: Registry, start: int, end: int):
    for i in range(start, end):
        key = f"k{i}"
        reg[key] = i


def _reader(reg: Registry, start: int, end: int, results: list):
    for i in range(start, end):
        key = f"k{i}"
        try:
            val = reg.get(key, None)
            if val is not None:
                results.append(val)
        except Exception as e:
            results.append(str(e))


def _deleter(reg: Registry):
    for i in range(0, 100, 2):
        try:
            del reg[f"k{i}"]
        except NotRegisteredError:
            pass


def _getter(reg: Registry, results: list):
    for i in range(100):
        try:
            val = reg.get(f"k{i}")
            results.append(val)
        except NotRegisteredError:
            results.append(None)


def _make_and_register_func(reg: Registry, n: int):
    @reg.register(f"f{n}")
    def f(x):
        return x + n

    return f


def _bulk_writer(reg: Registry, start: int, end: int):
    with reg.bulk() as r:
        for i in range(start, end):
            key = f"k{i}"
            if key not in r:
                r[key] = i
            else:
                try:
                    r[key] = i
                except AlreadyRegisteredError:
                    pass


def _mutator(reg: Registry):
    for i in range(50, 100):
        reg[f"k{i}"] = i


def _snapper(reg: Registry, out_list: list):
    out_list.append(reg.snapshot())


def test_concurrent_set_and_get():
    r = Registry[str, int]()

    write_threads = [
        threading.Thread(target=_writer, args=(r, i * 10, (i + 1) * 10))
        for i in range(5)
    ]
    read_results = []
    read_threads = [
        threading.Thread(target=_reader, args=(r, 0, 50, read_results))
        for _ in range(5)
    ]

    # Start writers
    for t in write_threads:
        t.start()
    # Start readers concurrently
    for t in read_threads:
        t.start()

    for t in write_threads + read_threads:
        t.join()

    # All keys should exist
    for i in range(50):
        key = f"k{i}"
        assert key in r
        assert r[key] == i
    # Reader results contain only valid values
    for val in read_results:
        assert isinstance(val, int)


def test_concurrent_deletion_and_access():
    r = Registry[str, int]()
    for i in range(100):
        r[f"k{i}"] = i

    threads = []
    results = []

    for _ in range(5):
        threads.append(threading.Thread(target=_deleter, args=(r,)))
        threads.append(threading.Thread(target=_getter, args=(r, results)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Check all remaining keys are odd
    for i in range(0, 100, 2):
        assert f"k{i}" not in r
    for i in range(1, 100, 2):
        assert f"k{i}" in r
        assert r[f"k{i}"] == i


def test_concurrent_register_decorator():
    r = Registry[str, int]()

    threads = [
        threading.Thread(
            target=_make_and_register_func,
            args=(
                r,
                i,
            ),
        )
        for i in range(20)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All registered functions must work
    for i in range(20):
        f = r[f"f{i}"]
        assert f(10) == 10 + i


def test_bulk_context_under_concurrency():
    r = Registry[str, int]()

    threads = [
        threading.Thread(target=_bulk_writer, args=(r, i * 10, (i + 1) * 10))
        for i in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All keys should exist
    for i in range(100):
        key = f"k{i}"
        assert key in r
        assert isinstance(r[key], int)


def test_snapshot_under_concurrent_modification():
    r = Registry[str, int]()

    for i in range(50):
        r[f"k{i}"] = i

    snapshot_results = []

    threads = []
    for _ in range(5):
        threads.append(threading.Thread(target=_mutator, args=(r,)))
        threads.append(threading.Thread(target=_snapper, args=(r, snapshot_results)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All snapshots should be subsets of final state
    final_keys = set(r)
    for snap in snapshot_results:
        assert set(snap.keys()).issubset(final_keys)
