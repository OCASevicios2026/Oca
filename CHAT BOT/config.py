from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # YCloud
    ycloud_api_key: str = ""
    # Secreto del webhook (lo defines al crear el endpoint en YCloud Dashboard > Developer > Webhooks)
    ycloud_webhook_secret: str = ""
    # Numero de WhatsApp de OCA en formato E.164 (ej: +573174004016)
    whatsapp_business_phone: str = ""
    # Opcional: numero al que se notifican los leads de cotizacion (formato E.164)
    lead_notify_phone: str = ""

    # Gemini (Google AI Studio: https://aistudio.google.com/apikey)
    # Nota: gemini-2.5-flash ya no se ofrece a usuarios nuevos; usamos 3.5-flash.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    # PostgreSQL (Railway la inyecta como DATABASE_URL)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/oca_chatbot"

    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
