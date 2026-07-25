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