# Diagnóstico Express SEA

Este proyecto es un MVP local para apoyar un diagnóstico preliminar de pertinencia de ingreso al SEIA, usando resoluciones públicas del Servicio de Evaluación Ambiental de Chile y una rúbrica interna.

Importante: esta herramienta no entrega un pronunciamiento del SEA, no constituye jurisprudencia vinculante y no reemplaza una consulta de pertinencia ni un análisis jurídico-técnico profesional. Si faltan antecedentes, el resultado debe tratarse como `INDETERMINADO` y revisarse con un consultor.

## Qué Hace

- Extrae texto desde resoluciones PDF cargadas manualmente.
- Genera JSON estructurados con datos y criterios administrativos.
- Carga esos JSON en una base SQLite local.
- Permite generar un diagnóstico preliminar por rúbrica.
- Compara el proyecto consultado con resoluciones comparables ya procesadas.
- Muestra analítica simple de la base cargada.
- Permite consultar criterios SEA, resúmenes y fragmentos de respaldo.

## Estructura

```text
data/
  pdfs/          PDF originales cargados manualmente
  textos/        Texto extraído desde cada PDF
  resultados/    JSON generados por el análisis
  diagnostico_express.sqlite
docs/
  conectar_ia_real.md
  guia_validacion_manual.md
  prompt_extraccion_ia.md
  uso_diagnostico_rubrica.md
src/
  app_streamlit.py              Interfaz principal
  analitica_datos.py            Consultas y datos para analítica
  comparador_precedentes.py     Comparación referencial de precedentes
  zonas_maule.py                Lista local de comunas del Maule con PDA para apoyo preliminar
  motor_rubrica.py              Reglas del diagnóstico preliminar
  busqueda_precedentes.py       Búsqueda simple existente
  base_datos.py                 Crea y carga SQLite
  extraer_texto_pdfs.py         Extrae texto desde PDF
  analizar_textos.py            Genera JSON, con IA simulada o futura IA real
  validacion.py                 Valida estructura JSON
tests/
  test_comparador_precedentes.py
  test_motor_y_analitica.py
.env.example
.gitignore
requirements.txt
README.md
```

## Instalación

Desde la carpeta del proyecto:

```bash
py -m pip install -r requirements.txt
```

Comando equivalente:

```bash
python -m pip install -r requirements.txt
```

## Cargar Resoluciones

Copia tus PDF en:

```text
data/pdfs
```

Para el MVP conviene usar pocos documentos revisables, por ejemplo 10 a 20 resoluciones.

## Ejecutar El Flujo

Extraer texto:

```bash
py src/extraer_texto_pdfs.py
```

O:

```bash
python src/extraer_texto_pdfs.py
```

Analizar textos y crear JSON:

```bash
py src/analizar_textos.py
```

O:

```bash
python src/analizar_textos.py
```

Crear o actualizar SQLite:

```bash
py src/base_datos.py
```

O:

```bash
python src/base_datos.py
```

Levantar Streamlit:

```bash
py -m streamlit run src/app_streamlit.py
```

O:

```bash
python -m streamlit run src/app_streamlit.py
```

Ejecutar pruebas:

```bash
py -m pytest
```

O:

```bash
python -m pytest
```

## Pestañas De La Aplicación

### Diagnóstico Preliminar

Permite ingresar datos básicos del proyecto. Al presionar `Generar diagnóstico`, la aplicación:

- evalúa la rúbrica;
- muestra riesgo preliminar;
- muestra literales o criterios relevantes;
- informa datos faltantes;
- guarda temporalmente los datos en `st.session_state` para usarlos en el comparador.

`INDETERMINADO` significa que falta información relevante o que la regla disponible no basta para concluir preliminarmente. En ese caso se debe derivar a consultor.

### Comparador De Precedentes

Compara el proyecto consultado con resoluciones procesadas en la base local.

Primero busca resoluciones de la región seleccionada. Si no hay suficientes precedentes regionales, la app muestra un aviso y permite ampliar voluntariamente a otras regiones.

El indicador se llama `Nivel de coincidencia de antecedentes`. No es riesgo, probabilidad ni certeza jurídica.

Puntaje referencial:

- Misma región: hasta 30 puntos.
- Mismo sector: hasta 25 puntos.
- Mismo subtipo: hasta 20 puntos.
- Palabras clave: hasta 15 puntos.
- Literales o criterios: hasta 10 puntos.

Si un componente no se puede comparar, no se asignan puntos automáticos y se informa como dato no comparable.

La pestaña muestra:

- hasta cinco resoluciones comparables;
- coincidencias;
- diferencias;
- datos no comparables;
- criterios extraídos;
- fragmentos de respaldo;
- normativa citada;
- matriz comparativa;
- informe descargable en Markdown.

La ausencia de precedentes no significa que el proyecto no deba ingresar al SEIA. Una coincidencia con resoluciones que no ingresaron tampoco permite concluir automáticamente que el proyecto consultado no ingresa.

### Analítica De Datos

Muestra indicadores y gráficos de las resoluciones cargadas:

- total de resoluciones procesadas;
- regiones y comunas representadas;
- resoluciones de energía e inmobiliarias;
- distribución de ingreso al SEIA;
- registros sin región o sin tipo determinado;
- gráficos por región, sector, resultado, año y subtipo;
- tabla filtrada descargable en CSV.

Filtros disponibles:

- región;
- comuna;
- sector o tipo;
- subtipo;
- año de resolución cuando la fecha sea válida.

La sección `Calidad y cobertura de los datos` muestra campos faltantes o `No determinado`. La analítica refleja solo los documentos cargados y no representa necesariamente el universo total del SEA.

### Criterios SEA

Permite consultar resoluciones procesadas y revisar:

- datos principales;
- resumen ejecutivo;
- criterios identificados;
- nivel de confianza;
- fragmentos de respaldo.

## Limitaciones Actuales

La base SQLite no almacena como campos estructurados algunos datos técnicos. Por eso el comparador no puede comparar automáticamente:

- potencia eléctrica de precedentes;
- tensión eléctrica de precedentes;
- número de viviendas de precedentes;
- superficie de precedentes;
- trazados, fajas, distancias o coordenadas.

Esos datos pueden estar en el texto o resumen, pero el MVP no los infiere desde texto libre para evitar errores.
Para mantener el diagnóstico preliminar simple, el formulario inmobiliario tampoco usa movimiento de material como variable de evaluación.
En proyectos inmobiliarios del Maule, el formulario pregunta comuna y si el proyecto se ubica en área urbana, rural, ambas o no sabe. Con esa información, el MVP orienta el análisis a h.1), g) o ambos. Para áreas urbanas, usa una lista local de comunas asociadas a PDA o zona saturada como apoyo preliminar: Talca, Maule, Curicó, Teno, Romeral, Rauco, Molina y Sagrada Familia. Esta ayuda no reemplaza verificar el polígono, área urbana o instrumento oficial aplicable al caso concreto.

## Errores Frecuentes

Si Streamlit no abre:

```bash
py -m pip install -r requirements.txt
py -m streamlit run src/app_streamlit.py
```

Si `py` no existe, usa:

```bash
python -m pip install -r requirements.txt
python -m streamlit run src/app_streamlit.py
```

Si la base no existe:

```bash
py src/base_datos.py
```

Si no aparecen documentos:

- verifica que haya JSON en `data/resultados`;
- ejecuta `py src/base_datos.py`;
- revisa que los JSON tengan campos mínimos válidos.

Si un PDF no extrae texto, puede ser escaneado. En ese caso se necesitaría OCR en una etapa futura.

## Seguridad

No subas a GitHub:

- `.env`;
- claves API;
- PDF sensibles;
- bases SQLite con datos que no quieras compartir.

El archivo `.gitignore` ayuda a excluir esos archivos.
