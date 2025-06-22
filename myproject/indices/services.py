def get_index_chart(ticker, selected_range='6m'):
    """
    Pobiera dane historyczne indeksu ze Stooq i generuje wykres świecowy z wolumenem oraz SMA20.
    Zwraca HTML wykresu (plotly) lub None.
    """
    import pandas as pd
    import requests
    from io import StringIO
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from plotly.offline import plot
    from datetime import date
    import numpy as np
    url = f"https://stooq.pl/q/d/l/?s={ticker}&i=d"
    try:
        response = requests.get(url, timeout=5)
        if response.ok and response.text.strip():
            f = StringIO(response.text)
            df = pd.read_csv(f)
            if not df.empty:
                column_map = {
                    '<DATE>': 'Data', '<OPEN>': 'Otwarcie', '<HIGH>': 'Najwyzszy',
                    '<LOW>': 'Najnizszy', '<CLOSE>': 'Zamkniecie', '<VOL>': 'Wolumen'
                }
                for eng, pl in column_map.items():
                    if eng in df.columns:
                        df.rename(columns={eng: pl}, inplace=True)
                df['Data'] = pd.to_datetime(df['Data'])
                df = df.sort_values('Data')
                if len(df) >= 20:
                    df['SMA20'] = df['Zamkniecie'].rolling(window=20).mean()
                else:
                    df['SMA20'] = None
                range_map = {
                    '1m': 30, '6m': 182, 'ytd': 'ytd', '1r': 365, '5l': 365*5, 'max': None
                }
                days = range_map.get(selected_range, 182)
                if not df.empty:
                    if days == 'ytd':
                        start = pd.Timestamp(date.today().replace(month=1, day=1))
                        df = df[df['Data'] >= start]
                    elif isinstance(days, int):
                        last_date = df['Data'].max()
                        start = last_date - pd.Timedelta(days=days)
                        df = df[df['Data'] >= start]
                if df.empty:
                    return None
                has_volume = 'Wolumen' in df.columns and not df['Wolumen'].isnull().all()
                if has_volume:
                    volume_colors = [
                        'rgba(0,200,0,0.5)' if close >= open_ else 'rgba(200,0,0,0.5)'
                        for open_, close in zip(df['Otwarcie'], df['Zamkniecie'])
                    ]
                    fig = make_subplots(
                        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        row_width=[0.2, 0.8], subplot_titles=(f'Notowania {ticker.upper()}', 'Wolumen')
                    )
                else:
                    fig = make_subplots(
                        rows=1, cols=1, subplot_titles=(f'Notowania {ticker.upper()}',)
                    )
                fig.add_trace(
                    go.Candlestick(
                        x=df['Data'], open=df['Otwarcie'], high=df['Najwyzszy'],
                        low=df['Najnizszy'], close=df['Zamkniecie'], name='Notowania', showlegend=True
                    ), row=1, col=1
                )
                if len(df) >= 20:
                    fig.add_trace(
                        go.Scatter(
                            x=df['Data'], y=df['SMA20'], mode='lines', name='SMA 20',
                            line=dict(color='orange', width=2), showlegend=True
                        ), row=1, col=1
                    )
                if has_volume:
                    fig.add_trace(
                        go.Bar(
                            x=df['Data'], y=df['Wolumen'], name='Wolumen',
                            marker_color=volume_colors, showlegend=True, opacity=0.7
                        ), row=2, col=1
                    )
                    max_vol = df['Wolumen'].max() if not df['Wolumen'].isnull().all() else 1
                    fig.update_yaxes(title_text="Cena", row=1, col=1, showgrid=True, gridcolor='#e5e5e5')
                    fig.update_yaxes(title_text="Wolumen", row=2, col=1, range=[0, max_vol * 1.05], fixedrange=False, showgrid=True, gridcolor='#e5e5e5')
                    fig.update_xaxes(title_text="Data", row=2, col=1, tickformat='%Y-%m-%d', rangeslider_visible=False, showgrid=True, gridcolor='#e5e5e5')
                else:
                    fig.update_yaxes(title_text="Cena", row=1, col=1, showgrid=True, gridcolor='#e5e5e5')
                    fig.update_xaxes(title_text="Data", row=1, col=1, tickformat='%Y-%m-%d', rangeslider_visible=False, showgrid=True, gridcolor='#e5e5e5')
                fig.update_layout(
                    height=650,
                    xaxis_rangeslider_visible=False,
                    title={
                        'text': f'<b>Wykres notowań dla {ticker.upper()}</b>' if not has_volume else f'<b>Wykres notowań i wolumenu dla {ticker.upper()}</b>',
                        'x': 0.5, 'xanchor': 'center', 'font': {'size': 20}
                    },
                    margin=dict(t=70, b=40, l=40, r=20),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                    plot_bgcolor='white', hovermode='x unified',
                )
                return plot(fig, output_type='div', include_plotlyjs=True)
    except Exception as e:
        print(f"Błąd podczas pobierania danych indeksu: {str(e)}")
    return None