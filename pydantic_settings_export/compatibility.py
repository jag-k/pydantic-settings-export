import argparse
import typing

try:
    # Deprecated in Python 3.14
    from argparse import FileType  # type: ignore[ty:deprecated]

except ImportError:
    import sys
    from gettext import gettext

    class FileType:
        """Factory for creating file object types.

        Instances of FileType are typically passed as type= arguments to the
        ArgumentParser add_argument() method.

        Keyword Arguments:
            - mode -- A string indicating how the file is to be opened. Accepts the
                same values as the builtin open() function.
            - bufsize -- The file's desired buffer size. Accepts the same values as
                the builtin open() function.
            - encoding -- The file's encoding. Accepts the same values as the
                builtin open() function.
            - errors -- A string indicating how encoding and decoding errors are to
                be handled. Accepts the same value as the builtin open() function.
        """

        def __init__(self, mode="r", bufsize=-1, encoding=None, errors=None):
            self._mode = mode
            self._bufsize = bufsize
            self._encoding = encoding
            self._errors = errors

        def __call__(self, string: str) -> typing.IO:
            """
            Open a file or standard input/output based on the provided string argument.

            This method determines the file object to return based on the input value
            of the `string` parameter. If the `string` is "-", it decides to return
            either the standard input or standard output, depending on the mode. Otherwise,
            it attempts to open the specified file. If the file cannot be opened,
            an argparse.ArgumentTypeError is raised with an appropriate error message.

            :param string: The name of the file to open or "-" for standard input/output.
            :raises ValueError: If the mode provided is invalid when handling "-" as the argument.
            :raises argparse.ArgumentTypeError: If the specified file cannot be opened.
            :return: A file object corresponding to the specified file or standard input/output.
            """
            # the special argument "-" means sys.std{in,out}
            if string == "-":
                if "r" in self._mode:
                    return sys.stdin.buffer if "b" in self._mode else sys.stdin
                elif any(c in self._mode for c in "wax"):
                    return sys.stdout.buffer if "b" in self._mode else sys.stdout
                else:
                    msg = gettext('argument "-" with mode %r') % self._mode
                    raise ValueError(msg)

            # all other arguments are used as file names
            try:
                return open(string, self._mode, self._bufsize, self._encoding, self._errors)
            except OSError as e:
                args = {"filename": string, "error": e}
                message = gettext("can't open '%(filename)s': %(error)s")
                raise argparse.ArgumentTypeError(message % args) from e

        def __repr__(self) -> str:
            args = self._mode, self._bufsize
            kwargs = [("encoding", self._encoding), ("errors", self._errors)]
            args_str = ", ".join(
                [repr(arg) for arg in args if arg != -1] + [f"{kw}={arg!r}" for kw, arg in kwargs if arg is not None]
            )
            return f"{type(self).__name__}({args_str})"
