import re
import textwrap


def sanitize_rst_text(text: str) -> str:
    """Remove inline RST syntax."""
    # Replace :foo:`~bar.Baz` with Baz
    text = re.sub(r":[\w:-]+:`~[\w\.]+\.(\w+)`", r"\1", text)

    # Replace :foo:`bar` and :foo:`bar <anything> with bar`
    text = re.sub(r":[\w:-]+:`([^`<]+)(?: <[^`>]+>)?`", r"\1", text)

    # Replace `label <URL>`_ with label (URL)
    text = re.sub(r"`([^`<]+) <([^`>]+)>`_", r"\1 (\2)", text)

    # Replace ``foo`` with `foo`
    text = re.sub(r"``([^`]+)``", r"\1", text)

    # Remove RST directives with options (e.g., .. code-block:: python\n   :caption: foo)
    # This pattern matches directive lines and any indented option lines that follow
    text = re.sub(r"\.\. [\w-]+::( \w+)?(\n   :[^\n]+)*\n\n", "", text)

    # De-double slashes
    text = re.sub(r"\\", "", text)

    return text


def rst_to_text(text: str, line_length: int = 80) -> str:
    """Remove RST syntax and wrap the docstring."""

    def is_code_block(text: str) -> bool:
        return all(not line or line.startswith("    ") for line in text.splitlines())

    def is_list(text: str) -> bool:
        return all(line.startswith("-") or line.startswith("  ") for line in text.splitlines())

    text = sanitize_rst_text(text)
    paragraphs = re.split(r"\n\n+", text)
    paragraphs = [
        textwrap.fill(paragraph, width=line_length)
        if not is_code_block(paragraph) and not is_list(paragraph)
        else paragraph
        for paragraph in paragraphs
    ]
    text = "\n\n".join(paragraphs)
    return text
