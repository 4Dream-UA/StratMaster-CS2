from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    logo_url: str | None = None
    model_config = {"from_attributes": True}


class AppSettingsUpdate(BaseModel):
    logo_url: str | None = None
