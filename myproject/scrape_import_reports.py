import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from myproject.companies.models import Company
from myproject.reports.models import Report
from myproject import db

def update_reports():
    url = "https://strefainwestorow.pl/dane/raporty/lista-publikacji-raportow-okresowych/all"
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

    for _, row in df.iterrows():
        ticker = str(row['Ticker']).strip()
        name = str(row['Pełna nazwa']).strip()
        try:
            report_date = datetime.strptime(row['Data publikacji'], "%d-%m-%Y").date()
        except Exception:
            continue
        report_type = str(row['Raport']).strip()
        company = Company.query.filter_by(ticker=ticker).first()
        if not company:
            continue
        exists = Report.query.filter_by(
            company_id=company.id,
            report_date=report_date,
            report_type=report_type
        ).first()
        if exists:
            continue
        report = Report(
            company_id=company.id,
            report_date=report_date,
            report_type=report_type
        )
        db.session.add(report)
    db.session.commit()