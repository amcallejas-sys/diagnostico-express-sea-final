# Conectar una IA real al MVP

Esta guia explica como activar OpenAI en el proyecto.

## La API es gratuita?

No exactamente. La API normalmente se paga por uso. Puede haber creditos iniciales o creditos comprados, segun tu cuenta, pero no conviene asumir que sera gratis.

Para controlar costos, prueba primero con 1 o 2 documentos antes de procesar todos.

## Paso 1: crear una API key

1. Entra a la plataforma de OpenAI.
2. Crea una API key.
3. No compartas esa clave por chat, correo ni documentos publicos.

## Paso 2: crear el archivo .env

Copia el archivo `.env.example` y renombralo como `.env`.

Debe quedar asi:

```text
OPENAI_API_KEY=tu_clave_aqui
OPENAI_MODEL=gpt-5
MAX_CARACTERES_IA=60000
```

`MAX_CARACTERES_IA` limita cuanto texto de cada resolucion se envia a la IA. Esto ayuda a controlar costos.

## Paso 3: instalar dependencias

```bash
python -m pip install -r requirements.txt
```

## Paso 4: probar con pocos documentos

Para evitar gasto innecesario, deja temporalmente solo 1 o 2 archivos `.txt` en `data/textos`, o copia una muestra a una carpeta aparte.

Luego ejecuta:

```bash
python src/analizar_textos.py
```

Si el archivo `.env` tiene una clave valida, el script dira:

```text
Modo IA real: OpenAI
```

Si no hay clave, dira:

```text
Modo local: reglas simples, sin costo API
```

## Paso 5: revisar JSON

Abre el resultado en `data/resultados` y revisa:

- nombre del proyecto;
- region;
- comuna;
- resultado;
- debe_ingresar_al_seia;
- criterios_sea;
- fragmento_respaldo.

## Paso 6: cargar la base de datos

Cuando el JSON este bien:

```bash
python src/base_datos.py
```

Despues recarga Streamlit.

## Recomendacion

No proceses todos los documentos hasta revisar 1 o 2 resultados. La IA puede equivocarse y tambien consume creditos.
