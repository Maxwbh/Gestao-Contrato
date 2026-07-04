"""
DB-02: Campo JSON portável entre PostgreSQL, MySQL, Oracle e SQLite.

Para PostgreSQL e MySQL ≥5.7: usa o JSONField nativo do Django (jsonb/json).
Para Oracle: usa NCLOB com serialização manual.
Para SQLite (dev/testes): usa JSONField nativo (TEXT internamente).
"""
import json
from django.db import models


class PortableJSONField(models.JSONField):
    """
    JSONField com suporte portável a múltiplos bancos.

    Comportamento por vendor:
      - postgresql → jsonb (nativo, indexável)
      - mysql      → json (nativo, MySQL ≥ 5.7.8)
      - oracle     → NCLOB com from_db_value/get_prep_value
      - sqlite3    → text (comportamento padrão do JSONField Django)
    """

    def db_type(self, connection) -> str:
        vendor = connection.vendor
        if vendor == 'postgresql':
            return 'jsonb'
        if vendor == 'mysql':
            return 'json'
        if vendor == 'oracle':
            return 'NCLOB'
        return 'text'

    def from_db_value(self, value, expression, connection):
        if connection.vendor == 'oracle' and isinstance(value, str):
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return value
        return super().from_db_value(value, expression, connection)

    def get_prep_value(self, value):
        if value is None:
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return super().get_prep_value(value)
