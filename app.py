import pandas as pd
import math
import streamlit as st

# Función para cargar archivo de inventario desde Google Drive
def load_inventory_file():
    # URL para obtener el archivo de inventario
    inventario_url = "https://docs.google.com/spreadsheets/d/1DVcPPILcqR0sxBZZAOt50lQzoKhoLCEx/export?format=xlsx"
    
    # Cargar el archivo de inventario
    inventario_api_df = pd.read_excel(inventario_url, sheet_name="Hoja3")
    
    # Renombrar la columna 'emb' a 'embalaje_alternativa' en el inventario
    inventario_api_df.rename(columns={'emb': 'embalaje_alternativa'}, inplace=True)
    
    return inventario_api_df

# Función para procesar el archivo de faltantes
def procesar_faltantes(faltantes_df, inventario_api_df, columnas_adicionales, bodega_seleccionada):
    # Asegurar que los nombres de las columnas no tengan mayúsculas o espacios extra
    faltantes_df.columns = faltantes_df.columns.str.lower().str.strip()
    inventario_api_df.columns = inventario_api_df.columns.str.lower().str.strip()

    # Verificar que el archivo de faltantes tenga las columnas necesarias
    columnas_necesarias = {'cur', 'codart', 'faltante', 'embalaje'}
    if not columnas_necesarias.issubset(faltantes_df.columns):
        st.error(f"El archivo de faltantes debe contener las columnas: {', '.join(columnas_necesarias)}")
        return pd.DataFrame()  # Devuelve un DataFrame vacío si faltan columnas

    # Extraer los valores únicos de 'cur' en el archivo de faltantes
    cur_faltantes = faltantes_df['cur'].unique()

    # Filtrar el inventario para los cur faltantes
    alternativas_inventario_df = inventario_api_df[inventario_api_df['cur'].isin(cur_faltantes)]

    # Si se selecciona una bodega, filtrar por la bodega seleccionada
    if bodega_seleccionada:
        alternativas_inventario_df = alternativas_inventario_df[alternativas_inventario_df['bodega'].isin(bodega_seleccionada)]

    # Filtrar inventario para las alternativas que tengan unidades en presentación de lote
    alternativas_disponibles_df = alternativas_inventario_df[alternativas_inventario_df['unidadespresentacionlote'] > 0]

    # Renombrar columnas para evitar confusión
    alternativas_disponibles_df.rename(columns={
        'codart': 'codart_alternativa',
        'opcion': 'opcion_alternativa',
        'embalaje': 'embalaje_alternativa'  # Ya se renombró anteriormente en el inventario
    }, inplace=True)

    # Hacer un merge con el archivo de faltantes para buscar las alternativas
    alternativas_disponibles_df = pd.merge(
        faltantes_df[['cur', 'codart', 'faltante', 'embalaje']],
        alternativas_disponibles_df,
        on='cur',
        how='inner'
    )

    # Filtrar registros donde 'opcion_alternativa' sea mayor a 0
    alternativas_disponibles_df = alternativas_disponibles_df[alternativas_disponibles_df['opcion_alternativa'] > 0]

    # Agregar columna de cantidad necesaria ajustada por embalaje
    alternativas_disponibles_df['cantidad_necesaria'] = alternativas_disponibles_df.apply(
        lambda row: math.ceil(row['faltante'] * row['embalaje'] / row['embalaje_alternativa'])
        if pd.notnull(row['embalaje']) and pd.notnull(row['embalaje_alternativa']) and row['embalaje_alternativa'] > 0
        else None,
        axis=1
    )

    # Ordenar las alternativas disponibles por 'codart' y 'unidadespresentacionlote'
    alternativas_disponibles_df.sort_values(by=['codart', 'unidadespresentacionlote'], inplace=True)

    # Crear un listado con las mejores alternativas disponibles
    mejores_alternativas = []
    for codart_faltante, group in alternativas_disponibles_df.groupby('codart'):
        faltante_cantidad = group['faltante'].iloc[0]

        # Buscar en la bodega seleccionada la mejor opción
        mejor_opcion_bodega = group[group['unidadespresentacionlote'] >= faltante_cantidad]
        mejor_opcion = mejor_opcion_bodega.head(1) if not mejor_opcion_bodega.empty else group.nlargest(1, 'unidadespresentacionlote')
        
        mejores_alternativas.append(mejor_opcion.iloc[0])

    # Crear el DataFrame final con las mejores alternativas
    resultado_final_df = pd.DataFrame(mejores_alternativas)

    # Definir las columnas finales a incluir en el resultado
    columnas_finales = ['cur', 'codart', 'faltante', 'embalaje', 'codart_alternativa', 'opcion_alternativa', 
                        'embalaje_alternativa', 'cantidad_necesaria', 'unidadespresentacionlote', 'bodega', 'carta']
    columnas_finales.extend([col.lower() for col in columnas_adicionales])
    
    # Filtrar las columnas que están presentes en el DataFrame final
    columnas_presentes = [col for col in columnas_finales if col in resultado_final_df.columns]
    resultado_final_df = resultado_final_df[columnas_presentes]

    return resultado_final_df

# Cargar archivo de faltantes y el inventario
faltantes_url = "https://docs.google.com/spreadsheets/d/1DWI94qJuuB7wK5aMeFk3CKBtjXOVn1iU/export?format=xlsx"
faltantes_df = pd.read_excel(faltantes_url, sheet_name="Hoja1")  # Ajusta el nombre de la hoja si es necesario

# Cargar el inventario
inventario_api_df = load_inventory_file()

# Llamar a la función de procesamiento de faltantes
columnas_adicionales = []  # Puedes agregar más columnas aquí si es necesario
bodega_seleccionada = None  # Ajusta la bodega seleccionada si es necesario
resultado_df = procesar_faltantes(faltantes_df, inventario_api_df, columnas_adicionales, bodega_seleccionada)

# Mostrar el resultado final
st.write(resultado_df)
