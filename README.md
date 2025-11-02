[![CI and Publish](https://github.com/i3iorn/mnemoreg/actions/workflows/publish.yml/badge.svg)](https://github.com/i3iorn/mnemoreg/actions/workflows/publish.yml)
# mnemoreg

mnemoreg is a tiny thread-safe registry mapping useful for registering
callables and other values by string keys. It's intentionally small and
suitable for embedding in other projects. It has no dependencies beyond
the Python standard library.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Implementation Notes](#implementation-notes)
- [License](#license)
- [Contributing](#contributing)
- [Contact](#contact)

## Installation
You can install mnemoreg via pip:

```bash
pip install mnemoreg
```

## Usage

Here is a simple example of how to use mnemoreg:

```python
from mnemoreg import Registry

r = Registry[str, int]()
r["one"] = 1
print(r["one"])  # 1


@r.register("plus")
def plus(x):
    return x + 1


print(r["plus"](4))  # 5
```

You can also skip the explicit register key argument and in that case the
function name will be used as the key:
```python
@r.register()
def multiply(x, y):
    return x * y
print(r["multiply"](3, 4))  # 12
```

You can serialize the registry to a dictionary and recreate it later:
```python
data = r.to_dict()
new_r = Registry.from_dict(data)
print(new_r["one"])  # 1
print(new_r["plus"](10))  # 11
```

See `tests/` for more usage examples.

## Implementation Notes
mnemoreg uses a threading lock to ensure thread safety during registry
modifications. The internal storage is a simple dictionary mapping string keys
to values of a generic type. See mnemoreg/core.py for implementation details.

## License
mnemoreg is licensed under the MIT License. See the LICENSE file for details.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request on
GitHub.

## Contact
For questions or suggestions, please open an issue on the GitHub repository.
