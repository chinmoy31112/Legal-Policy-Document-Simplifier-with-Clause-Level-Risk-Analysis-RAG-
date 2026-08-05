from pydantic import BaseModel, ConfigDict, Field

class ORM:
    def __init__(self):
        self.metadata_ = {"key": "value"}
        self.metadata = "SQLALCHEMY_METADATA_OBJECT"

class DocumentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")

obj = ORM()
print(DocumentDetail.model_validate(obj).model_dump())
