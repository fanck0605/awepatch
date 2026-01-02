# awepatch

**Awesome Patch** - A Python library for runtime function patching using AST manipulation.

[![Build Status](https://github.com/fanck0605/awepatch/workflows/Build/badge.svg)](https://github.com/fanck0605/awepatch/actions/workflows/build.yml)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/fanck0605/awepatch)](https://github.com/fanck0605/awepatch/blob/main/LICENSE)

## Overview

`awepatch` is a powerful Python library that allows you to dynamically patch callable objects at runtime by manipulating their Abstract Syntax Tree (AST). Unlike traditional monkey patching, `awepatch` modifies the actual code object of functions, providing a cleaner and more maintainable approach to runtime code modification.

## Features

- 🔧 **Runtime Function Patching**: Modify function behavior without changing source code
- 🎯 **AST-Based Manipulation**: Clean and precise code modifications using AST
- 🔄 **Automatic Restoration**: Context manager support for temporary patches
- 🎭 **Multiple Patch Modes**: Insert code before, after, or replace existing statements
- 📦 **Batch Patching**: Apply multiple patches to a function in a single call
- 🧩 **Pattern Matching**: Use string, regex, or tuple patterns to locate code to patch
- 🎯 **Nested Matching**: Target nested code blocks with tuple pattern syntax
- 🔄 **Manual Control**: Apply and restore patches manually with `CallablePatcher`
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

### Basic Function Patching

```python
from awepatch import patch_callable, Patch

def greet(name: str) -> str:
    message = f"Hello, {name}!"
    return message

# Temporarily patch the function
with patch_callable(
    greet,
    Patch('message = f"Hello, {name}!"', 'message = f"Hi there, {name}!"', "replace")
):
    print(greet("World"))  # Output: Hi there, World!

# Function is automatically restored after context
print(greet("World"))  # Output: Hello, World!
```

### Patch Modes

`awepatch` supports three different patching modes:

#### Replace Mode

Replace existing code with new code:

```python
from awepatch import patch_callable, Patch

def calculate(x: int) -> int:
    x = x * 2
    return x

with patch_callable(calculate, Patch("x = x * 2", "x = x * 3", "replace")):
    print(calculate(5))  # Output: 15
```

#### Before Mode

Insert code before the matched statement:

```python
from awepatch import patch_callable, Patch

def process() -> list[int]:
    items: list[int] = []
    items.append(3)
    return items

with patch_callable(process, Patch("items.append(3)", "items.append(1)", "before")):
    print(process())  # Output: [1, 3]
```

#### After Mode

Insert code after the matched statement:

```python
from awepatch import patch_callable, Patch

def process() -> list[int]:
    items: list[int] = []
    items.append(3)
    return items

with patch_callable(process, Patch("items.append(3)", "items.append(5)", "after")):
    print(process())  # Output: [3, 5]
```

### Patching Methods

#### Instance Methods

```python
from awepatch import patch_callable, Patch

class Calculator:
    def add(self, x: int, y: int) -> int:
        result = x + y
        return result

calc = Calculator()
with patch_callable(calc.add, Patch("result = x + y", "result = x + y + 1", "replace")):
    print(calc.add(2, 3))  # Output: 6
```

#### Class Methods

```python
from awepatch import patch_callable, Patch

class MathUtils:
    @classmethod
    def multiply(cls, x: int, y: int) -> int:
        result = x * y
        return result

with patch_callable(MathUtils.multiply, Patch("result = x * y", "result = x * y * 2", "replace")):
    print(MathUtils.multiply(3, 4))  # Output: 24
```

#### Static Methods

```python
from awepatch import patch_callable, Patch

class Helper:
    @staticmethod
    def format_name(name: str) -> str:
        result = name.upper()
        return result

with patch_callable(Helper.format_name, Patch("result = name.upper()", "result = name.lower()", "replace")):
    print(Helper.format_name("HELLO"))  # Output: hello
```

### Pattern Matching

You can use both string literals and regular expressions for pattern matching:

```python
import re
from awepatch import patch_callable, Patch

def process_data(value: int) -> int:
    value = value + 10
    return value

# Using string pattern
with patch_callable(process_data, Patch("value = value + 10", "value = value + 20", "replace")):
    print(process_data(5))  # Output: 25

# Using regex pattern
with patch_callable(process_data, Patch(re.compile(r"value = value \+ \d+"), "value = value + 30", "replace")):
    print(process_data(5))  # Output: 35
```

#### Nested Pattern Matching

For complex nested structures, you can use tuple patterns to match nested AST nodes:

```python
from awepatch import patch_callable, Patch

def nested_function(x: int) -> int:
    if x > 0:
        x = x * 2
    return x

# Match nested statement inside if block
with patch_callable(
    nested_function,
    Patch(("if x > 0:", "x = x * 2"), "x = x * 3", "replace")
):
    print(nested_function(5))  # Output: 15
```

### Advanced Usage: AST Statements

For more complex modifications, you can provide AST statements directly:

```python
import ast
from awepatch import patch_callable, Patch

def complex_function(x: int) -> int:
    x = x * 2
    return x

# Parse replacement code as AST
new_statements = ast.parse("x = x * 5").body

with patch_callable(complex_function, Patch("x = x * 2", new_statements, "replace")):
    print(complex_function(3))  # Output: 15
```

### Multiple Patches

Apply multiple patches to a function in a single call:

```python
from awepatch import patch_callable, Patch

def calculate(x: int, y: int) -> int:
    x = x + 10
    y = y * 2
    result = x + y
    return result

# Apply multiple patches at once
with patch_callable(
    calculate,
    [
        Patch("x = x + 10", "print('processing x')", "before"),
        Patch("y = y * 2", "y = y * 3", "replace"),
        Patch("result = x + y", "print(f'result: {result}')", "after"),
    ]
):
    print(calculate(5, 10))
    # Output:
    # processing x
    # result: 45
    # 45

# You can also apply multiple patches to the same line (before/after modes)
def process(x: int) -> int:
    x = x + 10
    return x

with patch_callable(
    process,
    [
        Patch("x = x + 10", "print('before')", "before"),
        Patch("x = x + 10", "print('after')", "after"),
    ]
):
    result = process(5)
    # Output:
    # before
    # after
```

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

## API Reference

### `Patch`

```python
class Patch(NamedTuple):
    """A single patch operation.
    
    Attributes:
        trgt: The pattern(s) to search for in the source code.
              Can be a string, regex pattern, or tuple of patterns for nested matching.
        repl: The replacement code (string) or AST statements (list).
        mode: The mode of patching (before/after/replace), defaults to "before".
    """
    trgt: str | re.Pattern[str] | tuple[str | re.Pattern[str], ...]
    repl: str | Sequence[ast.stmt]
    mode: Literal["before", "after", "replace"] = "before"
```

### `patch_callable`

```python
def patch_callable(
    func: Callable[..., Any],
    /,
    patch: Patch | list[Patch],
) -> CallablePatcher:
    """
    Create a patcher for a callable's code object using AST manipulation.
    
    Can be used as a context manager or by calling apply()/restore() manually.

    Args:
        func: The function to patch.
        patch: A single Patch or list of Patch objects for applying multiple patches.

    Returns:
        CallablePatcher: A patcher object that can be used as a context manager
                        or manually controlled with apply() and restore().

    Raises:
        TypeError: If func is not callable or is a lambda function.
        ValueError: If pattern is not found, matches multiple locations, or patches conflict.
    """
```

### `CallablePatcher`

```python
class CallablePatcher:
    """A patcher object for managing function patches."""
    
    def apply(self) -> Callable[..., Any]:
        """Apply the patches to the function and return it."""
    
    def restore(self) -> None:
        """Restore the original function."""
    
    def __enter__(self) -> Callable[..., Any]:
        """Context manager entry - applies patches."""
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Context manager exit - restores original function."""
```

### Using CallablePatcher

```python
from awepatch import patch_callable, Patch

def my_function(x: int) -> int:
    return x + 1

# Create a patcher
patcher = patch_callable(my_function, Patch("return x + 1", "return x + 2", "replace"))

# Apply manually
patcher.apply()
print(my_function(3))  # Output: 5

# Restore manually
patcher.restore()
print(my_function(3))  # Output: 4

# Or use as context manager
with patcher:
    print(my_function(3))  # Output: 5
print(my_function(3))  # Output: 4
```

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
