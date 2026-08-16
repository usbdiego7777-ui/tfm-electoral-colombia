# Análisis del comportamiento electoral territorial en Colombia
## Inercia, pobreza y regionalización del voto de izquierda a nivel municipal (2006–2022)

**Trabajo Fin de Máster — Máster en Big Data, Data Science e Inteligencia Artificial (UCM)**
**Autor:** Diego Abella · Tutores: Carlos Ortega y Santiago Mota

---

## 1. Descripción del proyecto

Este proyecto analiza qué factores explican el voto del bloque de izquierda (Polo Democrático →
Colombia Humana → Pacto Histórico) en las elecciones presidenciales de primera vuelta en Colombia,
a nivel municipal, entre 2006 y 2022. Es una herramienta de comprensión del voto territorial para
**analistas electorales, investigadores y periodistas de datos** que quieren entender el mapa
electoral colombiano — y qué no lo explica.

### Origen y reencuadre del proyecto

El diseño original planteaba una hipótesis distinta: que los residuos de un modelo estructural
(pobreza + conflicto armado) revelarían posible coacción territorial del voto en zonas de
conflicto. Esa hipótesis se sometió a prueba rigurosa (ver `notebooks/03b_experimentos_decisivos.ipynb`)
y no se sostuvo: el conflicto armado no aporta capacidad explicativa una vez controlado por
pobreza y región (ΔR²≈ruido, correlación parcial incluso negativa). El proyecto se reencuadró
en torno a lo que los datos sí demuestran.

Contar esto forma parte del trabajo: someter una hipótesis a prueba y aceptar lo que los datos
dicen es investigación de verdad, y el resultado negativo es en sí mismo una conclusión
científica válida.

### Los cuatro hallazgos reales

1. **La inercia electoral es el predictor dominante.** El voto de un municipio se explica
   sobre todo por cómo votó en la elección anterior. Ningún modelo ajustado (lineal o no lineal)
   supera de forma clara al baseline de "copiar el resultado anterior" en la métrica que importa
   (correlación intra-año).

2. **La relación pobreza–voto es heterogénea y de signo opuesto por región** (falacia ecológica
   documentada): correlación negativa en la región Andina/Caribe, positiva en
   frontera/Amazonía-Orinoquía. La correlación global de ~0,03 es el promedio de dos señales
   reales que se cancelan.

3. **El voto de izquierda está fuertemente regionalizado** — el bloque Pacífico/periferia
   explica el 96-99% de lo que NBI+región capturan juntos. Es más regionalización que
   estructuración por pobreza.

4. **El conflicto armado no añade capacidad explicativa** una vez controlado por pobreza y
   región. Es un resultado negativo, genuino y contraintuitivo: desmiente la hipótesis intuitiva
   de "más conflicto → voto anómalo/capturado".

### Los residuos del modelo: su uso honesto

Los residuos del modelo con inercia (lag) identifican municipios que votan de forma
significativamente distinta a lo que su propia trayectoria histórica predice. Son una señal de
cambio político genuino — no una prueba de coacción o fraude.

> *"Los residuos miden la desviación del voto respecto a lo que la trayectoria histórica del
> municipio y su perfil estructural predicen. Son una señal de cambio político que merece
> análisis adicional, no una prueba de irregularidad."*

---

## 2. Aplicación web

La aplicación está desplegada en Streamlit Cloud y accesible directamente desde el navegador,
sin necesidad de instalación local:

**🔗 [tfm-electoral-colombia-2026.streamlit.app](https://tfm-electoral-colombia-2026.streamlit.app)**

Es una app multi-página (navegación por menú lateral), con tres secciones:

- **Explorador territorial** (`app/Explorador_territorial.py`, página de entrada): tres pestañas
  — mapa interactivo del % de izquierda por municipio y año (sobre mapa base real, con zoom y
  desplazamiento), evolución temporal 2006-2022 (curva "V"), y relación NBI-voto por región con
  selector de filtro.
- **Predicción y análisis individual:** selecciona departamento, municipio y año — muestra el
  voto real, el voto que predice la trayectoria histórica del municipio, y la desviación entre
  ambos con un indicador visual (verde/naranja/rojo según la magnitud).
- **Rompen su tendencia:** dos mapas de residuos de 2022 (absoluto y centrado
  respecto a la ola nacional) y tabla de los 20 municipios con mayor desviación. Filtrado por
  fiabilidad estadística — los municipios con menos de 30 votos no compiten en el ranking.

La app consume directamente los datos ya procesados (`datos/procesados/`), nunca recalcula nada
en caliente — no requiere ni usa ningún modelo serializado.

---

## 3. Estructura del repositorio

```
tfm-electoral-colombia/
├── README.md
├── requirements.txt
├── .gitignore
├── datos/
│   ├── raw/                    # Datos originales livianos (versionados en git)
│   ├── procesados/             # Dataset maestro, tabla de residuos y datasets derivados
│   └── geo/                    # Geometría municipal simplificada (MGN 2018)
│       └── municipios_colombia_simplificado.geojson  # ✅ 3,8 MB
├── notebooks/
│   ├── figuras/                # Figuras reutilizables (Streamlit + memoria)
│   ├── 01_preprocesamiento.ipynb        # ✅ Integración de fuentes → dataset maestro
│   ├── 02_eda.ipynb                     # ✅ Análisis exploratorio
│   ├── 03_modelizacion.ipynb            # ✅ Pipeline predictivo: ventana expansiva
│   ├── 03b_experimentos_decisivos.ipynb # ✅ Conflicto vs. pobreza/región
│   ├── 04_residuos_y_anomalias.ipynb    # ✅ Residuos + mapas coropléticos (memoria)
│   └── 05_productivizacion.ipynb        # No aplica — ver nota abajo
├── src/
│   ├── preprocesamiento.py     # ✅ Funciones de integración y limpieza de datos
│   ├── agregacion_2022.py      # ✅ Agrega datos de 2022 de mesa a municipio
│   ├── filtrar_victimas.py     # ✅ Filtra el fichero de víctimas (2,5GB → manejable)
│   ├── integrar_nbi.py         # ✅ Integra NBI 2005/2018 al panel electoral
│   ├── integrar_victimas.py    # ✅ Integra PER_OCU (conflicto) al panel electoral
│   ├── integrar_geometria.py   # ✅ Geometría municipal MGN 2018 (dissolve + simplificación)
│   ├── verificar_calidad_y_finalizar.py  # ✅ Verificación de calidad del dataset maestro
│   ├── eda_utils.py            # ✅ Funciones auxiliares del EDA
│   ├── modelo.py               # ✅ Funciones de modelización: ventanas, métricas, modelos
│   └── utils.py                # Utilidades compartidas
├── app/                         # ✅ Aplicación Streamlit — desplegada
│   ├── Explorador_territorial.py   # Página 1 (entrada) — 3 pestañas: mapa, evolución, NBI-voto
│   ├── data_utils.py            # Carga de datos y estilo, compartido entre páginas
│   └── pages/
│       ├── 2_Prediccion_y_analisis_individual.py
│       └── 3_Rompen_su_tendencia.py
├── modelos/                      # No aplica — la app consume datos precalculados
│                                  # (tabla_residuos.csv), no necesita modelo serializado
└── memoria/
    └── TFM_Diego_Abella.pdf     # 🔄 Pendiente
```

> **Nota sobre `05_productivizacion.ipynb` y `modelos/`:** el diseño original de la app preveía
> serializar un modelo en `modelos/modelo_final.pkl` para hacer predicciones en vivo. Al construir
> la app se confirmó que las tres páginas se apoyan enteramente en datos ya precalculados
> (`dataset_maestro_electoral.csv` y `tabla_residuos.csv`, ambos generados en fases anteriores) —
> no hay ningún flujo de predicción en tiempo real que requiera cargar un modelo. Por eso el
> notebook `05` y la carpeta `modelos/` no se usan; la productivización vive directamente en
> `app/`.

---

## 4. Instalación y ejecución

### Instalación

```bash
git clone https://github.com/usbdiego7777-ui/tfm-electoral-colombia.git
cd tfm-electoral-colombia
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuración de rutas

El proyecto no usa rutas locales hardcodeadas. Cada notebook define al inicio:

```python
BASE_DIR = ".."  # Raíz del proyecto — ajustar solo si se ejecuta desde otra ubicación
```

La app de Streamlit calcula `BASE_DIR` automáticamente a partir de la ubicación de
`app/data_utils.py` (ver ese fichero) — no requiere configuración manual salvo que se despliegue
en un entorno con una estructura de carpetas distinta, en cuyo caso puede fijarse con la variable
de entorno `TFM_BASE_DIR`.

### Orden de ejecución de los notebooks

> ⚠️ **Importante:** los notebooks usan rutas relativas con `BASE_DIR = '..'`
> y **deben ejecutarse desde la carpeta `notebooks/`**, no desde la raíz del proyecto.
> Si se abren desde otro directorio, ajustar `BASE_DIR` al principio de cada notebook.

| Orden | Notebook | Estado | Descripción |
|-------|----------|--------|-------------|
| 1 | `01_preprocesamiento.ipynb` | ✅ Completado | Integra las cinco fuentes en el dataset maestro |
| 2 | `02_eda.ipynb` | ✅ Completado | Análisis exploratorio: distribución, correlaciones, regionalización |
| 3 | `03_modelizacion.ipynb` | ✅ Completado | Pipeline predictivo con ventana expansiva temporal |
| 3b | `03b_experimentos_decisivos.ipynb` | ✅ Completado | Experimentos conflicto vs. pobreza/región (*) |
| 4 | `04_residuos_y_anomalias.ipynb` | ✅ Completado | Residuos, tabla de residuos y mapas coropléticos de la memoria |
| 5 | `05_productivizacion.ipynb` | No aplica | Ver nota en la sección 3 — la productivización vive en `app/` |

(*) `03b` no depende de ningún fichero generado por `03` — ambos cargan directamente
`datos/procesados/dataset_maestro_electoral.csv`. El orden 3→3b es narrativo, no técnico.

### Lanzar la aplicación web (local)

```bash
streamlit run app/Explorador_territorial.py
```

Streamlit detecta automáticamente `app/pages/` y añade las Páginas 2 y 3 al menú lateral — no
hace falta lanzar cada página por separado.

---

## 5. Datos y fuentes

Todas las fuentes son públicas y de acceso libre. El análisis detallado de licencias figura
en la sección de Datos de la memoria del TFM.

| Bloque | Fuente | Nivel | Años | Licencia |
|--------|--------|-------|------|----------|
| Resultados electorales 1998–2018 | [Registraduría — CEDAE](https://cedae.registraduria.gov.co/datos-para-la-democracia/resultados-electorales/descarga-datos) | Municipio | 1998–2018 | Datos abiertos del Estado colombiano |
| Resultados electorales 2022 | [Observatorio Registraduría](https://observatorio.registraduria.gov.co/views/electoral/historicos-resultados.php) | Mesa → municipio | 2022 | Datos abiertos del Estado colombiano |
| Víctimas del conflicto armado | [datos.gov.co — UARIV](https://www.datos.gov.co/Inclusi-n-Social-y-Reconciliaci-n/VICTIMAS-POR-A-OS-DEPARTAMENTAL/jurc-ck3a/about_data) | Departamento | 1998–2022 | Creative Commons — uso libre |
| NBI Censo 2005 | [DANE](https://www.dane.gov.co/files/censos/resultados/NBI_total_dpto_30_Jun_2012.xls) | Municipio | Censo 2005 | DANE — datos abiertos |
| NBI Censo 2018 | [DANE](https://www.dane.gov.co/files/censo2018/informacion-tecnica/CNPV-2018-NBI.xlsx) | Municipio | Censo 2018 | DANE — datos abiertos |
| IPM 2018–2022 | [DANE](https://www.dane.gov.co/files/investigaciones/condiciones_vida/pobreza/2022/anexo_dptal_pobreza_multidimensional_2022.xlsx) | Departamento | 2018–2022 | DANE — datos abiertos |
| Geometría municipal (MGN 2018, capa Municipio) | [DANE — Geoportal](https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/) (descarga manual vía geovisor, sin URL directa) | Municipio | MGN versión 2018 | DANE — datos abiertos |

### Datos pesados (no versionados en git)

Los ficheros originales de 2022 (nivel mesa), el fichero de víctimas y el shapefile crudo del
MGN superan el límite cómodo de GitHub. Están disponibles en Google Drive con acceso público de
lectura:

**[Carpeta de datos originales — Google Drive](https://drive.google.com/drive/folders/10MmaVe-ESKJQQPAvStOXWBVO4JbcNVuT?usp=sharing)**

| Fichero | Tamaño | Script de transformación | Resultado en el repo |
|---------|--------|--------------------------|----------------------|
| `VICTIMAS_DEPARTAMENTAL.csv` | 2,5 GB | `src/filtrar_victimas.py` | `datos/procesados/VICTIMAS_FILTRADO_V2.csv` |
| `MMV_NACIONAL_PRESIDENTE_2022_1v.csv` | 131 MB | `src/agregacion_2022.py` | `datos/procesados/` |
| `MMV_NACIONAL_PRESIDENTE_2022_2v.csv` | 64 MB | `src/agregacion_2022.py` | `datos/procesados/` |
| `MGN2018_MPIO_POLITICO.rar` (shapefile crudo, MGN 2018, dentro de `shapefile_municipios/`) | 50,3 MB comprimido | `src/integrar_geometria.py` | `datos/geo/municipios_colombia_simplificado.geojson` |

> **Nota sobre el `.rar` del shapefile:** es un respaldo manual para reproducibilidad (por si hace
> falta reconstruir la geometría desde cero con otro criterio de simplificación), no un insumo que
> ningún script del repo descargue o descomprima automáticamente. `src/integrar_geometria.py`
> recibe siempre una ruta local ya descomprimida (`.shp`/`.shx`/`.dbf`/`.prj`) — quien quiera
> reproducir ese paso necesita descomprimirlo a mano primero (con WinRAR, 7-Zip o `unrar`), igual
> que se hizo aquí.

---

## 6. Metodología (resumen)

### Dataset
- **Unidad de análisis:** municipio × elección — ~5.500 filas modeladas (2006-2022)
- **Variable objetivo:** % de voto del bloque de izquierda en primera vuelta presidencial
- **Fuentes integradas:** cinco fuentes públicas oficiales, casadas por código DIVIPOLA municipal
- **Peso muestral:** `min(votos_totales / 500, 1.0)` — fiabilidad estadística continua; municipios
  con <30 votos marcados como baja confiabilidad y excluidos del análisis de residuos

### Validación temporal
Ventana expansiva (nunca split aleatorio, por la variable de inercia electoral):

| Train | Test |
|-------|------|
| 2006 | 2010 (*) |
| 2006–2010 | 2014 |
| 2006–2014 | 2018 |
| 2006–2018 | **2022** (test estrella) |

(*) La ventana 2006→2010 se reporta aparte — entrenar con una sola elección no permite anticipar
shocks de nivel nacional (efecto Mockus en 2010). No se incluye en el promedio de métricas.

### Modelos probados
Ridge/Lasso (baseline) → Random Forest / SVR (principales) → XGBoost (opcional)

Ningún modelo ajustado supera al baseline de inercia ("copiar el resultado anterior") en la
correlación intra-año — la métrica relevante cuando los saltos de nivel nacional entre elecciones
dominan el R² global.

### Métricas
RMSE, MAE, R² global y **correlación intra-año** (la que de verdad importa: mide si el modelo
ordena bien los municipios dentro de cada elección, independientemente del nivel nacional).

### Experimentos de residuos (Fase 3b)
Se probó explícitamente si el conflicto armado (per_ocu) añade capacidad explicativa por encima
de pobreza + región:
- **Experimento 1:** modelo estructural sin lag → colapsa a constante → residuos = distancia a
  la media nacional (no es señal de conflicto, es descriptivo)
- **Experimento 2:** per_ocu con NBI+región como control → ΔR²≈ruido, correlación parcial
  negativa → el conflicto no explica el voto por encima de pobreza y periferia
- **Conclusión:** lo que parecía señal de conflicto era pobreza estructural + periferia rural
  amplificada por el ascenso político de Petro (2018-2022)

### Interpretabilidad
SHAP + análisis de residuos del modelo con lag + mapas coropléticos interactivos de municipios
que rompen su tendencia histórica (app Streamlit, sección 3)

---

## 7. Limitaciones principales

1. **Inferencia ecológica:** el análisis es a nivel municipal — los patrones son territoriales,
   no individuales. No se puede inferir comportamiento de votantes individuales.
2. **Conflicto solo departamental:** la fuente UARIV no ofrece granularidad municipal; la
   variable de conflicto se hereda del departamento.
3. **Pobreza vía proxy:** NBI censal de 2005 y 2018 como proxy de pobreza estructural; introduce
   cierta heterogeneidad temporal.
4. **Correlacional, no causal:** los residuos son señal de cambio político, no prueba de
   irregularidad. El modelo no puede distinguir coacción de cambio político genuino.
5. **Pocos puntos temporales:** 5-6 elecciones modeladas limitan el análisis de serie por
   municipio.
6. **2022 como cambio de régimen:** la izquierda salta de ~25% a ~41% y gana por primera vez —
   un R² más bajo en ese año de test no invalida el modelo; refleja un cambio estructural real.
7. **Micro-electorados:** municipios de Guainía, Vaupés y Amazonas con <30 votos quedan fuera
   del análisis de residuos por falta de fiabilidad estadística.

---

## 8. Autor y tutores

**Autor:** Diego Abella
**Máster:** Big Data, Data Science e Inteligencia Artificial — UCM (semipresencial)
**Tutores/Evaluadores:** Carlos Ortega y Santiago Mota

---

## 9. Licencia del código

El código de este proyecto se publica bajo licencia **MIT**.
Los datos siguen las licencias de sus fuentes originales, indicadas en la sección 5.
