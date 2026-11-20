"""Motor de resumen para exámenes: resume (no elimina) y llega al ~40% del PDF."""
import base64, math, re
import fitz  # PyMuPDF
import markdown
import anthropic

MODEL = "claude-sonnet-5-5"   # puedes cambiarlo
RATIO = 0.40                  # el resumen = 40% de las hojas
PAGES_PER_CHUNK = 6
MAX_IMGS_PER_CHUNK = 8
WORDS_PER_SCANNED_PAGE = 350

SYSTEM = """Eres un tutor experto que prepara resúmenes de estudio para exámenes.
REGLAS:
1. RESUMIR no es ELIMINAR: condensa la redacción, pero conserva TODAS las ideas, definiciones,
   fórmulas, fechas, nombres y conceptos importantes. Solo recorta relleno y repeticiones.
2. Detecta el tipo de contenido:
   - TEÓRICO: usa títulos, viñetas, definiciones en **negrita**, y para cada concepto difícil
     añade un "💡 Ejemplo:" corto y claro que ayude a entenderlo.
   - PRÁCTICO (matemáticas, física, química, etc.): CONSERVA cada ejercicio y problema resuelto,
     en el mismo orden. Para cada uno escribe: **Enunciado**, **Datos/Fórmulas**, **Resolución paso a paso**
     (explicando el porqué de cada paso) y **Resultado**. Usa LaTeX con $...$ para fórmulas.
   - Si el texto mezcla ambos, aplica cada formato donde corresponda.
3. IMÁGENES: se te dan imágenes con un ID (ej. p3_1). Inserta las útiles con [[IMG:p3_1]] justo
   donde ayuden y explícalas en 1-3 líneas debajo ("📷 Qué muestra: ..."). Si una página está
   escaneada, léela de la imagen de página.
4. LONGITUD: respeta el presupuesto de palabras indicado (±10%). No lo superes.
5. Responde en el idioma del documento, en Markdown, sin preámbulos."""


def extract(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, p in enumerate(doc):
        text = p.get_text().strip()
        scanned = len(text) < 30
        imgs = []
        if scanned:
            imgs.append((f"pagina{i+1}", p.get_pixmap(dpi=110).tobytes("png")))
        else:
            for j, info in enumerate(p.get_images(full=True)):
                try:
                    pix = fitz.Pixmap(doc, info[0])
                    if pix.width < 150 or pix.height < 150:
                        continue
                    if pix.n - pix.alpha >= 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    data = pix.tobytes("png")
                    if len(data) < 3_000_000:
                        imgs.append((f"p{i+1}_{j+1}", data))
                except Exception:
                    pass
        pages.append({"n": i + 1, "text": text, "scanned": scanned, "images": imgs})
    return pages


def _words(t): return len(re.findall(r"\w+", t))


def _chunks(pages):
    for i in range(0, len(pages), PAGES_PER_CHUNK):
        yield pages[i:i + PAGES_PER_CHUNK]


def _build_content(chunk, budget, mode):
    first, last = chunk[0]["n"], chunk[-1]["n"]
    hint = {"auto": "Detecta si es teórico o práctico.",
            "teoria": "Trátalo como TEÓRICO.",
            "practico": "Trátalo como PRÁCTICO (conserva todos los ejercicios)."}[mode]
    parts = [{"type": "text", "text":
              f"Páginas {first}–{last}. Presupuesto: ~{budget} palabras. {hint}\n"}]
    imgs = []
    for p in chunk:
        parts.append({"type": "text", "text": f"\n--- Página {p['n']} ---\n{p['text']}"})
        imgs += p["images"]
    for iid, data in imgs[:MAX_IMGS_PER_CHUNK]:
        parts.append({"type": "text", "text": f"IMAGEN ID={iid}"})
        parts.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                      "data": base64.b64encode(data).decode()}})
    return parts, dict(imgs[:MAX_IMGS_PER_CHUNK])


def summarize(pdf_bytes, api_key, mode="auto", progress=lambda f, m: None):
    client = anthropic.Anthropic(api_key=api_key)
    pages = extract(pdf_bytes)
    total = len(pages)
    target_pages = math.ceil(total * RATIO)
    chunks = list(_chunks(pages))
    out, all_imgs = [], {}
    orig_words = 0
    for k, chunk in enumerate(chunks):
        progress(k / len(chunks), f"Resumiendo páginas {chunk[0]['n']}–{chunk[-1]['n']} de {total}…")
        w = sum(WORDS_PER_SCANNED_PAGE if p["scanned"] else _words(p["text"]) for p in chunk)
        orig_words += w
        budget = max(80, round(w * RATIO))
        content, imgs = _build_content(chunk, budget, mode)
        all_imgs.update(imgs)
        msgs = [{"role": "user", "content": content}]
        r = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM, messages=msgs)
        text = r.content[0].text
        if _words(text) > budget * 1.2:  # reajuste si se pasó del 40%
            msgs += [{"role": "assistant", "content": text},
                     {"role": "user", "content": f"Te pasaste. Condensa a ~{budget} palabras "
                      "sin perder conceptos ni ejercicios clave. Devuelve solo el resumen."}]
            text = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM,
                                          messages=msgs).content[0].text
        out.append(text)
    progress(1.0, "Listo")
    md = "\n\n---\n\n".join(out)
    sw = _words(md)
    stats = {"paginas_originales": total, "paginas_objetivo": target_pages,
             "paginas_resumen_aprox": round(total * sw / max(orig_words, 1), 1),
             "porcentaje_real": round(100 * sw / max(orig_words, 1), 1)}
    return md, all_imgs, stats


def to_html(md, imgs, title="Resumen"):
    def sub(m):
        iid = m.group(1)
        if iid in imgs:
            b64 = base64.b64encode(imgs[iid]).decode()
            return f'<img src="data:image/png;base64,{b64}" style="max-width:80%">'
        return ""
    md = re.sub(r"\[\[IMG:([\w\-]+)\]\]", lambda m: f"@@{m.group(1)}@@", md)
    body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    body = re.sub(r"@@([\w\-]+)@@", sub, body)
    return (f"<html><head><meta charset='utf-8'><title>{title}</title>"
            "<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>"
            "<style>body{font-family:Arial;max-width:800px;margin:auto;line-height:1.5}"
            "img{display:block;margin:10px auto}</style></head><body>" + body + "</body></html>")
