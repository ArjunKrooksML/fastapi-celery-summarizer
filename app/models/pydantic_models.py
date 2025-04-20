from pydantic import BaseModel
from typing import Optional

class SummText(BaseModel):
    text: str
    max_length:int= 150