# awepatch

[English](https://github.com/fanck0605/awepatch/blob/main/README.md) | [中文](https://github.com/fanck0605/awepatch/blob/main/README_zh.md)

**Awesome Patch** - A Python library for runtime function patching using AST manipulation.

[![Build Status](https://github.com/fanck0605/awepatch/workflows/Build/badge.svg)](https://github.com/fanck0605/awepatch/actions/workflows/build.yml)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/fanck0605/awepatch)](https://github.com/fanck0605/awepatch/blob/main/LICENSE)

## Overview

`awepatch` is a powerful Python library that allows you to dynamically patch source code at runtime by manipulating their Abstract Syntax Tree (AST). Unlike traditional monkey patching, `awepatch` modifies the actual code object of functions, providing a cleaner and more maintainable approach to runtime code modification.

## Features

- 🔧 **Runtime Function Patching**: Modify function behavior without changing source code
- 🎯 **AST-Based Manipulation**: Clean and precise code modifications using AST
- 🔄 **Automatic Restoration**: Context manager support for temporary patches
- 🎭 **Multiple Patch Modes**: Insert code before, after, or replace existing statements
- 🧩 **Pattern Matching**: Use string, regex, or tuple patterns to locate code to patch
- 🎯 **Nested Matching**: Target nested code blocks with tuple pattern syntax
- 🔗 **Decorator Support**: Works with decorated functions, class methods, and static methods
- ⚡ **Type-Safe**: Full type hints support with strict type checking

## Installation

```bash
pip install awepatch
```

Or using `uv`:

```bash
uv pip install awepatch
```

## Quick Start

### Function Patching

```python
import re

from awepatch import FunctionPatcher


def calculate(x: int, y: int) -> int:
    x = x + 10
    y = y * 2
    result = x + y
    return result


patcher = FunctionPatcher()
patcher.add_patch(
    calculate,
    target="x = x + 10",
    content="print(f'processing: {x=}')",
    mode="before",
)
patcher.add_patch(
    calculate,
    target="y = y * 2",
    content="y = y * 3",
    mode="replace",
)
patcher.add_patch(
    calculate,
    target=re.compile(r"result = x \+ y"),
    content="print(f'result: {result}')",
    mode="after",
)
with patcher:
    print(calculate(5, 10))

# Output:
# processing: x=5
# result: 45
# 45
```

### Module Patching

```python
# foo.py
from dataclasses import dataclass

@dataclass(slots=True)
class User:
    name: str
    age: int

def greet(user: User) -> str:
    if hasattr(user, "gender"):
        return f"Hello, {user.name}! You are {user.age} years old. Your gender is {user.gender}."
    else:
        return f"Hello, {user.name}! You are {user.age} years old."

# example.py
from awepatch.module import ModulePatcher

patcher = ModulePatcher()
patcher.add_patch(
    "foo",
    target=(
        "class User:",
        "age: int",
    ),
    content=""" 
gender: str = "unspecified"
""",
    mode="after",
)
with patcher:
    import foo
    user = foo.User(name="Bob", age=25)
    print(foo.greet(user))

# Output: Hello, Bob! You are 25 years old. Your gender is unspecified.
```

### Nested Pattern Matching

For complex nested structures, you can use tuple patterns or lineno offsets to match nested AST nodes:

```python
from awepatch import FunctionPatcher
from awepatch.utils import Ident


def nested_function(x: int) -> int:
    if x > 0:
        x = x * 2
    x = x * 2
    return x


# Match nested statement inside if block
with FunctionPatcher().add_patch(
    nested_function,
    target=("if x > 0:", "x = x * 2"),
    content="x = x * 3",
    mode="replace",
):
    print(nested_function(5))  # Output: 30


# Or match by line number offset
with FunctionPatcher().add_patch(
    nested_function,
    target=Ident("x = x * 2", lineno="+2"),
    content="x = x * 3",
    mode="replace",
):
    print(nested_function(5))  # Output: 30
```

## Advanced Usage

### Patch for multi-process applications

For applications that spawn multiple processes, you must use `ModulePatcher` to ensure that patches are applied in each child process.

Use `.pth` file to auto-apply patches on module import in each process may be a good choice.

```python
# loader.py
patcher = ModulePatcher()
patcher.add_patch(
    "foo",
    target=(
        "class User:",
        "age: int",
    ),
    content 
)
patcher.apply()

# xxx-awepatch.pth
# xxx-awepatch.pth must be placed in site-packages directory
import loader
```

See Also:

<https://github.com/tox-dev/pre-commit-uv/blob/main/src/pre_commit_uv_patch.pth>
<https://github.com/pypa/setuptools/blob/main/setup.py#L12>
<https://github.com/jawah/urllib3.future/blob/main/urllib3_future.pth>

## Use Cases

- **Testing**: Mock function behavior without complex mocking frameworks
- **Debugging**: Inject logging or debugging code at runtime
- **Hot-patching**: Apply fixes or modifications without restarting applications
- **Experimentation**: Test code changes quickly without modifying source files
- **Instrumentation**: Add monitoring or profiling code dynamically

## Limitations

- Lambda functions cannot be patched (they lack proper source code information)
- Functions must have accessible source code via `inspect.getsourcelines()`
- Pattern matching must uniquely identify target statement(s) in the function
- Only single function definitions are supported in the AST
- Conflicting patches (e.g., combining 'replace' with 'before'/'after' on same target) are not allowed

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/fanck0605/awepatch.git
cd awepatch

# Install development dependencies
uv sync
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=awepatch --cov-report=html

# Run specific test file
pytest tests/test_patch_callable.py
```

### Code Quality

```bash
# Format code
ruff format

# Lint code
ruff check

# Fix auto-fixable issues
ruff check --fix
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/fanck0605/awepatch/blob/main/LICENSE) file for details.

## Author

**Chuck Fan** - [fanck0605@qq.com](mailto:fanck0605@qq.com)

## Acknowledgments

- Inspired by the need for cleaner runtime code modification in Python
- Built with modern Python tooling and best practices

---

**Note**: This library modifies function code objects at runtime. Use with caution in production environments and always test thoroughly.
