import streamlit as st
from docx import Document
from docx.shared import Pt, RGBColor
from PIL import Image
import pytesseract
import io

# ----------------------------------------------------------------------
# 🔹 TEXTE D’INTRODUCTION (repris exactement comme dans ton premier code)
# ----------------------------------------------------------------------
st.markdown("""
## 📘 Adaptateur de textes pour élèves dyslexiques  
Cette application permet d’adapter automatiquement un texte en appliquant  
un **code couleur pour aider la lecture** :  
- voyelles en rouge  
- consonnes en bleu  
- graphèmes complexes en vert  
- lettres muettes en gris  
- mots outils en noir  

Elle peut adapter un texte que vous collez, ou un texte issu d’une **photo** grâce à l’OCR.
""")

st.write("---")

# ----------------------------------------------------------------------
# 🔹 PARAMÈTRES UTILISATEUR
# ----------------------------------------------------------------------

# Police
police = st.selectbox(
    "Choisir la police pour le document final",
    ["OpenDyslexic", "Arial", "Times New Roman"],
    index=0
)

# OCR
st.subheader("📸 Paramètres OCR (si vous utilisez une photo)")
st.markdown("""
- **Binarisation** : rend le texte plus net.  
- **Redimensionnement** : aide la reconnaissance des lettres.  
👉 *Vous pouvez laisser les réglages par défaut si vous n’êtes pas sûr.*
""")

binarize = st.checkbox("Binariser l’image", value=True)
resize = st.checkbox("Redimensionner pour améliorer l’OCR", value=True)

uploaded_image = st.file_uploader("Importer une image contenant du texte", type=["jpg", "jpeg", "png"])

# Texte manuel
texte_saisi = st.text_area("Ou coller un texte à adapter :", height=200)

st.write("---")

# ----------------------------------------------------------------------
# 🔹 GRAPHÈME CIBLE (repris exact)
# ----------------------------------------------------------------------
use_target = st.checkbox("Utiliser un graphème cible")
target_graph = ""
if use_target:
    target_graph = st.text_input("Graphème cible à mettre en valeur (ex : 'ou', 'on')").strip().lower()

# ----------------------------------------------------------------------
# 🔹 LISTE DES GRAPHÈMES COMPLEXES (repris de ton code original)
# ----------------------------------------------------------------------
graphèmes_complexes = [
    "on", "an", "en", "in", "ain", "ein", "ien",
    "ch", "ph", "gn", "ou", "oi", "ui", "eau",
    "au", "eu", "oeu", "ill", "ail", "eil", "euil",
    "ouille"
]

# ----------------------------------------------------------------------
# 🔹 DÉTECTION DES LETTRES MUETTES
# ----------------------------------------------------------------------
def est_lettre_muette(mot, i):
    if i == len(mot) - 1:
        if mot[i] in ["e", "s", "t", "x", "d", "p", "g"]:
            return True
    if mot[i] == "h":
        return True
    return False

# ----------------------------------------------------------------------
# 🔹 OCR SUR L’IMAGE
# ----------------------------------------------------------------------
texte_image = ""

if uploaded_image is not None:
    image = Image.open(uploaded_image)

    if resize:
        image = image.resize((image.width * 2, image.height * 2))

    if binarize:
        image = image.convert("L").point(lambda x: 0 if x < 128 else 255, '1')

    texte_image = pytesseract.image_to_string(image, lang="fra")

# ----------------------------------------------------------------------
# 🔹 CHOIX DU TEXTE SOURCE
# ----------------------------------------------------------------------
texte_source = texte_image if texte_image.strip() else texte_saisi

if not texte_source.strip():
    st.warning("Veuillez coller un texte ou importer une image.")
    st.stop()

# ----------------------------------------------------------------------
# 🔹 COULEURS DU DOCX
# ----------------------------------------------------------------------
couleur_voy = RGBColor(255, 0, 0)
couleur_cons = RGBColor(0, 0, 255)
couleur_complexe = RGBColor(0, 128, 0)
couleur_muette = RGBColor(128, 128, 128)
couleur_noir = RGBColor(0, 0, 0)

# ----------------------------------------------------------------------
# 🔹 FONCTION D’ANALYSE DU TEXTE (reprend TA LOGIQUE EXACTE)
# ----------------------------------------------------------------------
def colorier_mot(mot):
    result = []
    i = 0
    mot_inf = mot.lower()

    while i < len(mot):
        if use_target and mot_inf[i:].startswith(target_graph):
            result.append(("".join(mot[i:i+len(target_graph)]), couleur_complexe))
            i += len(target_graph)
            continue

        match = False
        for g in sorted(graphèmes_complexes, key=len, reverse=True):
            if mot_inf[i:].startswith(g):
                result.append(("".join(mot[i:i+len(g)]), couleur_complexe))
                i += len(g)
                match = True
                break
        if match:
            continue

        lettre = mot[i]
        if lettre.lower() in "aeiouy":
            couleur = couleur_voy
        elif est_lettre_muette(mot_inf, i):
            couleur = couleur_muette
        elif lettre.isalpha():
            couleur = couleur_cons
        else:
            couleur = couleur_noir

        result.append((lettre, couleur))
        i += 1

    return result

# ----------------------------------------------------------------------
# 🔹 GÉNÉRATION DU DOCUMENT
# ----------------------------------------------------------------------
if st.button("Créer le .docx adapté"):
    doc = Document()

    # appliquer police
    style = doc.styles["Normal"]
    style.font.name = police
    style.font.size = Pt(16)

    for ligne in texte_source.split("\n"):
        p = doc.add_paragraph()
        for mot in ligne.split(" "):
            morceaux = colorier_mot(mot)
            for texte, couleur in morceaux:
                run = p.add_run(texte)
                run.font.color.rgb = couleur
            p.add_run(" ")

    # message final (repris exact)
    doc.add_paragraph("\nCréé avec le <3 par un prof fatigué mais motivé.")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    st.download_button(
        "Télécharger le document",
        data=buffer,
        file_name="texte_adapte.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
