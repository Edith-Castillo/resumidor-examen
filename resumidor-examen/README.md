# 📚 Resumidor para exámenes

Sube PDFs y obtén un resumen del **40% de las hojas**, sin eliminar información importante.
- **Teoría**: definiciones, viñetas y ejemplos explicados.
- **Práctica** (mate/física/química): conserva todos los ejercicios, ordenados y resueltos paso a paso.
- **Imágenes**: inserta las figuras del PDF y explica qué muestran. Soporta PDFs escaneados.

## Usar
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```
Ejemplo: 50 hojas → resumen de 20 hojas.

## Subir a GitHub (https://github.com/new)
1. Crea el repo `resumidor-examen` (sin README).
2. En esta carpeta:
```bash
git init && git add . && git commit -m "Resumidor para exámenes"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/resumidor-examen.git
git push -u origin main
```
3. (Opcional) Despliega gratis en https://share.streamlit.io y guarda la API key en *Secrets*.
