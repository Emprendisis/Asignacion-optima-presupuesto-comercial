# Asignación Óptima de Presupuesto Comercial

Aplicación didáctica en Python y Streamlit para demostrar cómo la lógica de frontera eficiente de Harry Markowitz puede aplicarse a decisiones comerciales de una PyME, sustituyendo activos bursátiles por canales comerciales.

## Objetivo del modelo

Responder:

> ¿Cuál es la combinación óptima de inversión comercial para maximizar las ventas con el menor riesgo posible?

Cada canal comercial se interpreta como un activo. La aplicación estima rendimiento, riesgo, correlación y diversificación para construir una frontera eficiente mediante simulación Monte Carlo.

## Definición de ROI Comercial

El retorno esperado de cada canal se mide como:

```text
ROI Comercial = Ventas Generadas / Inversión Realizada
```

Ejemplo: si un canal generó $3,000,000 en ventas con $1,000,000 de inversión, su ROI Comercial es 3.0.

## Definición de Riesgo Comercial

El riesgo comercial se define como la desviación estándar histórica del ROI Comercial de cada canal.

Un canal con ROI muy variable entre meses tiene mayor riesgo que un canal con ROI más estable.

## Lógica financiera utilizada

La aplicación calcula:

- ROI esperado por canal.
- Riesgo histórico por canal.
- Matriz de correlación entre canales.
- Matriz de covarianza.
- 10,000 portafolios comerciales simulados.
- ROI esperado de cada portafolio.
- Riesgo esperado de cada portafolio.
- Sharpe comercial, suponiendo tasa libre de riesgo igual a cero.
- Portafolio óptimo de máximo Sharpe.

## Archivos del proyecto

```text
app.py
requirements.txt
README.md
plantilla_roi_comercial.xlsx
```

## Formato esperado del Excel

La primera columna debe llamarse `Mes`.

Las columnas restantes deben representar canales comerciales. Los valores deben ser ROI Comercial histórico.

Ejemplo:

| Mes | Google Ads | Facebook Ads | LinkedIn | Vendedores |
|---|---:|---:|---:|---:|
| Ene | 3.1 | 2.5 | 1.8 | 2.4 |
| Feb | 2.8 | 3.4 | 1.9 | 2.7 |
| Mar | 3.5 | 1.9 | 2.1 | 2.8 |

La plantilla incluida contiene 24 meses de datos ficticios para:

- Google Ads
- Facebook Ads
- LinkedIn
- Vendedores
- Distribuidores
- Referidos

## Validaciones incluidas

La aplicación valida:

- Archivo vacío.
- Falta de columna `Mes`.
- Menos de dos canales comerciales.
- Datos no numéricos.
- Menos de tres observaciones históricas.
- Columnas comerciales sin datos válidos.

## Cómo ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cómo desplegar en Streamlit Cloud

1. Crear un repositorio en GitHub.
2. Subir estos archivos:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `plantilla_roi_comercial.xlsx`
3. Entrar a Streamlit Cloud.
4. Seleccionar el repositorio.
5. Definir `app.py` como archivo principal.
6. Desplegar la aplicación.

## Ejemplo de uso

1. Abrir la aplicación.
2. Descargar la plantilla Excel.
3. Sustituir los datos ficticios por información histórica real de la empresa.
4. Cargar el archivo actualizado.
5. Definir el presupuesto comercial disponible.
6. Revisar:
   - Resumen estadístico.
   - Matrices de correlación y covarianza.
   - Frontera eficiente.
   - Portafolio óptimo.
   - Asignación monetaria recomendada por canal.

## Interpretación ejecutiva

El portafolio óptimo no necesariamente asigna más presupuesto al canal con mayor ROI individual. La lógica de Markowitz privilegia la combinación de canales que, en conjunto, ofrece mejor relación entre retorno esperado y riesgo.

Esto permite explicar la diversificación comercial: combinar canales con comportamientos distintos puede reducir la volatilidad del resultado comercial total.
