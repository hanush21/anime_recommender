import pandas as pd

input_path = "rating.csv"         
output_path = "ratings_clean_1.csv"  
max_rows = 7_000_000                  
min_reviews = 50                      
max_missing = 0                   


df = pd.read_csv(input_path)


expected_cols = {"user_id", "anime_id", "rating"}
if not expected_cols.issubset(df.columns):
    raise ValueError(f"El CSV debe contener las columnas: {expected_cols}")


user_stats = (
    df.groupby("user_id")["rating"]
      .agg(total_reviews="count", missing_reviews=lambda x: (x == -1).sum())
      .reset_index()
)


valid_users = user_stats[
    (user_stats["total_reviews"] >= min_reviews) &
    (user_stats["missing_reviews"] <= max_missing)
]["user_id"]

df_filtered = df[df["user_id"].isin(valid_users)].copy()


df_filtered.sort_values(by="user_id", inplace=True)


final_users = []
total_rows = 0

for user_id, group in df_filtered.groupby("user_id"):
    group_size = len(group)
    total_rows += group_size
    final_users.append(group)
    if total_rows >= max_rows:
        break

df_clean = pd.concat(final_users, ignore_index=True)

df_clean.to_csv(output_path, index=False)


print(f"Usuarios originales: {df['user_id'].nunique()}")
print(f"Usuarios válidos (>= {min_reviews} reviews y <= {max_missing} '-1'): {len(valid_users)}")
print(f"Total de filas finales: {len(df_clean)} (objetivo {max_rows})")
print(f"Archivo limpio guardado en: {output_path}")