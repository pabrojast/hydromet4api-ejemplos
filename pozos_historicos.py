import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime

# Configuración de la API
BASE_URL = "https://hydromet4api.hidrofuturo.cl/api/v1/plataforma-pozos"

def obtener_listado_pozos():
    """Obtiene el listado completo de pozos disponibles"""
    response = requests.get(f"{BASE_URL}/listado-pozos")
    if response.status_code == 200:
        data = response.json()
        return data.get('pozos', [])
    return []

def obtener_datos_pozo(pozo_id):
    """Obtiene los datos históricos de un pozo específico"""
    response = requests.get(f"{BASE_URL}/pozos-data/{pozo_id}")
    if response.status_code == 200:
        return response.json()
    return None

def procesar_datos_pozo(datos_pozo):
    """Procesa los datos del pozo en un DataFrame"""
    if not datos_pozo or 'data' not in datos_pozo:
        return None, None
    
    info = datos_pozo.get('info', {})
    df = pd.DataFrame(datos_pozo['data'])
    
    if not df.empty and 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
    
    return df, info

def crear_grafico_pozo(df, info, pozo_id):
    """Crea gráfico de serie temporal para un pozo"""
    if df is None or df.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(14, 6), facecolor='white')
    
    # Configurar estilo
    ax.set_facecolor('#F8F9FA')
    ax.grid(True, color='white', linewidth=1, alpha=0.5, linestyle='-')
    
    # Plotear línea de nivel del agua
    ax.plot(df['date'], df['value'], 
            color='#1E88E5', linewidth=2, 
            marker='o', markersize=4, markerfacecolor='#1E88E5',
            markeredgecolor='white', markeredgewidth=1,
            label='Nivel del agua')
    
    # Información del pozo
    punto_monitoreo = info.get('punto_monitoreo', 'N/A')
    tipo_nivel = info.get('tipo_nivel', 'N/A')
    lat = info.get('latitude', 'N/A')
    lon = info.get('longitude', 'N/A')
    
    # Título y etiquetas
    titulo = f'Histórico de Nivel de Agua - {pozo_id}\n'
    titulo += f'Punto Monitoreo: {punto_monitoreo} | Tipo: {tipo_nivel}'
    if lat != 'N/A' and lon != 'N/A':
        titulo += f' | Lat: {lat:.4f}, Lon: {lon:.4f}'
    
    ax.set_title(titulo, fontsize=13, fontweight='bold', pad=20, color='#2C3E50')
    ax.set_xlabel('Fecha', fontsize=11, fontweight='semibold', color='#34495E')
    ax.set_ylabel('Nivel (m.s.n.m.)', fontsize=11, fontweight='semibold', color='#34495E')
    
    # Estadísticas básicas
    nivel_min = df['value'].min()
    nivel_max = df['value'].max()
    nivel_mean = df['value'].mean()
    
    # Añadir líneas de referencia
    ax.axhline(y=nivel_mean, color='#E74C3C', linestyle='--', linewidth=1.5, 
               alpha=0.7, label=f'Promedio: {nivel_mean:.2f} m')
    ax.axhline(y=nivel_max, color='#27AE60', linestyle=':', linewidth=1, 
               alpha=0.5, label=f'Máximo: {nivel_max:.2f} m')
    ax.axhline(y=nivel_min, color='#F39C12', linestyle=':', linewidth=1, 
               alpha=0.5, label=f'Mínimo: {nivel_min:.2f} m')
    
    # Configurar leyenda
    ax.legend(loc='best', fontsize=9, framealpha=0.95, 
              edgecolor='#34495E', fancybox=True, shadow=True)
    
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

def crear_grafico_comparativo(pozos_data):
    """Crea gráfico comparativo de múltiples pozos"""
    fig, ax = plt.subplots(figsize=(16, 8), facecolor='white')
    
    # Configurar estilo
    ax.set_facecolor('#F8F9FA')
    ax.grid(True, color='white', linewidth=1, alpha=0.5, linestyle='-')
    
    # Colores para cada pozo
    colores = ['#1E88E5', '#E74C3C', '#27AE60', '#F39C12', '#9B59B6', 
               '#3498DB', '#E67E22', '#1ABC9C']
    
    for idx, (pozo_id, df, info) in enumerate(pozos_data):
        if df is not None and not df.empty:
            punto_monitoreo = info.get('punto_monitoreo', pozo_id)
            color = colores[idx % len(colores)]
            
            ax.plot(df['date'], df['value'], 
                   color=color, linewidth=2, alpha=0.8,
                   marker='o', markersize=3, 
                   label=f'{punto_monitoreo} ({pozo_id})')
    
    # Título y etiquetas
    ax.set_title('Comparación de Niveles de Agua - Pozos Seleccionados', 
                fontsize=14, fontweight='bold', pad=20, color='#2C3E50')
    ax.set_xlabel('Fecha', fontsize=11, fontweight='semibold', color='#34495E')
    ax.set_ylabel('Nivel (m.s.n.m.)', fontsize=11, fontweight='semibold', color='#34495E')
    
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

def generar_graficos_pozos_ejemplo():
    """Genera gráficos para pozos de ejemplo"""
    # Crear carpeta de salida
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("Obteniendo listado de pozos...")
    pozos = obtener_listado_pozos()
    
    if not pozos:
        print("No se pudo obtener el listado de pozos")
        return
    
    print(f"Total de pozos disponibles: {len(pozos)}")
    
    # Seleccionar 3 pozos de ejemplo
    # Podemos tomar los primeros 3 o seleccionar específicos
    pozos_ejemplo = [
        "Pozo_104_E809_N774",  # L104
        "Pozo_3_E797_N645",     # L3
        "Pozo_16_E752_N698"     # L16
    ]
    
    print(f"\nProcesando {len(pozos_ejemplo)} pozos de ejemplo...")
    
    pozos_data = []
    
    for pozo_id in pozos_ejemplo:
        print(f"\nProcesando pozo: {pozo_id}")
        
        # Obtener datos del pozo
        datos = obtener_datos_pozo(pozo_id)
        
        if not datos:
            print(f"  Sin datos para {pozo_id}")
            continue
        
        # Procesar datos
        df, info = procesar_datos_pozo(datos)
        
        if df is None or df.empty:
            print(f"  No se pudieron procesar datos de {pozo_id}")
            continue
        
        print(f"  Registros: {len(df)}")
        print(f"  Rango: {df['date'].min()} a {df['date'].max()}")
        print(f"  Nivel mínimo: {df['value'].min():.2f} m")
        print(f"  Nivel máximo: {df['value'].max():.2f} m")
        
        # Guardar datos para gráfico comparativo
        pozos_data.append((pozo_id, df, info))
        
        # Crear gráfico individual
        fig = crear_grafico_pozo(df, info, pozo_id)
        if fig:
            filename = f"{output_dir}/{pozo_id}_historico.png"
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"  Guardado: {filename}")
            plt.close(fig)
    
    # Crear gráfico comparativo
    if pozos_data:
        print("\nGenerando gráfico comparativo...")
        fig_comp = crear_grafico_comparativo(pozos_data)
        filename_comp = f"{output_dir}/pozos_comparativo.png"
        fig_comp.savefig(filename_comp, dpi=300, bbox_inches='tight')
        print(f"Guardado: {filename_comp}")
        plt.close(fig_comp)
    
    print(f"\nTodos los gráficos de pozos guardados en la carpeta '{output_dir}'")

if __name__ == "__main__":
    print("Generando gráficos históricos de pozos...")
    generar_graficos_pozos_ejemplo()
