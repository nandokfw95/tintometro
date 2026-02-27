import os
import sys

def resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto para um recurso, funcionando no exe (PyInstaller)
    e no modo normal (python).
    """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)