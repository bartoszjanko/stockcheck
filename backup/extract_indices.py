import pandas as pd

# Wczytaj dane z pliku CSV
df = pd.read_csv("gpw_spolki.csv")

# Zbierz wszystkie indeksy z kolumny 'indices'
all_indices = []

for indices in df["indices"]:
    # Rozdziel po przecinku i usuń spacje
    parts = [index.strip() for index in indices.split(',')]
    all_indices.extend(parts)

# Usuń duplikaty i posortuj
unique_indices = sorted(set(all_indices))

# Zapisz do nowego pliku CSV
df_indices = pd.DataFrame(unique_indices, columns=["index_name"])
df_indices.to_csv("gpw_indeksy.csv", index=False)

print("Indeksy zapisane do gpw_indeksy.csv")