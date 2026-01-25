import importlib

import pytest

from awepatch.module import ModulePatcher


def test_module_patch_dataclass() -> None:
    from tests.test_module import module_for_test

    user = module_for_test.User(name="Alice", age=230)
    assert user.name == "Alice"
    assert user.age == 230
    assert not hasattr(user, "gender")

    patcher = ModulePatcher()
    patcher.add_patch(
        "tests.test_module.module_for_test",
        target="class User:",
        content=""" 
@dataclass
class User:
    name: str
    age: int
    gender: str = "unspecified"
""",
        mode="replace",
    )
    patcher.add_patch(
        "tests.test_module.module_for_test",
        target="def greet(user: User) -> str:",
        content=""" 
def greet(user: User) -> str:
    1 / 0  # intentional error for testing
""",
        mode="replace",
    )
    patcher.apply()
    try:
        importlib.reload(module_for_test)
        patched_user = module_for_test.User(name="Bob", age=25)
        assert patched_user.name == "Bob"
        assert hasattr(patched_user, "gender")
        assert isinstance(patched_user.age, int)
        assert patched_user.age == 25
        assert patched_user.gender == "unspecified"  # type: ignore
        with pytest.raises(ZeroDivisionError):
            module_for_test.greet(patched_user)
    finally:
        patcher.restore()


def test_module_patch_field() -> None:
    from tests.test_module import module_for_test

    user = module_for_test.User(name="Alice", age=230)
    assert user.name == "Alice"
    assert user.age == 230
    assert not hasattr(user, "gender")

    patcher = ModulePatcher()
    patcher.add_patch(
        "tests.test_module.module_for_test",
        target=("class User:", "age: int"),
        content=""" 
gender: str = "unspecified"
""",
        mode="after",
    )
    patcher.apply()
    try:
        importlib.reload(module_for_test)
        patched_user = module_for_test.User(name="Bob", age=25)
        assert patched_user.name == "Bob"
        assert hasattr(patched_user, "gender")
        assert isinstance(patched_user.age, int)
        assert patched_user.age == 25
        assert patched_user.gender == "unspecified"  # type: ignore
    finally:
        patcher.restore()
