import streamlit as st
import pandas as pd
import numpy as np

# -------------------------------------------------------------------------
# CONSTANTES GLOBALES
# -------------------------------------------------------------------------
RANGO_PRECIO = 480  # Rango total de precios
PASO = 10           # Paso de precio ajustado (cada 10 puntos)
LOTES_POR_COMPRA = 1  # Lotes asignados por defecto por cada nivel de precio
UNIDADES_POR_LOTE = 100  # Cada lote equivale a 100 unidades (onzas)

# -------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# -------------------------------------------------------------------------
def generar_precios(precio_inicial, rango_precio, paso, direccion):
    """
    Genera precios en múltiplos de 'paso' desde el precio inicial.
    """
    precios = []
    if direccion == "bajada":
        punto_actual = precio_inicial
        while punto_actual >= precio_inicial - rango_precio:
            precios.append(punto_actual)
            if punto_actual <= precio_inicial - 280:
                punto_actual -= 40  # Cada 40 puntos para p-280 a p-400
            elif punto_actual <= precio_inicial - 120:
                punto_actual -= 20  # Cada 20 puntos para p-130 hacia abajo
            else:
                punto_actual -= paso  # Cada 10 puntos normalmente
    elif direccion == "subida":
        precios = [precio_inicial + i * paso for i in range(rango_precio // paso + 1)]
    else:
        raise ValueError("La dirección debe ser 'bajada' o 'subida'.")
    return precios

def crear_dataframe(precios, lotes_por_compra, precio_inicial, modo):
    """
    Crea un DataFrame con los precios y los lotes asignados.
    """
    lotes = []
    for i, precio in enumerate(precios):
        if i == 22:  # Salta la compra 23 (indexada como 22)
            continue
        if precio == precio_inicial - 20:  # Asigna 2.5 lotes en p-20
            lote = 2.5
        elif i >= len(precios) - 3:  # Últimas 3 compras
            lote = 6 / 1.2  # Divide el lote de 6 entre 1.2
        elif i >= 13:  # Desde la compra 14 en adelante
            lote = 1.75
        elif precio == precio_inicial - 30 or precio == precio_inicial + 30:
            lote = 2  # Asigna 2 lotes para p-30 o p+30
        elif (precio_inicial - 90 <= precio <= precio_inicial - 40) or (precio_inicial + 40 <= precio <= precio_inicial + 90):
            lote = 1.25  # Asigna 1.25 lotes para el rango p-40 a p-90 y p+40 a p+90
        elif (precio_inicial - 120 <= precio <= precio_inicial - 100) or (precio_inicial + 100 <= precio <= precio_inicial + 120):
            lote = 1.5  # Asigna 1.5 lotes para el rango p-100 a p-120 y p+100 a p+120
        else:
            lote = lotes_por_compra  # Asigna el valor por defecto

        # Dividir el lote según la condición
        if i < 4 and precio != precio_inicial - 20:  # Primeras 4 compras, excepto p-20
            lote /= 2 * 1.06
        elif i >= len(precios) - 3:  # Últimas 3 compras, ya dividido
            lote /= 1.6 * 1.06
        else:  # Resto de las compras
            lote /= 2.5 * 1.06

        # Redondear a 2 decimales
        lote = round(lote, 2)

        lotes.append(lote)

    precios = [precio for i, precio in enumerate(precios) if i != 22]  # Elimina la compra 23

    # Resta 0.5 lotes a la penúltima compra
    if len(lotes) > 1:
        lotes[-2] = round(lotes[-2] - 0.5, 2)

    # Agrega una compra en p-460 con el mismo lotaje que la penúltima compra
    if len(precios) > 1:
        precios.insert(-1, precio_inicial - 460)
        lotes.insert(-1, lotes[-2])

    # Vuelve la última compra a 0 lotes
    if len(lotes) > 0:
        lotes[-1] = 0.00

    # En modo conservador, ajustar la tercera compra (indexada como 2)
    if modo == "conservador" and len(lotes) > 2:
        lotes[2] = lotes[1]

    df = pd.DataFrame({
        'Precio': precios,
        'Lotes': lotes
    })

    # Añade una fila en p-360 con 0 lotes sin modificar nada más
    nueva_fila = pd.DataFrame({'Precio': [precio_inicial - 360], 'Lotes': [0.00]})
    df = pd.concat([df, nueva_fila], ignore_index=True)

    # Ordena el DataFrame por precio en orden descendente
    df = df.sort_values(by='Precio', ascending=False).reset_index(drop=True)

    return df

def calcular_acumulados(df, precio_inicial, direccion):
    """
    Calcula columnas adicionales como lotes acumulados, break-even, flotante,
    puntos de salida, ganancias objetivo y porcentaje flotante sobre un millón.
    """
    # Lotes acumulados
    df['Lotes Acumulados'] = df['Lotes'].cumsum()

    # Evitar división por cero
    df['Lotes Acumulados'].replace(0, np.nan, inplace=True)

    # Break-even
    df['Break Even'] = (
        (df['Precio'] * df['Lotes'] * UNIDADES_POR_LOTE).cumsum() / (df['Lotes Acumulados'] * UNIDADES_POR_LOTE)
    )

    # Flotante
    df['Flotante'] = (
        (df['Precio'] - df['Break Even']) * df['Lotes Acumulados'] * UNIDADES_POR_LOTE
    )

    # Porcentaje de flotante sobre un millón
    df['Flotante (%) de un millón'] = (df['Flotante'] / 1_000_000) * 100

    # Puntos de salida
    if direccion == "bajada":
        df['Puntos de salida'] = abs(df['Precio'] - df['Break Even'])
    else:
        df['Puntos de salida'] = df['Break Even'] - df['Precio']

    # Puntos de salida para ganancias objetivo
    with np.errstate(divide='ignore', invalid='ignore'):
        df['Puntos de salida para 2500'] = (
            (df['Break Even'] + (2500 / (df['Lotes Acumulados'] * UNIDADES_POR_LOTE))) - df['Precio']
        )
        df['Puntos de salida para 5000'] = (
            (df['Break Even'] + (5000 / (df['Lotes Acumulados'] * UNIDADES_POR_LOTE))) - df['Precio']
        )
        df['Puntos de salida para 10000'] = (
            (df['Break Even'] + (10000 / (df['Lotes Acumulados'] * UNIDADES_POR_LOTE))) - df['Precio']
        )

    # Ganancia al regresar al precio inicial
    if direccion == "bajada":
        df['Ganancia al Regresar al Precio Inicial'] = (
            (precio_inicial - df['Precio']) * df['Lotes Acumulados'] * UNIDADES_POR_LOTE
        )
    else:
        df['Ganancia al Regresar al Precio Inicial'] = (
            (df['Precio'] - precio_inicial) * df['Lotes Acumulados'] * UNIDADES_POR_LOTE
        )

    # Martingala
    df['Martingala'] = df['Lotes'] / df['Lotes'].shift(1)
    df['Martingala'] = df['Martingala'].fillna(1)

    # Redondear columnas numéricas a 2 decimales
    df_numeric_cols = df.select_dtypes(include=['float', 'int']).columns
    df[df_numeric_cols] = df[df_numeric_cols].round(2)

    # Reemplazar posibles infinitos y NaN resultantes de divisiones por cero
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)

    return df

# -------------------------------------------------------------------------
# APLICACIÓN PRINCIPAL DE STREAMLIT
# -------------------------------------------------------------------------
def main():
    st.title("Calculadora de Distribución en Tramos (480 puntos)")

    precio_inicial = st.number_input(
        "Precio inicial por onza (USD):",
        min_value=1.00,
        value=2700.00,
        step=10.00,
        format="%.2f"
    )

    direccion = st.selectbox("Seleccione la dirección:", ["bajada", "subida"])

    modo = st.selectbox("Seleccione el modo:", ["arriesgado", "conservador"])

    if st.button("Calcular Distribución"):
        # Generar precios
        precios = generar_precios(precio_inicial, RANGO_PRECIO, PASO, direccion)

        # Crear DataFrame
        df = crear_dataframe(precios, LOTES_POR_COMPRA, precio_inicial, modo)

        # Calcular acumulados
        df = calcular_acumulados(df, precio_inicial, direccion)

        # Mostrar resultados
        st.write("### Detalles de las Transacciones")
        st.dataframe(df)

if __name__ == "__main__":
    main()
