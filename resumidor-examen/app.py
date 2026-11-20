import os
import anthropic
import streamlit as st
from summarizer import summarize, to_html

st.set_page_config(page_title="Resumidor para exámenes", page_icon="📚")
st.title("📚 Resumidor para exámenes")
st.caption("Resume al 40% de las hojas, sin perder lo importante. Conserva ejercicios y explica imágenes.")


def get_key():
    try:
        k = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        k = os.getenv("ANTHROPIC_API_KEY", "")
    return k.strip()


key = get_key()
if not key:
    st.error("Falta configurar la clave una sola vez. En Streamlit Cloud: Manage app → Settings → Secrets, "
             'y pega:  ANTHROPIC_API_KEY = "sk-ant-..."   (en local: variable de entorno).')
    st.stop()

mode = st.radio("Tipo de contenido", ["auto", "teoria", "practico"], horizontal=True,
                help="auto = detecta teoría o ejercicios (mate, física, química)")
files = st.file_uploader("Sube tus PDF", type="pdf", accept_multiple_files=True)

if st.button("Resumir", disabled=not files):
    for f in files:
        st.subheader(f.name)
        bar = st.progress(0.0, "Iniciando…")
        try:
            md, imgs, stats = summarize(f.read(), key, mode, lambda p, m: bar.progress(p, m))
        except anthropic.AuthenticationError:
            st.error("La clave guardada en Secrets es inválida o no tiene saldo. Revísala en console.anthropic.com.")
            st.stop()
        except anthropic.NotFoundError:
            st.error("El modelo no está disponible en tu cuenta. Cambia MODEL en summarizer.py (ej. claude-sonnet-4-6).")
            st.stop()
        st.info(f"Original: {stats['paginas_originales']} hojas → objetivo (40%): "
                f"{stats['paginas_objetivo']} hojas · resumen real ≈ {stats['paginas_resumen_aprox']} "
                f"hojas ({stats['porcentaje_real']}%)")
        html = to_html(md, imgs, f.name)
        st.download_button("⬇️ Descargar HTML (imprime como PDF con Ctrl+P)", html,
                           file_name=f"resumen_{f.name}.html", mime="text/html", key=f"h{f.name}")
        st.download_button("⬇️ Descargar Markdown", md, file_name=f"resumen_{f.name}.md", key=f"m{f.name}")
        st.markdown(md.replace("[[IMG:", "(imagen: ").replace("]]", ")"))
