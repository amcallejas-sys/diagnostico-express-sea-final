# Funcionalidad futura: contraste con areas protegidas

Este documento resume una mejora futura para el MVP **Diagnostico Express SEA**: permitir que la aplicacion contraste la ubicacion de un proyecto con capas geograficas publicas de areas protegidas.

## Objetivo

Agregar una revision territorial preliminar para responder, con apoyo de datos geograficos, si un proyecto podria ubicarse dentro o intersectar un area protegida.

Esta funcionalidad ayudaria especialmente cuando el titular responde `No sabe` en la pregunta:

```text
Esta dentro de area protegida
```

## Idea general

El MVP podria comparar dos tipos de informacion:

1. **Ubicacion del proyecto**
   - Coordenadas ingresadas manualmente.
   - Archivo KML/KMZ del proyecto.
   - Poligono GeoJSON o Shapefile del area del proyecto.

2. **Capas oficiales de contraste**
   - Areas protegidas.
   - SNASPE.
   - Santuarios de la Naturaleza.
   - Humedales urbanos, en una etapa posterior.
   - Sitios Ramsar u otras areas bajo proteccion oficial, si corresponde.

## Carpetas recomendadas

Para mantener ordenado el proyecto, se recomienda crear:

```text
data/capas/
  areas_protegidas/
  humedales/
  pda/
  otros/

data/proyectos_geograficos/
```

Uso sugerido:

```text
data/capas/areas_protegidas/
```

Aqui se guardarian las capas oficiales descargadas, por ejemplo areas protegidas del MMA.

```text
data/proyectos_geograficos/
```

Aqui se guardarian los archivos KML/KMZ/GeoJSON/Shapefile del proyecto consultado.

## Flujo recomendado

1. El usuario ingresa la ubicacion del proyecto.
2. El MVP lee la capa oficial de areas protegidas.
3. El MVP compara la ubicacion del proyecto con la capa oficial.
4. El MVP informa un resultado preliminar:

```text
Coincide espacialmente con una capa oficial de area protegida.
```

o:

```text
No se detecta coincidencia con las capas cargadas.
```

o:

```text
INDETERMINADO: falta ubicacion exacta o la capa no pudo ser leida.
```

## Resultado esperado en la app

La aplicacion no deberia decir:

```text
El proyecto esta legalmente dentro de un area protegida.
```

Deberia decir algo mas prudente:

```text
Segun la geometria ingresada y las capas cargadas, se detecta una coincidencia espacial preliminar con el area protegida: [nombre del area].
```

Siempre debe mantenerse la advertencia:

```text
Resultado preliminar. No reemplaza una revision juridico-tecnica ni una consulta de pertinencia.
```

## Etapas sugeridas

### Etapa 1: version simple con coordenadas

Agregar campos:

```text
Latitud
Longitud
```

El MVP revisa si ese punto cae dentro de una capa de areas protegidas.

Ventaja: es mas simple de implementar.

Limitacion: un punto puede no representar bien proyectos lineales o extensos.

### Etapa 2: subir archivo del proyecto

Permitir subir:

```text
KML
KMZ
GeoJSON
Shapefile
```

El MVP compara el poligono o trazado del proyecto con las capas oficiales.

Ventaja: es mas preciso para proyectos extensos, lineas, parques solares o inmobiliarios.

Limitacion: requiere mejor manejo de archivos geograficos.

### Etapa 3: visor simple en mapa

Mostrar:

- ubicacion del proyecto;
- area protegida detectada;
- nombre de la capa;
- fuente de informacion;
- fecha de la capa, si esta disponible.

## Librerias gratuitas posibles

Para esta funcionalidad se podrian usar librerias gratuitas de Python:

```text
geopandas
shapely
pyogrio
fiona
fastkml
```

Para partir, conviene usar **GeoJSON** o **Shapefile** porque suelen ser mas faciles de procesar que KMZ.

KMZ/KML es comodo para usuarios, pero puede requerir conversion previa.

## Fuentes publicas utiles

- Datos abiertos MMA - Areas Protegidas: https://lineasdebasepublicas.mma.gob.cl/datos_abiertos/dataset/areas-protegidas
- SNAP MMA: https://snap.mma.gob.cl/
- IDE MMA: https://ide.mma.gob.cl/ayuda
- Servicio ArcGIS MMA - Areas Protegidas: https://arcgis.mma.gob.cl/server/rest/services/SIMBIO/SIMBIO_AP/MapServer/0

## Precauciones importantes

- No asumir que una capa esta siempre actualizada.
- Registrar la fuente y fecha de descarga de cada capa.
- No reemplazar la revision profesional.
- No concluir juridicamente solo por una interseccion automatica.
- Si falta precision en la ubicacion del proyecto, devolver `INDETERMINADO`.
- Si el proyecto esta cerca del borde de un area protegida, derivar a consultor.

## Recomendacion para implementar mas adelante

Partir con una version pequeña:

1. Crear carpetas `data/capas/areas_protegidas` y `data/proyectos_geograficos`.
2. Descargar una capa oficial en GeoJSON.
3. Permitir ingresar latitud y longitud.
4. Hacer una primera prueba de interseccion punto-poligono.
5. Mostrar resultado preliminar y fuente.
6. Luego avanzar a KML/KMZ o poligonos del proyecto.

