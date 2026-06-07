import streamlit as st
import pandas as pd
import base64
from pathlib import Path
import os
print(os.getcwd())
print(os.listdir())
import os
from google import genai
from chesco_prompt import SYSTEM_INSTRUCTION

# ─── CONFIGURACIÓN DE PÁGINA ───────────────────────────────────────────────────
# Cambia page_title para modificar el título que aparece en la pestaña del navegador
# Cambia page_icon para cambiar el emoji/ícono de la pestaña
# layout="wide" hace que la app use todo el ancho de la pantalla
st.set_page_config(
    page_title="Churn Prediction | Arca Continental",  # <- título de la pestaña del browser
    page_icon="🥤",                                     # <- ícono de la pestaña
    layout="wide"
)

# ─── ESTILOS GLOBALES (CSS) ────────────────────────────────────────────────────
# Todo lo que está dentro de <style>...</style> controla la apariencia visual.
# Streamlit no tiene forma nativa de hacer esto tan personalizado, por eso usamos
# st.markdown con HTML/CSS directo. unsafe_allow_html=True es necesario para que funcione.
st.markdown("""
<style>

/* ── TIPOGRAFÍA ──────────────────────────────────────────────────────────────
   Importamos dos fuentes de Google Fonts:
   - "Bebas Neue": fuente de display, usada en títulos grandes
   - "DM Sans": fuente limpia para cuerpo de texto
   Para cambiar las fuentes, reemplaza los nombres aquí y en cada propiedad
   font-family que aparece más abajo */
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'DM Sans', sans-serif; /* <- fuente base de toda la app */
}

/* ── COLOR DE FONDO PRINCIPAL ────────────────────────────────────────────────
   #0d0d0d es casi negro. Cámbialo por cualquier color hex para cambiar el fondo.
   Ejemplo claro: background: #f5f5f5;
   Color blanco: background: #ffffff; */
[data-testid="stAppViewContainer"] {
    background: #ffeaea;   /* <- fondo principal de la app */
    color: #f0ece4;         /* <- color de texto general (blanco hueso) */
}

/* Hace que la barra superior de Streamlit sea transparente */
[data-testid="stHeader"] {
    background: transparent;
}

/* ── BARRA LATERAL (sidebar) ─────────────────────────────────────────────────
   Si no usas sidebar, puedes borrar estos dos bloques sin problema */
[data-testid="stSidebar"] {
    background: #111111;            /* <- fondo del sidebar, un poco más claro que el main */
    border-right: 1px solid #2a2a2a; /* <- línea divisora del sidebar */
}
[data-testid="stSidebar"] * {
    color: #f0ece4 !important; /* <- color de texto dentro del sidebar */
}

/* Oculta el menú hamburguesa de Streamlit y el footer de "Made with Streamlit" */
#MainMenu, footer { visibility: hidden; }


/* ══════════════════════════════════════════════════════════════════════════════
   SECCIÓN HERO (la imagen grande de fondo con el título encima)
   ══════════════════════════════════════════════════════════════════════════════ */

.hero-wrapper {
    position: relative;
    width: 100%;
    height: 480px;      /* <- altura del hero. Súbelo para hacerlo más alto */
    border-radius: 16px; /* <- esquinas redondeadas del hero */
    overflow: hidden;
    margin-bottom: 2.5rem;
}

.hero-img {
    width: 100%;
    height: 100%;
    object-fit: cover;  /* la imagen llena el espacio sin deformarse */
    display: block;
    filter: brightness(0.35); /* <- oscurece la foto. 0=negro, 1=original. Baja para más oscuro */
}

/* Capa de color roja encima de la foto para dar el tono Arca */
.hero-overlay {
    position: absolute;
    inset: 0;
    /* El degradado va de rojo (#C8102E) en la esquina superior izquierda a transparente.
       Cambia el ángulo (135deg) o el color rgba(200,16,46,...) para modificarlo */
    background: linear-gradient(135deg, rgba(200,16,46,0.55) 0%, rgba(0,0,0,0) 60%);
}

/* Posición del texto dentro del hero */
.hero-content {
    position: absolute;
    bottom: 40px; /* <- qué tan arriba del borde inferior está el texto */
    left: 44px;
    right: 44px;
}

/* Texto pequeño sobre el título principal ("Arca Continental") */
.hero-eyebrow {
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #faf7f8; /* <- rojo Arca. Cambia este hex para cambiar el color del eyebrow */
    margin-bottom: 10px;
}

/* Título principal del hero ("Predicción de Churn") */
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    /* clamp(mínimo, preferido, máximo): tamaño responsivo automático */
    font-size: clamp(44px, 6vw, 78px); /* <- tamaño del título hero */
    letter-spacing: 1px;
    color: #ffffff;
    line-height: 1;
    margin: 0 0 14px 0;
}

/* Párrafo descriptivo debajo del título */
.hero-sub {
    font-size: 15px;
    color: rgba(240,236,228); /* <- blanco con 75% de opacidad */
    max-width: 540px; /* <- limita el ancho del párrafo para que no sea muy largo */
    line-height: 1.6;
    margin: 0;
    font-weight: 300;
}


/* ══════════════════════════════════════════════════════════════════════════════
   ETIQUETAS DE SECCIÓN (el texto rojo pequeño tipo "NUESTROS CLIENTES")
   ══════════════════════════════════════════════════════════════════════════════ */
.section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #C8102E; /* <- color del eyebrow de cada sección */
    margin-bottom: 6px;
}

/* Títulos grandes de cada sección */
.section-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 32px;      /* <- tamaño del título de sección */
    color: #c8102e;
    letter-spacing: 0.5px;
    margin: 0 0 1.2rem 0;
}


/* ══════════════════════════════════════════════════════════════════════════════
   TARJETAS DE INFORMACIÓN (las 3 tarjetas: Arca, Churn, Engage)
   ══════════════════════════════════════════════════════════════════════════════ */
.info-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr); /* <- 3 columnas iguales. Cambia a repeat(2,1fr) para 2 */
    gap: 16px;            /* <- espacio entre tarjetas */
    margin-bottom: 2.5rem;
}

.info-card {
    background: #76201a; /* <- fondo de cada tarjeta. Un poco más claro que el fondo principal */
    border: 1px solid #2a2a2a; /* <- borde sutil de las tarjetas */
    border-radius: 14px; /* <- esquinas redondeadas de las tarjetas */
    padding: 24px 22px;
}

.info-card-icon {
    font-size: 28px;      /* <- tamaño del emoji/ícono de la tarjeta */
    margin-bottom: 12px;
}

.info-card-title {
    font-weight: 600;
    font-size: 15px;
    color: #f0ece4;
    margin-bottom: 8px;
}

.info-card-body {
    font-size: 13px;
    color: rgba(240,236,228); /* <- texto del cuerpo de la tarjeta, más tenue */
    line-height: 1.65;
    font-weight: 300;
}


/* ══════════════════════════════════════════════════════════════════════════════
   TARJETAS DE PERSONAS (las fotos de los 3 tipos de cliente)
   ══════════════════════════════════════════════════════════════════════════════ */
.person-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr); /* <- igual que info-grid: 3 columnas */
    gap: 16px;
    margin-bottom: 2.5rem;
}

.person-card {
    position: relative;
    border-radius: 14px;
    overflow: hidden;
    height: 240px; /* <- altura de las tarjetas de foto. Sube para fotos más altas */
}

.person-card img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: brightness(0.45) saturate(0.8); /* <- oscurece y desatura la foto */
    display: block;
}

/* Degradado rojo en la parte inferior de cada foto (donde va el texto) */
.person-card-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(200,16,46,0.7) 0%, transparent 55%);
    /* <- el degradado sube desde abajo (rojo) hacia arriba (transparente) */
}

.person-card-info {
    position: absolute;
    bottom: 18px; /* <- distancia del texto al borde inferior de la foto */
    left: 18px;
    right: 18px;
}

.person-card-name {
    font-weight: 600;
    font-size: 14px;
    color: #fff;
}

.person-card-role {
    font-size: 11px;
    color: rgba(255,255,255,0.7);
    margin-top: 2px;
    font-weight: 300;
}


/* ── LÍNEA DIVISORA ──────────────────────────────────────────────────────────
   Cambia el color #2a2a2a por otro para cambiar el color de la línea */
.divider {
    border: none;
    border-top: 1px solid #2a2a2a;
    margin: 2rem 0;
}


/* ══════════════════════════════════════════════════════════════════════════════
   ZONA DE CARGA DE ARCHIVOS
   ══════════════════════════════════════════════════════════════════════════════ */
.upload-wrapper {
    background: #76201a;
    border: 1.5px dashed #C8102E; /* <- borde punteado rojo que enmarca la zona de carga */
    border-radius: 16px;
    padding: 36px 28px;
    margin-bottom: 2rem;
}

.upload-header {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 22px;
    color: #f0ece4;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.upload-sub {
    font-size: 13px;
    color: rgba(240,236,228,0.45); /* <- texto descriptivo tenue debajo del título */
    margin-bottom: 20px;
    font-weight: 300;
}

/* Los badges rojos que muestran los nombres de los archivos requeridos */
.file-badge {
    display: inline-block;
    background: #C8102E22;          /* <- fondo rojo muy transparente (22 = 13% opacidad) */
    border: 1px solid #C8102E55;    /* <- borde rojo semitransparente */
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    color: #e84060;                 /* <- color del texto del badge */
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-right: 6px;
    margin-bottom: 8px;
}

/* Personaliza el componente nativo de Streamlit para subir archivos */
[data-testid="stFileUploader"] {
    background: #76201a !important;
    border-radius: 10px !important;
    border: 1px solid #2a2a2a !important;
    padding: 4px !important;
    margin-bottom: 10px !important;
}
[data-testid="stFileUploader"] label {
    color: rgba(240,236,228,0.65) !important;
    font-size: 13px !important;
}

/* ── PESTAÑAS (tabs de la vista previa de datos) ─────────────────────────────
   Color del texto de pestaña inactiva y activa */
[data-testid="stTabs"] button {
    color: rgba(240,236,228,0.5) !important; /* <- pestaña inactiva */
    font-size: 13px !important;
    font-weight: 500 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #C8102E !important;              /* <- pestaña activa (rojo Arca) */
    border-bottom-color: #C8102E !important; /* <- línea inferior de la pestaña activa */
}

/* Bordes redondeados para mensajes de alerta de Streamlit */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 14px !important;
}


/* ══════════════════════════════════════════════════════════════════════════════
   BARRA DE ESTADÍSTICAS (los 4 números: +130K clientes, 18 países, etc.)
   ══════════════════════════════════════════════════════════════════════════════ */
.stat-bar {
    display: flex;
    gap: 0;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 2rem;
}

.stat-item {
    flex: 1;               /* cada stat ocupa el mismo ancho */
    padding: 18px 20px;
    border-right: 1px solid #2a2a2a; /* línea divisora entre stats */
}
.stat-item:last-child { border-right: none; } /* quita la línea del último */

.stat-value {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 30px;   /* <- tamaño del número grande en cada stat */
    color: #C8102E;    /* <- color del número (rojo Arca) */
    line-height: 1;
}

.stat-label {
    font-size: 11px;
    color: rgba(227,40,74); /* <- etiqueta tenue debajo del número */
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-top: 4px;
    font-weight: 500;
}

</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN HERO
# La imagen viene de Unsplash. Para cambiarla, reemplaza la URL del src="..."
# por cualquier otra URL de imagen pública o un archivo local.
# ══════════════════════════════════════════════════════════════════════════════
hero_image_path = Path("arcawallpaper.jpg")
hero_image_mime = "image/png" if hero_image_path.suffix.lower() == ".png" else "image/jpeg"
hero_image_src = f"data:{hero_image_mime};base64,{base64.b64encode(hero_image_path.read_bytes()).decode()}"

st.markdown(f"""
<div class="hero-wrapper">
  <img class="hero-img"
       src="{hero_image_src}"
       alt="Arca Continental operations" />
  <!-- Capa roja encima de la imagen -->
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <!-- Texto pequeño sobre el título. Cámbialo aquí directamente -->
    <p class="hero-eyebrow">Arca Continental</p>
    <!-- Título principal del hero. El <br> es un salto de línea -->
    <h1 class="hero-title">Predicción<br>de Churn</h1>
    <!-- Párrafo descriptivo -->
    <p class="hero-sub">
      Anticipa la pérdida de clientes antes de que ocurra. 
      Carga tus archivos y obtén predicciones accionables al instante.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# BARRA DE ESTADÍSTICAS
# Para cambiar un número o etiqueta, edita el texto dentro de
# <div class="stat-value"> y <div class="stat-label"> respectivamente.
# Para agregar más stats, copia y pega un bloque <div class="stat-item">...</div>
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="stat-bar">
  <div class="stat-item">
    <div class="stat-value">+130K</div>          <!-- número grande -->
    <div class="stat-label">Clientes activos</div> <!-- etiqueta debajo -->
  </div>
  <div class="stat-item">
    <div class="stat-value">18</div>
    <div class="stat-label">Países de operación</div>
  </div>
  <div class="stat-item">
    <div class="stat-value">~8%</div>
    <div class="stat-label">Tasa de churn promedio</div>
  </div>
  <div class="stat-item">
    <div class="stat-value">ML</div>
    <div class="stat-label">Modelo predictivo</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TARJETAS DE INFORMACIÓN
# Cada tarjeta tiene: info-card-icon (emoji), info-card-title y info-card-body.
# Para agregar una tarjeta, copia un bloque <div class="info-card">...</div>
# Recuerda también cambiar el grid a repeat(4, 1fr) si añades una 4ta tarjeta.
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="info-grid">
  <div class="info-card">
    <div class="info-card-icon">🥤</div>          <!-- cambia el emoji aquí -->
    <div class="info-card-title">Arca Continental</div>
    <div class="info-card-body">
      Una de las embotelladoras más importantes de Coca-Cola en América Latina, 
      con presencia en México, Sudamérica y Estados Unidos.
    </div>
  </div>
  <div class="info-card">
    <div class="info-card-icon">📊</div>
    <div class="info-card-title">¿Qué es el Churn?</div>
    <div class="info-card-body">
      Ocurre cuando un cliente deja de comprar o reduce significativamente su 
      actividad. Predecirlo permite actuar antes de que la pérdida sea definitiva.
    </div>
  </div>
  <div class="info-card">
    <div class="info-card-icon">🎯</div>
    <div class="info-card-title">Engage & Retención</div>
    <div class="info-card-body">
      Analizar ventas, coolers y comportamiento del cliente permite diseñar 
      estrategias de retención personalizadas y altamente efectivas.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TARJETAS DE PERSONAS (fotos de tipos de cliente)
# Para cambiar una foto, reemplaza la URL dentro de src="..."
# por cualquier URL de imagen pública de Unsplash u otro servicio.
# El texto debajo de cada foto se edita en person-card-name y person-card-role.
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<p class="section-label">Nuestros Clientes</p>', unsafe_allow_html=True)
st.markdown(
    """
    <h2 style="
        color:#e3284a;
        font-family:'Bebas Neue',sans-serif;
        font-size:32px;
        letter-spacing:0.5px;
    ">
        El éxito de nuestra empresa se mide en la sonrisa de quien nos elige
    </h2>
    """,
    unsafe_allow_html=True
)

st.markdown("""
<div class="person-grid">
  <div class="person-card">
    <!-- URL de la foto. Cámbiala para mostrar otra imagen -->
    <img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&q=80" alt="Cliente 1" />
    <div class="person-card-overlay"></div>
    <div class="person-card-info">
      <div class="person-card-name">Punto de venta tradicional</div>    <!-- nombre/tipo -->
      <div class="person-card-role">Tiendas de abarrotes · Canal tradicional</div> <!-- subtítulo -->
    </div>
  </div>
  <div class="person-card">
    <img src="https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=400&q=80" alt="Cliente 2" />
    <div class="person-card-overlay"></div>
    <div class="person-card-info">
      <div class="person-card-name">Restaurantes y HORECA</div>
      <div class="person-card-role">Hospitality · Food Service</div>
    </div>
  </div>
  <div class="person-card">
    <img src="https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=400&q=80" alt="Cliente 3" />
    <div class="person-card-overlay"></div>
    <div class="person-card-info">
      <div class="person-card-name">Retail moderno</div>
      <div class="person-card-role">Supermercados · Autoservicios</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Línea divisora horizontal
st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ZONA DE CARGA DE ARCHIVOS
# La parte decorativa (cuadro rojo punteado + badges) es solo visual HTML.
# Los uploaders reales de Streamlit están debajo, divididos en 2 columnas.
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="upload-wrapper">
  <div class="upload-header">Carga tus archivos</div>
  <div class="upload-sub">Arrastra o selecciona los 5 archivos CSV requeridos para iniciar el análisis</div>
  <!-- Badges decorativos que muestran los nombres de archivos esperados -->
  <span class="file-badge">clientes.csv</span>
  <span class="file-badge">coolers.csv</span>
  <span class="file-badge">preds_submission.csv</span>
  <span class="file-badge">sales_test.csv</span>
  <span class="file-badge">sales_train.csv</span>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "📋 Carga los 5 archivos CSV",
    type=["csv"],
    accept_multiple_files=True,
    help="Selecciona los 5 archivos CSV requeridos en un solo paso."
)

file_map = {file.name.lower(): file for file in uploaded_files} if uploaded_files else {}
required_files = [
    "clientes.csv",
    "coolers.csv",
    "preds_submission.csv",
    "sales_churn_test.csv",
    "sales_churn_train.csv"
]
loaded = len(uploaded_files) if uploaded_files else 0

if loaded > 0:
    st.markdown(f"""
    <div style="background:#C8102E18; border:1px solid #C8102E44; border-radius:10px;
                padding:14px 18px; margin-top:1rem; font-size:14px; color:#f0ece4;">
      ✅ &nbsp;<strong>{loaded} de 5 archivos cargados</strong>
      {'&nbsp;— ¡Listos para analizar!' if loaded == 5 else '&nbsp;— Continúa cargando archivos.'}
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# VISTA PREVIA DE DATOS
# Este bloque solo se ejecuta cuando los 5 archivos fueron cargados correctamente.
# ══════════════════════════════════════════════════════════════════════════════
if all(name in file_map for name in required_files):
    clientes_file = file_map["clientes.csv"]
    coolers_file = file_map["coolers.csv"]
    preds_file = file_map["preds_submission.csv"]
    sales_test_file = file_map["sales_churn_test.csv"]
    sales_train_file = file_map["sales_churn_train.csv"]

    clientes          = pd.read_csv(clientes_file)
    coolers           = pd.read_csv(coolers_file)
    preds_submission  = pd.read_csv(preds_file)
    sales_churn_test  = pd.read_csv(sales_test_file)
    sales_churn_train = pd.read_csv(sales_train_file)

    st.success("Los 5 archivos fueron cargados correctamente")

else:
    if loaded > 0:
        missing = [name for name in required_files if name not in file_map]
        st.warning(
            f"Faltan los siguientes archivos: {', '.join(missing)}. "
            "Asegúrate de que los nombres coincidan exactamente."
        )
    st.markdown("""
    <div style="background:#76201a; border:1px solid #2a2a2a; border-radius:12px;
                padding:24px; text-align:center; margin-top:1.5rem;
                color:rgba(240,236,228,0.35); font-size:14px; font-weight:300;">
      Carga los 5 archivos CSV para visualizar la vista previa de los datos
    </div>
    """, unsafe_allow_html=True)

#==============================================================================
#Siguiente sección: Análisis exploratorio de datos 
#==============================================================================

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN DE RESULTADOS DEL MODELO
# Pega este bloque justo después del comentario:
#   #==============================================================================
#   #Siguiente sección: Análisis exploratorio de datos
#   #==============================================================================
#
# Asegúrate de tener instalado: pip install streamlit pandas plotly
# ══════════════════════════════════════════════════════════════════════════════

import plotly.express as px
import plotly.graph_objects as go

# ── Carga el CSV de predicciones ──────────────────────────────────────────────
# Ajusta la ruta si el archivo está en otro lugar
PREDICTIONS_PATH = "master_predictions_data_3.csv"

@st.cache_data
def load_predictions(path=PREDICTIONS_PATH):
    df = pd.read_csv(path)
    # Ingreso anual estimado: cajas/mes × $50 MXN × 12 meses
    df["revenue_est"] = df["promedio_uni_boxes_sold_m"] * 384 * 12
    # Categoría de riesgo
    df["risk_cat"] = pd.cut(
        df["prob_churn"],
        bins=[0.3,0.331 , 0.65, 1],
        labels=["Bajo (<0.3)", "Medio (0.331-0.65)", "Alto (>0.65)"],
        include_lowest=True,
    )
    # Mapeo territorio → estado (para el mapa)
    territory_to_state = {
        "Guadalajara": "Jalisco", "Jalisco": "Jalisco",
        "Monterrey": "Nuevo León", "Nuevo Leon": "Nuevo León",
        "Saltillo": "Coahuila", "Piedras negras": "Coahuila", "Monclova": "Coahuila",
        "Matamoros": "Tamaulipas", "Laredo": "Tamaulipas", "Reynosa": "Tamaulipas",
        "San Luis Potosi": "San Luis Potosí", "Mesa Central": "Guanajuato",
        "Aguascalientes": "Aguascalientes", "Zacatecas": "Zacatecas",
        "Comarca Lagunera": "Durango", "Durango": "Durango",
        "Culiacan": "Sinaloa", "Mazatlan": "Sinaloa",
        "Juarez": "Chihuahua", "Chihuahua": "Chihuahua", "Delicias": "Chihuahua",
        "Obregon": "Sonora", "Hermosillo": "Sonora",
        "Mexicali": "Baja California", "La Paz": "Baja California Sur",
    }
    df["state"] = df["territory_d"].map(territory_to_state).fillna(df["territory_d"])
    return df

df = load_predictions()

# ── Métricas globales ─────────────────────────────────────────────────────────
total        = len(df)
high_risk    = (df["prob_churn"] >= 0.651).sum()
med_risk     = ((df["prob_churn"] >= 0.331) & (df["prob_churn"] < 0.65)).sum()
low_risk     = (df["prob_churn"] < 0.3).sum()
rev_at_risk  = df.loc[df["prob_churn"] >= 0.651, "revenue_est"].sum()
avg_churn    = df["prob_churn"].mean()

# ── CSS adicional exclusivo de esta sección ───────────────────────────────────
st.markdown("""
<style>
/* ── Tarjetas de métricas KPI ─────────────────────────────────── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 1.5rem 0 2rem 0;
}
.kpi-card {
    background: #711812;
    border: 1px solid #2e1111;
    border-radius: 14px;
    padding: 20px 20px 16px 20px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.kpi-card.red::before   { background: #C8102E; }
.kpi-card.amber::before { background: #e87c2b; }
.kpi-card.green::before { background: #2fb56a; }
.kpi-card.grey::before  { background: #6b6b6b; }

.kpi-label {
    font-size: 10px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: rgba(240,236,228,0.45);
    font-weight: 600;
    margin-bottom: 8px;
}
.kpi-value {
    font-family: "Bebas Neue", sans-serif;
    font-size: 38px;
    line-height: 1;
    color: #f0ece4;
}
.kpi-sub {
    font-size: 11px;
    color: rgba(240,236,228,0.35);
    margin-top: 6px;
    font-weight: 300;
}

/* ── Tabla de clientes ────────────────────────────────────────── */
.risk-table-wrap {
    background: #711e19;
    border: 1px solid #2e1111;
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 2rem;
}
.risk-table-header {
    padding: 18px 22px 14px 22px;
    border-bottom: 1px solid #2e1111;
    display: flex;
    align-items: baseline;
    gap: 12px;
}
.risk-table-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 22px;
    color: #f0ece4;
    letter-spacing: 0.5px;
}
.risk-table-count {
    font-size: 12px;
    color: rgba(240,236,228,0.4);
    font-weight: 300;
}
.risk-tbl {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.risk-tbl th {
    text-align: left;
    padding: 10px 18px;
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(240,236,228,0.35);
    font-weight: 600;
    border-bottom: 1px solid #e3284a;
    background: #76201a;
}
.risk-tbl td {
    padding: 10px 18px;
    color: #f0ece4;
    border-bottom: 1px solid #76201a;
    font-weight: 300;
}
.risk-tbl tr:hover td { background: #220d0d; }

.pill-red    { background:#C8102E22; color:#e84060; border:1px solid #C8102E55;
               border-radius:20px; padding:2px 10px; font-size:11px; font-weight:600; white-space:nowrap; }
.pill-amber  { background:#e87c2b22; color:#e87c2b; border:1px solid #e87c2b55;
               border-radius:20px; padding:2px 10px; font-size:11px; font-weight:600; white-space:nowrap; }
.pill-green  { background:#2fb56a22; color:#2fb56a; border:1px solid #2fb56a55;
               border-radius:20px; padding:2px 10px; font-size:11px; font-weight:600; white-space:nowrap; }

/* ── Bloques de ahorro ────────────────────────────────────────── */
.savings-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 14px;
    margin-bottom: 2rem;
}
.savings-card {
    background: #76201a;
    border: 1px solid #2e1111;
    border-radius: 14px;
    padding: 22px;
}
.savings-scenario {
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(240,236,228,0.4);
    margin-bottom: 6px;
    font-weight: 600;
}
.savings-amount {
    font-family: "Bebas Neue", sans-serif;
    font-size: 34px;
    line-height: 1;
    color: #2fb56a;
}
.savings-amount.amber { color: #e87c2b; }
.savings-amount.red   { color: #e84060; }
.savings-desc {
    font-size: 12px;
    color: rgba(240,236,228,0.45);
    margin-top: 8px;
    line-height: 1.5;
    font-weight: 300;
}

/* ── Tabla top clientes ───────────────────────────────────────── */
.top-tbl-wrap {
    background: #76201a;
    border: 1px solid #2e1111;
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 2rem;
}

/* ── Mapa ─────────────────────────────────────────────────────── */
.map-wrapper {
    background: #76201a;
    border: 1px solid #2e1111;
    border-radius: 14px;
    padding: 22px;
    margin-bottom: 2rem;
}
.map-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 26px;
    color: #f0ece4;
    margin-bottom: 4px;
}
.map-sub {
    font-size: 13px;
    color: rgba(240,236,228,0.4);
    margin-bottom: 16px;
    font-weight: 300;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ENCABEZADO DE SECCIÓN
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<p class="section-label">Resultados del Modelo</p>', unsafe_allow_html=True)
st.markdown("""
<h2 style="font-family:'Bebas Neue',sans-serif;font-size:32px;
           color:#c8102e;letter-spacing:0.5px;margin:0 0 0.2rem 0;">
    Dashboard de Predicción de Churn
</h2>
<p style="font-size:14px;color:rgba(240,236,228,0.5);font-weight:300;margin-bottom:0;">
    Análisis completo sobre los <strong style="color:#f0ece4;">
    {:,}</strong> clientes del modelo &nbsp;·&nbsp;
    Precio estimado por caja: <strong style="color:#f0ece4;">$50 MXN</strong>
</p>
""".format(total), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KPIs PRINCIPALES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card red">
    <div class="kpi-label">Clientes en alto riesgo</div>
    <div class="kpi-value">{high_risk:,}</div>
    <div class="kpi-sub">{high_risk/total*100:.1f}% del total · prob ≥ 65.1%</div>
  </div>
  <div class="kpi-card amber">
    <div class="kpi-label">Ingreso anual en riesgo</div>
    <div class="kpi-value">${rev_at_risk/1e9:.2f}B</div>
    <div class="kpi-sub">MXN estimado (alto riesgo)</div>
  </div>
  <div class="kpi-card green">
    <div class="kpi-label">Clientes en bajo riesgo</div>
    <div class="kpi-value">{low_risk:,}</div>
    <div class="kpi-sub">{low_risk/total*100:.1f}% del portafolio seguro</div>
  </div>
  <div class="kpi-card grey">
    <div class="kpi-label">Prob. churn promedio</div>
    <div class="kpi-value">{avg_churn:.1f}%</div>
    <div class="kpi-sub">Media sobre {total:,} clientes</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TABLA DE PREDICCIONES (con filtro de riesgo)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<p class="section-label">Explorador de Clientes</p>', unsafe_allow_html=True)

col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 1])
with col_f1:
    risk_filter = st.selectbox(
        "Filtrar por nivel de riesgo",
        ["Todos", "Alto (≥65.1%)", "Medio (33.1–65%)", "Bajo (<33.1%)"],
        index=0,
    )
with col_f2:
    terr_options = ["Todos"] + sorted(df["territory_d"].unique().tolist())
    terr_filter = st.selectbox("Filtrar por territorio", terr_options)
with col_f3:
    n_rows = st.selectbox("Filas a mostrar", [50, 100, 200, 500], index=0)

# Aplicar filtros
dff = df.copy()
if risk_filter == "Alto (≥65.1%)":
    dff = dff[dff["prob_churn"] >= 0.651]
elif risk_filter == "Medio (33.1–65%)":
    dff = dff[(dff["prob_churn"] >= 0.331) & (dff["prob_churn"] < 0.65)]
elif risk_filter == "Bajo (<33.1%)":
    dff = dff[dff["prob_churn"] < 0.331]
if terr_filter != "Todos":
    dff = dff[dff["territory_d"] == terr_filter]

dff_show = dff.sort_values("prob_churn", ascending=False).head(n_rows).reset_index(drop=True)

def risk_pill(p):
    if p >= 0.651:
        return f'<span class="pill-red">🔴 {p:.1f}%</span>'
    elif p >= 0.331:
        return f'<span class="pill-amber">🟡 {p:.1f}%</span>'
    else:
        return f'<span class="pill-green">🟢 {p:.1f}%</span>'

def revenue_bar(r, max_r=600000):
    pct = min(r / max_r * 100, 100)
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<div style="width:70px;background:#2e1111;border-radius:4px;height:6px;">'
        f'<div style="width:{pct:.0f}%;background:#C8102E;height:6px;border-radius:4px;"></div>'
        f'</div>'
        f'<span style="font-size:12px;">${r:,.0f}</span>'
        f'</div>'
    )

rows_html = ""
for _, row in dff_show.iterrows():
    cid = str(row["customer_id"])[:14] + "…"
    pill = risk_pill(row["prob_churn"])
    rev  = revenue_bar(row["revenue_est"])
    rows_html += (
        f"<tr>"
        f"<td><code style='font-size:11px;color:#a08080;'>{cid}</code></td>"
        f"<td>{pill}</td>"
        f"<td>{row['territory_d']}</td>"
        f"<td style='color:rgba(240,236,228,0.6);font-size:12px;'>{row['comercial_subchannel_d']}</td>"
        f"<td style='text-align:right;'>{row['promedio_uni_boxes_sold_m']:.1f}</td>"
        f"<td>{rev}</td>"
        f"</tr>"
    )

table_html = f"""
<div class="risk-table-wrap">
  <div class="risk-table-header">
    <span class="risk-table-title">Clientes</span>
    <span class="risk-table-count">{len(dff_show):,} de {len(dff):,} registros</span>
  </div>
  <div style="overflow-x:auto; max-height:420px; overflow-y:auto;">
    <table class="risk-tbl">
      <thead>
        <tr>
          <th>Cliente ID</th>
          <th>Prob. Churn</th>
          <th>Territorio</th>
          <th>Subchannel</th>
          <th>Cajas / mes</th>
          <th>Ingreso anual est.</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>
"""
st.markdown(table_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUES DE AHORRO POTENCIAL + TABLA TOP CLIENTES RIESGOSOS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<p class="section-label">Impacto Financiero</p>', unsafe_allow_html=True)
st.markdown("""
<h2 style="font-family:'Bebas Neue',sans-serif;font-size:28px;
           color:#c8102e;letter-spacing:0.5px;margin:0 0 1.2rem 0;">
    Ahorro Potencial si se Retienen Clientes de Alto Riesgo
</h2>
""", unsafe_allow_html=True)

save10 = rev_at_risk * 0.10
save25 = rev_at_risk * 0.25
save50 = rev_at_risk * 0.50

st.markdown(f"""
<div class="savings-grid">
  <div class="savings-card">
    <div class="savings-scenario">Escenario conservador · 10% retención</div>
    <div class="savings-amount">${save10/1e6:.1f}M</div>
    <div class="savings-desc">
      Si se retiene 1 de cada 10 clientes en alto riesgo, 
      se recuperan <strong>${save10/1e6:.1f}M MXN</strong> anuales estimados.
    </div>
  </div>
  <div class="savings-card">
    <div class="savings-scenario">Escenario moderado · 25% retención</div>
    <div class="savings-amount amber">${save25/1e6:.0f}M</div>
    <div class="savings-desc">
      Con campañas de retención dirigidas que alcancen 25% de éxito, 
      el ahorro asciende a <strong>${save25/1e6:.0f}M MXN</strong>.
    </div>
  </div>
  <div class="savings-card">
    <div class="savings-scenario">Escenario optimista · 50% retención</div>
    <div class="savings-amount red">${save50/1e6:.0f}M</div>
    <div class="savings-desc">
      Retener la mitad de los clientes de alto riesgo protegería 
      <strong>${save50/1e6:.0f}M MXN</strong> del ingreso anual proyectado.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Top 15 clientes más riesgosos ────────────────────────────────────────────
top15 = df.nlargest(15, "prob_churn")[
    ["customer_id", "prob_churn", "territory_d",
     "promedio_uni_boxes_sold_m", "revenue_est",
     "comercial_subchannel_d", "rtm_customer_size_d"]
].reset_index(drop=True)

col_tbl, col_chart = st.columns([1.2, 1])

with col_tbl:
    rows_top = ""
    for _, r in top15.iterrows():
        cid  = str(r["customer_id"])[:12] + "…"
        pill = risk_pill(r["prob_churn"])
        rows_top += (
            f"<tr>"
            f"<td><code style='font-size:10px;color:#a08080;'>{cid}</code></td>"
            f"<td>{pill}</td>"
            f"<td>{r['territory_d']}</td>"
            f"<td style='text-align:right;'>{r['promedio_uni_boxes_sold_m']:.1f}</td>"
            f"<td style='text-align:right;color:#e84060;font-weight:600;'>${r['revenue_est']:,.0f}</td>"
            f"</tr>"
        )
    st.markdown(f"""
    <div class="top-tbl-wrap">
      <div class="risk-table-header">
        <span class="risk-table-title">Top 15 Clientes en Mayor Riesgo</span>
        <span class="risk-table-count">ingreso anual en riesgo</span>
      </div>
      <div style="overflow-x:auto;">
        <table class="risk-tbl">
          <thead><tr>
            <th>ID</th><th>Prob.</th><th>Territorio</th>
            <th style="text-align:right;">Cajas/mes</th>
            <th style="text-align:right;">Ingreso anual</th>
          </tr></thead>
          <tbody>{rows_top}</tbody>
        </table>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_chart:
    # Distribución de riesgo por subchannel
    sub_risk = (
        df[df["prob_churn"] >= 0.651]
        .groupby("comercial_subchannel_d")
        .size()
        .sort_values(ascending=True)
        .reset_index(name="count")
    )
    fig_sub = go.Figure(go.Bar(
        x=sub_risk["count"],
        y=sub_risk["comercial_subchannel_d"],
        orientation="h",
        marker_color="#C8102E",
        marker_line_width=0,
        text=sub_risk["count"].apply(lambda x: f"{x:,}"),
        textposition="outside",
        textfont=dict(color="rgba(240,236,228,0.6)", size=11),
    ))
    fig_sub.update_layout(
        title=dict(
            text="Clientes en Alto Riesgo por Canal",
            font=dict(family="DM Sans", size=14, color="rgba(240,236,228,0.8)"),
            x=0,
        ),
        paper_bgcolor="rgba(118,32,26,1)",
        plot_bgcolor="rgba(118,32,26,1)",
        font=dict(family="DM Sans", color="rgba(240,236,228,0.6)"),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, color="rgba(240,236,228,0.6)", tickfont=dict(size=11)),
        margin=dict(l=10, r=40, t=40, b=10),
        height=380,
    )
    st.plotly_chart(fig_sub, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAPA DE MÉXICO — CLIENTES DE ALTO RIESGO POR ESTADO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<p class="section-label">Distribución Geográfica</p>', unsafe_allow_html=True)
st.markdown("""
<h2 style="font-family:'Bebas Neue',sans-serif;font-size:28px;
           color:#c8102e;letter-spacing:0.5px;margin:0 0 0.4rem 0;">
    Mapa de Riesgo — México
</h2>
<p style="font-size:13px;color:rgba(240,236,228,0.45);font-weight:300;margin-bottom:1rem;">
    Tamaño de burbuja = clientes en alto riesgo por estado.
</p>
""", unsafe_allow_html=True)

state_df = (
    df.groupby("state")
    .agg(
        total=("customer_id", "count"),
        high_risk=("prob_churn", lambda x: (x >= 0.651).sum()),
        avg_prob=("prob_churn", "mean"),
        revenue_at_risk=("revenue_est", lambda x: x[df.loc[x.index, "prob_churn"] >= 0.651].sum()),
    )
    .reset_index()
)

state_df["risk_pct"] = (state_df["high_risk"] / state_df["total"] * 100).round(1)
state_df["revenue_M"] = (state_df["revenue_at_risk"] / 1e6).round(1)

state_coords = {
    "Aguascalientes": (21.8853, -102.2916),
    "Baja California": (30.8406, -115.2838),
    "Baja California Sur": (26.0444, -111.6661),
    "Chihuahua": (28.6320, -106.0691),
    "Coahuila": (27.0587, -101.7068),
    "Durango": (24.0277, -104.6532),
    "Guanajuato": (21.0190, -101.2574),
    "Jalisco": (20.6597, -103.3496),
    "Nuevo León": (25.5922, -99.9962),
    "San Luis Potosí": (22.1565, -100.9855),
    "Sinaloa": (25.1721, -107.4795),
    "Sonora": (29.2972, -110.3309),
    "Tamaulipas": (24.2669, -98.8363),
    "Zacatecas": (22.7709, -102.5832),
}

state_df["lat"] = state_df["state"].map(lambda x: state_coords.get(x, (None, None))[0])
state_df["lon"] = state_df["state"].map(lambda x: state_coords.get(x, (None, None))[1])
state_df = state_df.dropna(subset=["lat", "lon"])

fig_map = px.scatter_geo(
    state_df,
    lat="lat",
    lon="lon",
    size="high_risk",
    color="high_risk",
    hover_name="state",
    hover_data={
        "lat": False,
        "lon": False,
        "high_risk": ":,",
        "total": ":,",
        "risk_pct": ":.1f",
        "revenue_M": ":.1f",
        "avg_prob": ":.1f",
    },
    color_continuous_scale=["#5a1520", "#C8102E", "#ff3355"],
    size_max=55,
)

fig_map.update_geos(
    scope="north america",
    projection_type="mercator",
    center=dict(lat=24, lon=-102),
    lataxis_range=[14, 33],
    lonaxis_range=[-118, -86],
    visible=False,
    bgcolor=" #f7e6e6",
    showland=True,
    landcolor="#f2c9c9",
    showocean=True,
    oceancolor="#fff3f3",
    showcountries=True,
    countrycolor="#8b1e2d",
)

fig_map.update_layout(
    paper_bgcolor="#f7e6e6",
    plot_bgcolor="#f7e6e6",
    margin=dict(l=0, r=0, t=0, b=0),
    height=500,
    coloraxis_colorbar=dict(
        title="Clientes<br>alto riesgo",
        tickfont=dict(color="rgba(240,236,228,0.6)"),
    ),
    hoverlabel=dict(
        bgcolor="#D25454",
        bordercolor="#C8102E",
        font=dict(family="DM Sans", color="#f0ece4", size=13),
    ),
)

st.plotly_chart(fig_map, use_container_width=True)

# ── Ranking de estados debajo del mapa ───────────────────────────────────────
state_sorted = state_df.sort_values("high_risk", ascending=False).reset_index(drop=True)
max_risk = max(state_sorted["high_risk"].max(), 1)

ranking_df = state_sorted.copy()

ranking_df = ranking_df[[
    "state",
    "high_risk",
    "total",
    "risk_pct",
    "revenue_M"
]]

ranking_df.columns = [
    "Estado",
    "Clientes alto riesgo",
    "Total clientes",
    "% alto riesgo",
    "Ingreso en riesgo ($M)"
]

ranking_df["Clientes alto riesgo"] = ranking_df["Clientes alto riesgo"].astype(int)
ranking_df["Total clientes"] = ranking_df["Total clientes"].astype(int)
ranking_df["% alto riesgo"] = ranking_df["% alto riesgo"].round(1)
ranking_df["Ingreso en riesgo ($M)"] = ranking_df["Ingreso en riesgo ($M)"].round(1)

rows_ranking = ""
for _, r in ranking_df.iterrows():
    rows_ranking += (
        f"<tr>"
        f"<td>{r['Estado']}</td>"
        f"<td style='text-align:right;font-weight:600;color:#e84060;'>{r['Clientes alto riesgo']:,}</td>"
        f"<td style='text-align:right;'>{r['Total clientes']:,}</td>"
        f"<td style='text-align:right;color:#e87c2b;font-weight:600;'>{r['% alto riesgo']}%</td>"
        f"<td style='text-align:right;color:#e84060;font-weight:600;'>${r['Ingreso en riesgo ($M)']:.1f}M</td>"
        f"</tr>"
    )

st.markdown(f"""
<div class="top-tbl-wrap">
  <div class="risk-table-header">
    <span class="risk-table-title">Ranking de Estados por Riesgo</span>
    <span class="risk-table-count">clientes en alto riesgo por ubicación</span>
  </div>
  <div style="overflow-x:auto;">
    <table class="risk-tbl">
      <thead><tr>
        <th>Estado</th>
        <th style="text-align:right;">Clientes alto riesgo</th>
        <th style="text-align:right;">Total clientes</th>
        <th style="text-align:right;">% alto riesgo</th>
        <th style="text-align:right;">Ingreso en riesgo ($M)</th>
      </tr></thead>
      <tbody>{rows_ranking}</tbody>
    </table>
  </div>
</div>
""", unsafe_allow_html=True)
# ══════════════════════════════════════════════════════════════════════════════
# STATS ADICIONALES: distribución de riesgo + tamaño de cliente
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<p class="section-label">Análisis de Segmentos</p>', unsafe_allow_html=True)

col_pie, col_size = st.columns(2)

with col_pie:
    risk_counts = df["risk_cat"].value_counts().reset_index()
    risk_counts.columns = ["cat", "count"]
    fig_pie = go.Figure(go.Pie(
        labels=risk_counts["cat"],
        values=risk_counts["count"],
        hole=0.6,
        marker=dict(colors=["#2fb56a", "#e87c2b", "#C8102E"],
                    line=dict(color="#1a0a0a", width=3)),
        textfont=dict(color="#f0ece4", size=12, family="DM Sans"),
        hovertemplate="<b>%{label}</b><br>%{value:,} clientes<br>%{percent}<extra></extra>",
    ))
    fig_pie.update_layout(
        title=dict(text="Distribución por Nivel de Riesgo",
                   font=dict(family="DM Sans", size=14, color="rgba(240,236,228,0.8)"), x=0),
        paper_bgcolor="rgba(118, 32, 26,1)",
        plot_bgcolor="rgba(118, 32, 26,1)",
        font=dict(family="DM Sans", color="rgba(240,236,228,0.6)"),
        legend=dict(font=dict(color="rgba(240,236,228,0.6)", size=12)),
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        hoverlabel=dict(bgcolor="#1a0a0a", bordercolor="#C8102E",
                        font=dict(family="DM Sans", color="#f0ece4")),
    )
    # Texto central
    fig_pie.add_annotation(
        text=f"<b>{total/1000:.0f}K</b><br><span style='font-size:10px'>clientes</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color="#f0ece4", family="Bebas Neue"),
        align="center",
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_size:
    size_risk = (
        df.groupby(["rtm_customer_size_d", "risk_cat"])
        .size()
        .reset_index(name="count")
    )
    size_order = ["Mini", "Pequeño", "Mediano", "Grande", "Gigante"]
    color_map  = {"Bajo (<0.331)": "#2fb56a", "Medio (0.331-0.65)": "#e87c2b", "Alto (>0.651)": "#C8102E"}

    fig_size = px.bar(
        size_risk,
        x="rtm_customer_size_d",
        y="count",
        color="risk_cat",
        color_discrete_map=color_map,
        category_orders={"rtm_customer_size_d": size_order},
        barmode="stack",
        labels={"count": "Clientes", "rtm_customer_size_d": "Tamaño", "risk_cat": "Riesgo"},
    )
    fig_size.update_layout(
        title=dict(text="Riesgo por Tamaño de Cliente",
                   font=dict(family="DM Sans", size=14, color="rgba(240,236,228,0.8)"), x=0),
        paper_bgcolor="rgba(118, 32, 26,1)",
        plot_bgcolor="rgba(118, 32, 26,1)",
        font=dict(family="DM Sans", color="rgba(240,236,228,0.6)"),
        xaxis=dict(showgrid=False, color="rgba(240,236,228,0.5)"),
        yaxis=dict(showgrid=True, gridcolor="#2e1111", color="rgba(240,236,228,0.5)"),
        legend=dict(font=dict(color="rgba(240,236,228,0.6)", size=11), title_text=""),
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        bargap=0.25,
        hoverlabel=dict(bgcolor="#1a0a0a", bordercolor="#C8102E",
                        font=dict(family="DM Sans", color="#f0ece4")),
    )
    fig_size.update_traces(marker_line_width=0)
    st.plotly_chart(fig_size, use_container_width=True)
#==============================================================================
#MISSION CHESCO - INSTRUCCIONES PARA EL ASISTENTE VIRTUAL
@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
def ask_chesco(user_question, df):
    api_key = st.secrets["GEMINI_API_KEY"]

    if not api_key:
        return "No encontré la API key de Gemini. Configúrala como variable de entorno GEMINI_API_KEY."

    client = get_gemini_client()

    muestra_datos = df.head(30).to_csv(index=False)

    prompt = f"""{SYSTEM_INSTRUCTION}

A continuación tienes una muestra del archivo de predicciones:

{muestra_datos}

Pregunta del usuario:
{user_question}

Responde en español, de forma clara, ejecutiva y útil.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        return response.text

    except Exception as e:
        error_text = str(e)

        if "503" in error_text or "UNAVAILABLE" in error_text:
            return """
⚠️ Chesco está experimentando alta demanda en Gemini en este momento.

Para no interrumpir el análisis, intenta de nuevo en unos segundos.
"""

    if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
        return """
⚠️ Chesco alcanzó temporalmente el límite gratuito de Gemini.

Espera unos segundos e intenta de nuevo.
"""

    return f"⚠️ Ocurrió un error al consultar Gemini: `{e}`"

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("## 🥤 Chesco — Asistente de Churn")

if "chesco_messages" not in st.session_state:
    st.session_state.chesco_messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Soy Chesco 🥤, tu asistente de análisis de churn de Arca Continental. ¿Qué cliente o indicador quieres analizar?"
        }
    ]

for msg in st.session_state.chesco_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_question = st.chat_input("Pregúntale algo a Chesco...")

if "last_chesco_question" not in st.session_state:
    st.session_state.last_chesco_question = None

if user_question and user_question != st.session_state.last_chesco_question:

    st.session_state.last_chesco_question = user_question

    st.session_state.chesco_messages.append(
        {"role": "user", "content": user_question}
    )

    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Chesco está analizando..."):
            answer = ask_chesco(user_question, df)
            st.markdown(answer)

    st.session_state.chesco_messages.append(
        {"role": "assistant", "content": answer}
    )