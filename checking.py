from myproject import create_app
from myproject.companies.models import Company

app = create_app()

# with app.app_context():
#     companies = Company.query.all()
#     for c in companies:
#         print(f"id={c.id}, ticker={c.ticker}, name={c.name}, note={c.note}")


from myproject import db
from myproject.auth.models import User
with app.app_context():
    admin = User(email="admin@admin.pl", username="admin1", password="haselko", role="admin")
    db.session.add(admin)
    db.session.commit()
    print("Admin dodany!")


