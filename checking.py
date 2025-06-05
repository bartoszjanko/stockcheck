from myproject import create_app
from myproject.models import Company

app = create_app()

with app.app_context():
    companies = Company.query.all()
    for c in companies:
        print(f"id={c.id}, ticker={c.ticker}, name={c.name}, note={c.note}")


from myproject import db
from myproject.models import User
admin = User(email="admin@admin.com", username="admin", password="haselko", role="admin")
db.session.add(admin)
db.session.commit()


from myproject import db
from myproject.models import User
admin = User(email="admin@admin.com", username="admin", password="haselko", role="admin")
db.session.add(admin)
db.session.commit()