from passlib.context import CryptContext

# Configuramos el contexto de seguridad (el mismo que usará tu FastAPI)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# La contraseña que queremos encriptar para las pruebas
password_plana = "Prueba123*"

# Generamos el hash
hash_generado = pwd_context.hash(password_plana)

print("\n--- COPIA ESTE CÓDIGO ---")
print(hash_generado)
print("-------------------------\n")