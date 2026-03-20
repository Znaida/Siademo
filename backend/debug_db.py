import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

print("--- REVISIÓN DE ENTORNO PYTHON ---")
print(f"HOST: {os.getenv('DB_HOST')}")
print(f"DB:   {os.getenv('DB_NAME')}")
print(f"USER: {os.getenv('DB_USER')}")

def test_conexion():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cur = conn.cursor()
        # Verificamos dónde está conectado realmente Python
        cur.execute("SELECT current_database(), inet_server_addr(), inet_server_port();")
        info = cur.fetchone()
        print("\n--- CONEXIÓN REAL DE PYTHON ---")
        print(f"Base de datos: {info[0]}")
        print(f"Dirección IP:  {info[1]}")
        print(f"Puerto:        {info[2]}")
        
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'zenaida_admin';")
        existe = cur.fetchone()[0]
        print(f"¿Zenaida existe para Python?: {'SÍ' if existe > 0 else 'NO'}")
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

test_conexion()