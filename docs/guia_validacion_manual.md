# Guia de validacion manual

Antes de confiar en los resultados del MVP, revisa una muestra de documentos.

## Texto extraido

- Abre el archivo `.txt` generado en `data/textos`.
- Verifica si el texto es legible.
- Si el archivo esta vacio o con caracteres raros, probablemente el PDF es escaneado o tiene mala capa de texto.

## Resultado JSON

- Abre el archivo `.json` generado en `data/resultados`.
- Revisa que los campos principales no esten inventados.
- Si no hay respaldo claro, el valor debe ser `null` o `"no determinado"`.

## Criterios SEA

Para cada criterio extraido, revisa:

- si el criterio aparece realmente en el documento;
- si la explicacion es coherente;
- si el fragmento de respaldo es breve;
- si el nivel de confianza no exagera cuando el texto es ambiguo.

## Decision sobre ingreso al SEIA

Revisa especialmente:

- `resultado`;
- `debe_ingresar_al_seia`;
- `fragmento_respaldo`.

Estos campos son sensibles y deben tener revision humana.
