import os
from pydantic_settings import BaseSettings, SettingsConfigDict

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, '.env')

class Settings(BaseSettings):
    database_url: str = 'sqlite+aiosqlite:///./discord_bot.db'
    token: str
    debug_server_id: int
    application_channel_id: int
    rcd_application_channel_id: int
    pve_channel_id: int
    pve_app_channel_id: int
    rcd_list_channel_id: int

    model_config = SettingsConfigDict(
        env_file=env_path,  # Используем абсолютный путь
        env_file_encoding='utf-8'
    )


#class Config:
    #    env_file = '.env'


settings = Settings()
