import logging
from typing import Optional


def setup_logging(level: int = logging.INFO, use_rich: Optional[bool] = None) -> None:
    """Configure project-wide logging.

    - If `rich` is installed and `use_rich` is True (or None and rich is present), uses
      `rich.logging.RichHandler` for pretty console output and better tracebacks.
    - Otherwise falls back to standard library `logging` with a readable format.
    """
    # detect rich availability
    if use_rich is None:
        try:
            import rich  # type: ignore
            use_rich = True
        except Exception:
            use_rich = False

    if use_rich:
        try:
            from rich.logging import RichHandler  # type: ignore
            from rich.traceback import install as _install_tb  # type: ignore

            _install_tb()
            handler = RichHandler(rich_tracebacks=True)
            root = logging.getLogger()
            # remove existing handlers to avoid duplicate logs
            for h in list(root.handlers):
                root.removeHandler(h)
            root.addHandler(handler)
            root.setLevel(level)
            # set a simple logger name in messages
            logging.getLogger("ai").setLevel(level)
        except Exception:
            # fallback to std logging
            _std_setup(level)
    else:
        _std_setup(level)


def _std_setup(level: int) -> None:
    root = logging.getLogger()
    # remove existing handlers first
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = "%(levelname)s:%(name)s: %(message)s"
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)
    root.setLevel(level)
