from sqlalchemy import create_engine

user = "coniitic_registro"
password = "G3!+GUyN-1bXP+]x"   # XAMPP normalmente no tiene contraseña
host = "localhost"
database = "coniitic_registro"

engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}/{database}"
)

try:
    connection = engine.connect()
    print("Conexión exitosa 🚀")
    connection.close()
except Exception as e:
    print("Error:", e)
