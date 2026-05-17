import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout='wide', page_title='Revolut Impact: 360° Analysis', page_icon='⚡', initial_sidebar_state='collapsed')

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
    }
    
    .metric-box {
        flex: 1;
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
</style>
""", unsafe_allow_html=True)

# ----------------- DATOS -----------------
@st.cache_data
def load_data():
    try:
        import json
        import os
        
        # 1. Intentar usar los Secretos de la Nube (Seguridad en Producción)
        if "gcp_service_account" in st.secrets:
            key_dict = json.loads(st.secrets["gcp_service_account"])
            credentials = service_account.Credentials.from_service_account_info(key_dict)
        # 2. Si estamos en local, usar el archivo key.json
        elif os.path.exists("key.json"):
            credentials = service_account.Credentials.from_service_account_file("key.json")
        else:
            raise Exception("No se encontraron credenciales válidas")
            
        project_id = credentials.project_id if credentials.project_id else 'revolut-en-peru'
        client = bigquery.Client(credentials=credentials, project=project_id)
        
        try:
            query = "SELECT * FROM `analisis_mercado.v_dashboard_revolut`"
            df = client.query(query).to_dataframe()
        except:
            query = "SELECT * FROM `analisis_mercado.fuga_depositos`"
            df = client.query(query).to_dataframe()
        return df
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    df['mes_proyeccion'] = pd.to_datetime(df['mes_proyeccion'])
    min_date = df['mes_proyeccion'].min()
    # Ajustar para que el impacto inicie en Enero 2027 (lanzamiento estimado)
    months_to_shift = (2027 - min_date.year) * 12 + (1 - min_date.month)
    df['mes_proyeccion'] = df['mes_proyeccion'] + pd.DateOffset(months=months_to_shift)

# Variables Globales BQ
total_fuga_12m = 0
if not df.empty:
    total_fuga_12m = df['fuga_depositos_millones_pen'].sum()
perdida_spread = total_fuga_12m * 0.025

# ----------------- HEADER (KPIs FIJOS) -----------------
st.markdown("<h1>⚡ REVOLUT THREAT INTELLIGENCE: 360°</h1>", unsafe_allow_html=True)

st.markdown(f"""
<div class='kpi-board'>
    <div class='metric-box' style='border-color: #FF3333;'>
        <div class='metric-label'>Fuga de Capital Proyectada (12M)</div>
        <div class='metric-value-red'>S/ {total_fuga_12m:,.1f} M</div>
    </div>
    <div class='metric-box' style='border-color: #FF9900;'>
        <div class='metric-label'>Pérdida por Spread Cambiario (Banca)</div>
        <div class='metric-value-orange'>- S/ {perdida_spread:,.1f} M</div>
    </div>
    <div class='metric-box' style='border-color: #00FFFF;'>
        <div class='metric-label'>Brecha Promedio Tasa Préstamos</div>
        <div class='metric-value-cyan'>~49.3%</div>
    </div>
    <div class='metric-box'>
        <div class='metric-label'>Fecha de Análisis</div>
        <div style='color: #FFFFFF; font-size: 1.5rem; font-weight: bold; margin-top: 5px;'>14 de Mayo<br>del 2026</div>
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
        <table class='custom-table'>
            <tr><th class='left-align'>Producto</th><th>Banca Top 4 (BCP/BBVA/IBK/Scotiabank)</th><th>Cajas Municipales</th><th class='revolut-highlight'>Revolut (Benchmark)</th></tr>
            <tr><td class='left-align'>Cuenta Ahorro/Sueldo</td><td>0.00% - 1.50%</td><td>1.00% - 3.50%</td><td class='revolut-highlight'>15.00% (hasta S/ 5k)</td></tr>
            <tr><td class='left-align'>CTS (Compensación)</td><td>1.00% - 3.00%</td><td>5.50% - 7.00%</td><td class='revolut-highlight'>No aplica directo (Pero superaría al mercado)</td></tr>
            <tr><td class='left-align'>DPF (360 Días)</td><td>4.00% - 4.30%</td><td>5.00% - 6.00%</td><td class='revolut-highlight'>15% - 7.5% - 5% (Sin congelar)</td></tr>
            <tr><td class='left-align'>Fondos Mutuos Conservadores</td><td>4.00% - 6.00% (Variable)</td><td>N/A</td><td class='revolut-highlight'>Rendimiento Diario Fijo</td></tr>
            <tr><td class='left-align' style='background-color:#111; font-weight:bold;'>Liquidez del Dinero</td><td class='banca-warn' colspan='2'>Inmovilizado para ganar tasas altas (>4%)</td><td class='revolut-highlight'>100% Inmediata</td></tr>
        </table>
        """, unsafe_allow_html=True)
    
    with col2:
        # Gráfico Barras Comparativo
        df_ahorros = pd.DataFrame({
            'Producto': ['Ahorro Tradicional', 'DPF (1 Año)', 'Cajas (CTS/DPF)', 'Revolut (Tier 1)'],
            'Tasa Máxima TEA (%)': [1.5, 4.3, 7.0, 15.0]
        })
        fig = px.bar(df_ahorros, x='Producto', y='Tasa Máxima TEA (%)', text='Tasa Máxima TEA (%)',
                     color='Producto',
                     color_discrete_map={'Ahorro Tradicional': '#555', 'DPF (1 Año)': '#777', 'Cajas (CTS/DPF)': '#FF9900', 'Revolut (Tier 1)': '#00FFFF'})
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF', showlegend=False, height=300, margin=dict(t=20, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

# TAB 2: SPREAD CAMBIARIO
with tabs[1]:
    st.subheader("El Negocio del Tipo de Cambio: Fin del Oligopolio")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        <table class='custom-table'>
            <tr><th class='left-align'>Entidad / App</th><th>Spread Promedio (Venta-Compra)</th><th>Impacto en S/ 1,000 USD</th></tr>
            <tr><td class='left-align'>BCP / BBVA / Scotiabank</td><td class='banca-warn'>~ 2.50% - 3.00%</td><td class='banca-warn'>Pierdes ~$ 25 - $30 USD</td></tr>
            <tr><td class='left-align'>Interbank (Cambio Seguro)</td><td style='color:#FF9900'>~ 1.50% - 2.00%</td><td style='color:#FF9900'>Pierdes ~$ 15 - $20 USD</td></tr>
            <tr><td class='left-align'>YAPE / PLIN (Cambio In-App)</td><td class='banca-warn'>~ 2.00% - 2.50%</td><td class='banca-warn'>Pierdes ~$ 20 - $25 USD</td></tr>
            <tr><td class='left-align'>Casas de Cambio Digitales (Rextie, TKambio)</td><td style='color:#00FF00'>~ 0.50% - 0.80%</td><td style='color:#00FF00'>Pierdes ~$ 5 - $8 USD</td></tr>
            <tr><td class='left-align revolut-highlight'>Revolut</td><td class='revolut-highlight'>~ 0.00% - 0.50% (Interbancario Real)</td><td class='revolut-highlight'>Pierdes $ 0 - $5 USD</td></tr>
        </table>
        <p style='color:#888; font-size:0.9rem; margin-top:10px;'>*Revolut suele aplicar un markup del 1% solo los fines de semana cuando los mercados están cerrados.</p>
        """, unsafe_allow_html=True)
        
    with col2:
        # Gráfico Donut de Quién pierde más por Spread
        if not df.empty:
            df_spread = df.groupby('entidad_origen')['fuga_depositos_millones_pen'].sum().reset_index()
            fig = px.pie(df_spread, values='fuga_depositos_millones_pen', names='entidad_origen', hole=0.6,
                         color_discrete_sequence=['#FF3333', '#FF6633', '#FF9900', '#FFCC00', '#555555'])
            fig.update_traces(textposition='inside', textinfo='percent+label', textfont=dict(color='#FFFFFF', size=14))
            fig.update_layout(title="Distribución de Pérdida de Clientes (Fuga de Capital)", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF', margin=dict(t=40, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)

# TAB 3: PRÉSTAMOS
with tabs[2]:
    st.subheader("La Burbuja del Crédito: Consumo y MYPES")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        fig_loans = go.Figure()
        fig_loans.add_trace(go.Bar(name='Rango Min-Max (Banca Perú)', x=['Consumo', 'MYPEs'], y=[80, 80], base=[20, 15], marker_color='rgba(255, 51, 51, 0.5)', text=['Rango: 20%-80%', 'Rango: 15%-80%'], textposition='auto'))
        fig_loans.add_trace(go.Scatter(name='Promedio Sistema (SBS)', x=['Consumo', 'MYPEs'], y=[57.39, 55.62], mode='markers+text', marker=dict(color='#FF3333', size=12, symbol='line-ew', line=dict(width=2)), text=['57.4%', '55.6%'], textposition='top center'))
        fig_loans.add_trace(go.Scatter(name='Revolut (Foco Prime)', x=['Consumo', 'MYPEs'], y=[8.0, 9.0], mode='markers+text', marker=dict(color='#00FFFF', size=12, symbol='line-ew', line=dict(width=2)), text=['8.0%', '9.0%'], textposition='bottom center'))
        
        fig_loans.update_layout(title="Rangos de Tasas de Interés (TEA %)", barmode='overlay', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF', height=350, yaxis_title="Tasa de Interés (%)")
        st.plotly_chart(fig_loans, use_container_width=True)

    with col2:
        st.markdown("""
        <table class='custom-table'>
            <tr><th class='left-align'>Segmento</th><th>Tasa Sistema (Promedio)</th><th class='revolut-highlight'>Oferta Revolut (Estimado)</th></tr>
            <tr><td class='left-align'>Consumo (Bajo Riesgo / Prime)</td><td>~ 20% - 30%</td><td class='revolut-highlight'>7% - 9%</td></tr>
            <tr><td class='left-align'>Consumo (Riesgo Medio/Alto)</td><td class='banca-warn'>50% - 80%</td><td class='revolut-highlight'>No compite (Rechazo automático)</td></tr>
            <tr><td class='left-align'>MYPEs (Formales, buen récord)</td><td>~ 15% - 30%</td><td class='revolut-highlight'>9% - 12%</td></tr>
            <tr><td class='left-align'>MYPEs (Informales/Riesgo)</td><td class='banca-warn'>50% - 80%</td><td class='revolut-highlight'>No compite</td></tr>
        </table>
        <br>
        <p style='color:#DDD;'><strong>Análisis:</strong> Revolut no atacará la base de la pirámide ni a clientes no bancarizados. Su estrategia es hacer "Cherry-Picking", robando a los mejores clientes (riesgo A) de los grandes bancos ofreciéndoles tasas de primer mundo.</p>
        """, unsafe_allow_html=True)

# TAB 4: MANTENIMIENTO Y COMISIONES
with tabs[3]:
    st.subheader("Cargos Ocultos y Comisiones: El fin del 'Saldo Mínimo'")
    st.markdown("""
    <table class='custom-table'>
        <tr>
            <th class='left-align'>Concepto</th>
            <th>BCP (Cta. Ilimitada / Digital)</th>
            <th>BBVA (Cta. Independencia / Digital)</th>
            <th>Interbank (Súper Tasa / Simple)</th>
            <th class='revolut-highlight'>Revolut (Estándar)</th>
        </tr>
        <tr>
            <td class='left-align'>Mantenimiento Mensual</td>
            <td><span class='cross-red'>S/ 12.00</span> / <span class='check-green'>S/ 0.00</span></td>
            <td><span class='cross-red'>S/ 10.00</span> / <span class='check-green'>S/ 0.00</span></td>
            <td><span class='cross-red'>Condicionado (S/ 200 min)</span></td>
            <td class='revolut-highlight'>S/ 0.00 (Incondicional)</td>
        </tr>
        <tr>
            <td class='left-align'>Transferencias a otros bancos</td>
            <td><span class='check-green'>S/ 0.00 (Diferido)</span> / <span class='cross-red'>Costo si es Inmediata</span></td>
            <td><span class='check-green'>S/ 0.00</span></td>
            <td><span class='check-green'>S/ 0.00</span></td>
            <td class='revolut-highlight'>S/ 0.00 (Inmediata y Diferida)</td>
        </tr>
        <tr>
            <td class='left-align'>Uso de Cajeros Otra Red</td>
            <td><span class='cross-red'>Cobro de Comisión</span></td>
            <td><span class='cross-red'>Cobro de Comisión</span></td>
            <td><span class='cross-red'>Cobro de Comisión</span></td>
            <td class='revolut-highlight'>Gratis hasta un límite mensual</td>
        </tr>
        <tr>
            <td class='left-align'>Pagos Internacionales (TC)</td>
            <td><span class='cross-red'>Markup del 2% - 3%</span></td>
            <td><span class='cross-red'>Markup del 2% - 3%</span></td>
            <td><span class='cross-red'>Markup del 2% - 3%</span></td>
            <td class='revolut-highlight'>Sin Markup (Interbancario)</td>
        </tr>
    </table>
    """, unsafe_allow_html=True)

# TAB 5: PROYECCIÓN MIGRACIÓN
with tabs[4]:
    st.subheader("Hemorragia de Depósitos: Simulación a 12 Meses")
    if not df.empty:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig_area = px.area(df, x='mes_proyeccion', y='fuga_depositos_millones_pen', color='entidad_origen',
                               color_discrete_sequence=['#FF3333', '#FF6633', '#FF9900', '#FFCC00', '#00FFFF'],
                               title="Migración Acumulativa por Entidad (Millones PEN)")
            fig_area.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#FFF', height=400, xaxis_title="Mes", yaxis_title="Millones Migrados")
            st.plotly_chart(fig_area, use_container_width=True)
        with col2:
            yape_mig = df[df['entidad_origen'] == 'BCP']['fuga_depositos_millones_pen'].sum() * 0.4
            plin_mig = df[df['entidad_origen'].isin(['BBVA', 'Interbank', 'Scotiabank'])]['fuga_depositos_millones_pen'].sum() * 0.4
            st.markdown(f"""
            <div style='background-color:#111; padding:20px; border-radius:8px; border:1px solid #333;'>
                <h4 style='color:#FFF;'>Peligro Inminente: Canales Digitales</h4>
                <p style='color:#DDD; margin-top:10px;'>Yape y Plin son las pasarelas más vulnerables. Al estar sus usuarios 100% digitalizados, la fricción para abrir una cuenta en Revolut e inyectar fondos vía tarjeta de débito es casi nula.</p>
                <div style='margin-top:20px; border-left: 3px solid #FF3333; padding-left: 10px;'>
                    <strong style='color:#FF3333'>Migración Estimada YAPE:</strong><br>
                    <span style='font-size:1.5rem; color:#FFF'>S/ {yape_mig:,.1f} Millones</span>
                </div>
                <div style='margin-top:15px; border-left: 3px solid #FF9900; padding-left: 10px;'>
                    <strong style='color:#FF9900'>Migración Estimada PLIN:</strong><br>
                    <span style='font-size:1.5rem; color:#FFF'>S/ {plin_mig:,.1f} Millones</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No hay datos de BigQuery para la proyección.")

# TAB 6: ANÁLISIS
with tabs[5]:
    st.subheader("Análisis Estructural: Las Debilidades del Sistema Peruano")
    st.markdown("""
    <div style='padding: 20px; background-color: #111; border-radius: 8px; border: 1px solid #333;'>
        <ul style='color: #DDD; font-size: 1.1rem; line-height: 1.8;'>
            <li><strong style='color:#FF3333'>Márgenes Inflados (Spread):</strong> La banca tradicional en Perú goza de uno de los spreads de intermediación más altos de la región. Dependen de cobrar mucho por prestar y pagar poco por ahorrar. La llegada de una <i>Super App</i> con arquitectura de bajo costo rompe este modelo.</li>
            <li><strong style='color:#FF3333'>Costo de Legado Operativo:</strong> BCP, BBVA e Interbank tienen inmensas redes de agencias físicas y planillas gigantescas. Revolut no tiene sucursales, lo que le permite trasladar ese ahorro directamente a la tasa de interés del 15% para el cliente.</li>
            <li><strong style='color:#FF3333'>El "Impuesto" al Cambio de Divisa:</strong> Los peruanos están acostumbrados a perder entre el 2% y 3% de su dinero cada vez que compran dólares en el banco. Aunque existen casas de cambio digitales, Revolut integra esto nativamente a costo cero.</li>
            <li><strong style='color:#00FFFF'>Cherry Picking de Clientes Prime:</strong> Revolut no financiará la inclusión financiera en Perú. Su objetivo es robar los perfiles A y B (clientes con liquidez, viajeros, asalariados de alto nivel), dejando a los bancos locales con las carteras de mayor riesgo, lo que deteriorará la calidad de sus activos.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# TAB 7: CONCLUSIONES
with tabs[6]:
    st.subheader("Conclusiones y Plan de Acción Defensivo")
    st.markdown("""
<div style='padding: 20px; background-color: #111; border-radius: 8px; border: 1px solid #333;'>
<h4 style='color:#00FFFF;'>Conclusión Principal</h4>
<p style='color: #DDD; font-size: 1.1rem; line-height: 1.6;'>La entrada de Revolut al Perú (estimada para fines de 2026 / inicios de 2027) no es solo un competidor más; es un cambio de paradigma. Si replican su benchmark de México (15% garantizado con liquidez), el <strong>Costo de Oportunidad</strong> para el cliente digital peruano será demasiado alto como para ignorarlo. Las billeteras (Yape/Plin) sangrarán depósitos hacia Revolut de forma instantánea.</p>
<h4 style='color:#FF9900; margin-top:20px;'>Estrategia de Retención (Plan de Acción)</h4>
<ul style='color: #DDD; font-size: 1.1rem; line-height: 1.8;'>
<li><strong>Contraofensiva de Tasas (Cuentas Remuneradas):</strong> Los bancos líderes deben lanzar inmediatamente (o potenciar) cuentas 100% digitales que ofrezcan tasas escalonadas atractivas (min. 6%-8%) <i>sin bloquear la liquidez</i>, para mitigar el shock del 15%.</li>
<li><strong>Guerra de Divisas:</strong> Reducir el spread cambiario in-app a niveles de casas de cambio digitales (0.5%) para evitar que el cliente use Revolut como su puente de divisas principal.</li>
<li><strong>Fidelización del Cliente Prime:</strong> Blindar a la cartera de bajo riesgo con refinanciamientos de deuda de consumo a tasas de un solo dígito antes de que Revolut les envíe una oferta pre-aprobada.</li>
</ul>
</div>
    """, unsafe_allow_html=True)
