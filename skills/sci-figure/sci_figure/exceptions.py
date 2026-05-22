"""Custom exceptions for sci-figure v2."""


class SciFigureError(Exception):
    """Base exception."""
    pass


class PDFError(SciFigureError):
    pass


class PDFNotFoundError(PDFError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"PDF file not found: {path}")


class PDFCorruptError(PDFError):
    def __init__(self, path: str, reason: str = ""):
        self.path = path
        detail = f" ({reason})" if reason else ""
        super().__init__(f"Cannot open PDF{detail}: {path}")


class PDFEncryptedError(PDFError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"PDF is encrypted: {path}")


class FigureNotFoundError(SciFigureError):
    def __init__(self, figure_num: int, available: list = None):
        self.figure_num = figure_num
        self.available = available or []
        avail_str = (
            f" Available: {', '.join(str(n) for n in self.available)}"
            if self.available else " No figures detected."
        )
        super().__init__(f"Figure {figure_num} not found.{avail_str}")


class SubfigureNotFoundError(SciFigureError):
    def __init__(self, figure_num: int, sublabel: str, available: list = None):
        self.figure_num = figure_num
        self.sublabel = sublabel
        self.available = available or []
        avail_str = f" Available: {', '.join(self.available)}" if self.available else ""
        super().__init__(f"Sub-figure '{sublabel}' not found in Figure {figure_num}.{avail_str}")
