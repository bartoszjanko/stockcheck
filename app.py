from myproject import create_app, db
from myproject.scrape_import_reports import update_reports
from myproject.scrape_import_recommendations import update_recommendations
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if 'company' in tables:
        update_reports() # automatyczna aktualizacja terminarza z raportami ze strefy inwestora
        update_recommendations() # automatyczna aktualizacja rekomendacji

if __name__ == '__main__':
    app.run(debug=True)
