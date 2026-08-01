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

**🔗 [Enlace a la app — pendiente de despliegue]**

La app tiene tres secciones:

- **Explorador del voto territorial:** mapa interactivo del % de izquierda por municipio y año,
  evolución temporal 2006-2022, relación NBI-voto por región.
- **Análisis individual:** selecciona un municipio y año — ve el voto real, el voto predicho
  por el modelo y la desviación respecto a su trayectoria histórica.
- **Municipios que rompen su tendencia:** mapa de residuos del modelo en 2022, filtrado por
  fiabilidad estadística. Los municipios con menos de 30 votos no se muestran como señal.

---

## 3. Estructura del repositorio

```
tfm-electoral-colombia/
├── README.md
├── requirements.txt
├── .gitignore
├── datos/
│   ├── raw/                    # Datos originales livianos (versionados en git)
│   └── procesados/             # Dataset maestro integrado y datasets derivados
├── notebooks/
│   ├── figuras/                # Figuras reutilizables (Streamlit + memoria)
│   ├── 01_preprocesamiento.ipynb       # ✅ Integración de fuentes → dataset maestro
│   ├── 02_eda.ipynb                    # ✅ Análisis exploratorio
│   ├── 03_modelizacion.ipynb           # ✅ Pipeline predictivo: ventana expansiva
│   ├── 03b_experimentos_decisivos.ipynb # ✅ Conflicto vs. pobreza/región
│   ├── 04_residuos_y_anomalias.ipynb   # 🔄 En desarrollo
│   └── 05_productivizacion.ipynb       # 🔄 En desarrollo
├── src/
│   ├── preprocesamiento.py     # ✅ Funciones de integración y limpieza de datos
│   ├── agregacion_2022.py      # ✅ Agrega datos de 2022 de mesa a municipio
│   ├── filtrar_victimas.py     # ✅ Filtra el fichero de víctimas (2,5GB → manejable)
│   ├── modelo.py               # ✅ Funciones de modelización: ventanas, métricas, modelos
│   └── utils.py                # Utilidades compartidas
├── app/
│   └── streamlit_app.py        # 🔄 En desarrollo
├── modelos/
│   └── modelo_final.pkl        # 🔄 Pendiente (se genera en fase de productivización)
└── memoria/
    └── TFM_Diego_Abella.pdf
```

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

### Orden de ejecución de los notebooks

> ⚠️ **Importante:** los notebooks usan rutas relativas con `BASE_DIR = '..'`
> y **deben ejecutarse desde la carpeta `notebooks/`**, no desde la raíz del proyecto.
> Si se abren desde otro directorio, ajustar `BASE_DIR` al principio de cada notebook.

Los notebooks deben ejecutarse en este orden:

| Orden | Notebook | Estado | Descripción |
|-------|----------|--------|-------------|
| 1 | `01_preprocesamiento.ipynb` | ✅ Completado | Integra las cinco fuentes en el dataset maestro |
| 2 | `02_eda.ipynb` | ✅ Completado | Análisis exploratorio: distribución, correlaciones, regionalización |
| 3 | `03_modelizacion.ipynb` | ✅ Completado | Pipeline predictivo con ventana expansiva temporal |
| 3b | `03b_experimentos_decisivos.ipynb` | ✅ Completado | Experimentos conflicto vs. pobreza/región (*) |
| 4 | `04_residuos_y_anomalias.ipynb` | 🔄 En desarrollo | Análisis de residuos y mapa de municipios |
| 5 | `05_productivizacion.ipynb` | 🔄 En desarrollo | Serializa el modelo final en `modelos/modelo_final.pkl` |

(*) `03b` no depende de ningún fichero generado por `03` — ambos cargan directamente
`datos/procesados/dataset_maestro_electoral.csv`. El orden 3→3b es narrativo, no técnico.

### Lanzar la aplicación web (local)

```bash
streamlit run app/streamlit_app.py
```

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

### Datos pesados (no versionados en git)

Los ficheros originales de 2022 (nivel mesa) y el fichero de víctimas superan el límite de
GitHub. Están disponibles en Google Drive con acceso público de lectura:

**[Carpeta de datos originales — Google Drive](https://drive.google.com/drive/folders/10MmaVe-ESKJQQPAvStOXWBVO4JbcNVuT?usp=sharing)**

| Fichero | Tamaño | Script de transformación | Resultado en el repo |
|---------|--------|--------------------------|----------------------|
| `VICTIMAS_DEPARTAMENTAL.csv` | 2,5 GB | `src/filtrar_victimas.py` | `datos/procesados/VICTIMAS_FILTRADO_V2.csv` |
| `MMV_NACIONAL_PRESIDENTE_2022_1v.csv` | 131 MB | `src/agregacion_2022.py` | `datos/procesados/` |
| `MMV_NACIONAL_PRESIDENTE_2022_2v.csv` | 64 MB | `src/agregacion_2022.py` | `datos/procesados/` |

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
SHAP + análisis de residuos del modelo con lag + mapa coroplético de municipios que rompen
su tendencia histórica

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
