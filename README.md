# Predicción del comportamiento electoral presidencial en Colombia a nivel municipal

**Factores socioeconómicos y de conflicto armado (1998–2022)**

Trabajo Fin de Máster — Máster en Big Data, Data Science e Inteligencia Artificial (UCM)

---

## 1. Descripción del proyecto

Este proyecto construye una herramienta de apoyo para un **observatorio de integridad electoral**
(referencia conceptual: MOE — Misión de Observación Electoral de Colombia). A partir del perfil
socioeconómico y de conflicto armado de un municipio colombiano, el modelo predice el porcentaje
de voto esperado para el bloque de izquierda (Polo Democrático → Colombia Humana → Pacto
Histórico) en primera vuelta presidencial.

La aportación no es solo predictiva: **los residuos del modelo** (la diferencia entre el voto real
y el voto que el perfil estructural del municipio predice) se usan como señal para identificar
municipios cuyo comportamiento electoral se desvía de lo esperado — candidatos a revisión de
integridad electoral, en contextos de posible captura territorial del voto por parte de actores
armados.

> Los residuos miden la desviación del voto que no explican ni la estructura socioeconómica ni el
> nivel de conflicto del territorio. Esta desviación es una señal para revisión, no una prueba de
> fraude o coacción.

## 2. Estructura del repositorio

```
tfm-electoral-colombia/
├── README.md
├── requirements.txt
├── .gitignore
├── datos/
│   ├── raw/               # Datos originales (los ficheros >30MB no se versionan, ver sección 5)
│   └── procesados/        # Dataset maestro integrado y datasets intermedios limpios
├── notebooks/
│   ├── 01_preprocesamiento.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_modelizacion.ipynb
│   ├── 04_residuos_y_anomalias.ipynb
│   └── 05_productivizacion.ipynb
├── src/
│   ├── preprocesamiento.py
│   ├── modelo.py
│   └── utils.py
├── app/
│   └── streamlit_app.py   # Aplicación web (explorador de datos, predicción, mapa de anomalías)
├── modelos/
│   └── modelo_final.pkl   # Modelo serializado (se añade en la fase de productivización)
└── memoria/
    └── TFM_Diego_Abella.pdf
```

## 3. Instalación

```bash
git clone <URL_DE_ESTE_REPO>
cd tfm-electoral-colombia
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Ejecución

El proyecto no usa rutas locales hardcodeadas. Cada notebook y script define una variable
`BASE_DIR` configurable al inicio, que apunta a la raíz del proyecto:

```python
BASE_DIR = "."  # Ajustar solo si se ejecuta desde otra ubicación
```

Orden de ejecución de los notebooks:

1. `01_preprocesamiento.ipynb` — construye el dataset maestro integrado
2. `02_eda.ipynb` — análisis exploratorio
3. `03_modelizacion.ipynb` — validación por ventana expansiva, modelos regresores
4. `04_residuos_y_anomalias.ipynb` — análisis de residuos y mapa de anomalías
5. `05_productivizacion.ipynb` — serialización del modelo final

Para lanzar la aplicación web:

```bash
streamlit run app/streamlit_app.py
```

## 5. Datos y fuentes

| Bloque | Fuente | Nivel | Licencia / uso |
|---|---|---|---|
| Resultados electorales 1998–2018 | Registraduría Nacional del Estado Civil — [CEDAE](https://cedae.registraduria.gov.co/datos-para-la-democracia/resultados-electorales/descarga-datos) | Municipio | Datos abiertos del Estado colombiano, uso libre para investigación |
| Resultados electorales 2022 | [Observatorio de la Registraduría](https://observatorio.registraduria.gov.co/views/electoral/historicos-resultados.php) | Mesa (agregado a municipio) | Datos abiertos del Estado colombiano, uso libre para investigación |
| Víctimas del conflicto armado | [datos.gov.co — UARIV](https://www.datos.gov.co/Inclusi-n-Social-y-Reconciliaci-n/VICTIMAS-POR-A-OS-DEPARTAMENTAL/jurc-ck3a/about_data) | Departamento | Portal de datos abiertos del gobierno colombiano, licencia Creative Commons |
| NBI Censo 2005 | [DANE](https://www.dane.gov.co/files/censos/resultados/NBI_total_dpto_30_Jun_2012.xls) | Municipio | DANE — datos abiertos, uso libre |
| NBI Censo 2018 | [DANE](https://www.dane.gov.co/files/censo2018/informacion-tecnica/CNPV-2018-NBI.xlsx) | Municipio | DANE — datos abiertos, uso libre |
| IPM 2018–2022 | [DANE](https://www.dane.gov.co/files/investigaciones/condiciones_vida/pobreza/2022/anexo_dptal_pobreza_multidimensional_2022.xlsx) | Departamento | DANE — datos abiertos, uso libre |

Los ficheros originales de resultados electorales de 2022 a nivel de mesa, y el fichero original de
víctimas del conflicto (>30MB cada uno), superan el límite de tamaño de GitHub y no se versionan en
este repositorio. Están disponibles, tal como recomienda la guía del máster, en una carpeta de
Google Drive con acceso de lectura para cualquier persona con el enlace:

**[Carpeta de datos originales pesados (Google Drive)](https://drive.google.com/drive/folders/10MmaVe-ESKJQQPAvStOXWBVO4JbcNVuT?usp=sharing)**

Contiene:
- `VICTIMAS_DEPARTAMENTAL.csv` (original, 2,5GB) — se transforma con `src/filtrar_victimas.py`, cuyo resultado (`VICTIMAS_FILTRADO_V2.csv`) sí está en `datos/procesados/`
- `MMV_NACIONAL_PRESIDENTE_2022_1v.csv` (131MB) y `_2v.csv` (64MB) — se agregan a nivel municipal con `src/agregacion_2022.py`, cuyo resultado sí está en `datos/procesados/`

El resto de ficheros originales (resultados electorales 1998-2018, NBI 2005 y 2018, IPM, registro de
fuentes) sí están versionados en `datos/raw/` de este repositorio, al ser de tamaño reducido.

El análisis detallado de licencias de cada fuente se incluye en la sección de Datos de la memoria
del TFM (no solo en este README).

## 6. Metodología (resumen)

- **Unidad de análisis:** municipio × elección (~5.500 filas)
- **Variable objetivo:** % de voto del bloque de izquierda en primera vuelta
- **Validación:** ventana expansiva temporal (nunca split aleatorio, por la variable lag)
- **Modelos:** Ridge/Lasso (baseline) → Random Forest / SVR (principales) → XGBoost (opcional)
- **Métricas:** RMSE, MAE, R² (modelos de regresión)
- **Interpretabilidad:** SHAP + análisis de residuos + mapa coroplético

Detalle completo en `memoria/TFM_Diego_Abella.pdf`.

## 7. Limitaciones

Este análisis trabaja a nivel municipal (inferencia ecológica, no individual), usa el conflicto
armado como covariable departamental por falta de granularidad municipal en la fuente oficial, y
los residuos altos son indicios para revisión, no prueba de fraude o coacción electoral. Detalle
completo de limitaciones en la memoria.

## 8. Autor

Diego Abella — Máster en Big Data, Data Science e IA, UCM (semipresencial)

## 9. Licencia del código

Pendiente de definir (sugerido: MIT para el código; los datos siguen las licencias de sus fuentes
originales, indicadas en la sección 5).
