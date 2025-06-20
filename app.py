from myproject import create_app, db
from myproject.scarp_import_reports import update_reports

app = create_app()

with app.app_context():
    # Nie uruchamiaj update_reports() ani importów jeśli nie ma jeszcze tabel
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if 'company' in tables:
        update_reports() # automatyczna aktualizacja terminarza z raportami ze strefy inwestora
        from myproject.scrape_recommendations import update_recommendations
        update_recommendations() # automatyczna aktualizacja rekomendacji

if __name__ == '__main__':
    app.run(debug=True)
