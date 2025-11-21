import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

# Configuración de la API
BASE_URL = "https://hydromet4api.hidrofuturo.cl/api/v1/metamodelos"

def obtener_zonas():
    """Obtiene las zonas hidrogeológicas disponibles"""
    response = requests.get(f"{BASE_URL}/zonas")
    if response.status_code == 200:
        return response.json()
    return []

def obtener_datos_historicos(zona_id, tipo="head-absoluto"):
    """Obtiene datos históricos MODFLOW"""
    endpoint = f"{BASE_URL}/metamodelo-mensual-{tipo}-historico"
    params = {"zona": zona_id}
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('data', [])
    return []

def obtener_datos_metamodelo(zona_id, tipo="head-absoluto"):
    """Obtiene datos del metamodelo (pronóstico)"""
    endpoint = f"{BASE_URL}/metamodelo-mensual-{tipo}-modelacion"
    params = {"zona": zona_id}
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('data', [])
    return []

def procesar_datos(datos_historicos, datos_metamodelo):
    """Procesa y combina datos históricos y del metamodelo"""
    # Convertir a DataFrames
    df_hist = pd.DataFrame(datos_historicos)
    df_modelo = pd.DataFrame(datos_metamodelo)
    
    # Convertir fechas
    if not df_hist.empty and 'date' in df_hist.columns:
        df_hist['date'] = pd.to_datetime(df_hist['date'])
        df_hist = df_hist.sort_values('date')
    
    if not df_modelo.empty and 'date' in df_modelo.columns:
        df_modelo['date'] = pd.to_datetime(df_modelo['date'])
        df_modelo = df_modelo.sort_values('date')
    
    # Encontrar punto de transición
    fecha_transicion = None
    if not df_hist.empty and not df_modelo.empty:
        fecha_transicion = df_hist['date'].max()
    
    return df_hist, df_modelo, fecha_transicion

def crear_grafico(df_hist, df_modelo, fecha_transicion, zona_nombre, tipo="head_absoluto"):
    """Crea gráfico estilo imagen proporcionada"""
    fig = go.Figure()
    
    # Título del gráfico
    titulo_tipo = "Head Absoluto" if tipo == "head_absoluto" else "Head Delta"
    titulo = f"Zona_{zona_nombre} - {titulo_tipo}"
    
    # Agregar datos históricos (MODFLOW) en gris
    if not df_hist.empty and 'value' in df_hist.columns:
        fig.add_trace(go.Scatter(
            x=df_hist['date'],
            y=df_hist['value'],
            mode='lines',
            name='MODFLOW',
            line=dict(color='#808080', width=1.5)
        ))
    
    # Agregar pronóstico (Metamodelo) en azul
    if not df_modelo.empty and 'value' in df_modelo.columns:
        fig.add_trace(go.Scatter(
            x=df_modelo['date'],
            y=df_modelo['value'],
            mode='lines',
            name='Metamodelo',
            line=dict(color='#1E90FF', width=2)
        ))
    
    # Agregar línea vertical de transición
    if fecha_transicion:
        fig.add_shape(
            type="line",
            x0=fecha_transicion, x1=fecha_transicion,
            y0=0, y1=1,
            yref='paper',
            line=dict(color="gray", width=1, dash="dash")
        )
        fig.add_annotation(
            x=fecha_transicion, y=1,
            yref='paper',
            text="Fin MODFLOW",
            showarrow=False,
            xanchor="right",
            yanchor="top"
        )
    
    # Configurar layout
    fig.update_layout(
        title=dict(
            text=titulo,
            font=dict(size=14)
        ),
        xaxis=dict(
            title="Fecha",
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=0.5
        ),
        yaxis=dict(
            title=f"{titulo_tipo} (m)",
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=0.5
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.95,
            xanchor="left",
            x=0.02,
            bordercolor="gray",
            borderwidth=1
        ),
        margin=dict(l=60, r=30, t=50, b=50),
        height=400
    )
    

    
    return fig

def generar_graficos_todas_zonas():
    """Genera gráficos para todas las zonas disponibles"""
    import os
    
    # Crear carpeta de salida
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    zonas = obtener_zonas()
    
    if not zonas:
        print("No se pudieron obtener las zonas")
        return
    
    graficos = []
    
    for zona in zonas:
        # La API devuelve strings con IDs de zona
        if isinstance(zona, str):
            zona_id = zona
            zona_nombre = zona
        else:
            zona_id = zona.get('id')
            zona_nombre = zona.get('nombre', f'Zona_{zona_id}')
        
        print(f"Procesando zona: {zona_nombre}")
        
        # Head Absoluto
        hist_abs = obtener_datos_historicos(zona_id, "head-absoluto")
        modelo_abs = obtener_datos_metamodelo(zona_id, "head-absoluto")
        df_hist_abs, df_modelo_abs, fecha_trans_abs = procesar_datos(hist_abs, modelo_abs)
        
        if not df_hist_abs.empty or not df_modelo_abs.empty:
            fig_abs = crear_grafico(df_hist_abs, df_modelo_abs, fecha_trans_abs, 
                                   zona_nombre, "head_absoluto")
            filename = f"{output_dir}/{zona_nombre}_head_absoluto.png"
            fig_abs.write_image(filename, width=1200, height=400, scale=2)
            print(f"  Guardado: {filename}")
            graficos.append(('head_absoluto', zona_nombre, fig_abs))
        
        # Head Delta
        hist_delta = obtener_datos_historicos(zona_id, "head-delta")
        modelo_delta = obtener_datos_metamodelo(zona_id, "head-delta")
        df_hist_delta, df_modelo_delta, fecha_trans_delta = procesar_datos(hist_delta, modelo_delta)
        
        if not df_hist_delta.empty or not df_modelo_delta.empty:
            fig_delta = crear_grafico(df_hist_delta, df_modelo_delta, fecha_trans_delta,
                                    zona_nombre, "head_delta")
            filename = f"{output_dir}/{zona_nombre}_head_delta.png"
            fig_delta.write_image(filename, width=1200, height=400, scale=2)
            print(f"  Guardado: {filename}")
            graficos.append(('head_delta', zona_nombre, fig_delta))
    
    print(f"\nTodos los gráficos guardados en la carpeta '{output_dir}'")
    return graficos

def crear_dashboard_comparativo(zona_id, zona_nombre=""):
    """Crea un dashboard con ambos tipos de gráficos para una zona"""
    # Obtener datos
    hist_abs = obtener_datos_historicos(zona_id, "head-absoluto")
    modelo_abs = obtener_datos_metamodelo(zona_id, "head-absoluto")
    hist_delta = obtener_datos_historicos(zona_id, "head-delta")
    modelo_delta = obtener_datos_metamodelo(zona_id, "head-delta")
    
    # Procesar datos
    df_hist_abs, df_modelo_abs, fecha_trans_abs = procesar_datos(hist_abs, modelo_abs)
    df_hist_delta, df_modelo_delta, fecha_trans_delta = procesar_datos(hist_delta, modelo_delta)
    
    # Crear subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f"Head Absoluto - {zona_nombre}", 
                       f"Head Delta - {zona_nombre}"),
        vertical_spacing=0.15
    )
    
    # Head Absoluto
    if not df_hist_abs.empty:
        fig.add_trace(
            go.Scatter(x=df_hist_abs['date'], y=df_hist_abs['value'],
                      name='MODFLOW', line=dict(color='#808080')),
            row=1, col=1
        )
    
    if not df_modelo_abs.empty:
        fig.add_trace(
            go.Scatter(x=df_modelo_abs['date'], y=df_modelo_abs['value'],
                      name='Metamodelo', line=dict(color='#1E90FF')),
            row=1, col=1
        )
    
    # Head Delta
    if not df_hist_delta.empty:
        fig.add_trace(
            go.Scatter(x=df_hist_delta['date'], y=df_hist_delta['value'],
                      name='MODFLOW Delta', line=dict(color='#808080'),
                      showlegend=False),
            row=2, col=1
        )
    
    if not df_modelo_delta.empty:
        fig.add_trace(
            go.Scatter(x=df_modelo_delta['date'], y=df_modelo_delta['value'],
                      name='Metamodelo Delta', line=dict(color='#1E90FF'),
                      showlegend=False),
            row=2, col=1
        )
    
    # Actualizar layout
    fig.update_xaxes(title_text="Fecha", row=2, col=1)
    fig.update_yaxes(title_text="Head Absoluto (m)", row=1, col=1)
    fig.update_yaxes(title_text="Head Delta (m)", row=2, col=1)
    
    fig.update_layout(
        height=800,
        showlegend=True,
        title_text=f"Dashboard Zona: {zona_nombre}",
        hovermode='x unified'
    )
    
    return fig

if __name__ == "__main__":
    print("Generando gráficos para todas las zonas...")
    generar_graficos_todas_zonas()
