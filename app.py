"""
Asignación Óptima de Presupuesto Comercial
Modelo de Frontera Eficiente de Markowitz aplicado a canales comerciales.

Autor: Proyecto académico / demostración ejecutiva
Python: 3.12
Dependencias: streamlit, pandas, numpy, plotly, scipy, openpyxl
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats  # Se conserva como dependencia permitida para soporte estadístico básico.


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

APP_TITLE = "Asignación Óptima de Presupuesto Comercial"
APP_SUBTITLE = "Modelo de Frontera Eficiente de Markowitz aplicado a decisiones comerciales."
DEFAULT_BUDGET = 5_000_000
N_PORTFOLIOS = 10_000
RANDOM_SEED = 42
RISK_FREE_RATE = 0.0
TEMPLATE_FILE = "plantilla_roi_comercial.xlsx"


@dataclass
class PortfolioResult:
    """Contenedor de resultados del portafolio óptimo."""

    simulations: pd.DataFrame
    optimal_weights: np.ndarray
    optimal_return: float
    optimal_risk: float
    optimal_sharpe: float
    optimal_index: int


# =========================================================
# ESTILO VISUAL
# =========================================================


def apply_page_config() -> None:
    """Configura la página de Streamlit."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )



def inject_css() -> None:
    """Inyecta estilos compatibles con tema oscuro."""
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2.35rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.2rem;
        }
        .subtitle {
            font-size: 1.12rem;
            opacity: 0.80;
            margin-bottom: 1.4rem;
        }
        .section-header {
            font-size: 1.35rem;
            font-weight: 750;
            margin-top: 1.5rem;
            margin-bottom: 0.6rem;
        }
        .info-box {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            background: rgba(128, 128, 128, 0.06);
            margin-bottom: 1rem;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 14px;
            padding: 0.85rem;
            background: rgba(128, 128, 128, 0.06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# CARGA Y VALIDACIÓN DE DATOS
# =========================================================


def read_excel_file(uploaded_file) -> pd.DataFrame:
    """
    Lee el archivo Excel cargado por el usuario.

    Parameters
    ----------
    uploaded_file:
        Archivo cargado mediante st.file_uploader.

    Returns
    -------
    pd.DataFrame
        Base histórica de ROI comercial.
    """
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as exc:
        raise ValueError(
            "No fue posible leer el archivo. Verifique que sea un Excel válido con extensión .xlsx."
        ) from exc

    return df



def validate_input_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, list[str]]:
    """
    Valida el formato del archivo de entrada.

    Reglas de validación:
    - El archivo no debe estar vacío.
    - Debe existir la columna Mes.
    - Deben existir al menos dos canales comerciales.
    - Debe haber al menos tres observaciones históricas.
    - Los datos de ROI deben ser numéricos.

    Returns
    -------
    Tuple[pd.DataFrame, list[str]]
        DataFrame limpio y lista de canales comerciales.
    """
    if df is None or df.empty:
        raise ValueError("El archivo está vacío. Cargue una base con información histórica de ROI comercial.")

    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    if "Mes" not in df.columns:
        raise ValueError("El archivo debe contener una columna llamada 'Mes'.")

    channels = [col for col in df.columns if col != "Mes"]

    if len(channels) < 2:
        raise ValueError("Se requieren al menos dos canales comerciales para aplicar diversificación.")

    if len(df) < 3:
        raise ValueError("Se requieren al menos tres observaciones históricas para estimar riesgo.")

    # Convierte los ROI a numérico. Si hay texto inválido, se detecta explícitamente.
    converted = df[channels].apply(pd.to_numeric, errors="coerce")

    invalid_columns = []
    for channel in channels:
        original_non_empty = df[channel].notna()
        invalid_values = original_non_empty & converted[channel].isna()
        if invalid_values.any():
            invalid_columns.append(channel)

    if invalid_columns:
        raise ValueError(
            "Se encontraron datos no numéricos en los siguientes canales: "
            + ", ".join(invalid_columns)
            + ". Revise que todos los ROI sean números."
        )

    # Elimina filas sin información numérica en todos los canales.
    clean_df = pd.concat([df[["Mes"]], converted], axis=1).dropna(how="all", subset=channels)

    if len(clean_df) < 3:
        raise ValueError("Después de limpiar datos vacíos, quedan menos de tres observaciones históricas.")

    empty_channels = [channel for channel in channels if clean_df[channel].dropna().empty]
    if empty_channels:
        raise ValueError(
            "Los siguientes canales no tienen datos válidos: " + ", ".join(empty_channels)
        )

    # Si hay datos faltantes parciales, se imputan con la media del canal para mantener el ejemplo didáctico.
    # En una implementación productiva se recomienda revisar la causa de los datos faltantes.
    clean_df[channels] = clean_df[channels].apply(lambda s: s.fillna(s.mean()), axis=0)

    return clean_df, channels


# =========================================================
# CÁLCULOS DEL MODELO
# =========================================================


def calculate_statistics(df: pd.DataFrame, channels: list[str]) -> Tuple[pd.Series, pd.Series, pd.DataFrame, pd.DataFrame]:
    """Calcula ROI esperado, riesgo, correlación y covarianza."""
    roi_data = df[channels]
    expected_roi = roi_data.mean()
    risk = roi_data.std(ddof=1)
    correlation_matrix = roi_data.corr()
    covariance_matrix = roi_data.cov()

    return expected_roi, risk, correlation_matrix, covariance_matrix



def simulate_portfolios(
    expected_roi: pd.Series,
    covariance_matrix: pd.DataFrame,
    n_portfolios: int = N_PORTFOLIOS,
    risk_free_rate: float = RISK_FREE_RATE,
    seed: int = RANDOM_SEED,
) -> PortfolioResult:
    """
    Genera portafolios aleatorios mediante simulación Monte Carlo.

    La suma de pesos de cada portafolio es 100%.
    No se permiten posiciones negativas porque se trata de asignación presupuestal.
    """
    rng = np.random.default_rng(seed)
    n_assets = len(expected_roi)
    channels = list(expected_roi.index)

    expected_values = expected_roi.values
    covariance_values = covariance_matrix.values

    weights = rng.dirichlet(alpha=np.ones(n_assets), size=n_portfolios)
    portfolio_returns = weights @ expected_values
    portfolio_variances = np.einsum("ij,jk,ik->i", weights, covariance_values, weights)
    portfolio_risks = np.sqrt(np.maximum(portfolio_variances, 0))

    # Sharpe comercial: exceso de ROI sobre tasa libre de riesgo dividido entre riesgo.
    # Si el riesgo es cero, se evita división inválida.
    sharpe = np.divide(
        portfolio_returns - risk_free_rate,
        portfolio_risks,
        out=np.zeros_like(portfolio_returns),
        where=portfolio_risks > 0,
    )

    simulations = pd.DataFrame(
        {
            "ROI Esperado": portfolio_returns,
            "Riesgo": portfolio_risks,
            "Sharpe": sharpe,
        }
    )

    for i, channel in enumerate(channels):
        simulations[f"Peso {channel}"] = weights[:, i]

    optimal_index = int(np.nanargmax(sharpe))
    optimal_weights = weights[optimal_index]

    return PortfolioResult(
        simulations=simulations,
        optimal_weights=optimal_weights,
        optimal_return=float(portfolio_returns[optimal_index]),
        optimal_risk=float(portfolio_risks[optimal_index]),
        optimal_sharpe=float(sharpe[optimal_index]),
        optimal_index=optimal_index,
    )



def build_summary_table(expected_roi: pd.Series, risk: pd.Series) -> pd.DataFrame:
    """Construye la tabla de resumen estadístico por canal."""
    summary = pd.DataFrame(
        {
            "Canal": expected_roi.index,
            "ROI Esperado": expected_roi.values,
            "Riesgo": risk.values,
        }
    )
    return summary.sort_values("ROI Esperado", ascending=False).reset_index(drop=True)



def build_optimal_allocation(
    channels: list[str],
    weights: np.ndarray,
    budget: float,
) -> pd.DataFrame:
    """Construye la tabla de asignación monetaria óptima."""
    allocation = pd.DataFrame(
        {
            "Canal": channels,
            "Peso %": weights,
            "Asignación monetaria": weights * budget,
        }
    )
    return allocation.sort_values("Peso %", ascending=False).reset_index(drop=True)


# =========================================================
# GRÁFICAS
# =========================================================


def plot_heatmap(matrix: pd.DataFrame, title: str, value_format: str = ".2f") -> go.Figure:
    """Genera un heatmap Plotly para matrices."""
    fig = px.imshow(
        matrix,
        text_auto=value_format,
        aspect="auto",
        color_continuous_scale="RdBu",
        title=title,
    )
    fig.update_layout(
        height=520,
        margin=dict(l=20, r=20, t=70, b=20),
        coloraxis_colorbar=dict(title="Valor"),
    )
    return fig



def plot_efficient_frontier(result: PortfolioResult) -> go.Figure:
    """Grafica la nube de portafolios simulados y el punto óptimo."""
    sims = result.simulations

    fig = px.scatter(
        sims,
        x="Riesgo",
        y="ROI Esperado",
        color="Sharpe",
        color_continuous_scale="Viridis",
        title="Frontera eficiente simulada: riesgo vs ROI esperado",
        labels={
            "Riesgo": "Riesgo esperado",
            "ROI Esperado": "ROI esperado",
            "Sharpe": "Sharpe",
        },
        opacity=0.72,
    )

    fig.add_trace(
        go.Scatter(
            x=[result.optimal_risk],
            y=[result.optimal_return],
            mode="markers+text",
            marker=dict(size=16, symbol="star", color="red", line=dict(width=1, color="white")),
            text=["Máximo Sharpe"],
            textposition="top center",
            name="Portafolio óptimo",
        )
    )

    fig.update_layout(
        height=650,
        margin=dict(l=20, r=20, t=70, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig



def plot_budget_pie(allocation: pd.DataFrame) -> go.Figure:
    """Grafica la distribución óptima del presupuesto comercial."""
    fig = px.pie(
        allocation,
        names="Canal",
        values="Asignación monetaria",
        title="Distribución óptima del presupuesto comercial",
        hole=0.35,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=520, margin=dict(l=20, r=20, t=70, b=20))
    return fig


# =========================================================
# FORMATO DE TABLAS
# =========================================================


def format_summary_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Aplica formato visual a la tabla de resumen."""
    return df.style.format({"ROI Esperado": "{:.2f}", "Riesgo": "{:.2f}"})



def format_matrix(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Aplica formato visual a matrices."""
    return df.style.format("{:.4f}").background_gradient(cmap="RdBu")



def format_allocation_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Aplica formato visual a la tabla de asignación."""
    return df.style.format({"Peso %": "{:.2%}", "Asignación monetaria": "${:,.0f}"})


# =========================================================
# COMPONENTES DE INTERFAZ
# =========================================================


def render_header() -> None:
    """Muestra título y explicación inicial."""
    st.markdown(f'<div class="main-title">{APP_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{APP_SUBTITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="info-box">
        Esta aplicación trata cada canal comercial como un activo. El ROI Comercial histórico representa el rendimiento; 
        la desviación estándar del ROI representa el riesgo; y la correlación permite identificar beneficios de diversificación.
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_sidebar() -> Tuple[Optional[object], float]:
    """Renderiza controles laterales y devuelve archivo cargado y presupuesto."""
    st.sidebar.header("Parámetros")

    uploaded_file = st.sidebar.file_uploader(
        "Cargar archivo Excel con ROI Comercial histórico",
        type=["xlsx"],
        help="El archivo debe contener una columna Mes y columnas adicionales con canales comerciales.",
    )

    budget = st.sidebar.number_input(
        "Presupuesto total disponible",
        min_value=0.0,
        value=float(DEFAULT_BUDGET),
        step=100_000.0,
        format="%.2f",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Supuesto del modelo: tasa libre de riesgo = 0.")
    st.sidebar.caption(f"Simulaciones Monte Carlo: {N_PORTFOLIOS:,} portafolios.")

    template_path = Path(TEMPLATE_FILE)
    if template_path.exists():
        with open(template_path, "rb") as file:
            st.sidebar.download_button(
                label="Descargar plantilla Excel",
                data=file,
                file_name=TEMPLATE_FILE,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    return uploaded_file, budget



def render_empty_state() -> None:
    """Muestra instrucciones cuando aún no hay archivo cargado."""
    st.info("Cargue un archivo Excel para iniciar el análisis. Puede usar la plantilla incluida en la barra lateral.")
    st.markdown(
        """
        **Formato esperado:**

        | Mes | Google Ads | Facebook Ads | LinkedIn | Vendedores | Distribuidores | Referidos |
        |---|---:|---:|---:|---:|---:|---:|
        | Ene | 3.1 | 2.5 | 1.8 | 2.4 | 1.9 | 3.2 |
        | Feb | 2.8 | 3.4 | 1.9 | 2.7 | 2.1 | 3.0 |
        | Mar | 3.5 | 1.9 | 2.1 | 2.8 | 2.0 | 3.4 |
        """
    )



def render_results(
    df: pd.DataFrame,
    channels: list[str],
    budget: float,
) -> None:
    """Ejecuta el modelo y muestra las siete secciones solicitadas."""
    expected_roi, risk, corr_matrix, cov_matrix = calculate_statistics(df, channels)
    result = simulate_portfolios(expected_roi, cov_matrix)
    summary = build_summary_table(expected_roi, risk)
    allocation = build_optimal_allocation(channels, result.optimal_weights, budget)

    # SECCIÓN 1
    st.markdown('<div class="section-header">1. Resumen estadístico</div>', unsafe_allow_html=True)
    st.dataframe(format_summary_table(summary), use_container_width=True)

    # SECCIÓN 2
    st.markdown('<div class="section-header">2. Matriz de correlación</div>', unsafe_allow_html=True)
    st.dataframe(format_matrix(corr_matrix), use_container_width=True)
    st.plotly_chart(plot_heatmap(corr_matrix, "Heatmap de correlación", ".2f"), use_container_width=True)

    # SECCIÓN 3
    st.markdown('<div class="section-header">3. Matriz de covarianza</div>', unsafe_allow_html=True)
    st.dataframe(format_matrix(cov_matrix), use_container_width=True)
    st.plotly_chart(plot_heatmap(cov_matrix, "Heatmap de covarianza", ".4f"), use_container_width=True)

    # SECCIÓN 4
    st.markdown('<div class="section-header">4. Frontera eficiente</div>', unsafe_allow_html=True)
    st.plotly_chart(plot_efficient_frontier(result), use_container_width=True)

    # SECCIÓN 5
    st.markdown('<div class="section-header">5. Portafolio óptimo</div>', unsafe_allow_html=True)
    st.dataframe(format_allocation_table(allocation), use_container_width=True)

    # SECCIÓN 6
    st.markdown('<div class="section-header">6. Indicadores finales</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    col1.metric("ROI esperado de la cartera", f"{result.optimal_return:.2f}")
    col2.metric("Riesgo esperado de la cartera", f"{result.optimal_risk:.2f}")
    col3.metric("Sharpe de la cartera", f"{result.optimal_sharpe:.2f}")

    # SECCIÓN 7
    st.markdown('<div class="section-header">7. Gráfico de distribución</div>', unsafe_allow_html=True)
    st.plotly_chart(plot_budget_pie(allocation), use_container_width=True)

    with st.expander("Interpretación ejecutiva"):
        st.write(
            "El portafolio óptimo maximiza la relación entre ROI esperado y riesgo. "
            "No necesariamente concentra el presupuesto en el canal de mayor ROI individual; "
            "la recomendación incorpora riesgo histórico, correlación y diversificación entre canales."
        )


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================


def main() -> None:
    """Punto de entrada de la aplicación."""
    apply_page_config()
    inject_css()
    render_header()

    uploaded_file, budget = render_sidebar()

    if uploaded_file is None:
        render_empty_state()
        return

    try:
        raw_df = read_excel_file(uploaded_file)
        clean_df, channels = validate_input_data(raw_df)
    except ValueError as err:
        st.error(str(err))
        return
    except Exception as err:  # Protección general para evitar caída de la app en demostraciones.
        st.error(f"Ocurrió un error inesperado al procesar el archivo: {err}")
        return

    st.success("Archivo cargado y validado correctamente.")

    with st.expander("Vista previa de datos cargados", expanded=False):
        st.dataframe(clean_df, use_container_width=True)

    render_results(clean_df, channels, budget)


if __name__ == "__main__":
    main()
