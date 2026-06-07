"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           PIPELINE MAESTRO — PREDICCIÓN DE CHURN                           ║
║           Arca Continental · Canal Tradicional México 2024                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Orden de ejecución:                                                         ║
║    1. EDA          → análisis exploratorio y validaciones de calidad         ║
║    2. Features     → ingeniería de variables temporales                      ║
║    3. Predicción   → aplicar modelo CatBoost sobre el test                   ║
║    4. Normalización→ redistribuir scores (65 % bajo / 24 % medio / 11 % alto)║
║    5. Master       → construir el CSV maestro final para el dashboard        ║
║                                                                               ║
║  Archivos de entrada requeridos (misma carpeta que este script):              ║
║    · Clientes.csv                · Sales_churn_train.csv                     ║
║    · Coolers.csv                 · Sales_churn_test.csv                      ║
║    · preds_submission.csv        · catboost_model.cbm                        ║
║                                                                               ║
║  Archivos intermedios generados automáticamente:                              ║
║    · train_features.csv          · snapshot.csv                              ║
║    · coolers_unico.csv           · sales_historial_unico.csv                 ║
║                                                                               ║
║  Archivos de salida finales:                                                  ║
║    · results.csv                 → predicciones crudas del modelo            ║
║    · results_normalized.csv      → scores redistribuidos [0, 1]              ║
║    · master_predictions_data.csv → tabla maestra para el dashboard           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTACIONES GLOBALES
# ─────────────────────────────────────────────────────────────────────────────
import warnings
warnings.filterwarnings("ignore")

import sys
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # backend sin pantalla (para entornos de servidor)
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from scipy import stats
from scipy.stats import rankdata, mannwhitneyu

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN GLOBAL (ajustar si cambian los nombres de archivo o umbrales)
# ─────────────────────────────────────────────────────────────────────────────
ARCHIVOS = {
    "clientes"    : "Clientes.csv",
    "coolers"     : "Coolers.csv",
    "train"       : "Sales_churn_train.csv",
    "test"        : "Sales_churn_test.csv",
    "submission"  : "preds_submission.csv",
    "modelo"      : "catboost_model.cbm",
}

# Parámetros de negocio para la normalización de scores
PCT_BAJO               = 0.65    # fracción de clientes en segmento Bajo
PCT_MEDIO              = 0.89    # fracción acumulada Bajo + Medio
SCORE_CORTE_BAJO_MEDIO = 0.33    # umbral de score que separa Bajo de Medio
SCORE_CORTE_MEDIO_ALTO = 0.65    # umbral de score que separa Medio de Alto
THRESHOLD_MODELO       = 0.466   # threshold de decisión del CatBoost

# Paleta de colores unificada para todas las gráficas
COLOR_NO_CHURN = "#4CAF50"
COLOR_CHURN    = "#F44336"
COLOR_NEUTRAL  = "#42A5F5"
COLOR_WARN     = "#FF9800"

# Estilo visual compartido
plt.rcParams.update({
    "figure.facecolor" : "white",
    "axes.facecolor"   : "#f9f9f9",
    "axes.spines.top"  : False,
    "axes.spines.right": False,
    "font.family"      : "DejaVu Sans",
    "axes.titlesize"   : 13,
    "axes.labelsize"   : 11,
    "axes.titleweight" : "bold",
})


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES DE LOGGING
# ─────────────────────────────────────────────────────────────────────────────
def banner(titulo: str) -> None:
    """Imprime un banner visual para separar las etapas del pipeline."""
    linea = "═" * 70
    print(f"\n{linea}")
    print(f"  {titulo}")
    print(f"{linea}\n")


def ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def info(msg: str) -> None:
    print(f"  ·  {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠  {msg}")


def error_exit(msg: str) -> None:
    print(f"\n  ✗  ERROR: {msg}")
    sys.exit(1)


def verificar_archivos(archivos: dict) -> None:
    """Verifica que todos los archivos de entrada existan antes de empezar."""
    import os
    faltantes = [v for k, v in archivos.items() if not os.path.exists(v)]
    if faltantes:
        error_exit(
            f"No se encontraron los siguientes archivos: {faltantes}\n"
            "  Asegúrate de ejecutar este script desde la carpeta donde están los CSV."
        )
    ok(f"Todos los archivos de entrada encontrados ({len(archivos)})")


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 1 — EDA: ANÁLISIS EXPLORATORIO Y VALIDACIONES DE CALIDAD
# ══════════════════════════════════════════════════════════════════════════════
def etapa_eda() -> dict:
    """
    Carga los cinco CSV fuente, valida la calidad de los datos y genera
    estadísticas descriptivas. Devuelve un diccionario con los DataFrames
    cargados para que las etapas siguientes no tengan que releerlos del disco.
    """
    banner("ETAPA 1 — EDA: Análisis Exploratorio y Validaciones")

    # ── Carga ────────────────────────────────────────────────────────────────
    clientes    = pd.read_csv(ARCHIVOS["clientes"])
    coolers     = pd.read_csv(ARCHIVOS["coolers"])
    sales_train = pd.read_csv(ARCHIVOS["train"])
    sales_test  = pd.read_csv(ARCHIVOS["test"])
    submission  = pd.read_csv(ARCHIVOS["submission"])

    for nombre, df in [("clientes", clientes), ("coolers", coolers),
                        ("sales_train", sales_train), ("sales_test", sales_test)]:
        n_cli = df["customer_id"].nunique() if "customer_id" in df.columns else "—"
        info(f"{nombre:15s}: {df.shape[0]:>9,} filas × {df.shape[1]} cols  "
             f"| clientes únicos: {n_cli}")

    # ── Validaciones de negocio ───────────────────────────────────────────────
    print()
    info("Validaciones de negocio:")

    # Nulos
    for nombre, df in [("clientes", clientes), ("coolers", coolers),
                        ("train", sales_train), ("test", sales_test)]:
        n_nulos = df.isnull().sum().sum()
        if n_nulos == 0:
            ok(f"[{nombre}] Sin valores nulos")
        else:
            warn(f"[{nombre}] {n_nulos} valores nulos detectados")

    # Valores negativos en sales_train
    n_neg_trans = (sales_train["num_transacciones"] < 0).sum()
    n_neg_boxes = (sales_train["uni_boxes_sold_m"]  < 0).sum()
    if n_neg_trans == 0 and n_neg_boxes == 0:
        ok("[train] Sin valores negativos en transacciones ni cajas")
    else:
        warn(f"[train] Negativos: {n_neg_trans} en transacciones, {n_neg_boxes} en cajas")

    # Target válido
    vals_target = set(sales_train["target"].unique())
    if vals_target <= {0, 1}:
        ok(f"[train] Target solo contiene {{0, 1}}")
    else:
        warn(f"[train] Target contiene valores inesperados: {vals_target}")

    # Duplicados en clientes
    n_dup = clientes.duplicated(subset=["customer_id"]).sum()
    if n_dup == 0:
        ok("[clientes] Sin customer_id duplicados")
    else:
        warn(f"[clientes] {n_dup} customer_id duplicados")

    # ── Distribución del target ───────────────────────────────────────────────
    print()
    tasa_churn = sales_train["target"].mean() * 100
    info(f"Tasa de churn global en train: {tasa_churn:.1f}%")
    info(f"Desbalance: {(1-sales_train['target'].mean())/sales_train['target'].mean():.1f}:1  "
         f"(No Churn : Churn)")

    # ── Coherencia de IDs entre archivos ─────────────────────────────────────
    print()
    ids = {
        "clientes"   : set(clientes["customer_id"].astype(str)),
        "coolers"    : set(coolers["customer_id"].astype(str)),
        "train"      : set(sales_train["customer_id"].astype(str)),
        "test"       : set(sales_test["customer_id"].astype(str)),
    }
    universo = set.union(*ids.values())
    info(f"Universo total de customer_id únicos: {len(universo):,}")
    for nombre, id_set in ids.items():
        otros    = set.union(*[v for k, v in ids.items() if k != nombre])
        huerfanos = id_set - otros
        status = "✓" if len(huerfanos) == 0 else "⚠"
        info(f"  {status} [{nombre}] IDs totales: {len(id_set):,}  |  "
             f"huérfanos: {len(huerfanos)}")

    ok("EDA completado")
    return {
        "clientes"   : clientes,
        "coolers"    : coolers,
        "sales_train": sales_train,
        "sales_test" : sales_test,
        "submission" : submission,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 2 — FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════
def etapa_features(datos: dict) -> pd.DataFrame:
    """
    Construye todas las variables temporales (lags, medias rodantes, deltas,
    ratios, z-scores, recency, etc.) sobre el dataset de entrenamiento.
    Guarda train_features.csv y snapshot.csv para uso posterior.
    Devuelve el DataFrame enriquecido.
    """
    banner("ETAPA 2 — Feature Engineering")

    clientes    = datos["clientes"]
    coolers     = datos["coolers"]
    sales_train = datos["sales_train"]

    # ── Merge mensual base ───────────────────────────────────────────────────
    data = (
        sales_train
        .merge(coolers,  on=["customer_id", "calmonth"], how="left")
        .merge(clientes, on="customer_id",               how="left")
    )
    info(f"Dataset base para features: {data.shape[0]:,} filas × {data.shape[1]} cols")

    df = data.copy()
    df = df.sort_values(["customer_id", "calmonth"]).reset_index(drop=True)

    variables = ["num_transacciones", "uni_boxes_sold_m"]

    # ── Lags (1, 2, 3 meses) ─────────────────────────────────────────────────
    for var in variables:
        for lag in [1, 2, 3]:
            df[f"{var}_lag_{lag}"] = df.groupby("customer_id")[var].shift(lag)

    # ── Medias y sumas rodantes (3 m y 6 m) ──────────────────────────────────
    for var in variables:
        for w, s in [(3, "3m"), (6, "6m")]:
            df[f"{var}_mean_{s}"] = (
                df.groupby("customer_id")[var]
                  .transform(lambda x: x.shift(1).rolling(w, min_periods=1).mean())
            )
            df[f"{var}_sum_{s}"] = (
                df.groupby("customer_id")[var]
                  .transform(lambda x: x.shift(1).rolling(w, min_periods=1).sum())
            )

    # ── Desviación estándar rodante ───────────────────────────────────────────
    for var in variables:
        for w, s in [(3, "3m"), (6, "6m")]:
            df[f"{var}_std_{s}"] = (
                df.groupby("customer_id")[var]
                  .transform(lambda x: x.shift(1).rolling(w, min_periods=2).std())
            )

    # ── Deltas (cambio absoluto) ──────────────────────────────────────────────
    for var in variables:
        df[f"{var}_delta_1m"] = df.groupby("customer_id")[var].diff(1)
        df[f"{var}_delta_3m"] = (
            df[var] -
            df.groupby("customer_id")[var]
              .transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
        )

    # ── Ratios (cambio relativo) ──────────────────────────────────────────────
    EPS = 1e-6
    for var in variables:
        lag1  = df.groupby("customer_id")[var].shift(1)
        mean3 = df.groupby("customer_id")[var].transform(
            lambda x: x.shift(1).rolling(3, min_periods=1).mean()
        )
        df[f"{var}_ratio_1m"] = df[var] / (lag1  + EPS)
        df[f"{var}_ratio_3m"] = df[var] / (mean3 + EPS)

    # ── Meses activos y ratio de actividad (6 m) ─────────────────────────────
    for var in variables:
        df[f"{var}_active_months_6m"] = (
            df.groupby("customer_id")[var]
              .transform(
                  lambda x: x.shift(1).rolling(6, min_periods=1)
                             .apply(lambda y: (y > 0).sum())
              )
        )

    df["hist_months"] = (
        df.groupby("customer_id")["calmonth"]
          .transform(lambda x: (x != 0).cumsum())
    )

    for var in variables:
        df[f"{var}_active_ratio_6m"] = (
            df[f"{var}_active_months_6m"] /
            np.minimum(df["hist_months"] - 1, 6).clip(lower=1)
        )

    # ── Coeficiente de variación ──────────────────────────────────────────────
    for var in variables:
        df[f"{var}_cv_6m"] = df[f"{var}_std_6m"] / (df[f"{var}_mean_6m"] + EPS)

    # ── Z-score rodante (3 m) ─────────────────────────────────────────────────
    EPS_Z = 1
    for var in variables:
        df[f"{var}_zscore_3m"] = (
            (df.groupby("customer_id")[var].shift(1) - df[f"{var}_mean_3m"])
            / (df[f"{var}_std_3m"] + EPS_Z)
        )
        df[f"{var}_zscore_current_3m"] = (
            (df[var] - df[f"{var}_mean_3m"])
            / (df[f"{var}_std_3m"] + EPS_Z)
        )

    # ── Máximo rodante y ratio vs máximo ─────────────────────────────────────
    for var in variables:
        df[f"{var}_max_6m"] = (
            df.groupby("customer_id")[var]
              .transform(lambda x: x.shift(1).rolling(6, min_periods=1).max())
        )
        df[f"{var}_ratio_max_6m"] = df[var] / (df[f"{var}_max_6m"] + EPS)

    # ── Recency: meses desde la última compra ─────────────────────────────────
    df["inactive_month"] = (df["num_transacciones"] == 0).astype(int)
    df["months_since_last_purchase"] = (
        df.groupby((df["inactive_month"] == 0).cumsum()).cumcount()
    )

    # ── Guardar ───────────────────────────────────────────────────────────────
    df.to_csv("train_features.csv", index=False)
    ok(f"train_features.csv guardado  ({df.shape[0]:,} filas × {df.shape[1]} cols)")

    # Snapshot: último registro por cliente
    snapshot = df.sort_values(["customer_id", "calmonth"]).groupby("customer_id").tail(1).copy()
    snapshot.to_csv("snapshot.csv", index=False)
    ok(f"snapshot.csv guardado  ({len(snapshot):,} clientes)")

    features_nuevas = [c for c in df.columns if c not in data.columns]
    info(f"Features generadas: {len(features_nuevas)}")
    ok("Feature Engineering completado")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 3 — PREDICCIÓN CON CATBOOST
# ══════════════════════════════════════════════════════════════════════════════
def etapa_prediccion(datos: dict) -> pd.DataFrame:
    """
    Carga el modelo CatBoost entrenado, construye las features del set de test
    usando el historial de snapshot, predice probabilidades de churn y aplica
    la regla de negocio (clientes activos → prob ≈ 0).
    Guarda results.csv.
    """
    banner("ETAPA 3 — Predicción con CatBoost")

    try:
        from catboost import CatBoostClassifier, Pool
    except ImportError:
        error_exit("CatBoost no está instalado. Ejecuta: pip install catboost")

    # ── Cargar modelo ────────────────────────────────────────────────────────
    model = CatBoostClassifier()
    model.load_model(ARCHIVOS["modelo"])
    ok(f"Modelo cargado: {ARCHIVOS['modelo']}")

    # ── Columnas y categóricas requeridas por el modelo ──────────────────────
    CAT_COLS = ["territory_d", "comercial_subchannel_d", "rtm_customer_size_d"]

    FEATURES = [
        "months_since_last_purchase",
        "num_transacciones_lag_1",
        "territory_d",
        "num_transacciones_delta_1m",
        "num_coolers",
        "num_doors",
        "rtm_customer_size_d",
        "comercial_subchannel_d",
        "uni_boxes_sold_m_lag_1",
        "uni_boxes_sold_m_delta_1m",
        "num_transacciones_zscore_3m",
        "num_transacciones_mean_6m",
        "num_transacciones_mean_3m",
        "num_transacciones_max_6m",
        "uni_boxes_sold_m_lag_2",
        "uni_boxes_sold_m_active_ratio_6m",
        "num_transacciones_sum_6m",
        "uni_boxes_sold_m_zscore_3m",
        "num_transacciones_delta_3m",
        "num_transacciones_active_ratio_6m",
    ]

    # ── Función: construir features del test con contexto histórico ───────────
    def build_features(snapshot_df: pd.DataFrame,
                       history_df: pd.DataFrame) -> pd.DataFrame:
        """
        Reconstruye las features temporales para snapshot_df usando history_df
        como contexto. Garantiza no data-leakage al hacer merge con el historial
        y extraer solo las filas del snapshot al final.
        """
        snap = snapshot_df.copy()
        hist = history_df.copy()

        for frame in [snap, hist]:
            frame["customer_id"] = frame["customer_id"].astype(str)
            frame["calmonth"]    = frame["calmonth"].astype(int)

        full = (
            pd.concat([hist, snap], ignore_index=True)
              .drop_duplicates(subset=["customer_id", "calmonth"], keep="last")
              .sort_values(["customer_id", "calmonth"])
              .reset_index(drop=True)
        )

        EPS = 1e-6

        # Lags
        full["num_transacciones_lag_1"] = full.groupby("customer_id")["num_transacciones"].shift(1)
        full["uni_boxes_sold_m_lag_1"]  = full.groupby("customer_id")["uni_boxes_sold_m"].shift(1)
        full["uni_boxes_sold_m_lag_2"]  = full.groupby("customer_id")["uni_boxes_sold_m"].shift(2)

        # Deltas
        full["num_transacciones_delta_1m"] = (
            full["num_transacciones"] - full["num_transacciones_lag_1"]
        )
        full["uni_boxes_sold_m_delta_1m"] = (
            full["uni_boxes_sold_m"] - full["uni_boxes_sold_m_lag_1"]
        )

        # Medias rodantes
        for w, s in [(3, "3m"), (6, "6m")]:
            full[f"num_transacciones_mean_{s}"] = (
                full.groupby("customer_id")["num_transacciones"]
                    .transform(lambda x: x.rolling(w, min_periods=1).mean())
            )

        # Máximo, suma, delta 3 m
        full["num_transacciones_max_6m"] = (
            full.groupby("customer_id")["num_transacciones"]
                .transform(lambda x: x.rolling(6, min_periods=1).max())
        )
        full["num_transacciones_sum_6m"] = (
            full.groupby("customer_id")["num_transacciones"]
                .transform(lambda x: x.rolling(6, min_periods=1).sum())
        )
        full["num_transacciones_delta_3m"] = (
            full["num_transacciones"] -
            full.groupby("customer_id")["num_transacciones"].shift(3)
        )

        # Z-scores
        for var in ["num_transacciones", "uni_boxes_sold_m"]:
            full[f"{var}_zscore_3m"] = (
                full.groupby("customer_id")[var]
                    .transform(lambda s: (s - s.rolling(3, min_periods=1).mean()) /
                                         (s.rolling(3, min_periods=1).std().replace(0, np.nan)))
            )

        # Ratios de actividad
        for var in ["num_transacciones", "uni_boxes_sold_m"]:
            full[f"{var}_active_ratio_6m"] = (
                full.groupby("customer_id")[var]
                    .transform(lambda s: (s > 0).rolling(6, min_periods=1).mean())
            )

        # Recency
        full["had_purchase"]    = (full["num_transacciones"] > 0).astype(int)
        full["last_purchase_month"] = (
            full.groupby("customer_id")
                .apply(lambda g: g["calmonth"].where(g["had_purchase"] == 1).ffill())
                .reset_index(level=0, drop=True)
        )
        full["months_since_last_purchase"] = full.groupby("customer_id").cumcount()

        # Extraer solo el snapshot
        keys   = snap[["customer_id", "calmonth"]].drop_duplicates()
        result = full.merge(keys, on=["customer_id", "calmonth"], how="inner")

        # Limpiar tipos
        for c in CAT_COLS:
            if c in result.columns:
                result[c] = result[c].fillna("unknown").astype(str)
        for c in result.columns:
            if c not in CAT_COLS + ["customer_id", "calmonth"]:
                result[c] = pd.to_numeric(result[c], errors="coerce")

        return result

    def clean_for_catboost(df: pd.DataFrame, cat_cols: list) -> pd.DataFrame:
        """Garantiza tipos correctos para CatBoost: str en categóricas, numérico en el resto."""
        df = df.copy()
        for c in cat_cols:
            if c in df.columns:
                df[c] = df[c].astype(str).fillna("unknown")
        for c in df.columns:
            if c not in cat_cols + ["customer_id", "calmonth"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    # ── Preparar test ─────────────────────────────────────────────────────────
    clientes = datos["clientes"]
    coolers  = datos["coolers"]
    test     = datos["sales_test"].copy()

    test = test.merge(coolers,  on=["customer_id", "calmonth"], how="left")
    test = test.merge(clientes, on="customer_id",               how="left")

    snapshot_test = (
        test.sort_values(["customer_id", "calmonth"])
            .groupby("customer_id")
            .tail(1)
            .copy()
    )
    history_df   = pd.read_csv("snapshot.csv")

    info(f"Construyendo features para {len(snapshot_test):,} clientes de test…")
    features_test = build_features(snapshot_test, history_df)

    X_pred = features_test[FEATURES].copy()
    X_pred = clean_for_catboost(X_pred, CAT_COLS)

    # ── Predicción ────────────────────────────────────────────────────────────
    cat_idx   = [FEATURES.index(c) for c in CAT_COLS if c in FEATURES]
    pool_pred = Pool(data=X_pred, cat_features=cat_idx)

    probs = model.predict_proba(pool_pred)[:, 1]
    preds = (probs > THRESHOLD_MODELO).astype(int)

    # Regla de negocio: cliente activo en el último mes → no churn
    mask_activo = (
        (snapshot_test["num_transacciones"].values > 0) &
        (snapshot_test["uni_boxes_sold_m"].values  > 0)
    )
    probs[mask_activo] = np.minimum(probs[mask_activo], 0.01)
    preds[mask_activo] = 0

    # ── Guardar results.csv ───────────────────────────────────────────────────
    df_results = pd.DataFrame({
        "target"      : preds,
        "customer_id" : snapshot_test["customer_id"].values,
        "probability" : probs,
    })
    df_results.to_csv("results.csv", index=False)

    ok(f"results.csv guardado  ({len(df_results):,} clientes)")
    info(f"Predicciones churn = 1: {preds.sum():,} ({preds.mean()*100:.1f}%)")
    info(f"Probabilidad media    : {probs.mean():.4f}")
    ok("Predicción completada")
    return df_results


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 4 — NORMALIZACIÓN DE SCORES
# ══════════════════════════════════════════════════════════════════════════════
def etapa_normalizacion() -> pd.DataFrame:
    """
    Lee results.csv, aplica la transformación de tres fases:
      1. Rango ordinal (romper empates)
      2. Interpolación lineal por tramos (alinear con reglas de negocio)
      3. Schema alignment (reordenar columnas)
    Verifica monotonicidad y distribución objetivo.
    Guarda results_normalized.csv.
    """
    banner("ETAPA 4 — Normalización de Scores (Rank + Piecewise Interpolation)")

    df_raw = pd.read_csv("results.csv")
    probs  = df_raw["probability"].values
    n      = len(probs)

    # Diagnóstico de baja entropía
    valor_modal = pd.Series(probs).mode()[0]
    n_modal     = (probs == valor_modal).sum()
    info(f"Score modal: {valor_modal}  —  afecta al {n_modal/n*100:.1f}% de los registros")
    info(f"Valores únicos disponibles: {len(np.unique(probs)):,}  de {n:,} posibles")

    # ── Fase 1: Rango Ordinal ─────────────────────────────────────────────────
    rank      = rankdata(probs, method="ordinal")
    rank_norm = (rank - 1) / (n - 1)
    ok(f"Fase 1 — Rango Ordinal: {len(np.unique(rank_norm)):,} valores únicos (sin empates)")

    # ── Fase 2: Interpolación Lineal por Tramos ───────────────────────────────
    xp = [0.0, PCT_BAJO, PCT_MEDIO, 1.0]
    fp = [0.0, SCORE_CORTE_BAJO_MEDIO, SCORE_CORTE_MEDIO_ALTO, 1.0]
    transformed = np.round(np.interp(rank_norm, xp, fp), 6)
    ok(f"Fase 2 — Interpolación: rango [{transformed.min():.4f}, {transformed.max():.4f}]")

    # ── Fase 3: Schema Alignment ──────────────────────────────────────────────
    df_out = pd.DataFrame({
        "target"      : transformed,
        "customer_id" : df_raw["customer_id"].values,
    })

    # ── Validación: distribución por segmentos ────────────────────────────────
    buckets = pd.cut(
        transformed,
        bins  =[-0.001, SCORE_CORTE_BAJO_MEDIO, SCORE_CORTE_MEDIO_ALTO, 1.001],
        labels=["Bajo", "Medio", "Alto"],
    )
    counts  = buckets.value_counts()
    objetivo = {"Bajo": PCT_BAJO, "Medio": PCT_MEDIO - PCT_BAJO, "Alto": 1 - PCT_MEDIO}

    print()
    info("Distribución de scores normalizado:")
    for seg in ["Bajo", "Medio", "Alto"]:
        cnt  = counts[seg]
        real = cnt / n * 100
        obj  = objetivo[seg] * 100
        flag = "✓" if abs(real - obj) < 0.2 else "⚠"
        info(f"  {flag} {seg:5s}: {cnt:>8,} clientes  ({real:.1f}%  objetivo: {obj:.0f}%)")

    # ── Validación: monotonicidad ─────────────────────────────────────────────
    rng     = np.random.default_rng(42)
    idx_a   = rng.integers(0, n, 50_000)
    idx_b   = rng.integers(0, n, 50_000)
    mask    = probs[idx_a] != probs[idx_b]
    violac  = ((probs[idx_a][mask] > probs[idx_b][mask]) &
               (transformed[idx_a][mask] <= transformed[idx_b][mask])).sum()
    ok(f"Monotonicidad  — violaciones: {violac}  {'✓' if violac == 0 else '⚠ REVISAR'}")

    df_out.to_csv("results_normalized.csv", index=False)
    ok("results_normalized.csv guardado")
    ok("Normalización completada")
    return df_out


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 5 — MASTER GENERATOR: CSV MAESTRO PARA EL DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def etapa_master(datos: dict) -> pd.DataFrame:
    """
    Construye el CSV maestro que une:
      · results_normalized.csv  → scores normalizados (base)
      · Clientes.csv            → atributos estáticos (territorio, subcanal, tamaño)
      · coolers_unico.csv       → promedio de coolers y puertas por cliente
      · sales_historial_unico.csv → promedio histórico de transacciones y cajas

    Genera previamente coolers_unico.csv y sales_historial_unico.csv si no existen.
    Guarda master_predictions_data.csv.
    """
    banner("ETAPA 5 — Master Generator: CSV Maestro")

    clientes    = datos["clientes"]
    coolers_raw = datos["coolers"]
    train       = datos["sales_train"]
    test        = datos["sales_test"]

    # ── Generar coolers_unico.csv ─────────────────────────────────────────────
    # Un registro por cliente con el promedio histórico de coolers y puertas.
    col_id      = coolers_raw.columns[0]
    col_coolers = coolers_raw.columns[2]
    col_doors   = coolers_raw.columns[3]

    df_coolers_unico = (
        coolers_raw.groupby(col_id)[[col_coolers, col_doors]]
                   .mean()
                   .reset_index()
                   .rename(columns={
                       col_coolers: "promedio_num_coolers",
                       col_doors  : "promedio_num_doors",
                   })
    )
    df_coolers_unico.to_csv("coolers_unico.csv", index=False)
    ok(f"coolers_unico.csv generado  ({len(df_coolers_unico):,} clientes únicos)")

    # ── Generar sales_historial_unico.csv ─────────────────────────────────────
    # Limpieza de negativos en train + concatenación con test + promedio por cliente.
    col_trans  = train.columns[2]
    col_boxes  = train.columns[3]
    col_target = "target" if "target" in train.columns else train.columns[4]

    # Negativos con target = 0 → eliminar
    cond_neg   = (train[col_trans] < 0) | (train[col_boxes] < 0)
    train_clean = train[~(cond_neg & (train[col_target] == 0))].copy()

    # Negativos con target = 1 → convertir a 0
    mask_mod = cond_neg & (train_clean[col_target] == 1)
    train_clean.loc[mask_mod & (train_clean[col_trans] < 0), col_trans] = 0
    train_clean.loc[mask_mod & (train_clean[col_boxes] < 0), col_boxes] = 0

    info(f"Limpieza de train: {(cond_neg & (train[col_target] == 0)).sum()} filas eliminadas, "
         f"{mask_mod.sum()} corregidas")

    df_historial = pd.concat([train_clean, test], ignore_index=True)
    df_ventas_unico = (
        df_historial.groupby(df_historial.columns[0])[[col_trans, col_boxes]]
                    .mean()
                    .reset_index()
                    .rename(columns={
                        col_trans: "promedio_num_transacciones",
                        col_boxes: "promedio_uni_boxes_sold_m",
                    })
    )
    df_ventas_unico.to_csv("sales_historial_unico.csv", index=False)
    ok(f"sales_historial_unico.csv generado  ({len(df_ventas_unico):,} clientes únicos)")

    # ── Construir el master ───────────────────────────────────────────────────
    df_base = pd.read_csv("results_normalized.csv")

    # Columna 0 = target (score), columna 1 = customer_id
    col_id_base   = df_base.columns[1]
    col_score     = df_base.columns[0]

    # Reordenar: customer_id primero para el merge, luego recuperar orden
    df_base = df_base.rename(columns={col_score: "prob_churn"})

    # Normalizar nombres de customer_id en archivos secundarios
    for df_aux in [clientes, df_coolers_unico, df_ventas_unico]:
        df_aux.rename(columns={df_aux.columns[0]: col_id_base}, inplace=True)

    df_master = (
        df_base
        .merge(clientes,          on=col_id_base, how="left")
        .merge(df_coolers_unico,  on=col_id_base, how="left")
        .merge(df_ventas_unico,   on=col_id_base, how="left")
        .fillna(0)
    )

    # Reordenar columnas: prob_churn → primera, customer_id → segunda
    otras = [c for c in df_master.columns if c not in ["prob_churn", col_id_base]]
    df_master = df_master[["prob_churn", col_id_base] + otras]

    df_master.to_csv("master_predictions_data.csv", index=False)

    ok(f"master_predictions_data.csv guardado")
    info(f"  Filas    : {len(df_master):,}")
    info(f"  Columnas : {df_master.shape[1]}  →  {df_master.columns.tolist()}")
    ok("Master Generator completado")
    return df_master


# ══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA — ORQUESTADOR DEL PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    """
    Orquesta la ejecución secuencial de las cinco etapas.
    Mide el tiempo de cada etapa y el total del pipeline.
    """
    print(__doc__)

    t_inicio = time.time()

    # ── Verificar archivos de entrada ─────────────────────────────────────────
    banner("VERIFICACIÓN DE ARCHIVOS DE ENTRADA")
    verificar_archivos(ARCHIVOS)

    tiempos = {}

    # ── Etapa 1: EDA ──────────────────────────────────────────────────────────
    t0    = time.time()
    datos = etapa_eda()
    tiempos["EDA"] = time.time() - t0

    # ── Etapa 2: Feature Engineering ─────────────────────────────────────────
    t0 = time.time()
    etapa_features(datos)
    tiempos["Features"] = time.time() - t0

    # ── Etapa 3: Predicción ───────────────────────────────────────────────────
    t0 = time.time()
    etapa_prediccion(datos)
    tiempos["Predicción"] = time.time() - t0

    # ── Etapa 4: Normalización ────────────────────────────────────────────────
    t0 = time.time()
    etapa_normalizacion()
    tiempos["Normalización"] = time.time() - t0

    # ── Etapa 5: Master Generator ─────────────────────────────────────────────
    t0 = time.time()
    etapa_master(datos)
    tiempos["Master"] = time.time() - t0

    # ── Resumen final ─────────────────────────────────────────────────────────
    banner("PIPELINE COMPLETADO ✓")

    print("  Tiempos por etapa:")
    for etapa, segundos in tiempos.items():
        print(f"    {etapa:15s}: {segundos:6.1f} s")
    print(f"\n  Tiempo total: {time.time() - t_inicio:.1f} s\n")

    print("  Archivos de salida generados:")
    import os
    for archivo in ["results.csv", "results_normalized.csv",
                    "master_predictions_data.csv",
                    "train_features.csv", "snapshot.csv",
                    "coolers_unico.csv", "sales_historial_unico.csv"]:
        if os.path.exists(archivo):
            size = os.path.getsize(archivo) / 1024**2
            ok(f"{archivo:40s}  ({size:.2f} MB)")
        else:
            warn(f"{archivo}  — no encontrado")


if __name__ == "__main__":
    main()
