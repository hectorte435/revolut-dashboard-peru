import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import plotly.express as px
import plotly.graph_objects as go

# Verificado: Acceso de edición confirmado en el nuevo directorio.

st.set_page_config(layout='wide', page_title='Impacto de Revolut en Perú', page_icon='⚡', initial_sidebar_state='collapsed')

# CSS para ocultar menú/sidebar y estilar métricas y pestañas (Permitiendo Scroll)
st.markdown("""
<style>
    [data-testid="collapsedControl"] { display: none; }
    [data-testid="stHeader"] { display: none; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    .stApp { background-color: #050505; color: #FFFFFF; }
    
    h1, h2, h3 { color: #FFFFFF !important; font-family: 'Courier New', Courier, monospace; }
    h4 { color: #00FFFF !important; }
    
    /* Contenedor KPIs Fijos Top */
    .kpi-board {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin-bottom: 20px;
        border-bottom: 2px solid #222;
        padding-bottom: 15px;
        flex-wrap: wrap; /* Mobile Responsive */
    }
    
    .metric-box {
        flex: 1;
        min-width: 200px; /* Mobile Responsive */
        background-color: #111111;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 0 10px rgba(0,255,255,0.05);
    }
    
    .metric-value-cyan { color: #00FFFF; font-size: 2rem; font-weight: bold; text-shadow: 0 0 8px rgba(0,255,255,0.4); }
    .metric-value-red { color: #FF3333; font-size: 2rem; font-weight: bold; text-shadow: 0 0 10px rgba(255,51,51,0.4); }
    .metric-value-orange { color: #FF9900; font-size: 2rem; font-weight: bold; text-shadow: 0 0 10px rgba(255,153,0,0.4); }
    .metric-label { color: #AAAAAA; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #050505; gap: 10px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: #111111;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 15px;
        color: #888888;
        font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #222222 !important;
        border-bottom: 2px solid #00FFFF !important;
        color: #FFFFFF !important;
        font-weight: bold;
    }
    
    /* Tablas CSS */
    .custom-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 1rem; }
    .custom-table th { background-color: #1a1a1a; color: #FFF; padding: 10px; text-align: center; border-bottom: 2px solid #333; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #222; text-align: center; color: #DDD; }
    .custom-table .left-align { text-align: left; }
    .revolut-highlight { color: #00FFFF; font-weight: bold; }
    .banca-warn { color: #FF3333; }
    .check-green { color: #00FF00; font-weight: bold; }
    .cross-red { color: #FF3333; font-weight: bold; }
    .table-container { overflow-x: auto; width: 100%; } /* Mobile Responsive */
</style>
""", unsafe_allow_html=True)

# ----------------- DATOS LOCALES (SIN CONEXIÓN A BIGQUERY) -----------------
@st.cache_data
def load_data():
    # Generar directamente los datos de simulación en memoria para evitar llamadas a la nube
    meses_sim = [f"Mes {i}" for i in range(1, 13)]
    total_migracion_12m = 1948.20
    migracion_acumulada_banca = []
    migracion_acumulada_fintech = []
    m_banca = 0
    m_fintech = 0
    
    for i in range(1, 13):
        peso_mes = (i ** 1.5) / (sum(j ** 1.5 for j in range(1, 13)))
        incremento = total_migracion_12m * peso_mes
        m_banca += incremento * 0.70
        m_fintech += incremento * 0.30
        migracion_acumulada_banca.append(m_banca)
        migracion_acumulada_fintech.append(m_fintech)
        
    df_local = pd.DataFrame({
        'Línea temporal': meses_sim * 2,
        'Volumen Migrado (Millones PEN)': migracion_acumulada_banca + migracion_acumulada_fintech,
        'Sector de Origen': ['Banca Múltiple Tradicional'] * 12 + ['Otras Fintech / Cajas Privadas'] * 12
    })
    
    return df_local

df = load_data()

# Configuración de gráficos estáticos para evitar interferencias con el zoom y scroll en móviles
config_graficos_fijos = {'staticPlot': True}

# ----------------- VARIABLES GLOBALES CALIBRADAS -----------------
total_migracion_12m = 1948.20
costo_oportunidad_spread = -1.77
brecha_tasa_prestamos = 19.3

# ----------------- HEADER (KPIs FIJOS CORREGIDOS) -----------------
st.markdown("<h1>⚡ IMPACTO DE REVOLUT EN PERÚ</h1>", unsafe_allow_html=True)

st.markdown(f"""
<div class='kpi-board'>
    <div class='metric-box' style='border-color: #FF3333;'>
        <div class='metric-label'>Migración de Capital Proyectada (12M)</div>
        <div class='metric-value-red'>S/ {total_migracion_12m:,.1f} M</div>
    </div>
    <div class='metric-box' style='border-color: #FF9900;'>
        <div class='metric-label'>Costo de Oportunidad por Spread Cambiario</div>
        <div class='metric-value-orange'>S/ {costo_oportunidad_spread:,.2f} M</div>
    </div>
    <div class='metric-box' style='border-color: #00FFFF;'>
        <div class='metric-label'>Brecha Promedio Tasa Préstamos</div>
        <div class='metric-value-cyan'>~{brecha_tasa_prestamos}%</div>
    </div>
    <div class='metric-box'>
        <div class='metric-label'>Fecha de Actualización</div>
        <div style='color: #FFFFFF; font-size: 1.5rem; font-weight: bold; margin-top: 5px;'>20 de Junio<br>del 2026</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- TABS -----------------
tabs = st.tabs([
    "💰 1. Ahorros e Inversión", 
    "💱 2. Spread Cambiario", 
    "💳 3. Préstamos", 
    "🛠️ 4. Comisiones", 
    "🏃‍♂️ 5. Proyección Migración", 
    "🧠 6. Análisis", 
    "🎯 7. Conclusiones"
])

# TAB 1: GUERRA DE AHORROS
with tabs[0]:
    st.subheader("La Guerra de Tasas: Liquidez vs Rentabilidad")
    
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.markdown("""
        <div class='table-container'>
        <table class='custom-table'>
            <tr><th class='left-align'>Producto</th><th>Banca Múltiple Tradicional</th><th>Cajas Municipales</th><th class='revolut-highlight'>Revolut (Benchmark)</th></tr>
            <tr><td class='left-align'>Cuenta Ahorro/Sueldo</td><td>0.00% - 1.50%</td><td>1.00% - 3.50%</td><td class='revolut-highlight'>15.00% (hasta S/ 5k)</td></tr>
            <tr><td class='left-align'>CTS (Compensación)</td><td>1.00% - 3.00%</td><td>5.50% - 7.00%</td><td class='revolut-highlight'>Rendimiento Superior Indexado</td></tr>
            <tr><td class='left-align'>DPF (360 Días)</td><td>4.00% - 4.30%</td><td>5.00% - 6.00%</td><td class='revolut-highlight'>15% - 7.5% - 5% (Sin congelar)</td></tr>
            <tr><td class='left-align'>Fondos Mutuos Conservadores</td><td>4.00% - 6.00% (Variable)</td><td>N/A</td><td class='revolut-highlight'>Rendimiento Diario Fijo</td></tr>
            <tr><td class='left-align' style='background-color:#111; font-weight:bold;'>Liquidez del Dinero</td><td class='banca-warn' colspan='2'>Inmovilizado para ganar tasas altas (>4%)</td><td class='revolut-highlight'>100% Inmediata</td></tr>
        </table>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        df_ahorros = pd.DataFrame({
            'Producto': ['Ahorro Tradicional', 'DPF (1 Año)', 'Cajas (CTS/DPF)', 'Revolut (Tier 1)'],
            'Tasa Máxima TEA (%)': [1.5, 4.3, 7.0, 15.0]
        })
        fig_ahorros = px.bar(df_ahorros, x='Producto', y='Tasa Máxima TEA (%)', text='Tasa Máxima TEA (%)',
                             color='Producto',
                             color_discrete_map={'Ahorro Tradicional': '#555', 'DPF (1 Año)': '#777', 'Cajas (CTS/DPF)': '#FF9900', 'Revolut (Tier 1)': '#00FFFF'})
        fig_ahorros.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_ahorros.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF', showlegend=False, height=300, margin=dict(t=20, b=0, l=0, r=0))
        st.plotly_chart(fig_ahorros, use_container_width=True, config=config_graficos_fijos)
        
    st.markdown("""
    <p style='color:#DDD; margin-top:20px;'><strong>Análisis:</strong> La banca tradicional penaliza la liquidez de los depositantes y obliga a congelar fondos en DPFs institucionales para obtener rendimientos de apenas 4-5%. La propuesta de valor de la arquitectura tecnológica fintech rompe el paradigma al ofrecer un 15% con disponibilidad inmediata, gatillando una migración estructural de fondos líquidos hacia cuentas remuneradas eficientes.</p>
    """, unsafe_allow_html=True)

# TAB 2: SPREAD CAMBIARIO
with tabs[1]:
    st.subheader("El Negocio del Tipo de Cambio: Fin del Oligopolio")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        <div class='table-container'>
        <table class='custom-table'>
            <tr><th class='left-align'>Ecosistema Financiero</th><th>Spread Promedio (Venta-Compra)</th><th>Impacto en S/ 1,000 USD</th></tr>
            <tr><td class='left-align'>Banca Múltiple (Mesa de Dinero Retail)</td><td class='banca-warn'>~ 2.50% - 3.00%</td><td class='banca-warn'>Pérdida de ~$ 25 - $30 USD</td></tr>
            <tr><td class='left-align'>Canales Digitales Integrados (Banca)</td><td style='color:#FF9900'>~ 1.50% - 2.50%</td><td style='color:#FF9900'>Pérdida de ~$ 15 - $25 USD</td></tr>
            <tr><td class='left-align'>Casas de Cambio Digitales Independientes</td><td style='color:#00FF00'>~ 0.50% - 0.80%</td><td style='color:#00FF00'>Pérdida de ~$ 5 - $8 USD</td></tr>
            <tr><td class='left-align revolut-highlight'>Modelos Fintech Globales (Revolut)</td><td class='revolut-highlight'>~ 0.00% - 0.50% (Interbancario Real)</td><td class='revolut-highlight'>Optimización Máxima ($ 0 - $5 USD)</td></tr>
        </table>
        </div>
        <p style='color:#888; font-size:0.9rem; margin-top:10px;'>*Los modelos de tesorería descentralizados aplican markups mínimos los fines de semana por cierre estandarizado de mercados.</p>
        """, unsafe_allow_html=True)
        
    with col2:
        # Gráfico de Dona Calibrado al Impacto por Institución Financiera
        df_spread_dist = pd.DataFrame({
            'Origen de Fondos': ['Banca Múltiple Top 1', 'Banca Múltiple Top 2', 'Banca Retail General', 'Otras Entidades'],
            'Porcentaje de Impacto': [45, 30, 15, 10]
        })
        fig_donut = px.pie(df_spread_dist, values='Porcentaje de Impacto', names='Origen de Fondos', hole=0.6,
                           color_discrete_sequence=['#FF3333', '#FF6633', '#FF9900', '#555555'])
        fig_donut.update_traces(textposition='inside', textinfo='percent+label', textfont=dict(color='#FFFFFF', size=14))
        fig_donut.update_layout(title="Distribución del Costo de Oportunidad Cambiario", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF', margin=dict(t=40, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig_donut, use_container_width=True, config=config_graficos_fijos)
            
    st.markdown("""
    <p style='color:#DDD; margin-top:20px;'><strong>Análisis:</strong> El spread bancario tradicional actúa como una fricción de intermediación que asume el usuario. Al integrar tipos de cambio interbancarios puros en la app, se genera un costo de oportunidad directo para los canales tradicionales, forzando la migración del volumen transaccional de tesorería hacia rieles fintech.</p>
    """, unsafe_allow_html=True)

# TAB 3: PRÉSTAMOS
with tabs[2]:
    st.subheader("La Optimización del Crédito: Colocaciones de Bajo Riesgo")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        fig_loans = go.Figure()
        
        # Rango Min-Max (Banca Tradicional)
        fig_loans.add_trace(go.Bar(
            name='Rango Min-Max (Banca Tradicional)', 
            x=['Consumo Prime', 'MYPE Formal'], 
            y=[30, 25], 
            base=[10, 10], 
            marker_color='rgba(255, 51, 51, 0.35)', 
            marker_line=dict(color='#FF3333', width=1.5),
            text=['Rango: 10% - 40%', 'Rango: 10% - 35%'], 
            textposition='outside',
            textfont=dict(color='#FFFFFF', size=12)
        ))
        
        # Promedio Sistema Prime (SBS)
        fig_loans.add_trace(go.Scatter(
            name='Promedio Sistema Prime (SBS)', 
            x=['Consumo Prime', 'MYPE Formal'], 
            y=[27.5, 24.8], 
            mode='markers+text', 
            marker=dict(color='#FFCC00', size=12, symbol='x'), 
            text=['Promedio: 27.5%', 'Promedio: 24.8%'], 
            textposition='top center',
            textfont=dict(color='#FFCC00', size=11)
        ))
        
        # Revolut (Target Eficiente)
        fig_loans.add_trace(go.Scatter(
            name='Revolut (Target Eficiente)', 
            x=['Consumo Prime', 'MYPE Formal'], 
            y=[8.2, 9.5], 
            mode='markers+text', 
            marker=dict(color='#00FFFF', size=16, symbol='diamond', line=dict(width=2, color='#FFFFFF')), 
            text=['⚡ 8.2% TEA', '⚡ 9.5% TEA'], 
            textposition='bottom center',
            textfont=dict(color='#00FFFF', size=13)
        ))
        
        fig_loans.update_layout(
            title="Rangos de Tasas de Interés Corporativo/Retail (TEA %)", 
            barmode='overlay', 
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font_color='#FFF', 
            height=420, 
            yaxis=dict(title="Tasa de Interés (%)", range=[0, 50], gridcolor='#222222'),
            xaxis=dict(gridcolor='#222222'),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(0,0,0,0)"
            ),
            margin=dict(t=40, b=80, l=10, r=10)
        )
        st.plotly_chart(fig_loans, use_container_width=True, config=config_graficos_fijos)

    with col2:
        st.markdown(f"""
        <div class='table-container'>
        <table class='custom-table'>
            <tr><th class='left-align'>Segmento Objetivo</th><th>Tasa Sistema Promedio</th><th class='revolut-highlight'>Oferta Fintech de Target Eficiente</th></tr>
            <tr><td class='left-align'>Consumo (Bajo Riesgo / Calificación A)</td><td>~ 26.0% - 28.0%</td><td class='revolut-highlight'>7.0% - 9.0%</td></tr>
            <tr><td class='left-align'>MYPEs Formalizadas (Buen Récord)</td><td>~ 22.0% - 25.0%</td><td class='revolut-highlight'>8.5% - 11.0%</td></tr>
            <tr><td class='left-align'>Sectores Sub-estándar o Informales</td><td class='banca-warn'>> 50.0%</td><td class='revolut-highlight'>Fuera de Apetito de Riesgo</td></tr>
        </table>
        </div>
        <br>
        <p style='color:#DDD;'><strong>Análisis:</strong> La estrategia de penetración crediticia no busca captar la base de la pirámide desbancarizada. El enfoque se centra en el <i>Cherry-Picking</i> financiero: absorber los perfiles crediticios de primer orden de la banca múltiple tradicional mediante una brecha competitiva promedio del <strong>{brecha_tasa_prestamos}%</strong>, apalancada en eficiencias operativas automatizadas.</p>
        """, unsafe_allow_html=True)

# TAB 4: MANTENIMIENTO Y COMISIONES
with tabs[3]:
    st.subheader("Estructura de Costos Operativos y Remoción de Comisiones")
    st.markdown("""
    <div class='table-container'>
    <table class='custom-table'>
        <tr>
            <th class='left-align'>Concepto Operativo</th>
            <th>Banca Tradicional Líder</th>
            <th>Banca Retail Secundaria</th>
            <th class='revolut-highlight'>Modelos Digitales Nativo (Revolut)</th>
        </tr>
        <tr>
            <td class='left-align'>Mantenimiento Mensual Fijo</td>
            <td><span class='cross-red'>S/ 10.00 - S/ 15.00</span></td>
            <td><span class='cross-red'>Condicionado a Saldo Mínimo</span></td>
            <td class='revolut-highlight'>S/ 0.00 (Incondicional)</td>
        </tr>
        <tr>
            <td class='left-align'>Transferencias Interbancarias Inmediatas</td>
            <td><span class='cross-red'>Comisión según canal/monto</span></td>
            <td><span class='check-green'>S/ 0.00 Diferido</span></td>
            <td class='revolut-highlight'>S/ 0.00 (Rieles en Tiempo Real)</td>
        </tr>
        <tr>
            <td class='left-align'>Disposición de Efectivo (Red Externa)</td>
            <td><span class='cross-red'>Cargo Transaccional Alto</span></td>
            <td><span class='cross-red'>Comisión Cruzada</span></td>
            <td class='revolut-highlight'>Tasas Libres según Límites de Red</td>
        </tr>
        <tr>
            <td class='left-align'>Transacciones Internacionales (Comercio Electrónico)</td>
            <td><span class='cross-red'>Markup cambiario oculto (2% - 3%)</span></td>
            <td><span class='cross-red'>Comisión por Divisa</span></td>
            <td class='revolut-highlight'>Tipo de Cambio Real Directo</td>
        </tr>
    </table>
    </div>
    <p style='color:#DDD; margin-top:15px;'><strong>Análisis:</strong> Los ingresos por servicios y comisiones contingentes de los canales tradicionales sostienen costos de infraestructura física heredada. La introducción de modelos con costo base cero forzará una obligatoria optimización tarifaria en el ecosistema local para neutralizar el arbitraje transaccional.</p>
    """, unsafe_allow_html=True)

# TAB 5: PROYECCIÓN MIGRACIÓN
with tabs[4]:
    st.subheader("Redistribución de Liquidez: Simulación Estructurada a 12 Meses")
    
    # Simulación matemática limpia y realista acorde a los S/ 1,948.2 M del KPI Board
    meses_sim = [f"Mes {i}" for i in range(1, 13)]
    migracion_acumulada_banca = []
    migracion_acumulada_fintech = []
    
    m_banca = 0
    m_fintech = 0
    for i in range(1, 13):
        # Curva de adopción macroeconómica (S-Curve) ajustada a la meta exacta
        peso_mes = (i ** 1.5) / (sum(j ** 1.5 for j in range(1, 13)))
        incremento = total_migracion_12m * peso_mes
        m_banca += incremento * 0.70  # El 70% proviene de la Banca Múltiple Tradicional
        m_fintech += incremento * 0.30 # El 30% proviene de otras Fintechs/Cajas menores
        migracion_acumulada_banca.append(m_banca)
        migracion_acumulada_fintech.append(m_fintech)
        
    df_proyeccion_realista = pd.DataFrame({
        'Línea temporal': meses_sim * 2,
        'Volumen Migrado (Millones PEN)': migracion_acumulada_banca + migracion_acumulada_fintech,
        'Sector de Origen': ['Banca Múltiple Tradicional'] * 12 + ['Otras Fintech / Cajas Privadas'] * 12
    })
    
    col1, col2 = st.columns([2, 1])
    with col1:
        fig_area_calibrada = px.area(df_proyeccion_realista, x='Línea temporal', y='Volumen Migrado (Millones PEN)', color='Sector de Origen',
                                     color_discrete_sequence=['#FF3333', '#FF9900'],
                                     title="Dinámica de Absorción de Liquidez Acumulada")
        fig_area_calibrada.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF', height=400, xaxis_title="Evolución Mensual (Primer Año)", yaxis_title="Millones PEN")
        st.plotly_chart(fig_area_calibrada, use_container_width=True, config=config_graficos_fijos)
        
    with col2:
        vol_banca_múltiple = total_migracion_12m * 0.70
        vol_otros_sectores = total_migracion_12m * 0.30
        st.markdown(f"""
        <div style='background-color:#111; padding:20px; border-radius:8px; border:1px solid #333;'>
            <h4 style='color:#FFF;'>Análisis de Captación del Pasivo</h4>
            <p style='color:#DDD; margin-top:10px;'>La digitalización del usuario financiero reduce drásticamente las barreras de salida. La masa monetaria migra mediante canales de alta frecuencia hacia ecosistemas transaccionales de mayor tasa pasiva.</p>
            <div style='margin-top:20px; border-left: 3px solid #FF3333; padding-left: 10px;'>
                <strong style='color:#FF3333'>Absorción desde Banca Múltiple:</strong><br>
                <span style='font-size:1.5rem; color:#FFFFFF'>S/ {vol_banca_múltiple:,.2f} M</span>
            </div>
            <div style='margin-top:15px; border-left: 3px solid #FF9900; padding-left: 10px;'>
                <strong style='color:#FF9900'>Absorción desde Otros Sectores:</strong><br>
                <span style='font-size:1.5rem; color:#FFFFFF'>S/ {vol_otros_sectores:,.2f} M</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# TAB 6: ANÁLISIS
with tabs[5]:
    st.subheader("Análisis Estructural: Las Debilidades del Sistema Tradicional")
    st.markdown("""
    <div style='padding: 20px; background-color: #111; border-radius: 8px; border: 1px solid #333;'>
        <ul style='color: #DDD; font-size: 1.1rem; line-height: 1.8;'>
            <li><strong style='color:#FF3333'>Márgenes de Intermediación Elevados:</strong> Históricamente, el mercado local opera con spreads amplios en comparación con los estándares de la OCDE, sustentados en pasivos de bajo costo (cuentas corrientes y ahorros tradicionales). La irrupción de un competidor eficiente comprime estos márgenes globales.</li>
            <li><strong style='color:#FF3333'>Costos de Infraestructura Física (Legacy):</strong> La operación tradicional mantiene redes densas de sucursales operativas y soporte analógico. Las plataformas nativas en la nube convierten estos costos fijos en beneficios directos de tasa para el usuario final.</li>
            <li><strong style='color:#FF3333'>Fricción Cambiaria como Margen de Utilidad:</strong> Las tesorerías tradicionales asumen la conversión cambiaria minorista como un centro de alta rentabilidad. El arbitraje digital directo neutraliza esta captura de valor transferencias adentro.</li>
            <li><strong style='color:#00FFFF'>Cherry-Picking Automático:</strong> El algoritmo de evaluación no asume carteras sub-prime de inclusión masiva. Al captar los flujos de perfiles premium, se genera un efecto de selección adversa sobre la banca tradicional, alterando sus ratios consolidados de morosidad.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# TAB 7: CONCLUSIONES
with tabs[6]:
    st.subheader("Conclusiones y Plan de Acción Defensivo")
    st.markdown("""
<div style='padding: 20px; background-color: #111; border-radius: 8px; border: 1px solid #333;'>
<h4 style='color:#00FFFF;'>Conclusión Principal</h4>
<p style='color: #DDD; font-size: 1.1rem; line-height: 1.6;'>El ingreso de un neobanco de escala global redefine las fronteras de eficiencia del mercado privado. Si se replica un entorno competitivo de altas tasas pasivas con liquidez total, el costo de oportunidad para los saldos líquidos corporativos y retail será insostenible para el statu quo del sistema tradicional, acelerando flujos de capital hacia la banca digital.</p>
<h4 style='color:#FF9900; margin-top:20px;'>Estrategia de Retención Corporativa</h4>
<ul style='color: #DDD; font-size: 1.1rem; line-height: 1.8;'>
<li><strong>Lanzamiento Preventivo de Cuentas Remuneradas Dinámicas:</strong> Desarrollar opciones de captación transaccional digital con rendimientos indexados (6%-8% anual) con disponibilidad inmediata para mitigar fugas masivas hacia el competidor entrante.</li>
<li><strong>Alineamiento del Spread de Divisas en Canales Digitales:</strong> Reducir el spread cambiario minorista in-app para equiparar las condiciones del mercado mayorista interbancario y desincentivar el arbitraje externo.</li>
<li><strong>Contención Patrimonial Preventiva del Segmento Prime:</strong> Estructurar ofertas crediticias y pre-aprobaciones automatizadas con tasas de un solo dígito para asegurar y blindar la cartera de menor riesgo sistémico antes de la apertura del mercado.</li>
</ul>
</div>
    """, unsafe_allow_html=True)

# ----------------- FOOTERS (FUENTES Y AUTOR) -----------------
fuentes_html = "<p style='color:#777; font-size:0.85rem; text-align:center; margin-top:40px; border-top:1px solid #333; padding-top:15px;'><i>Fuentes: Superintendencia de Banca, Seguros y AFP (SBS) | Tarifarios corporativos analizados | Parámetros de Simulación de Tesorería Sectorial.</i></p>"

for i in range(7):
    with tabs[i]:
        st.markdown(fuentes_html, unsafe_allow_html=True)

st.markdown("<div style='text-align:center; margin-top: 10px; margin-bottom: 20px;'><h3 style='color:#00FFFF; letter-spacing: 1px; font-family: Arial, sans-serif;'>Elaborado por Econ. Hector Torres</h3></div>", unsafe_allow_html=True)
