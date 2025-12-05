import streamlit as st
from PIL import Image
import pytesseract
import cv2
import numpy as np
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import io
import re

# Configuration de base
st.set_page_config(page_title="Lecture Colorée CP", page_icon="📚", layout="wide")

# CSS pour l'aperçu
st.markdown("""
<style>
.police-preview { font-family: inherit; font-size: 18px; }
.document-preview { font-family: inherit; font-size: 24px; line-height: 2; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

# Configurations
POLICES = [
    {'nom': 'Arial', 'affichage': 'Arial'},
    {'nom': 'Comic Sans MS', 'affichage': 'Comic Sans MS'},
    {'nom': 'OpenDyslexic', 'affichage': 'OpenDyslexic'},
    {'nom': 'Belle Allure', 'affichage': 'Belle Allure'}
]

COULEURS = {
    'voyelles': "#FF0000",
    'consonnes': "#0000FF",
    'graphemes': "#008000",
    'muettes': "#808080",
    'mots_outils': "#8B4513"
}

# Fonctions utilitaires
def hex_to_rgb(hex_color):
    return RGBColor(*tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)))

def preprocess_image(image):
    img = np.array(image.convert('L'))
    _, img = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return img

def extraire_texte(image):
    img = preprocess_image(image)
    config = r'--oem 3 --psm 6 preserve_interword_spaces'
    return pytesseract.image_to_string(img, lang='fra', config=config)

def nettoyer_texte(texte):
    texte = re.sub(r'\n{3,}', '\n\n', texte)  # Garder max 2 sauts de ligne
    texte = re.sub(r'([.!?])\s*', r'\1\n\n', texte)  # Saut après ponctuation
    texte = re.sub(r'\n\s*\n', '\n\n', texte)  # Nettoyer les sauts multiples
    return texte.strip()

def capitaliser(texte):
    return '. '.join(sentence.capitalize() for sentence in texte.split('. '))

def colorier_texte(texte, mots_outils):
    resultat = []
    mots_outils = {m.lower() for m in mots_outils}
    i = 0
    while i < len(texte):
        char = texte[i]
        if not char.isalpha():
            resultat.append((char, None))
            i += 1
            continue

        # Trouver le mot complet
        debut = i
        while debut > 0 and texte[debut-1].isalpha():
            debut -= 1
        fin = i
        while fin < len(texte) and texte[fin].isalpha():
            fin += 1
        mot = texte[debut:fin]

        # Vérifier si c'est un mot-outil
        if mot.lower() in mots_outils:
            resultat.extend((c, 'mots_outils') for c in mot)
            i = fin
            continue

        # Vérifier les graphèmes complexes
        trouve = False
        for son in ['ouil', 'euil', 'ch', 'ph', 'gn', 'ill', 'ou', 'oi', 'ai', 'ei']:
            if i + len(son) <= len(texte) and texte[i:i+len(son)].lower() == son:
                resultat.extend((c, 'graphemes') for c in texte[i:i+len(son)])
                i += len(son)
                trouve = True
                break

        if not trouve:
            resultat.append((char, 'voyelles' if char.lower() in 'aeiouy' else 'consonnes'))
            i += 1

    return resultat

def creer_document(texte_colorie, police, couleurs):
    doc = Document()
    doc.styles['Normal'].font.name = police
    doc.styles['Normal'].font.size = Pt(25)
    doc.styles['Normal'].paragraph_format.line_spacing = 2

    for line in texte_colorie.split('\n'):
        para = doc.add_paragraph()
        para.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

        for char, couleur in line:
            run = para.add_run(char)
            run.font.name = police
            run.font.size = Pt(25)
            if couleur:
                run.font.color.rgb = hex_to_rgb(couleurs[couleur])

        if line.strip() and line[-1] in '.!?':
            para.add_run('  ')  # Espace après ponctuation

    return doc

# Interface
st.title("📚 Lecture Colorée CP")
st.markdown("Application d'adaptation de textes pour enfants DYS et TSA")

# Sidebar
with st.sidebar:
    st.header("Paramètres")

    # Sélection police avec aperçu
    police_selectionnee = st.selectbox(
        "Police d'écriture",
        POLICES,
        format_func=lambda x: f'<div class="police-preview" style="font-family:{x["nom"]}">{x["nom"]}</div>',
        index=0
    )
    police = police_selectionnee['nom']
    st.markdown(f'<p style="font-family:{police}; font-size:20px;">Exemple: Le chat mange une souris.</p>', unsafe_allow_html=True)

    # Personnalisation couleurs
    st.subheader("Couleurs")
    couleurs = {k: st.color_picker(k.capitalize(), v) for k, v in COULEURS.items()}

# Upload image
uploaded_file = st.file_uploader("Upload image", type=['png', 'jpg', 'jpeg'])
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Image uploadée", width=400)

    # Zones de saisie
    mots_perso = st.text_area("Mots-outils supplémentaires (séparés par virgules)")

    if st.button("Générer le document"):
        with st.spinner("Traitement en cours..."):
            # Extraction et traitement du texte
            texte_brut = extraire_texte(image)
            texte_nettoye = nettoyer_texte(texte_brut)
            texte_capitalise = capitaliser(texte_nettoye)

            # Préparation mots-outils
            mots_outils = ["le", "la", "un", "une", "je", "tu", "il", "elle", "nous", "ils"]
            if mots_perso:
                mots_outils.extend(m.strip() for m in mots_perso.split(',') if m.strip())

            # Colorisation
            texte_colorie = []
            for line in texte_capitalise.split('\n'):
                texte_colorie.append(colorier_texte(line, mots_outils))

            # Aperçu
            st.subheader("Aperçu du document")
            html = f'<div class="document-preview" style="font-family:{police}">'
            for line in texte_colorie:
                for char, couleur in line:
                    if char == '\n':
                        html += '<br>'
                    elif couleur:
                        html += f'<span style="color:{couleurs[couleur]}">{char}</span>'
                    else:
                        html += char
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

            # Création document Word
            doc = Document()
            for line in texte_colorie:
                para = doc.add_paragraph()
                para.paragraph_format.line_spacing = 2
                para.paragraph_format.space_after = Pt(12)
                para.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

                for char, couleur in line:
                    if char == '\n':
                        continue
                    run = para.add_run(char)
                    run.font.name = police
                    run.font.size = Pt(25)
                    if couleur:
                        run.font.color.rgb = hex_to_rgb(couleurs[couleur])

            # Téléchargement
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button(
                "Télécharger le document Word",
                bio.getvalue(),
                file_name="texte_colorie.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

st.markdown("---")
st.markdown("Projet open source - Adapté pour les enfants DYS et TSA")
