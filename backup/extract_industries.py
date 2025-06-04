import pandas as pd

# Wczytaj dane z pliku CSV
df = pd.read_csv("gpw_spolki.csv")

# Zbierz unikalne branże
unique_industries = sorted(df["industry"].dropna().unique())

# Zapisz do pliku CSV
df_industries = pd.DataFrame(unique_industries, columns=["industry_name"])
df_industries.to_csv("gpw_branze.csv", index=False)

print("Branże zapisane do gpw_branze.csv")