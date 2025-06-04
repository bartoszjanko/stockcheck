import csv
from myproject import create_app, db
from myproject.models import Company

app = create_app()

with app.app_context():
    with open('tickers.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not Company.query.filter_by(ticker=row['ticker']).first():
                company = Company(ticker=row['ticker'], name=row['name'])
                db.session.add(company)
        db.session.commit()
    print('Import completed.')
