import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
from myproject.models import Company, Recommendation
from myproject import db

def parse_name_and_ticker(cell):
    match = re.match(r"(.+?) \(([^)]+)\)", cell)
    if match:
        name = match.group(1).replace('*', '').strip()
        ticker = match.group(2).replace('*', '').strip()
    else:
        name = cell.replace('*', '').strip()
        ticker = ''
    return name, ticker

def update_recommendations():
    url = "https://strefainwestorow.pl/rekomendacje/lista-rekomendacji/wszystkie"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    headers = [th.text.strip() for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.text.strip() for td in tr.find_all("td")]
        if cells:
            rows.append(cells)
    df = pd.DataFrame(rows, columns=headers)

    pub_date_col = [col for col in df.columns if 'Data publikacji' in col][0]

    for _, row in df.iterrows():
        name, ticker = parse_name_and_ticker(row['Spółka'])
        try:
            publication_date = datetime.strptime(row[pub_date_col].split('\n')[0].strip(), "%d-%m-%Y").date()
        except Exception:
            continue
        recommendation_type = row['Rodzaj']
        target_price = row['Cena docelowa']
        publication_price = row['Cena w dniu publikacji']
        institution = row['Instytucja']
        company = Company.query.filter_by(ticker=ticker).first()
        if not company:
            continue
        exists = Recommendation.query.filter_by(
            company_id=company.id,
            publication_date=publication_date,
            recommendation_type=recommendation_type
        ).first()
        if exists:
            continue
        rec = Recommendation(
            company_id=company.id,
            ticker=ticker,
            name=name,
            publication_date=publication_date,
            recommendation_type=recommendation_type,
            target_price=target_price,
            publication_price=publication_price,
            institution=institution
        )
        db.session.add(rec)
    db.session.commit()
    print("Recommendations updated in the database.")

if __name__ == "__main__":
    update_recommendations()
