# Uso del diagnostico por rubrica

La aplicacion ahora tiene dos pestañas:

1. `Diagnostico preliminar`
2. `Criterios SEA`

## Para usar Diagnostico preliminar

1. Abre la aplicacion:

```bash
python -m streamlit run src/app_streamlit.py
```

2. Entra a:

```text
http://localhost:8501
```

3. Abre la pestaña `Diagnostico preliminar`.

4. Completa los datos que conozcas:

- tipo de gestion;
- sector;
- subtipo de energia, si corresponde;
- potencia MW;
- tension kV;
- cercania a humedal;
- area protegida;
- datos inmobiliarios, si corresponde;
- factores de modificacion con RCA, si corresponde.

5. Presiona `Generar diagnostico`.

La aplicacion mostrara:

- riesgo preliminar BAJO, MEDIO o ALTO;
- conclusion simple;
- literales relevantes;
- factores evaluados;
- casos SEA comparables desde la base de resoluciones.

## Como interpretar el resultado

`BAJO` significa que, con los datos ingresados, no aparece un factor critico evidente segun la rubrica.

`MEDIO` significa que hay una zona gris o faltan antecedentes relevantes.

`ALTO` significa que existe un factor que puede configurar ingreso obligatorio o requiere revision tecnica prioritaria.

## Importante

Este diagnostico es preliminar. No reemplaza una consulta de pertinencia, un pronunciamiento del SEA ni una revision juridico-tecnica profesional.

La pestaña `Criterios SEA` sigue mostrando las resoluciones procesadas y sus criterios extraidos.
