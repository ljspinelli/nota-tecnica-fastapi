from app.database import SessionLocal
from app.models import User
from app.services import hash_senha

db = SessionLocal()

admin = User(
    username="admin",
    senha_hash=hash_senha("123456")
)

db.add(admin)
db.commit()

print("Usuário admin criado com sucesso!")
