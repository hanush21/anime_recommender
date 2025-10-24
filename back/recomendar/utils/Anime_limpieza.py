import pandas as pd

# --- Configuración ---
input_path = "rating.csv"         # Ruta del CSV original
output_path = "ratings_clean_1.csv"  # Ruta del CSV limpio
max_rows = 7_000_000                     # Límite objetivo de filas (puede pasarse un poco)
min_reviews = 50                      # Mínimo de reviews por usuario
max_missing = 0                       # Máximo de reviews con -1 por usuario

# --- Cargar datos ---
df = pd.read_csv(input_path)

# Verificar columnas necesarias
expected_cols = {"user_id", "anime_id", "rating"}
if not expected_cols.issubset(df.columns):
    raise ValueError(f"El CSV debe contener las columnas: {expected_cols}")

# --- Calcular estadísticas por usuario ---
user_stats = (
    df.groupby("user_id")["rating"]
      .agg(total_reviews="count", missing_reviews=lambda x: (x == -1).sum())
      .reset_index()
)

# --- Filtrar usuarios válidos ---
valid_users = user_stats[
    (user_stats["total_reviews"] >= min_reviews) &
    (user_stats["missing_reviews"] <= max_missing)
]["user_id"]

df_filtered = df[df["user_id"].isin(valid_users)].copy()

# --- Ordenar por usuario para control del límite ---
df_filtered.sort_values(by="user_id", inplace=True)

# --- Seleccionar usuarios hasta (o un poco más de) 1 millón de filas ---
final_users = []
total_rows = 0

for user_id, group in df_filtered.groupby("user_id"):
    group_size = len(group)
    total_rows += group_size
    final_users.append(group)
    if total_rows >= max_rows:
        # Incluimos al usuario completo y luego detenemos
        break

# --- Combinar usuarios seleccionados ---
df_clean = pd.concat(final_users, ignore_index=True)

# --- Guardar resultado ---
df_clean.to_csv(output_path, index=False)

# --- Resumen ---
print(f"Usuarios originales: {df['user_id'].nunique()}")
print(f"Usuarios válidos (>= {min_reviews} reviews y <= {max_missing} '-1'): {len(valid_users)}")
print(f"Total de filas finales: {len(df_clean)} (objetivo {max_rows})")
print(f"Archivo limpio guardado en: {output_path}")