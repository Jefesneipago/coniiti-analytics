# src/db.py

import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Cargar variables del .env
load_dotenv()

def get_engine():
    try:
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST")
        database = os.getenv("DB_NAME")
        port = os.getenv("DB_PORT", "3306")

        if not all([user, host, database]):
            raise ValueError("Faltan variables de entorno para la conexión a la BD")

        engine = create_engine(
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
            pool_pre_ping=True,
            pool_recycle=3600
        )

        return engine

    except Exception as e:
        raise RuntimeError(f"Error creando conexión a la BD: {e}")