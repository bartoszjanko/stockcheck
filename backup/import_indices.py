import pandas as pd
from myproject import create_app, db
from myproject.models import Index

app = create_app()

def import_indices():
    df = pd.read_csv('gpw_indeksy.csv')
    for _, row in df.iterrows():
        index_name = str(row['index_name']).strip()
        if not Index.query.filter_by(index_name=index_name).first():
            db.session.add(Index(index_name=index_name))
    db.session.commit()
    print('Import indeksów zakończony.')

if __name__ == '__main__':
    with app.app_context():
        import_indices()
