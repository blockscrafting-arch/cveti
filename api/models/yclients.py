from pydantic import BaseModel
from typing import Optional, Dict, Any

class YClientsWebhookData(BaseModel):
    resource: str
    resource_id: int
    status: str
    data: Dict[str, Any]

# Пример структуры данных в вебхуке (может меняться в зависимости от версии API YClients)
# {
#   "resource": "payment",
#   "data": {
#     "client": { "phone": "79991234567" },
#     "amount": 5000,
#     "visit_id": 12345
#   }
# }
