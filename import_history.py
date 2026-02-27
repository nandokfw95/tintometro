# import_history.py
import json
import os
from datetime import datetime

HIST_PATH = os.path.join(os.path.dirname(__file__), "import_history.json")


def _load() -> dict:
    if not os.path.exists(HIST_PATH):
        return {}
    try:
        with open(HIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save(data: dict) -> None:
    with open(HIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_status_by_txt(txt_path: str) -> dict | None:
    """
    Retorna dict com status (se existir) para aquele TXT.
    A chave é o caminho completo do arquivo.
    """
    data = _load()
    return data.get(os.path.abspath(txt_path))


def mark_imported(txt_path: str, pedido: int, modo: str) -> None:
    """
    modo: "orcamento" ou "venda_base"
    """
    data = _load()
    key = os.path.abspath(txt_path)
    data[key] = {
        "importado": True,
        "pedido": int(pedido),
        "modo": str(modo),
        "quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "arquivo": os.path.basename(txt_path),
    }
    _save(data)