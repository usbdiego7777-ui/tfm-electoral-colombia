# ==============================================================================
# eda_utils.py
# Funciones reutilizables para el Analisis Exploratorio de Datos (Fase 2).
# El notebook notebooks/02_eda.ipynb importa estas funciones en vez de repetir
# codigo de graficado/resumen inline, siguiendo la misma disciplina que
# src/preprocesamiento.py en la Fase 1: el codigo vive aqui, el notebook lo
# invoca e interpreta resultados.
# ==============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def resumen_estadistico_predictoras(df: pd.DataFrame, columnas: list) -> pd.DataFrame:
    """
    Devuelve un resumen descriptivo (count, media, std, min, percentiles, max)
    para una lista de columnas predictoras, mas el % de nulos de cada una.
    """
    resumen = df[columnas].describe().T
    resumen["pct_nulos"] = df[columnas].isna().mean() * 100
    return resumen


def graficar_histogramas_predictoras(
    df: pd.DataFrame, columnas: list, ruta_salida: str = None, ncols: int = 2, bins: int = 40
) -> None:
    """
    Dibuja un histograma por cada columna de la lista, en una cuadricula de
    'ncols' columnas. Siempre se muestra embebido en el notebook (plt.show).
    Solo se guarda como PNG aparte en 'ruta_salida' si se indica - convencion
    del proyecto (ver bitacora Fase 2, seccion 12): guardar aparte solo los
    graficos reutilizables para Streamlit o la memoria, no todo el EDA.
    """
    nfilas = int(np.ceil(len(columnas) / ncols))
    fig, axes = plt.subplots(nfilas, ncols, figsize=(6 * ncols, 4.2 * nfilas))
    axes = np.array(axes).reshape(-1)

    for i, col in enumerate(columnas):
        axes[i].hist(df[col].dropna(), bins=bins, color="#4C72B0", edgecolor="white")
        axes[i].set_title(col)
        axes[i].set_xlabel(col)
        axes[i].set_ylabel("Frecuencia (municipio-año)")

    # Ocultar ejes sobrantes si columnas no llena la cuadricula completa
    for j in range(len(columnas), len(axes)):
        axes[j].axis("off")

    plt.tight_layout()
    if ruta_salida:
        plt.savefig(ruta_salida, dpi=130)
    plt.show()


def comparar_nbi_por_fuente(df: pd.DataFrame, ruta_salida: str = None) -> pd.DataFrame:
    """
    El NBI municipal proviene de 2 censos distintos segun el año electoral
    (Censo 2005 para 1998-2010, Censo 2018 para 2014-2022; ver columna
    'fuente_nbi', ya fijada en la Fase 1 - no se reabre esa decision aqui).
    Esta funcion compara la distribucion de nbi_total entre ambas fuentes,
    para documentar la heterogeneidad temporal introducida por el cambio de
    censo (limitacion ya anotada en el prompt de contexto del proyecto).

    Se muestra siempre embebido en el notebook. Solo se guarda como PNG
    aparte si se indica ruta_salida (ver convencion de la seccion 12 de la
    bitacora de Fase 2: guardar aparte solo lo reutilizable).
    """
    resumen = df.groupby("fuente_nbi")["nbi_total"].describe()

    fig, ax = plt.subplots(figsize=(6, 5))
    grupos = [df.loc[df["fuente_nbi"] == f, "nbi_total"].dropna() for f in resumen.index]
    ax.boxplot(grupos, tick_labels=list(resumen.index))
    ax.set_ylabel("NBI municipal (%)")
    ax.set_title("NBI municipal según fuente (censo 2005 vs. 2018)")
    plt.tight_layout()
    if ruta_salida:
        plt.savefig(ruta_salida, dpi=130)
    plt.show()

    return resumen


def verificar_impacto_imputacion_lag(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compara lag_pct_izquierda entre filas imputadas (con la media
    departamental del año, ver Fase 1) y filas con lag real, para dejar
    constancia de si la imputacion desplaza la distribucion de forma
    relevante. No decide nada sobre el modelado - solo documenta el efecto
    para que el Chat 5 lo tenga en cuenta.
    """
    resumen = df.groupby("lag_pct_izquierda_imputado")["lag_pct_izquierda"].describe()
    resumen.index = resumen.index.map({0: "lag_real", 1: "lag_imputado"})
    return resumen


def graficar_relacion_predictora_target(
    df: pd.DataFrame, columna_x: str, ruta_salida: str = None, columna_color: str = None
) -> float:
    """
    Scatter de una predictora contra pct_izquierda (el target), coloreado
    opcionalmente por una columna categorica (ej. region_dane). Devuelve la
    correlacion simple para citarla en el notebook.

    Se muestra siempre embebido en el notebook. Solo se guarda como PNG
    aparte si se indica ruta_salida (convencion de la seccion 12 de la
    bitacora de Fase 2).
    """
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    if columna_color and columna_color in df.columns:
        for valor, grupo in df.groupby(columna_color):
            ax.scatter(grupo[columna_x], grupo["pct_izquierda"], s=10, alpha=0.5, label=str(valor))
        ax.legend(fontsize=8)
    else:
        ax.scatter(df[columna_x], df["pct_izquierda"], s=10, alpha=0.5, color="#4C72B0")

    ax.set_xlabel(columna_x)
    ax.set_ylabel("% voto izquierda (1ª vuelta)")
    ax.set_title(f"{columna_x} vs. voto izquierda")
    plt.tight_layout()
    if ruta_salida:
        plt.savefig(ruta_salida, dpi=130)
    plt.show()

    return df[columna_x].corr(df["pct_izquierda"])


def graficar_correlaciones_por_departamento(
    df: pd.DataFrame, columna_x: str, ruta_salida: str = None, min_filas: int = 10,
    min_municipios_solido: int = 8,
) -> pd.DataFrame:
    """
    Grafico de barras horizontales con la correlacion de 'columna_x' contra
    el target, una barra por departamento, ordenadas de mas negativa a mas
    positiva. Pensado para mostrar heterogeneidad territorial (ej. NBI-voto)
    de forma directa - un scatter con miles de puntos superpuestos no
    comunica un cambio de signo, un ranking de barras si.

    Cada barra se anota con 'n=<numero de MUNICIPIOS UNICOS>' (no filas -
    un departamento aporta varias filas por año, pero la robustez de la
    correlacion depende de cuantos municipios distintos la sostienen). Los
    departamentos con menos de 'min_municipios_solido' municipios se pintan
    con un color mas tenue (alpha reducido) para señalar visualmente que son
    pistas sugerentes, no patrones robustos - una correlacion sobre 4-7
    municipios puede moverse entera por un solo caso atipico.

    Solo incluye departamentos con al menos 'min_filas' observaciones con
    ambas variables no nulas, para no reportar correlaciones inestables con
    muestras minusculas.

    Devuelve un DataFrame con columnas: correlacion, n_municipios.
    """
    def _correlacion(g):
        return g[columna_x].corr(g["pct_izquierda"]) if g["pct_izquierda"].notna().sum() >= min_filas else np.nan

    correlaciones = df.groupby("departamento").apply(_correlacion, include_groups=False).dropna()
    n_municipios = df.groupby("departamento")["divipola"].nunique()

    resultado = pd.DataFrame({
        "correlacion": correlaciones,
        "n_municipios": n_municipios.reindex(correlaciones.index),
    }).sort_values("correlacion")

    colores = []
    for _, fila in resultado.iterrows():
        color_base = "#C44E52" if fila["correlacion"] < 0 else "#55A868"
        alpha = 1.0 if fila["n_municipios"] >= min_municipios_solido else 0.4
        colores.append((color_base, alpha))

    fig, ax = plt.subplots(figsize=(8.5, 0.32 * len(resultado) + 1.2))
    for i, (depto, fila) in enumerate(resultado.iterrows()):
        color_base, alpha = colores[i]
        ax.barh(depto, fila["correlacion"], color=color_base, alpha=alpha)

    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel(f"Correlación {columna_x} - voto izquierda")
    ax.set_title(
        f"Correlación {columna_x}-voto por departamento\n"
        f"(color tenue = menos de {min_municipios_solido} municipios, correlación frágil)"
    )

    # Anotar n de municipios al final de cada barra
    xmin, xmax = ax.get_xlim()
    margen = (xmax - xmin) * 0.02
    for i, (depto, fila) in enumerate(resultado.iterrows()):
        x_texto = fila["correlacion"] + margen if fila["correlacion"] >= 0 else fila["correlacion"] - margen
        alineacion = "left" if fila["correlacion"] >= 0 else "right"
        ax.text(x_texto, i, f"n={int(fila['n_municipios'])}", va="center", ha=alineacion, fontsize=7)

    plt.tight_layout()
    if ruta_salida:
        plt.savefig(ruta_salida, dpi=130, bbox_inches="tight")
    plt.show()

    return resultado
