"""Smoke test: the core package imports cleanly.

Keeps the test suite green from the first commit and proves the package is
importable in CI before any feature logic exists.
"""


def test_rag_package_imports() -> None:
    import rag

    assert rag.__doc__ is not None
