# Skrypt do pobrania wszystkich unikalnych nazw indeksów z bazy danych
from myproject import create_app
from myproject.companies.models import Index

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        all_indices = sorted(set(i.index_name for i in Index.query.all()))
        for idx in all_indices:
            print(idx)
