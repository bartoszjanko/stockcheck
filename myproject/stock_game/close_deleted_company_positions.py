# Skrypt do zamykania pozycji w grze giełdowej, gdy spółka została usunięta z bazy Company
from myproject import create_app, db
from myproject.stock_game.models import GamePosition

def close_positions_for_deleted_companies():
    # Zamknij pozycje, gdzie company_id jest None i closed == False
    positions = GamePosition.query.filter_by(company_id=None, closed=False).all()
    for pos in positions:
        pos.closed = True
        print(f"Zamknięto pozycję: {pos.ticker} (id={pos.id})")
    db.session.commit()
    print(f"Zamknięto {len(positions)} pozycji bez powiązanej spółki.")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        close_positions_for_deleted_companies()
