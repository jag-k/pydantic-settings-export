__all__ = ("ExportWarning",)


class ExportWarning(UserWarning):
    """A problem while exporting settings that was skipped to let the rest of the export continue.

    For example, a generator failed, settings could not be imported, or an output file could not be read or written.
    ``--check`` treats these warnings as failures.
    """
