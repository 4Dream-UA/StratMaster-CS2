from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    logo_url: str | None = None
    # Whether the AI support assistant is switched on. Reported alongside
    # whether it *could* run at all, so the admin panel can distinguish
    # "turned off" from "no API key configured on the server".
    ai_agent_enabled: bool = True
    ai_agent_configured: bool = False
    ai_agent_model: str = ""
    model_config = {"from_attributes": True}


class AppSettingsUpdate(BaseModel):
    logo_url: str | None = None
    # Omitted leaves the current value alone, so saving a logo can't
    # silently flip the assistant back on.
    ai_agent_enabled: bool | None = None
