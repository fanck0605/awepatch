from dataclasses import dataclass


@dataclass
class User:
    name: str
    age: int


def greet(user: User) -> str:
    return f"Hello, {user.name}! You are {user.age} years old."
