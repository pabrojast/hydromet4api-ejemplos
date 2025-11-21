import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime

# Configuración de la API
BASE_URL_PRONOSTICO = "https://hydromet4api.hidrofuturo.cl/api/v1/salida/pronostico-pozos"
BASE_URL_POZOS = "https://hydromet4api.hidrofuturo.cl/api/v1/plataforma-pozos"

def obtener_listado_pozos_pronostico():
    """Obtiene el listado de pozos con pronósticos disponibles"""
    response = requests.get(f"{BASE_URL_PRONOSTICO}/listado")
    if response.status_code == 200:
        return response.json()
    return []

def obtener_datos_pronostico(pozo_id):
    """Obtiene los datos de pronóstico para un pozo específico"""
    response = requests.get(f"{BASE_URL_PRONOSTICO}-data/{pozo_id}")
    if response.status_code == 200:
        return response.json()
    return None

def obtener_info_pozo_completa(pozo_id):
    """Obtiene información completa del pozo desde la API de pozos (coordenadas, etc)"""
    response = requests.get(f"{BASE_URL_POZOS}/pozos-data/{pozo_id}")
    if response.status_code == 200:
        data = response.json()
        return data.get('info', {})
    return {}

def procesar_datos_pronostico(datos_pronostico):
    """Procesa los datos de pronóstico en un DataFrame"""
    if not datos_pronostico or 'data' not in datos_pronostico:
        return None, None
    
    info = datos_pronostico.get('info', {})
    df = pd.DataFrame(datos_pronostico['data'])
    
    if not df.empty and 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
    
    return df, info

def crear_grafico_pronostico(df, info, info_completa, pozo_id):
    """Crea gráfico de pronóstico para un pozo"""
    if df is None or df.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(14, 6), facecolor='white')
    
    # Configurar estilo
    ax.set_facecolor('#F8F9FA')
    ax.grid(True, color='white', linewidth=1, alpha=0.5, linestyle='-')
    
    # Plotear línea de pronóstico
    ax.plot(df['date'], df['value'], 
            color='#E74C3C', linewidth=2.5, 
            marker='o', markersize=5, markerfacecolor='#E74C3C',
            markeredgecolor='white', markeredgewidth=1.5,
            label='Pronóstico')
    
    # Rellenar área bajo la curva
    ax.fill_between(df['date'], df['value'], alpha=0.3, color='#E74C3C')
    
    # Información del pozo
    punto_monitoreo = info_completa.get('punto_monitoreo', 'N/A')
    lat = info_completa.get('latitude', 'N/A')
    lon = info_completa.get('longitude', 'N/A')
    tipo_nivel = info_completa.get('tipo_nivel', 'N/A')
    
    # Título y etiquetas
    titulo = f'Pronóstico de Nivel de Agua - {pozo_id}\n'
    titulo += f'Punto Monitoreo: {punto_monitoreo}'
    if tipo_nivel != 'N/A':
        titulo += f' | Tipo: {tipo_nivel}'
    if lat != 'N/A' and lon != 'N/A':
        titulo += f' | Lat: {lat:.4f}, Lon: {lon:.4f}'
    
    ax.set_title(titulo, fontsize=13, fontweight='bold', pad=20, color='#2C3E50')
    ax.set_xlabel('Fecha', fontsize=11, fontweight='semibold', color='#34495E')
    ax.set_ylabel('Variación Pronosticada (m)', fontsize=11, fontweight='semibold', color='#34495E')
    
    # Estadísticas del pronóstico
    valor_min = df['value'].min()
    valor_max = df['value'].max()
    valor_mean = df['value'].mean()
    
    # Añadir líneas de referencia
    ax.axhline(y=0, color='#2C3E50', linestyle='-', linewidth=2, 
               alpha=0.5, label='Nivel actual (referencia)')
    ax.axhline(y=valor_mean, color='#3498DB', linestyle='--', linewidth=1.5, 
               alpha=0.7, label=f'Promedio: {valor_mean:.4f} m')
    
    # Marcar puntos extremos
    if valor_max > 0:
        idx_max = df['value'].idxmax()
        ax.scatter(df.loc[idx_max, 'date'], df.loc[idx_max, 'value'], 
                  color='#27AE60', s=150, marker='^', zorder=5,
                  edgecolors='white', linewidths=2,
                  label=f'Máximo: {valor_max:.4f} m')
    
    if valor_min < 0:
        idx_min = df['value'].idxmin()
        ax.scatter(df.loc[idx_min, 'date'], df.loc[idx_min, 'value'], 
                  color='#F39C12', s=150, marker='v', zorder=5,
                  edgecolors='white', linewidths=2,
                  label=f'Mínimo: {valor_min:.4f} m')
    
    # Configurar leyenda
    ax.legend(loc='best', fontsize=9, framealpha=0.95, 
              edgecolor='#34495E', fancybox=True, shadow=True)
    
    # Añadir información de rango de fechas
    fecha_inicio = df['date'].min().strftime('%Y-%m-%d')
    fecha_fin = df['date'].max().strftime('%Y-%m-%d')
    ax.text(0.02, 0.98, f'Período: {fecha_inicio} a {fecha_fin}', 
            transform=ax.transAxes, fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Mejorar apariencia de los ejes
    ax.tick_params(axis='both', which='major', labelsize=9, colors='#34495E')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['left'].set_color('#95A5A6')
    ax.spines['bottom'].set_color('#95A5A6')
    
    # Rotar etiquetas del eje x
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    return fig

def crear_grafico_comparativo_pronosticos(pozos_data):
    """Crea gráfico comparativo de pronósticos de múltiples pozos"""
    fig, ax = plt.subplots(figsize=(16, 8), facecolor='white')
    
    # Configurar estilo
    ax.set_facecolor('#F8F9FA')
    ax.grid(True, color='white', linewidth=1, alpha=0.5, linestyle='-')
    
    # Colores para cada pozo
    colores = ['#E74C3C', '#3498DB', '#27AE60', '#F39C12', '#9B59B6', 
               '#E67E22', '#1ABC9C', '#34495E']
    
    for idx, (pozo_id, df, info, info_completa) in enumerate(pozos_data):
        if df is not None and not df.empty:
            punto_monitoreo = info_completa.get('punto_monitoreo', pozo_id)
            color = colores[idx % len(colores)]
            
            ax.plot(df['date'], df['value'], 
                   color=color, linewidth=2.5, alpha=0.8,
                   marker='o', markersize=4, 
                   label=f'{punto_monitoreo} ({pozo_id})')
            
            # Área bajo la curva con transparencia
            ax.fill_between(df['date'], df['value'], alpha=0.15, color=color)
    
    # Línea de referencia en 0
    ax.axhline(y=0, color='#2C3E50', linestyle='-', linewidth=2, 
               alpha=0.5, label='Nivel actual (referencia)')
    
    # Título y etiquetas
    ax.set_title('Comparación de Pronósticos de Nivel de Agua - Pozos Seleccionados', 
                fontsize=14, fontweight='bold', pad=20, color='#2C3E50')
    ax.set_xlabel('Fecha', fontsize=11, fontweight='semibold', color='#34495E')
    ax.set_ylabel('Variación Pronosticada (m)', fontsize=11, fontweight='semibold', color='#34495E')
    
    # Configurar leyenda
    ax.legend(loc='best', fontsize=9, framealpha=0.95, 
              edgecolor='#34495E', fancybox=True, shadow=True,
              ncol=2 if len(pozos_data) > 4 else 1)
    
    # Mejorar apariencia de los ejes
    ax.tick_params(axis='both', which='major', labelsize=9, colors='#34495E')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['left'].set_color('#95A5A6')
    ax.spines['bottom'].set_color('#95A5A6')
    
    # Rotar etiquetas del eje x
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    return fig

def generar_graficos_pronosticos():
    """Genera gráficos de pronósticos para pozos de ejemplo"""
    # Crear carpeta de salida
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("Obteniendo listado de pozos con pronósticos...")
    pozos_lista = obtener_listado_pozos_pronostico()
    
    if not pozos_lista:
        print("No se pudo obtener el listado de pozos con pronósticos")
        return
    
    print(f"Total de pozos con pronósticos disponibles: {len(pozos_lista)}")
    
    # Seleccionar 3 pozos de ejemplo
    pozos_ejemplo = [
        "Pozo_104_E809_N774",  # L104
        "Pozo_3_E797_N645",     # L3
        "Pozo_16_E752_N698"     # L16
    ]
    
    print(f"\nProcesando {len(pozos_ejemplo)} pozos de ejemplo...")
    
    pozos_data = []
    
    for pozo_id in pozos_ejemplo:
        print(f"\nProcesando pozo: {pozo_id}")
        
        # Obtener datos de pronóstico
        datos_pronostico = obtener_datos_pronostico(pozo_id)
        
        if not datos_pronostico:
            print(f"  Sin datos de pronóstico para {pozo_id}")
            continue
        
        # Procesar datos
        df, info = procesar_datos_pronostico(datos_pronostico)
        
        if df is None or df.empty:
            print(f"  No se pudieron procesar datos de pronóstico de {pozo_id}")
            continue
        
        # Obtener información completa del pozo
        info_completa = obtener_info_pozo_completa(pozo_id)
        
        print(f"  Registros de pronóstico: {len(df)}")
        print(f"  Rango: {df['date'].min()} a {df['date'].max()}")
        print(f"  Variación mínima: {df['value'].min():.6f} m")
        print(f"  Variación máxima: {df['value'].max():.6f} m")
        print(f"  Punto monitoreo: {info_completa.get('punto_monitoreo', 'N/A')}")
        
        # Guardar datos para gráfico comparativo
        pozos_data.append((pozo_id, df, info, info_completa))
        
        # Crear gráfico individual
        fig = crear_grafico_pronostico(df, info, info_completa, pozo_id)
        if fig:
            filename = f"{output_dir}/{pozo_id}_pronostico.png"
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"  Guardado: {filename}")
            plt.close(fig)
    
    # Crear gráfico comparativo
    if pozos_data:
        print("\nGenerando gráfico comparativo de pronósticos...")
        fig_comp = crear_grafico_comparativo_pronosticos(pozos_data)
        filename_comp = f"{output_dir}/pronosticos_comparativo.png"
        fig_comp.savefig(filename_comp, dpi=300, bbox_inches='tight')
        print(f"Guardado: {filename_comp}")
        plt.close(fig_comp)
    
    print(f"\nTodos los gráficos de pronósticos guardados en la carpeta '{output_dir}'")

if __name__ == "__main__":
    print("Generando gráficos de pronósticos de pozos...")
    generar_graficos_pronosticos()
