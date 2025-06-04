import pandas as pd
from myproject import create_app, db
from myproject.models import Industry

app = create_app()

def import_industries():
    df = pd.read_csv('gpw_branze.csv')
    for _, row in df.iterrows():
        industry_name = str(row['industry_name']).strip()
        if not Industry.query.filter_by(industry_name=industry_name).first():
            db.session.add(Industry(industry_name=industry_name))
    db.session.commit()
    print('Import branz zakończony.')

if __name__ == '__main__':
    with app.app_context():
        import_industries()
