import pytest
import threading
from mnemos import Registry, AlreadyRegisteredError, NotRegisteredError

import time

def test_concurrent_set_and_get():
    r = Registry[str, int]()

    def writer(start, end):
        for i in range(start, end):
            key = f"k{i}"
            r[key] = i

    def reader(start, end, results):
        for i in range(start, end):
            key = f"k{i}"
            try:
                val = r.get(key, None)
                if val is not None:
                    results.append(val)
            except Exception as e:
                results.append(str(e))

    write_threads = [threading.Thread(target=writer, args=(i*10, (i+1)*10)) for i in range(5)]
    read_results = []
    read_threads = [threading.Thread(target=reader, args=(0, 50, read_results)) for _ in range(5)]

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

    def deleter():
        for i in range(0, 100, 2):
            try:
                del r[f"k{i}"]
            except NotRegisteredError:
                pass

    def getter(results):
        for i in range(100):
            try:
                val = r.get(f"k{i}")
                results.append(val)
            except NotRegisteredError:
                results.append(None)

    threads = []
    results = []

    for _ in range(5):
        threads.append(threading.Thread(target=deleter))
        threads.append(threading.Thread(target=getter, args=(results,)))

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

    def make_func(n):
        @r.register(f"f{n}")
        def f(x):
            return x + n
        return f

    threads = [threading.Thread(target=make_func, args=(i,)) for i in range(20)]
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

    def bulk_writer(start, end):
        with r.bulk() as reg:
            for i in range(start, end):
                key = f"k{i}"
                if key not in reg:
                    reg[key] = i
                else:
                    try:
                        reg[key] = i
                    except AlreadyRegisteredError:
                        pass

    threads = [threading.Thread(target=bulk_writer, args=(i*10, (i+1)*10)) for i in range(10)]
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

    def mutator():
        for i in range(50, 100):
            r[f"k{i}"] = i

    def snapper():
        snapshot_results.append(r.snapshot())

    threads = []
    for _ in range(5):
        threads.append(threading.Thread(target=mutator))
        threads.append(threading.Thread(target=snapper))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All snapshots should be subsets of final state
    final_keys = set(r)
    for snap in snapshot_results:
        assert set(snap.keys()).issubset(final_keys)
