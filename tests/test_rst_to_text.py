"""Tests for RST to text conversion."""

from pydantic_settings_export.rst2text import rst_to_text


def test_rst_to_text_with_roles() -> None:
    """Test RST role conversion."""
    text = "Use :class:`~foo.Bar` and :mod:`baz` with :func:`qux`."
    result = rst_to_text(text)
    expected = "Use Bar and baz with qux."
    assert result == expected


def test_rst_to_text_with_links() -> None:
    """Test RST link conversion."""
    text = "See `PostgreSQL Docs <https://postgresql.org>`_ for more info."
    result = rst_to_text(text)
    expected = "See PostgreSQL Docs (https://postgresql.org) for more info."
    assert result == expected


def test_rst_to_text_with_inline_code() -> None:
    """Test inline code conversion."""
    text = "Use ``foo.bar()`` to call the function."
    result = rst_to_text(text)
    expected = "Use foo.bar() to call the function."
    assert result == expected


def test_rst_to_text_with_paragraphs() -> None:
    """Test paragraph wrapping."""
    text = (
        "This is a very long paragraph that should be wrapped at 80 columns "
        "when processed by the rst_to_text function.\n\nThis is another paragraph."
    )
    result = rst_to_text(text)
    expected = """This is a very long paragraph that should be wrapped at 80 columns when
processed by the rst_to_text function.

This is another paragraph."""
    assert result == expected


def test_rst_to_text_with_custom_line_length() -> None:
    """Test custom line length."""
    text = "This is a very long paragraph that should be wrapped at a custom column width."
    result = rst_to_text(text, line_length=40)
    expected = """This is a very long paragraph that
should be wrapped at a custom column
width."""
    assert result == expected


def test_rst_to_text_with_lists() -> None:
    """Test list preservation."""
    text = """Supports these formats:

- IPv4: ``192.168.1.100``
- IPv6: ``::1``
- Hostname: ``db.example.com``"""
    result = rst_to_text(text)
    expected = """Supports these formats:

- IPv4: 192.168.1.100
- IPv6: ::1
- Hostname: db.example.com"""
    assert result == expected


def test_rst_to_text_with_code_blocks() -> None:
    """Test code block preservation."""
    text = """Example usage:

.. code-block:: python

    def foo():
        return 42"""
    result = rst_to_text(text)
    expected = """Example usage:

    def foo():
        return 42"""
    assert result == expected


def test_rst_to_text_comprehensive() -> None:
    """Test comprehensive RST processing with multiple features."""
    text = """Database configuration with RST markup.

Supports :class:`PostgreSQL` and :mod:`MySQL` databases.

See `PostgreSQL Docs <https://postgresql.org>`_ for more info.

Common ports:

- PostgreSQL: 5432
- MySQL: 3306

Use :func:`validate_host` to check validity."""
    result = rst_to_text(text)
    expected = """Database configuration with RST markup.

Supports PostgreSQL and MySQL databases.

See PostgreSQL Docs (https://postgresql.org) for more info.

Common ports:

- PostgreSQL: 5432
- MySQL: 3306

Use validate_host to check validity."""
    assert result == expected


def test_rst_to_text_with_multiple_newlines() -> None:
    """Test handling of multiple consecutive newlines."""
    text = "First paragraph.\n\n\n\nSecond paragraph."
    result = rst_to_text(text)
    expected = "First paragraph.\n\nSecond paragraph."
    assert result == expected


def test_rst_to_text_removes_directives() -> None:
    """Test that RST directives are removed."""
    text = """Some text.

.. code-block:: python

More text."""
    result = rst_to_text(text)
    expected = """Some text.

More text."""
    assert result == expected


def test_rst_to_text_with_code_block_caption() -> None:
    """Test code block with caption option."""
    text = """Example with caption:

.. code-block:: python
   :caption: my_script.py

   def foo():
       return 42"""
    result = rst_to_text(text)
    expected = """Example with caption:

   def foo():
       return 42"""
    assert result == expected
