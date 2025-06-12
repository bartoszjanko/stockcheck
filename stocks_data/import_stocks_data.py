import pandas as pd
from myproject import create_app, db
from myproject.companies.models import Company, Index, Industry, company_index

app = create_app()

def import_companies():
    df_wse = pd.read_csv('/wse_stocks.csv')
    df_nc = pd.read_csv('/nc_stocks.csv')
    df = pd.concat([df_wse, df_nc], ignore_index=True)
    for _, row in df.iterrows():
        ticker = str(row['ticker']).strip()
        name = str(row['company_name']).strip()
        market = str(row['market']).strip()  # <-- dodajemy pobieranie rynku
        industry_name = str(row['industry']).strip()
        indices_str = str(row['indices']).strip()

        # Znajdź lub utwórz branżę
        industry = Industry.query.filter_by(industry_name=industry_name).first()
        if not industry:
            industry = Industry(industry_name=industry_name)
            db.session.add(industry)
            db.session.commit()

        # Znajdź lub utwórz spółkę
        company = Company.query.filter_by(ticker=ticker).first()
        if not company:
            company = Company(ticker=ticker, name=name, market=market, industry=industry)
            db.session.add(company)
            db.session.commit()
        else:
            company.name = name
            company.market = market  # <-- aktualizujemy rynek
            company.industry = industry
            db.session.commit()

        # Przypisz indeksy (wiele-do-wielu)
        company.indices.clear()
        for index_name in [i.strip() for i in indices_str.split(',') if i.strip()]:
            index = Index.query.filter_by(index_name=index_name).first()
            if not index:
                index = Index(index_name=index_name)
                db.session.add(index)
                db.session.commit()
            if index not in company.indices:
                company.indices.append(index)
        db.session.commit()
    print('Import spółek zakończony.')

if __name__ == '__main__':
    with app.app_context():
        import_companies()
