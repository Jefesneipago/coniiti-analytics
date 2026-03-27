import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db import get_engine

# ==============================
# CONFIGURACIÓN
# ==============================
st.set_page_config(
    page_title="Dashboard CONIITI 2025",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# CONEXIÓN A BD
# ==============================
@st.cache_resource
def init_connection():
    return get_engine()

# ==============================
# CARGA DE DATOS
# ==============================
@st.cache_data
def load_data():
    try:
        engine = init_connection()

        query = """
        SELECT 
            id,
            genero,
            pais,
            ucatolica,
            rol,
            programa,
            profesion,
            nom_Evento,
            qr_validado,
            fecha_uso,
            fecha_registro,
            num_documento,
            nombres
        FROM regeventos
        """

        df = pd.read_sql(query, engine)
        return df

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

df = load_data()

# ==============================
# ETL / TRANSFORMACIÓN
# ==============================
df['fecha_registro'] = pd.to_datetime(df['fecha_registro'], errors='coerce')
df['fecha_uso'] = pd.to_datetime(df['fecha_uso'], errors='coerce')

df['dias_anticipacion'] = (df['fecha_uso'] - df['fecha_registro']).dt.days

df['programa'] = df['programa'].fillna('No especificado')
df['rol'] = df['rol'].fillna('No especificado')
df['profesion'] = df['profesion'].fillna('No especificado')
df['genero'] = df['genero'].fillna('No especificado')
df['ucatolica'] = df['ucatolica'].fillna('No')

# ==============================
# FILTROS
# ==============================
st.sidebar.header("📊 Filtros")

# Función para crear filtros con opción "Seleccionar todo"
def crear_filtro(df, columna, label, icono="🔍"):
    """Crea un multiselect con opción de seleccionar/deseleccionar todo"""
    opciones = sorted(df[columna].dropna().unique())
    
    seleccionar_todo = st.sidebar.checkbox(
        f"{icono} Seleccionar todo {label.lower()}", 
        key=f"select_all_{columna}",
        value=True
    )
    
    if seleccionar_todo:
        valores_seleccionados = opciones
    else:
        valores_seleccionados = st.sidebar.multiselect(
            label,
            opciones,
            default=[],
            key=f"multiselect_{columna}"
        )
    
    return valores_seleccionados

# Aplicar filtros
with st.sidebar:
    programas = crear_filtro(df, 'programa', "📚 Programa")
    roles = crear_filtro(df, 'rol', "👤 Rol")
    paises = crear_filtro(df, 'pais', "🌍 País")
    
    st.sidebar.divider()
    st.sidebar.caption(f"✅ Datos totales: {len(df):,} registros")

# Aplicar filtros
try:
    df_filtrado = df[
        (df['programa'].isin(programas) if programas else True) &
        (df['rol'].isin(roles) if roles else True) &
        (df['pais'].isin(paises) if paises else True)
    ]
    
    st.sidebar.metric(
        "📊 Registros filtrados", 
        f"{len(df_filtrado):,}",
        delta=f"{len(df_filtrado) - len(df):+,}",
        delta_color="off"
    )
    
except Exception as e:
    st.error(f"Error al aplicar filtros: {e}")
    df_filtrado = df.copy()

df = df_filtrado

# Botón para resetear filtros
if st.sidebar.button("🔄 Resetear todos los filtros", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# Búsqueda rápida
st.sidebar.divider()
busqueda = st.sidebar.text_input("🔎 Búsqueda rápida", placeholder="Buscar en todos los campos...")
if busqueda:
    mascara = df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
    df = df[mascara]
    st.sidebar.success(f"🔍 {len(df)} resultados encontrados")

# ==============================
# TÍTULO Y METADATOS
# ==============================
st.title("📊 Dashboard CONIITI 2025")
st.markdown("### Sistema de analítica para toma de decisiones")
st.markdown(f"**Última actualización:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} | **Total registros:** {len(df):,}")

# ==============================
# KPIs MEJORADOS
# ==============================
total = len(df)
asistentes = df['qr_validado'].sum() if 'qr_validado' in df.columns else 0
tasa = asistentes / total if total > 0 else 0
participantes = df['num_documento'].nunique()

# KPI: Participantes UCATOLICA
ucatolica_count = df[df['ucatolica'] == 'Si'].shape[0] if 'ucatolica' in df.columns else 0
no_ucatolica_count = df[df['ucatolica'] == 'No'].shape[0] if 'ucatolica' in df.columns else 0

# KPI: Distribución por género
genero_counts = df['genero'].value_counts()
mujeres = genero_counts.get('Femenino', 0) + genero_counts.get('F', 0)
hombres = genero_counts.get('Masculino', 0) + genero_counts.get('M', 0)
otros = genero_counts.get('Otro', 0) + genero_counts.get('No especificado', 0)

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("👥 Inscritos", f"{total:,}")
col2.metric("✅ Asistentes", f"{asistentes:,}")
col3.metric("📈 Tasa de asistencia", f"{tasa:.1%}")
col4.metric("🧍 Participantes únicos", f"{participantes:,}")
col5.metric("🏛️ UCATOLICA", f"{ucatolica_count:,}", delta=f"{ucatolica_count/total:.1%}" if total > 0 else None)
col6.metric("🌍 Externos", f"{no_ucatolica_count:,}", delta=f"{no_ucatolica_count/total:.1%}" if total > 0 else None)

# ==============================
# TOP 10 ASISTENTES MÁS ACTIVOS
# ==============================
st.subheader("🏆 Top 10 - Asistentes más activos")

# Contar conferencias asistidas por persona
asistentes_top = df[df['qr_validado'] == 1].groupby(['num_documento', 'nombres']).agg({
    'nom_Evento': 'count'
}).reset_index()
asistentes_top.columns = ['Documento', 'Nombre', 'Conferencias asistidas']
asistentes_top = asistentes_top.sort_values('Conferencias asistidas', ascending=False).head(10)

# Crear tabla mejorada
col_top1, col_top2 = st.columns([3, 1])

with col_top1:
    # Mostrar tabla con formato mejorado
    st.dataframe(
        asistentes_top,
        column_config={
            "Documento": st.column_config.TextColumn("N° Documento"),
            "Nombre": st.column_config.TextColumn("Nombre completo"),
            "Conferencias asistidas": st.column_config.NumberColumn("Conferencias", format="%d")
        },
        hide_index=True,
        use_container_width=True
    )

with col_top2:
    # Gráfico de barras horizontal
    fig_top = px.bar(
        asistentes_top.head(10),
        x="Conferencias asistidas",
        y="Nombre",
        orientation='h',
        title="Top asistentes",
        text_auto=True,
        color="Conferencias asistidas",
        color_continuous_scale="Viridis"
    )
    fig_top.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_top, use_container_width=True)

# ==============================
# KPIs ESPECÍFICOS SOLICITADOS
# ==============================
st.subheader("📊 Análisis de participación")

col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

# KPI Género
with col_kpi1:
    st.markdown("### 🚻 Distribución por género")
    
    # Crear gráfico de dona para género
    fig_genero = go.Figure(data=[go.Pie(
        labels=['Mujeres', 'Hombres', 'Otros'],
        values=[mujeres, hombres, otros],
        hole=.3,
        marker_colors=['#FF69B4', '#4169E1', '#C0C0C0'],
        textinfo='label+percent',
        textposition='auto'
    )])
    fig_genero.update_layout(
        title="Participación por género",
        height=400,
        showlegend=True
    )
    st.plotly_chart(fig_genero, use_container_width=True)
    
    # Métricas adicionales
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("👩 Mujeres", f"{mujeres:,}")
    with col_b:
        st.metric("👨 Hombres", f"{hombres:,}")

# KPI UCATOLICA
with col_kpi2:
    st.markdown("### 🏛️ Comunidad UCATOLICA")
    
    # Gráfico de barras
    ucatolica_df = pd.DataFrame({
        'Categoría': ['UCATOLICA', 'Externos'],
        'Cantidad': [ucatolica_count, no_ucatolica_count]
    })
    
    fig_ucatolica = px.bar(
        ucatolica_df,
        x='Categoría',
        y='Cantidad',
        text='Cantidad',
        color='Categoría',
        color_discrete_map={'UCATOLICA': '#2E86AB', 'Externos': '#F18F01'},
        title="Distribución comunidad"
    )
    fig_ucatolica.update_traces(textposition='outside')
    fig_ucatolica.update_layout(height=400)
    st.plotly_chart(fig_ucatolica, use_container_width=True)
    
    # Métricas
    st.metric("Porcentaje UCATOLICA", f"{(ucatolica_count/total)*100:.1f}%" if total > 0 else "0%")

# KPI Adicional - Asistencia por género
with col_kpi3:
    st.markdown("### 📈 Asistencia por género")
    
    # Calcular asistencia por género
    asistencia_genero = df.groupby('genero')['qr_validado'].agg(['count', 'sum']).reset_index()
    asistencia_genero.columns = ['Género', 'Total', 'Asistentes']
    asistencia_genero['Tasa'] = asistencia_genero['Asistentes'] / asistencia_genero['Total']
    
    fig_asistencia = px.bar(
        asistencia_genero,
        x='Género',
        y='Tasa',
        text=asistencia_genero['Tasa'].apply(lambda x: f'{x:.1%}'),
        title="Tasa de asistencia por género",
        color='Género',
        color_discrete_sequence=['#FF69B4', '#4169E1', '#C0C0C0']
    )
    fig_asistencia.update_traces(textposition='outside')
    fig_asistencia.update_layout(height=400)
    st.plotly_chart(fig_asistencia, use_container_width=True)

# ==============================
# EVENTOS - SIN TOP (TODOS LOS DATOS)
# ==============================
st.subheader("📊 Análisis por evento")

eventos = df.groupby("nom_Evento")['qr_validado'].agg(['count','sum']).reset_index()
eventos.columns = ['Evento','Inscritos','Asistentes']
eventos['Tasa'] = eventos['Asistentes'] / eventos['Inscritos']

# Gráfico combinado
col_event1, col_event2 = st.columns(2)

with col_event1:
    fig_eventos = px.bar(
        eventos.sort_values('Inscritos', ascending=False),  # Sin limitar a top
        x="Evento",
        y=["Asistentes","Inscritos"],
        barmode="group",
        title="Asistencia vs Inscritos (Todos los eventos)",
        text_auto=True
    )
    fig_eventos.update_layout(xaxis_tickangle=-45, height=600)
    st.plotly_chart(fig_eventos, use_container_width=True)

with col_event2:
    fig_tasa = px.bar(
        eventos.sort_values('Tasa', ascending=False),  # Sin limitar a top
        x="Evento",
        y="Tasa",
        title="Tasa de asistencia por evento (Todos los eventos)",
        text=eventos['Tasa'].apply(lambda x: f'{x:.1%}'),
        color="Tasa",
        color_continuous_scale="RdYlGn"
    )
    fig_tasa.update_traces(textposition='outside')
    fig_tasa.update_layout(xaxis_tickangle=-45, height=600)
    st.plotly_chart(fig_tasa, use_container_width=True)

# ==============================
# PERFIL - SIN TOP (TODOS LOS DATOS)
# ==============================
st.subheader("👤 Perfil de participantes")

col5, col6 = st.columns(2)

programa_chart = df['programa'].value_counts().reset_index()
programa_chart.columns = ['Programa','Cantidad']

fig_programa = px.bar(
    programa_chart,  # Sin limitar a top
    x="Programa",
    y="Cantidad",
    title="Programas académicos (Todos)",
    color="Cantidad",
    color_continuous_scale="Blues",
    text_auto=True
)
fig_programa.update_layout(xaxis_tickangle=-45, height=500)
col5.plotly_chart(fig_programa, use_container_width=True)

rol_chart = df['rol'].value_counts().reset_index()
rol_chart.columns = ['Rol','Cantidad']

fig_rol = px.pie(
    rol_chart,
    values="Cantidad",
    names="Rol",
    title="Distribución por Rol",
    hole=0.3
)
col6.plotly_chart(fig_rol, use_container_width=True)

# ==============================
# PAÍSES - SIN TOP (TODOS LOS DATOS)
# ==============================
st.subheader("🌎 Distribución geográfica")

pais_chart = df['pais'].value_counts().reset_index()
pais_chart.columns = ['País','Cantidad']

col_pais1, col_pais2 = st.columns([2, 1])

with col_pais1:
    fig_pais = px.bar(
        pais_chart,  # Sin limitar a top
        x="País",
        y="Cantidad",
        title="Países de procedencia (Todos)",
        color="Cantidad",
        color_continuous_scale="Viridis",
        text_auto=True
    )
    fig_pais.update_layout(xaxis_tickangle=-45, height=500)
    st.plotly_chart(fig_pais, use_container_width=True)

with col_pais2:
    fig_pais_pie = px.pie(
        pais_chart,  # Sin limitar a top
        values="Cantidad",
        names="País",
        title="Distribución por país"
    )
    st.plotly_chart(fig_pais_pie, use_container_width=True)

# ==============================
# ANTICIPACIÓN
# ==============================
st.subheader("⏱️ Anticipación vs Asistencia")

col_antic1, col_antic2 = st.columns(2)

with col_antic1:
    fig_box = px.box(
        df,
        x="qr_validado",
        y="dias_anticipacion",
        title="Días de anticipación por tipo de participación",
        labels={"qr_validado": "Asistió", "dias_anticipacion": "Días de anticipación"}
    )
    st.plotly_chart(fig_box, use_container_width=True)

with col_antic2:
    # Histograma de anticipación
    fig_hist = px.histogram(
        df,
        x="dias_anticipacion",
        color="qr_validado",
        title="Distribución de días de anticipación",
        labels={"dias_anticipacion": "Días de anticipación", "count": "Frecuencia"},
        nbins=30
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ==============================
# MULTI EVENTO
# ==============================
st.subheader("🔁 Participación en múltiples eventos")

df_personas = df.groupby('num_documento').agg({
    'nom_Evento':'count',
    'qr_validado':'sum',
    'nombres':'first'
}).rename(columns={
    'nom_Evento':'total_eventos',
    'qr_validado':'eventos_asistidos'
}).reset_index()

# Estadísticas de participación
col_multi1, col_multi2, col_multi3 = st.columns(3)
with col_multi1:
    st.metric("Promedio eventos por persona", f"{df_personas['total_eventos'].mean():.1f}")
with col_multi2:
    st.metric("Máximo eventos asistidos", f"{df_personas['eventos_asistidos'].max()}")
with col_multi3:
    st.metric("Personas con 3+ eventos", f"{df_personas[df_personas['eventos_asistidos'] >= 3].shape[0]}")

fig_multi = px.histogram(
    df_personas,
    x="eventos_asistidos",
    title="Distribución de eventos asistidos por persona",
    labels={"eventos_asistidos": "Número de eventos asistidos", "count": "Número de personas"},
    nbins=20,
    color_discrete_sequence=['#2E86AB']
)
fig_multi.update_layout(showlegend=False)
st.plotly_chart(fig_multi, use_container_width=True)

# ==============================
# TABLA DE DATOS MEJORADA
# ==============================
st.subheader("📋 Vista detallada de datos")

# Selector de cantidad de filas
num_filas = st.selectbox("Mostrar filas:", [50, 100, 200, 500, 1000, len(df)], index=0)

# Mostrar dataframe con formato mejorado
st.dataframe(
    df.head(num_filas),
    column_config={
        "id": st.column_config.NumberColumn("ID", format="%d"),
        "nombres": st.column_config.TextColumn("Nombre"),
        "num_documento": st.column_config.TextColumn("Documento"),
        "genero": st.column_config.TextColumn("Género"),
        "ucatolica": st.column_config.TextColumn("UCATOLICA"),
        "qr_validado": st.column_config.CheckboxColumn("Asistió"),
        "fecha_registro": st.column_config.DatetimeColumn("Fecha registro"),
        "fecha_uso": st.column_config.DatetimeColumn("Fecha uso"),
    },
    hide_index=True,
    use_container_width=True
)

# ==============================
# EXPORTAR DATOS
# ==============================
st.sidebar.divider()
st.sidebar.markdown("### 📥 Exportar datos")

if st.sidebar.button("📊 Exportar datos filtrados a CSV", use_container_width=True):
    csv = df.to_csv(index=False)
    st.sidebar.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"coniiti_dashboard_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Footer
st.markdown("---")
st.markdown("📊 **Dashboard CONIITI 2025** | Desarrollado con Streamlit")