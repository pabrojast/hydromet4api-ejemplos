import requests
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from pyproj import Transformer
import os

# =============================================================================
# CARGAR DATOS DE POZOS
# Fuente API: GET /api/v1/plataforma-pozos/pozos-nivel-geojson
#
# Descripción: Puntos de monitoreo de pozos con clasificación por percentiles
# En el gráfico se visualizan como círculos de colores:
#   - Rojo: pozos con niveles bajos (<P33)
#   - Naranja: pozos con niveles medios-bajos (P33-P66)
#   - Amarillo: pozos con niveles medios-altos (P66-P90)
#   - Verde: pozos con niveles altos (>P90)
# =============================================================================
print("Obteniendo datos de pozos desde la API...")
response = requests.get('https://hydromet4api.hidrofuturo.cl/api/v1/plataforma-pozos/pozos-nivel-geojson')
if response.status_code != 200:
    print(f"Error al obtener datos de pozos: {response.status_code}")
    exit(1)
pozos_data = response.json()

# Extraer coordenadas y clasificaciones de pozos
pozos = []
for feature in pozos_data['features']:
    lon, lat = feature['geometry']['coordinates']
    clasificacion = feature['properties']['clasificacion_percentil']
    pozos.append({'lon': lon, 'lat': lat, 'clasificacion': clasificacion})

# =============================================================================
# CARGAR DATOS DE ZONAS/ACUÍFEROS
# Fuente API: GET /api/v1/metamodelos/metamodelos-zonas-geojson
#
# Descripción: Polígonos que definen las zonas del acuífero
# En el gráfico se visualizan como el fondo azul que representa:
#   - Zona núcleo
#   - Zona marginal norte
#   - Zona marginal sur
#   - Zona norte
# Los polígonos vienen en coordenadas UTM y se convierten a lat/lon
# =============================================================================
print("Obteniendo datos de zonas desde la API...")
response = requests.get('https://hydromet4api.hidrofuturo.cl/api/v1/metamodelos/metamodelos-zonas-geojson')
if response.status_code != 200:
    print(f"Error al obtener datos de zonas: {response.status_code}")
    exit(1)
zonas_data = response.json()

# Configurar transformador de coordenadas UTM (EPSG:32719, Zona 19S) a WGS84 (lat/lon)
# Las zonas vienen en UTM, los pozos en lat/lon
transformer = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)

# Convertir polígonos de zonas de UTM a lat/lon
zonas_latlon = []
for feature in zonas_data['features']:
    geom_type = feature['geometry']['type']
    nombre_zona = feature['properties']['zona']
    
    if geom_type == 'Polygon':
        coords_utm = feature['geometry']['coordinates'][0]  # Primer anillo del polígono
        coords_latlon = []
        for x_utm, y_utm in coords_utm:
            lon, lat = transformer.transform(x_utm, y_utm)
            coords_latlon.append([lon, lat])
        zonas_latlon.append({
            'nombre': nombre_zona,
            'coords': np.array(coords_latlon)
        })
    elif geom_type == 'MultiPolygon':
        # Para MultiPolygon, procesar cada polígono
        for polygon in feature['geometry']['coordinates']:
            coords_utm = polygon[0]  # Primer anillo de cada polígono
            coords_latlon = []
            for x_utm, y_utm in coords_utm:
                lon, lat = transformer.transform(x_utm, y_utm)
                coords_latlon.append([lon, lat])
            zonas_latlon.append({
                'nombre': nombre_zona,
                'coords': np.array(coords_latlon)
            })

# Definir colores por clasificación (paleta mejorada)
colores_map = {
    '<P33': '#E74C3C',      # Rojo vibrante
    'P33-P66': '#F39C12',   # Naranja
    'P66-P99': '#F1C40F',   # Amarillo dorado
    '>P99': '#27AE60'       # Verde esmeralda
}

# Contar pozos por categoría
conteos = {
    '<P33': 0,
    'P33-P66': 0,
    'P66-P99': 0,
    '>P99': 0
}

for pozo in pozos:
    conteos[pozo['clasificacion']] += 1

# Crear figura con estilo mejorado
plt.style.use('seaborn-v0_8-darkgrid')
fig, ax = plt.subplots(figsize=(14, 16), facecolor='white')
ax.set_facecolor('#F8F9FA')

# =============================================================================
# DIBUJAR POLÍGONOS DE ZONAS (FONDO AZUL DEL GRÁFICO)
# Las zonas del acuífero se muestran como áreas azules con bordes definidos
# Representan el contexto hidrogeológico donde están ubicados los pozos
# =============================================================================
for zona in zonas_latlon:
    # Fondo azul con gradiente visual
    polygon = Polygon(zona['coords'],
                     facecolor='#3498DB',
                     edgecolor='#1A5490',
                     alpha=0.5,
                     linewidth=2.5,
                     zorder=1)
    ax.add_patch(polygon)

    # Añadir sombra sutil para profundidad
    shadow = Polygon(zona['coords'],
                    facecolor='#2874A6',
                    edgecolor='none',
                    alpha=0.15,
                    linewidth=0,
                    zorder=0)
    ax.add_patch(shadow)

# Calcular límites del gráfico basados en todas las zonas
all_coords = np.vstack([z['coords'] for z in zonas_latlon])
lon_min, lon_max = all_coords[:, 0].min(), all_coords[:, 0].max()
lat_min, lat_max = all_coords[:, 1].min(), all_coords[:, 1].max()

# Añadir cuadrícula elegante
ax.grid(True, color='white', linewidth=1.2, alpha=0.4, linestyle='-', zorder=2)

# Plotear pozos con diseño mejorado
for pozo in pozos:
    color = colores_map[pozo['clasificacion']]

    # Determinar borde según criticidad
    if pozo['clasificacion'] in ['>P99', '<P33']:
        edgecolor = '#2C3E50'  # Gris oscuro para críticos
        linewidth = 2.5
        size = 200
    else:
        edgecolor = 'white'
        linewidth = 2
        size = 180

    # Dibujar pozos con mejor visualización
    ax.scatter(pozo['lon'], pozo['lat'],
              c=color, s=size,
              edgecolors=edgecolor,
              linewidths=linewidth,
              zorder=4,
              alpha=0.95,
              marker='o')

# Configurar título y etiquetas con diseño mejorado
ax.set_title('Distribución Espacial de Pozos por Clasificación de Percentiles\n(con Contexto de Acuíferos)',
            fontsize=18, fontweight='bold', pad=25,
            color='#2C3E50', family='sans-serif')
ax.set_xlabel('Longitud (°)', fontsize=13, fontweight='semibold', color='#34495E')
ax.set_ylabel('Latitud (°)', fontsize=13, fontweight='semibold', color='#34495E')

# Mejorar apariencia de los ejes
ax.tick_params(axis='both', which='major', labelsize=11, colors='#34495E')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_linewidth(1.5)
ax.spines['bottom'].set_linewidth(1.5)
ax.spines['left'].set_color('#95A5A6')
ax.spines['bottom'].set_color('#95A5A6')

# Ajustar límites
margin = 0.02
lon_range = lon_max - lon_min
lat_range = lat_max - lat_min
ax.set_xlim(lon_min - margin * lon_range, lon_max + margin * lon_range)
ax.set_ylim(lat_min - margin * lat_range, lat_max + margin * lat_range)

# Crear leyenda personalizada con diseño mejorado
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w',
           label=f'<P33 - Nivel Bajo ({conteos["<P33"]} pozos)',
           markerfacecolor='#E74C3C', markersize=12,
           markeredgecolor='#2C3E50', markeredgewidth=2),
    Line2D([0], [0], marker='o', color='w',
           label=f'P33-P66 - Nivel Medio-Bajo ({conteos["P33-P66"]} pozos)',
           markerfacecolor='#F39C12', markersize=11,
           markeredgecolor='white', markeredgewidth=1.5),
    Line2D([0], [0], marker='o', color='w',
           label=f'P66-P90 - Nivel Medio-Alto ({conteos["P66-P99"]} pozos)',
           markerfacecolor='#F1C40F', markersize=11,
           markeredgecolor='white', markeredgewidth=1.5),
    Line2D([0], [0], marker='o', color='w',
           label=f'>P90 - Nivel Alto ({conteos[">P99"]} pozos)',
           markerfacecolor='#27AE60', markersize=12,
           markeredgecolor='#2C3E50', markeredgewidth=2),
]

# Posicionar leyenda con estilo mejorado
legend = ax.legend(handles=legend_elements,
                   title='Clasificación de Percentil',
                   loc='upper right',
                   fontsize=10,
                   title_fontsize=12,
                   framealpha=0.97,
                   edgecolor='#34495E',
                   fancybox=True,
                   shadow=True,
                   borderpad=1.2)
legend.get_title().set_fontweight('bold')
legend.get_title().set_color('#2C3E50')

# Ajustar diseño
plt.tight_layout()

# =============================================================================
# GUARDAR GRÁFICO EN CARPETA DE SALIDA
# El gráfico muestra la distribución espacial de pozos sobre el acuífero
# con clasificación por colores según niveles de percentil
# =============================================================================
# Crear carpeta de outputs si no existe
os.makedirs('outputs', exist_ok=True)

# Guardar imagen en alta resolución
output_path = os.path.join('outputs', 'distribucion_pozos_percentiles.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Grafico guardado en: {output_path}")
print("Proceso completado exitosamente.")
