import sqlite3

db_path = '../storage/database.db' # Ajusta si es necesario

conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    # Insertamos un usuario de prueba (rol_id 1 para diferenciarlo del admin 0)
    # No le ponemos secret_2fa ni password real por ahora, solo para que aparezca en la lista
    cur.execute("""
        INSERT INTO usuarios (usuario, password_hash, nombre_completo, rol_id, activo) 
        VALUES (?, ?, ?, ?, ?)
    """, ("prueba_ventanilla", "sin_password", "Juan Perez - Ventanilla", 1, 1))
    
    conn.commit()
    print("✅ Usuario 'Juan Perez - Ventanilla' creado exitosamente.")
except Exception as e:
    print(f"❌ Error al crear usuario: {e}")
finally:
    conn.close()