import sqlite3
import os
import pyotp  # Necesitas esta para generar el código
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generar_acceso_inicial():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "..", "storage", "database.db")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    user = "zenaido"
    password_plano = "michota123" 
    password_hash = pwd_context.hash(password_plano)
    
    # --- Generamos el secreto para el Autenticador ---
    secret_2fa = pyotp.random_base32() 

    try:
        # Primero borramos si existía uno previo para no tener conflictos
        cur.execute("DELETE FROM usuarios WHERE usuario = ?", (user,))
        
        cur.execute("""
            INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol_id, secret_2fa, activo)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (user, password_hash, "Administrador de Sistema", 0, secret_2fa))
        
        conn.commit()
        
        print(f"\n✅ ¡ADMINISTRADOR ACTUALIZADO!")
        print(f"---------------------------------")
        print(f"👤 Usuario: {user}")
        print(f"🔑 Password: {password_plano}")
        print(f"📱 CÓDIGO 2FA (Guárdalo): {secret_2fa}")
        print(f"---------------------------------")
        print(f"💡 TIP: En Google Authenticator usa 'Agregar clave' y pega ese código.")
        print(f"---------------------------------\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    generar_acceso_inicial()