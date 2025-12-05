import streamlit as st
from PIL import Image
import pytesseract
import cv2
import numpy as np
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

# Configuration de la page
st.set_page_config(
    page_title="Lecture Colorée CP",
    page_icon="📚",
    layout="wide"
)

# CSS pour l'aperçu des polices
st.markdown("""
<style>
.police-preview {
    font-family: inherit;
    font-size: 18px;
}
</style>
""", unsafe_allow_html=True)

# Définitions globales
sons_complexes = [
    'ouil', 'euil', 'aille', 'eille', 'ille', 'ouille',
    'ain', 'aim', 'ein', 'eim', 'oin', 'ien', 'eau', 'oeu',
    'ch', 'ph', 'gn', 'ill', 'ail', 'eil', 'ou', 'au', 'eu', 'oi', 'oy',
    'ai', 'ei'
]
sons_nasals = ['an', 'am', 'en', 'em', 'on', 'om', 'in', 'im', 'un', 'um', 'yn', 'ym']
voyelles = 'aeiouyàâäéèêëïîôùûüÿæœAEIOUYÀÂÄÉÈÊËÏÎÔÙÛÜŸÆŒ'
lettres_muettes_fin = ['s', 't', 'd', 'p', 'x', 'z']

# Mots-outils de base
MOTS_OUTILS_BASE = [
    'est', 'et', 'un', 'une', 'le', 'la', 'les', 'de', 'du', 'des',
    'dans', 'sur', 'avec', 'pour', 'par', 'il', 'elle', 'ils', 'elles',
    'ont', 'sont', 'a', 'à', 'au', 'aux', 'ce', 'cette', 'ces',
    'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses'
]

# Polices disponibles
POLICES = [
    {'nom': 'Arial', 'affichage': 'Arial'},
    {'nom': 'Comic Sans MS', 'affichage': 'Comic Sans MS'},
    {'nom': 'Helvetica', 'affichage': 'Helvetica'},
    {'nom': 'OpenDyslexic', 'affichage': 'OpenDyslexic'},
    {'nom': 'Belle Allure', 'affichage': 'Belle Allure'}
]

# Palettes de couleurs
PALETTES = {
    "Standard": {
        'voyelles': "#FF0000",
        'consonnes': "#0000FF",
        'graphemes': "#008000",
        'muettes': "#808080",
        'mots_outils': "#8B4513"
    }
}

# Fonction pour convertir hex en RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return RGBColor(*tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)))

# Détection lettre muette
def detecter_lettre_muette(mot, position):
    if position == len(mot) - 1:
        lettre = mot[position].lower()
        if lettre in lettres_muettes_fin or (len(mot) >= 3 and mot[-3:].lower() == 'ent'):
            return True
    return position == 0 and mot[position].lower() == 'h'

# Extraction de mot complet
def extraire_mot_complet(texte, position):
    debut = position
    while debut > 0 and texte[debut - 1].isalpha():
        debut -= 1
    fin = position
    while fin < len(texte) and texte[fin].isalpha():
        fin += 1
    return texte[debut:fin], debut, fin

# Validation son nasal
def est_son_nasal_valide(texte, position, son):
    pos_apres = position + len(son)
    if pos_apres >= len(texte):
        return True
    char_apres = texte[pos_apres].lower()
    if char_apres in voyelles or (son[-1] == 'n' and char_apres == 'n') or (son[-1] == 'm' and char_apres == 'm'):
        return False
    return True

# Traitement des points
def traiter_points(texte):
    return texte.replace('. ', ' . ').replace('.', ' . ').replace('  ', ' ').strip()

# Capitalisation des phrases
def capitaliser_phrases(texte):
    phrases = texte.split(' . ')
    return ' . '.join(p.capitalize() if p else p for p in phrases)

# Extraction de texte améliorée
def extraire_texte_de_image(image):
    try:
        img = np.array(image.convert('L'))
        _, img = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        config = r'--oem 3 --psm 6'
        return pytesseract.image_to_string(img, lang='fra', config=config)
    except Exception as e:
        return f"Erreur: {str(e)}"

# Colorisation du texte
def colorier_texte(texte, mots_outils):
    resultat = []
    mots_outils_lower = {m.lower() for m in mots_outils}
    i = 0
    while i < len(texte):
        char = texte[i]
        if not char.isalpha():
            resultat.append((char, None))
            i += 1
            continue

        mot, debut, fin = extraire_mot_complet(texte, i)
        pos_dans_mot = i - debut

        if mot.lower() in mots_outils_lower:
            resultat.extend((c, 'mots_outils') for c in mot)
            i = fin
            continue

        if detecter_lettre_muette(mot, pos_dans_mot):
            resultat.extend((c, 'muettes') for c in mot[pos_dans_mot:])
            i = fin
            continue

        for son in sorted(sons_complexes + sons_nasals, key=len, reverse=True):
            if i + len(son) <= len(texte) and texte[i:i+len(son)].lower() == son:
                resultat.extend((c, 'graphemes') for c in texte[i:i+len(son)])
                i += len(son)
                break
        else:
            resultat.append((char, 'voyelles' if char.lower() in voyelles else 'consonnes'))
            i += 1
    return resultat

# Création du document Word
def creer_document(texte, police, couleurs):
    doc = Document()
    para = doc.add_paragraph()
    para.paragraph_format.line_spacing = 2
    para.paragraph_format.space_after = Pt(12)

    for char, couleur in texte:
        run = para.add_run(char)
        run.font.size = Pt(25)
        run.font.name = police
        if couleur:
            run.font.color.rgb = hex_to_rgb(couleurs[couleur])

    return doc

# Interface principale
st.title("📚 Lecture Colorée CP")
st.markdown("Application d'adaptation de textes pour enfants dys et TSA")

# Sidebar
with st.sidebar:
    st.header("Paramètres")

    # Choix police
    police_selectionnee = st.selectbox(
        "Police d'écriture",
        POLICES,
        format_func=lambda x: f'<div class="police-preview" style="font-family:{x["nom"]}">{x["nom"]}</div>',
        index=0
    )
    police = police_selectionnee['nom']

    # Aperçu police
    st.markdown(f'<p style="font-family:{police}; font-size:20px;">Exemple: Le chat mange une souris.</p>', unsafe_allow_html=True)

    # Choix couleurs
    st.subheader("Couleurs")
    col_voyelles = st.color_picker("Voyelles", "#FF0000")
    col_consonnes = st.color_picker("Consonnes", "#0000FF")
    col_graphemes = st.color_picker("Graphèmes", "#008000")
    col_muettes = st.color_picker("Lettres muettes", "#808080")
    col_mots_outils = st.color_picker("Mots-outils", "#8B4513")

    couleurs = {
        'voyelles': col_voyelles,
        'consonnes': col_consonnes,
        'graphemes': col_graphemes,
        'muettes': col_muettes,
        'mots_outils': col_mots_outils
    }

# Upload image
uploaded_file = st.file_uploader("Upload image", type=['png', 'jpg', 'jpeg'])
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Image uploadée", width=400)

    # Zone de saisie
    graphemes_cibles = st.text_area("Graphèmes cibles (un par ligne)")
    mots_perso = st.text_area("Mots-outils supplémentaires (séparés par virgules)")

    # Bouton génération
    if st.button("Générer les documents"):
        with st.spinner("Traitement en cours..."):
            # Extraction texte
            texte_brut = extraire_texte_de_image(image)
            texte_brut = traiter_points(texte_brut)
            texte_brut = capitaliser_phrases(texte_brut)
            texte_brut = '  '.join(texte_brut.split())

            # Préparation mots-outils
            mots_outils = MOTS_OUTILS_BASE.copy()
            if mots_perso:
                mots_outils.extend(m.strip() for m in mots_perso.split(',') if m.strip())

            # Colorisation
            texte_colorie = colorier_texte(texte_brut, mots_outils)

            # Création documents
            doc = creer_document(texte_colorie, police, couleurs)

            # Aperçu
            st.subheader("Aperçu")
            html = f'<div style="font-family:{police}; font-size:24px; line-height:2;">'
            for char, couleur in texte_colorie:
                if couleur:
                    html += f'<span style="color:{couleurs[couleur]}">{char}</span>'
                else:
                    html += char
            st.markdown(html + "</div>", unsafe_allow_html=True)

            # Téléchargement
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button(
                "Télécharger le document",
                bio.getvalue(),
                file_name="texte_colorie.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

st.markdown("---")
st.markdown("Projet open source - Adapté pour les enfants DYS et TSA")
