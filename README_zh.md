# awepatch

[English](https://github.com/fanck0605/awepatch/blob/main/README.md) | [中文](https://github.com/fanck0605/awepatch/blob/main/README_zh.md)

**Awesome Patch** - 一个使用 AST 操作进行运行时函数补丁的 Python 库。

[![构建状态](https://github.com/fanck0605/awepatch/workflows/Build/badge.svg)](https://github.com/fanck0605/awepatch/actions/workflows/build.yml)
[![Python 版本](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![许可证](https://img.shields.io/github/license/fanck0605/awepatch)](https://github.com/fanck0605/awepatch/blob/main/LICENSE)

## 概述

`awepatch` 是一个强大的 Python 库，允许你通过操作抽象语法树（AST）在运行时动态修补源代码。与传统的猴子补丁不同，`awepatch` 修改的是函数的实际代码对象，提供了一种更清晰、更易维护的运行时代码修改方法。

## 特性

- 🔧 **运行时函数补丁**：无需更改源代码即可修改函数行为
- 🎯 **基于 AST 的操作**：使用 AST 进行清晰而精确的代码修改
- 🔄 **自动恢复**：支持上下文管理器进行临时补丁
- 🎭 **多种补丁模式**：在现有语句之前、之后插入代码或替换语句
- 🧩 **模式匹配**：使用字符串、正则表达式或元组模式定位要补丁的代码
- 🎯 **嵌套匹配**：使用元组模式语法定位嵌套代码块
- 🔗 **装饰器支持**：适用于装饰函数、类方法和静态方法
- ⚡ **类型安全**：完整的类型提示支持和严格的类型检查

## 安装

```bash
pip install awepatch
```

或使用 `uv`：

```bash
uv pip install awepatch
```

## 快速开始

### 函数补丁

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

# 输出:
# processing: x=5
# result: 45
# 45
```

### 模块补丁

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

# 输出: Hello, Bob! You are 25 years old. Your gender is unspecified.
```

### 嵌套模式匹配

对于复杂的嵌套结构，你可以使用元组模式或行号偏移来匹配嵌套的 AST 节点：

```python
from awepatch import FunctionPatcher, Ident


def nested_function(x: int) -> int:
    if x > 0:
        x = x * 2
    x = x * 2
    return x


# 匹配 if 块内的嵌套语句
with FunctionPatcher().add_patch(
    nested_function,
    target=("if x > 0:", "x = x * 2"),
    content="x = x * 3",
    mode="replace",
):
    print(nested_function(5))  # 输出: 30


# 或通过行号偏移匹配
with FunctionPatcher().add_patch(
    nested_function,
    target=Ident("x = x * 2", lineno="+2"),
    content="x = x * 3",
    mode="replace",
):
    print(nested_function(5))  # 输出: 30
```

## 高级用法

### 多进程应用补丁

对于生成多个进程的应用程序，你必须使用 `ModulePatcher` 来确保补丁在每个子进程中都被应用。

使用 `.pth` 文件在每个进程导入模块时自动应用补丁可能是一个不错的选择。

```python
# loader.py
patcher = ModulePatcher()
patcher.add_patch(
    "foo",
    target=(
        "class User:",
        "age: int",
    ),
    content="gender: str = 'unspecified'"
)
patcher.apply()

# xxx-awepatch.pth
# xxx-awepatch.pth 必须放在 site-packages 目录中
import loader
```

参见：

- <https://github.com/tox-dev/pre-commit-uv/blob/main/src/pre_commit_uv_patch.pth>
- <https://github.com/pypa/setuptools/blob/main/setup.py#L12>
- <https://github.com/jawah/urllib3.future/blob/main/urllib3_future.pth>

## 使用场景

- **测试**：无需复杂的模拟框架即可模拟函数行为
- **调试**：在运行时注入日志或调试代码
- **热补丁**：无需重启应用程序即可应用修复或修改
- **实验**：无需修改源文件即可快速测试代码更改
- **仪器化**：动态添加监控或性能分析代码

## 限制

- Lambda 函数无法被补丁（它们缺少适当的源代码信息）
- 函数必须通过 `inspect.getsourcelines()` 访问源代码
- 模式匹配必须唯一标识函数中的目标语句
- AST 中仅支持单个函数定义
- 不允许冲突的补丁（例如，在同一目标上组合 'replace' 和 'before'/'after'）

## 开发

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/fanck0605/awepatch.git
cd awepatch

# 安装开发依赖
uv sync
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行覆盖率测试
pytest --cov=awepatch --cov-report=html

# 运行特定测试文件
pytest tests/test_patch_callable.py
```

### 代码质量

```bash
# 格式化代码
ruff format

# 检查代码
ruff check

# 修复可自动修复的问题
ruff check --fix
```

## 贡献

欢迎贡献！请随时提交 Pull Request。对于重大更改，请先开启一个 issue 讨论你想要更改的内容。

1. Fork 仓库
2. 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](https://github.com/fanck0605/awepatch/blob/main/LICENSE) 文件。

## 作者

**Chuck Fan** - [fanck0605@qq.com](mailto:fanck0605@qq.com)

## 致谢

- 受 Python 中更清晰的运行时代码修改需求启发
- 使用现代 Python 工具和最佳实践构建

---

**注意**：此库在运行时修改函数代码对象。在生产环境中请谨慎使用，并务必充分测试。
