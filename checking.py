from myproject import create_app
from myproject.models import Company

app = create_app()

with app.app_context():
    companies = Company.query.all()
    for c in companies:
        print(f"id={c.id}, ticker={c.ticker}, name={c.name}, note={c.note}")