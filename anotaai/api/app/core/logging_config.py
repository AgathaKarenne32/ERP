import json
import logging
import sys


class FormatadorJSON(logging.Formatter):
    def __init__(self, nome_servico: str):
        super().__init__()
        self.nome_servico = nome_servico

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": self.nome_servico,
            "message": record.getMessage(),
        }
        http = getattr(record, "http", None)
        if http:
            payload["http"] = http
        return json.dumps(payload, ensure_ascii=False)


def configurar_logging(nome_servico: str) -> None:
    """Logs estruturados em JSON, uma linha por evento — facilita agregação
    em ferramentas como Loki/ELK/CloudWatch depois."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatadorJSON(nome_servico))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
