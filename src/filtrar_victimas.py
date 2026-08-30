# ==============================================================================
# filtrar_victimas.py
# Preprocesamiento de UNA SOLA EJECUCION manual, sobre el fichero crudo de
# victimas del conflicto armado (UARIV). NO forma parte del pipeline
# reproducible del proyecto del proyecto ya que por tamano del fichero original, 
# no sepuede cargar al git(Se ha dejado en el drive del proyecto). 
#
# ENTRADA (no versionada en este repo, ver Drive en el README): fichero crudo
# VICTIMAS_DEPARTAMENTAL.csv, ~2,5 GB, ~11,3M filas. No se sube al repositorio
# por su peso.
#
# PROBLEMA QUE RESUELVE: el fichero crudo apila ~74 cortes mensuales del RUV
# (una fotografia por mes), lo que multiplicaba el conteo de victimas por ese
# mismo factor si se sumaba sin filtrar. Este script se queda solo con el
# corte mas reciente (2026-04-30) antes de agregar por año-departamento,
# evitando el sobreconteo.
#
# SALIDA (SI versionada): datos/procesados/VICTIMAS_FILTRADO_V2.csv (847 filas,
# año x departamento). Es la que consume src/integrar_victimas.py en el
# pipeline principal.
#
# Las rutas locales de abajo (C:/Users/Bunny/Downloads/...) se dejan tal cual,
# reflejando que este fue un paso de limpieza puntual sobre el fichero
# original del autor, no parte del flujo reproducible con BASE_DIR que usa el
# resto de src/.
# ==============================================================================

import pandas as pd

cols = ['FECHA_CORTE','COD_ESTADO_DEPTO','ESTADO_DEPTO','VIGENCIA','PER_OCU','PER_DECLA','EVENTOS']
df = pd.read_csv('C:/Users/Bunny/Downloads/VICTIMAS_DEPARTAMENTAL.csv',
                 encoding='latin1', usecols=cols, on_bad_lines='skip', low_memory=False)
print('Filas originales:', len(df))

print('Numero de FECHA_CORTE distintas:', df['FECHA_CORTE'].nunique())

df['FECHA_CORTE'] = pd.to_datetime(df['FECHA_CORTE'], format='%d/%m/%Y', errors='coerce')
ultimo = df['FECHA_CORTE'].max()
print('Ultimo corte disponible:', ultimo.date())
df = df[df['FECHA_CORTE'] == ultimo]
print('Filas en el ultimo corte:', len(df))

df = df[(df['VIGENCIA'] >= 1998) & (df['VIGENCIA'] <= 2022)]

resultado = df.groupby(['VIGENCIA','COD_ESTADO_DEPTO','ESTADO_DEPTO'])[['PER_OCU','PER_DECLA','EVENTOS']].sum().reset_index()
print('Filas resultado:', len(resultado))

print('Total nacional PER_OCU tras la correccion:', f"{resultado['PER_OCU'].sum():,.0f}")
print()
print('Antioquia por anio:')
print(resultado[resultado['ESTADO_DEPTO'].str.contains('Antioquia', na=False)].to_string(index=False))

resultado.to_csv('C:/Users/Bunny/Downloads/VICTIMAS_FILTRADO_V2.csv', index=False, encoding='utf-8')