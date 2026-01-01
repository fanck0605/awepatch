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
- 🧩 **Pattern Matching**: Use string or regex patterns to locate code to patch
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
from awepatch import patch_callable

def greet(name: str) -> str:
    message = f"Hello, {name}!"
    return message

# Temporarily patch the function
with patch_callable(
    greet,
    pattern='message = f"Hello, {name}!"',
    repl='message = f"Hi there, {name}!"',
    mode="replace"
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
def calculate(x: int) -> int:
    x = x * 2
    return x

with patch_callable(calculate, "x = x * 2", "x = x * 3", mode="replace"):
    print(calculate(5))  # Output: 15
```

#### Before Mode

Insert code before the matched statement:

```python
def process() -> list[int]:
    items: list[int] = []
    items.append(3)
    return items

with patch_callable(process, "items.append(3)", "items.append(1)", mode="before"):
    print(process())  # Output: [1, 3]
```

#### After Mode

Insert code after the matched statement:

```python
def process() -> list[int]:
    items: list[int] = []
    items.append(3)
    return items

with patch_callable(process, "items.append(3)", "items.append(5)", mode="after"):
    print(process())  # Output: [3, 5]
```

### Patching Methods

#### Instance Methods

```python
class Calculator:
    def add(self, x: int, y: int) -> int:
        result = x + y
        return result

calc = Calculator()
with patch_callable(calc.add, "result = x + y", "result = x + y + 1", mode="replace"):
    print(calc.add(2, 3))  # Output: 6
```

#### Class Methods

```python
class MathUtils:
    @classmethod
    def multiply(cls, x: int, y: int) -> int:
        result = x * y
        return result

with patch_callable(MathUtils.multiply, "result = x * y", "result = x * y * 2", mode="replace"):
    print(MathUtils.multiply(3, 4))  # Output: 24
```

#### Static Methods

```python
class Helper:
    @staticmethod
    def format_name(name: str) -> str:
        result = name.upper()
        return result

with patch_callable(Helper.format_name, "result = name.upper()", "result = name.lower()", mode="replace"):
    print(Helper.format_name("HELLO"))  # Output: hello
```

### Pattern Matching

You can use both string literals and regular expressions for pattern matching:

```python
import re

def process_data(value: int) -> int:
    value = value + 10
    return value

# Using string pattern
with patch_callable(process_data, "value = value + 10", "value = value + 20", mode="replace"):
    print(process_data(5))  # Output: 25

# Using regex pattern
with patch_callable(process_data, re.compile(r"value = value \+ \d+"), "value = value + 30", mode="replace"):
    print(process_data(5))  # Output: 35
```

### Advanced Usage: AST Statements

For more complex modifications, you can provide AST statements directly:

```python
import ast
from awepatch import patch_callable

def complex_function(x: int) -> int:
    x = x * 2
    return x

# Create custom AST statements
new_statements = [
    ast.Assign(
        targets=[ast.Name(id='x', ctx=ast.Store())],
        value=ast.BinOp(
            left=ast.Name(id='x', ctx=ast.Load()),
            op=ast.Mult(),
            right=ast.Constant(value=5)
        )
    )
]

with patch_callable(complex_function, "x = x * 2", new_statements, mode="replace"):
    print(complex_function(3))  # Output: 15
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
- Pattern matching must uniquely identify a single statement in the function
- Only single function definitions are supported in the AST

## API Reference

### `patch_callable`

```python
@contextmanager
def patch_callable(
    func: Callable[..., Any],
    pattern: str | re.Pattern[str],
    repl: str | list[ast.stmt],
    *,
    mode: Literal["before", "after", "replace"] = "before",
) -> Iterator[None]:
    """
    Context manager to patch a callable's code object using AST manipulation.

    Args:
        func: The function to patch
        pattern: Pattern to search for in the function's source code
        repl: Replacement code (string) or AST statements
        mode: Patching mode - "before", "after", or "replace"

    Raises:
        TypeError: If func is not callable or is a lambda function
        ValueError: If pattern is not found or matches multiple lines
    """
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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Chuck Fan** - [fanck0605@qq.com](mailto:fanck0605@qq.com)

## Acknowledgments

- Inspired by the need for cleaner runtime code modification in Python
- Built with modern Python tooling and best practices

---

**Note**: This library modifies function code objects at runtime. Use with caution in production environments and always test thoroughly.
