import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np
import os

# Configuración de la API
BASE_URL = "https://hydromet4api.hidrofuturo.cl/api/v1/metamodelos/balance"

def obtener_zonas():
    """Obtiene las zonas disponibles para balance hídrico"""
    response = requests.get(f"{BASE_URL}/zones")
    if response.status_code == 200:
        return response.json()
    return []

def obtener_datos_historicos(zona):
    """Obtiene datos históricos MODFLOW de balance"""
    endpoint = f"{BASE_URL}/metamodelo-mensual-balance-historico"
    params = {"zona": zona}
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('data', [])
    return []

def obtener_datos_metamodelo(zona):
    """Obtiene datos del metamodelo (pronóstico) de balance"""
    endpoint = f"{BASE_URL}/metamodelo-mensual-balance-modelacion"
    params = {"zona": zona}
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

def crear_grafico_balance(df_hist, df_modelo, fecha_transicion, zona_nombre, variable):
    """Crea gráfico de barras para una variable específica del balance"""
    fig = go.Figure()
    
    # Mapeo de variables a títulos y colores
    config_variables = {
        'value_step_in': {
            'titulo': 'Step In (Entrada)',
            'color_hist': '#2E86AB',
            'color_modelo': '#06AED5'
        },
        'value_step_out': {
            'titulo': 'Step Out (Salida)',
            'color_hist': '#DD1C1A',
            'color_modelo': '#F24236'
        },
        'value_step_rate': {
            'titulo': 'Step Rate (Tasa)',
            'color_hist': '#06A77D',
            'color_modelo': '#4CB963'
        }
    }
    
    config = config_variables.get(variable, {
        'titulo': variable,
        'color_hist': '#808080',
        'color_modelo': '#1E90FF'
    })
    
    titulo = f"Zona {zona_nombre} - Balance Hídrico: {config['titulo']}"
    
    # Agregar datos históricos (MODFLOW) como barras
    if not df_hist.empty and variable in df_hist.columns:
        fig.add_trace(go.Bar(
            x=df_hist['date'],
            y=df_hist[variable],
            name='MODFLOW',
            marker=dict(color=config['color_hist'], opacity=0.8)
        ))
    
    # Agregar pronóstico (Metamodelo) como barras
    if not df_modelo.empty and variable in df_modelo.columns:
        # Filtrar solo datos futuros (después de la transición)
        if fecha_transicion:
            df_futuro = df_modelo[df_modelo['date'] > fecha_transicion]
        else:
            df_futuro = df_modelo
        
        if not df_futuro.empty:
            fig.add_trace(go.Bar(
                x=df_futuro['date'],
                y=df_futuro[variable],
                name='Metamodelo',
                marker=dict(color=config['color_modelo'], opacity=0.8)
            ))
    
    # Agregar línea vertical de transición
    if fecha_transicion:
        fig.add_shape(
            type="line",
            x0=fecha_transicion, x1=fecha_transicion,
            y0=0, y1=1,
            yref='paper',
            line=dict(color="gray", width=2, dash="dash")
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
            title="Volumen (m³)",
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=0.5
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
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
        height=500,
        barmode='group',
        bargap=0.15
    )
    
    return fig

def crear_grafico_combinado(df_hist, df_modelo, fecha_transicion, zona_nombre):
    """Crea gráfico con las tres variables en subplots"""
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            'Step In (Entrada)',
            'Step Out (Salida)', 
            'Step Rate (Tasa)'
        ),
        vertical_spacing=0.08
    )
    
    variables = [
        ('value_step_in', '#2E86AB', '#06AED5'),
        ('value_step_out', '#DD1C1A', '#F24236'),
        ('value_step_rate', '#06A77D', '#4CB963')
    ]
    
    for idx, (variable, color_hist, color_modelo) in enumerate(variables, 1):
        # Datos históricos
        if not df_hist.empty and variable in df_hist.columns:
            fig.add_trace(
                go.Bar(
                    x=df_hist['date'],
                    y=df_hist[variable],
                    name='MODFLOW' if idx == 1 else None,
                    marker=dict(color=color_hist, opacity=0.8),
                    showlegend=(idx == 1),
                    legendgroup='hist'
                ),
                row=idx, col=1
            )
        
        # Datos del metamodelo (futuro)
        if not df_modelo.empty and variable in df_modelo.columns:
            if fecha_transicion:
                df_futuro = df_modelo[df_modelo['date'] > fecha_transicion]
            else:
                df_futuro = df_modelo
            
            if not df_futuro.empty:
                fig.add_trace(
                    go.Bar(
                        x=df_futuro['date'],
                        y=df_futuro[variable],
                        name='Metamodelo' if idx == 1 else None,
                        marker=dict(color=color_modelo, opacity=0.8),
                        showlegend=(idx == 1),
                        legendgroup='modelo'
                    ),
                    row=idx, col=1
                )
        
        # Línea de transición
        if fecha_transicion:
            fig.add_vline(
                x=fecha_transicion,
                line_dash="dash",
                line_color="gray",
                line_width=1,
                row=idx, col=1
            )
    
    # Actualizar ejes
    fig.update_xaxes(title_text="Fecha", row=3, col=1)
    fig.update_yaxes(title_text="m³", row=1, col=1)
    fig.update_yaxes(title_text="m³", row=2, col=1)
    fig.update_yaxes(title_text="m³", row=3, col=1)
    
    fig.update_layout(
        height=1200,
        showlegend=True,
        title_text=f"Balance Hídrico - Zona: {zona_nombre}",
        plot_bgcolor='white',
        paper_bgcolor='white',
        barmode='group',
        bargap=0.15
    )
    
    return fig

def crear_grafico_comparacion_zonas(datos_por_zona):
    """Crea gráfico de comparación de componentes del balance por zona (promedio)"""
    zonas = []
    step_in_prom = []
    step_out_prom = []
    step_rate_prom = []

    # Calcular promedios por zona
    for zona, (df_hist, df_modelo) in datos_por_zona.items():
        # Combinar histórico y modelo para calcular promedio total
        df_completo = pd.concat([df_hist, df_modelo], ignore_index=True)

        if not df_completo.empty:
            zonas.append(zona)

            # Calcular promedios
            step_in_prom.append(df_completo['value_step_in'].mean() if 'value_step_in' in df_completo.columns else 0)
            step_out_prom.append(df_completo['value_step_out'].mean() if 'value_step_out' in df_completo.columns else 0)
            step_rate_prom.append(df_completo['value_step_rate'].mean() if 'value_step_rate' in df_completo.columns else 0)

    # Crear gráfico
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Step In',
        x=zonas,
        y=step_in_prom,
        marker=dict(color='#2E86AB')
    ))

    fig.add_trace(go.Bar(
        name='Step Out',
        x=zonas,
        y=step_out_prom,
        marker=dict(color='#DD1C1A')
    ))

    fig.add_trace(go.Bar(
        name='Step Rate',
        x=zonas,
        y=step_rate_prom,
        marker=dict(color='#06A77D')
    ))

    fig.update_layout(
        title='Comparación de Componentes del Balance por Zona (Promedio)',
        xaxis=dict(title='Zona', tickangle=-45),
        yaxis=dict(title='Volumen Promedio (m³)', showgrid=True, gridcolor='lightgray'),
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=600,
        bargap=0.15,
        bargroupgap=0.1
    )

    return fig

def crear_grafico_balance_neto_zonas(datos_por_zona):
    """Crea gráfico de balance neto promedio por zona"""
    zonas = []
    balance_neto = []

    # Calcular balance neto por zona (Step In - Step Out)
    for zona, (df_hist, df_modelo) in datos_por_zona.items():
        df_completo = pd.concat([df_hist, df_modelo], ignore_index=True)

        if not df_completo.empty:
            zonas.append(zona)

            # Balance neto = entradas - salidas
            if 'value_step_in' in df_completo.columns and 'value_step_out' in df_completo.columns:
                neto = (df_completo['value_step_in'] - df_completo['value_step_out']).mean()
            else:
                neto = 0

            balance_neto.append(neto)

    # Crear colores según sea positivo o negativo
    colores = ['#06A77D' if val >= 0 else '#DD1C1A' for val in balance_neto]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=zonas,
        y=balance_neto,
        marker=dict(color=colores),
        name='Balance Neto'
    ))

    # Agregar línea de referencia en cero
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)

    fig.update_layout(
        title='Balance Neto Promedio por Zona',
        xaxis=dict(title='Zona', tickangle=-45),
        yaxis=dict(title='Balance Neto Promedio (m³)', showgrid=True, gridcolor='lightgray', zeroline=True),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=600,
        showlegend=False
    )

    return fig

def crear_grafico_evolucion_total(datos_por_zona):
    """Crea gráfico de evolución del balance total del sistema"""
    # Recopilar todos los datos históricos y de pronóstico
    fechas_hist = []
    valores_hist = []
    fechas_modelo = []
    valores_modelo = []

    fecha_transicion = None

    for zona, (df_hist, df_modelo) in datos_por_zona.items():
        # Datos históricos
        if not df_hist.empty and 'date' in df_hist.columns:
            for _, row in df_hist.iterrows():
                fecha = row['date']
                # Balance = Step In - Step Out
                balance = 0
                if 'value_step_in' in row and 'value_step_out' in row:
                    balance = row['value_step_in'] - row['value_step_out']

                if fecha not in fechas_hist:
                    fechas_hist.append(fecha)
                    valores_hist.append(balance)
                else:
                    idx = fechas_hist.index(fecha)
                    valores_hist[idx] += balance

        # Datos del modelo
        if not df_modelo.empty and 'date' in df_modelo.columns:
            # Encontrar fecha de transición
            if not df_hist.empty:
                fecha_transicion = df_hist['date'].max()

            for _, row in df_modelo.iterrows():
                fecha = row['date']
                balance = 0
                if 'value_step_in' in row and 'value_step_out' in row:
                    balance = row['value_step_in'] - row['value_step_out']

                if fecha not in fechas_modelo:
                    fechas_modelo.append(fecha)
                    valores_modelo.append(balance)
                else:
                    idx = fechas_modelo.index(fecha)
                    valores_modelo[idx] += balance

    # Ordenar por fecha
    if fechas_hist and valores_hist:
        datos_hist_sorted = sorted(zip(fechas_hist, valores_hist))
        fechas_hist, valores_hist = zip(*datos_hist_sorted)

    if fechas_modelo and valores_modelo:
        datos_modelo_sorted = sorted(zip(fechas_modelo, valores_modelo))
        fechas_modelo, valores_modelo = zip(*datos_modelo_sorted)

    # Crear gráfico
    fig = go.Figure()

    # Línea histórica
    if fechas_hist:
        fig.add_trace(go.Scatter(
            x=fechas_hist,
            y=valores_hist,
            mode='lines',
            name='Histórico',
            line=dict(color='#2E86AB', width=2)
        ))

    # Línea de pronóstico
    if fechas_modelo:
        # Filtrar solo fechas futuras
        if fecha_transicion:
            fechas_futuro = [f for f in fechas_modelo if f > fecha_transicion]
            valores_futuro = [valores_modelo[i] for i, f in enumerate(fechas_modelo) if f > fecha_transicion]
        else:
            fechas_futuro = fechas_modelo
            valores_futuro = valores_modelo

        if fechas_futuro:
            fig.add_trace(go.Scatter(
                x=fechas_futuro,
                y=valores_futuro,
                mode='lines',
                name='Pronóstico',
                line=dict(color='#F24236', width=2, dash='dash')
            ))

    # Línea de referencia en cero
    fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1)

    # Línea de transición
    if fecha_transicion:
        fig.add_vline(
            x=fecha_transicion,
            line_dash="dash",
            line_color="gray",
            line_width=2
        )
        fig.add_annotation(
            x=fecha_transicion,
            y=1,
            yref='paper',
            text="Transición",
            showarrow=False,
            xanchor="center",
            yanchor="bottom"
        )

    fig.update_layout(
        title='Evolución del Balance Total del Sistema',
        xaxis=dict(title='Fecha', showgrid=True, gridcolor='lightgray'),
        yaxis=dict(title='Balance Total (m³)', showgrid=True, gridcolor='lightgray', zeroline=True),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=600,
        hovermode='x unified'
    )

    return fig

def generar_graficos_todas_zonas():
    """Genera gráficos de balance para todas las zonas disponibles"""
    # Crear carpeta de salida
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    zonas = obtener_zonas()

    if not zonas:
        print("No se pudieron obtener las zonas")
        return

    graficos = []
    datos_por_zona = {}

    # Recopilar datos de todas las zonas
    for zona in zonas:
        zona_nombre = zona if isinstance(zona, str) else zona.get('nombre', zona)
        print(f"Procesando zona: {zona_nombre}")

        # Obtener datos
        hist = obtener_datos_historicos(zona_nombre)
        modelo = obtener_datos_metamodelo(zona_nombre)
        df_hist, df_modelo, fecha_trans = procesar_datos(hist, modelo)

        if df_hist.empty and df_modelo.empty:
            print(f"  Sin datos para {zona_nombre}")
            continue

        # Guardar datos para gráficos comparativos
        datos_por_zona[zona_nombre] = (df_hist, df_modelo)

        # Crear gráficos individuales para cada variable
        variables = [
            ('value_step_in', 'step_in'),
            ('value_step_out', 'step_out'),
            ('value_step_rate', 'step_rate')
        ]

        for variable, nombre_corto in variables:
            if variable in df_hist.columns or variable in df_modelo.columns:
                fig = crear_grafico_balance(df_hist, df_modelo, fecha_trans, zona_nombre, variable)
                filename = f"{output_dir}/{zona_nombre}_balance_{nombre_corto}.png"
                fig.write_image(filename, width=1400, height=500, scale=2)
                print(f"  Guardado: {filename}")
                graficos.append((zona_nombre, nombre_corto, fig))

        # Crear gráfico combinado
        fig_combinado = crear_grafico_combinado(df_hist, df_modelo, fecha_trans, zona_nombre)
        filename_combinado = f"{output_dir}/{zona_nombre}_balance_combinado.png"
        fig_combinado.write_image(filename_combinado, width=1400, height=1200, scale=2)
        print(f"  Guardado: {filename_combinado}")

    # Generar gráficos comparativos (agregados)
    if datos_por_zona:
        print("\nGenerando gráficos comparativos...")

        # Gráfico 1: Comparación de componentes por zona
        fig_comparacion = crear_grafico_comparacion_zonas(datos_por_zona)
        filename_comparacion = f"{output_dir}/comparacion_componentes_zonas.png"
        fig_comparacion.write_image(filename_comparacion, width=1400, height=600, scale=2)
        print(f"  Guardado: {filename_comparacion}")

        # Gráfico 2: Balance neto por zona
        fig_balance_neto = crear_grafico_balance_neto_zonas(datos_por_zona)
        filename_neto = f"{output_dir}/balance_neto_zonas.png"
        fig_balance_neto.write_image(filename_neto, width=1400, height=600, scale=2)
        print(f"  Guardado: {filename_neto}")

        # Gráfico 3: Evolución del balance total del sistema
        fig_evolucion = crear_grafico_evolucion_total(datos_por_zona)
        filename_evolucion = f"{output_dir}/evolucion_balance_total.png"
        fig_evolucion.write_image(filename_evolucion, width=1400, height=600, scale=2)
        print(f"  Guardado: {filename_evolucion}")

    print(f"\nTodos los gráficos de balance guardados en la carpeta '{output_dir}'")
    return graficos

if __name__ == "__main__":
    print("Generando gráficos de balance hídrico para todas las zonas...")
    generar_graficos_todas_zonas()
