import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------

st.set_page_config(
    page_title="Asignación Óptima de Presupuesto Comercial",
    layout="wide"
)

st.title("Asignación Óptima de Presupuesto Comercial")
st.markdown(
    """
    Aplicación didáctica basada en la lógica de Harry Markowitz.

    **Objetivo:** determinar la combinación óptima de inversión comercial
    para maximizar las ventas esperadas con el menor riesgo posible.
    """
)

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

st.sidebar.header("Configuración")

presupuesto = st.sidebar.number_input(
    "Presupuesto Total",
    min_value=1000.0,
    value=5000000.0,
    step=100000.0
)

n_simulaciones = st.sidebar.slider(
    "Número de simulaciones",
    min_value=1000,
    max_value=20000,
    value=5000,
    step=1000
)

# ---------------------------------------------------
# CARGA DE ARCHIVO
# ---------------------------------------------------

archivo = st.file_uploader(
    "Cargar archivo Excel histórico de ROI Comercial",
    type=["xlsx"]
)

# ---------------------------------------------------
# FUNCIONES
# ---------------------------------------------------

def validar_datos(df):
    if df.shape[0] < 3:
        return False, "Se requieren al menos 3 observaciones históricas."

    if df.shape[1] < 2:
        return False, "Debe existir una columna de fecha y al menos un canal."

    return True, ""


def calcular_metricas(datos):
    roi_esperado = datos.mean()
    riesgo = datos.std()

    resumen = pd.DataFrame({
        "ROI Esperado": roi_esperado,
        "Riesgo": riesgo
    })

    resumen = resumen.sort_values(
        "ROI Esperado",
        ascending=False
    )

    return resumen


def simular_portafolios(datos, simulaciones):

    medias = datos.mean().values
    covarianza = datos.cov().values

    n_activos = len(datos.columns)

    resultados = []

    for _ in range(simulaciones):

        pesos = np.random.random(n_activos)
        pesos = pesos / pesos.sum()

        roi = np.sum(medias * pesos)

        riesgo = np.sqrt(
            np.dot(
                pesos.T,
                np.dot(covarianza, pesos)
            )
        )

        sharpe = 0 if riesgo == 0 else roi / riesgo

        resultados.append(
            [roi, riesgo, sharpe, *pesos]
        )

    columnas = (
        ["ROI", "Riesgo", "Sharpe"]
        + list(datos.columns)
    )

    return pd.DataFrame(
        resultados,
        columns=columnas
    )


# ---------------------------------------------------
# PROCESAMIENTO
# ---------------------------------------------------

if archivo is not None:

    try:

        df = pd.read_excel(archivo)

        valido, mensaje = validar_datos(df)

        if not valido:
            st.error(mensaje)
            st.stop()

        st.success("Archivo cargado correctamente")

        st.subheader("Base de Datos")

        st.dataframe(df, use_container_width=True)

        # Eliminar primera columna (Mes)
        datos = df.iloc[:, 1:].copy()

        # Convertir a numérico
        for col in datos.columns:
            datos[col] = pd.to_numeric(
                datos[col],
                errors="coerce"
            )

        datos = datos.dropna()

        # ---------------------------------------------------
        # RESUMEN ESTADÍSTICO
        # ---------------------------------------------------

        st.subheader("ROI Esperado y Riesgo por Canal")

        resumen = calcular_metricas(datos)

        st.dataframe(
            resumen.style.format({
                "ROI Esperado": "{:.2f}",
                "Riesgo": "{:.2f}"
            }),
            use_container_width=True
        )

        # ---------------------------------------------------
        # CORRELACIÓN
        # ---------------------------------------------------

        correlacion = datos.corr()

        st.subheader("Matriz de Correlación")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.dataframe(
                correlacion.round(2),
                use_container_width=True
            )

        with col2:
            fig_corr = px.imshow(
                correlacion,
                text_auto=".2f",
                aspect="auto",
                title="Heatmap de Correlaciones"
            )

            st.plotly_chart(
                fig_corr,
                use_container_width=True
            )

        # ---------------------------------------------------
        # COVARIANZA
        # ---------------------------------------------------

        covarianza = datos.cov()

        st.subheader("Matriz de Covarianza")

        col3, col4 = st.columns([1, 1])

        with col3:
            st.dataframe(
                covarianza.round(4),
                use_container_width=True
            )

        with col4:
            fig_cov = px.imshow(
                covarianza,
                text_auto=".4f",
                aspect="auto",
                title="Heatmap de Covarianzas"
            )

            st.plotly_chart(
                fig_cov,
                use_container_width=True
            )

        # ---------------------------------------------------
        # MONTE CARLO
        # ---------------------------------------------------

        st.subheader(
            "Simulación Monte Carlo y Frontera Eficiente"
        )

        simulaciones = simular_portafolios(
            datos,
            n_simulaciones
        )

        cartera_optima = simulaciones.loc[
            simulaciones["Sharpe"].idxmax()
        ]

        # ---------------------------------------------------
        # FRONTERA EFICIENTE
        # ---------------------------------------------------

        fig = px.scatter(
            simulaciones,
            x="Riesgo",
            y="ROI",
            color="Sharpe",
            title="Frontera Eficiente Comercial"
        )

        fig.add_trace(
            go.Scatter(
                x=[cartera_optima["Riesgo"]],
                y=[cartera_optima["ROI"]],
                mode="markers",
                marker=dict(
                    size=18,
                    symbol="star",
                    color="red"
                ),
                name="Óptimo"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ---------------------------------------------------
        # PESOS ÓPTIMOS
        # ---------------------------------------------------

        st.subheader("Asignación Óptima")

        pesos = cartera_optima[datos.columns]

        asignacion = pd.DataFrame({
            "Canal": datos.columns,
            "Peso (%)": pesos.values * 100,
            "Asignación ($)": pesos.values * presupuesto
        })

        asignacion = asignacion.sort_values(
            "Peso (%)",
            ascending=False
        )

        st.dataframe(
            asignacion.style.format({
                "Peso (%)": "{:.2f}",
                "Asignación ($)": "${:,.0f}"
            }),
            use_container_width=True
        )

        # ---------------------------------------------------
        # MÉTRICAS
        # ---------------------------------------------------

        st.subheader("Indicadores de la Cartera")

        m1, m2, m3 = st.columns(3)

        with m1:
            st.metric(
                "ROI Esperado",
                f"{cartera_optima['ROI']:.2f}"
            )

        with m2:
            st.metric(
                "Riesgo",
                f"{cartera_optima['Riesgo']:.4f}"
            )

        with m3:
            st.metric(
                "Sharpe",
                f"{cartera_optima['Sharpe']:.2f}"
            )

        # ---------------------------------------------------
        # PIE CHART
        # ---------------------------------------------------

        st.subheader(
            "Distribución Óptima del Presupuesto"
        )

        fig_pie = px.pie(
            asignacion,
            names="Canal",
            values="Asignación ($)",
            hole=0.40
        )

        st.plotly_chart(
            fig_pie,
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

else:
    st.info(
        "Carga la plantilla ROI Comercial para comenzar."
    )