# mnemos

mnemos is a tiny thread-safe registry mapping useful for registering
callables and other values by string keys. It's intentionally small and
suitable for embedding in other projects.

Quickstart

```python
from mnemos import Registry

r = Registry[str, int]()
r["one"] = 1
print(r["one"])  # 1

@r.register("plus")
def plus(x):
    return x + 1

print(r["plus"](4))  # 5
```

See `tests/` for more usage examples.

