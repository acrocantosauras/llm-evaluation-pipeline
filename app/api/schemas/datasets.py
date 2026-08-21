from pydantic import BaseModel


class DatasetCreate(BaseModel):
    name: str
    description: str = ""


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: str
