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

    # Panel administrativo de notificaciones
    admin_user: str = ""
    admin_password: str = ""
    # Origenes permitidos para CORS (panel web + formulario de la web)
    cors_origins: str = "https://ocaservicios.com,https://www.ocaservicios.com"

    # Groq (https://console.groq.com/keys)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    # Vision: analisis de imagenes (fotos, planos, croquis)
    groq_vision_model: str = "llama-3.2-11b-vision-preview"
    # Transcipcion de notas de voz
    groq_stt_model: str = "whisper-large-v3"

    # PostgreSQL (Railway la inyecta como DATABASE_URL)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/oca_chatbot"

    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
