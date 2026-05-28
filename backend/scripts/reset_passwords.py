import sys
sys.path.insert(0, '.')
from app.db import database, models
from app.core.security import get_password_hash, verify_password

db = next(database.get_db())

new_hash = get_password_hash('admin123')
print(f'New hash prefix: {new_hash[:30]}...')

# Verify the hash works before saving
ok = verify_password('admin123', new_hash)
print(f'Hash self-verification: {ok}')

for doc in db.query(models.Doctor).all():
    doc.hashed_password = new_hash
    print(f'Resetting: {doc.username}')

db.commit()
print('Done - all passwords set to: admin123')

# Verify
db2 = next(database.get_db())
dr = db2.query(models.Doctor).filter_by(username='dr_smith').first()
result = verify_password('admin123', dr.hashed_password)
print(f'Login test dr_smith/admin123: {"SUCCESS" if result else "FAILED"}')
db2.close()
db.close()
