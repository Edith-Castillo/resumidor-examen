import os, streamlit as st
from summarizer import summarize, to_html

st.set_page_config(page_title="Resumidor para exámenes", page_icon="📚")
st.title("📚 Resumidor para exámenes")
st.caption("Resume al 40% de las hojas, sin perder lo importante. Conserva ejercicios y explica imágenes.")

key = st.text_input("API key de Anthropic", type="password", value=os.getenv("ANTHROPIC_API_KEY", ""))
mode = st.radio("Tipo de contenido", ["auto", "teoria", "practico"], horizontal=True,
                help="auto = detecta teoría o ejercicios (mate, física, química)")
files = st.file_uploader("Sube tus PDF", type="pdf", accept_multiple_files=True)

if st.button("Resumir", disabled=not (key and files)):
    for f in files:
        st.subheader(f.name)
        bar = st.progress(0.0, "Iniciando…")
        md, imgs, stats = summarize(f.read(), key, mode, lambda p, m: bar.progress(p, m))
        st.info(f"Original: {stats['paginas_originales']} hojas → objetivo (40%): "
                f"{stats['paginas_objetivo']} hojas · resumen real ≈ {stats['paginas_resumen_aprox']} "
                f"hojas ({stats['porcentaje_real']}%)")
        html = to_html(md, imgs, f.name)
        st.download_button("⬇️ Descargar HTML (imprime como PDF con Ctrl+P)", html,
                           file_name=f"resumen_{f.name}.html", mime="text/html", key=f"h{f.name}")
        st.download_button("⬇️ Descargar Markdown", md, file_name=f"resumen_{f.name}.md", key=f"m{f.name}")
        st.markdown(md.replace("[[IMG:", "(imagen: ").replace("]]", ")"))
