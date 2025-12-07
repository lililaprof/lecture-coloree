import streamlit as st
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

# Configuration de base
st.set_page_config(page_title="Lecture Colorée CP", page_icon="📚", layout="wide")

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

# Listes de mots-outils par manuel
LISTES_MANUELS = {
    'Ma liste perso': [],
    'Taoki': ['est', 'et', 'un', 'une', 'le', 'la', 'les', 'de', 'il', 'elle', 'dans', 'sur', 'avec'],
    'Pilotis': ['le', 'la', 'les', 'un', 'une', 'des', 'il', 'elle', 'est', 'dans', 'sur', 'avec', 'pour'],
    'Léo et Léa': ['le', 'la', 'l', 'un', 'une', 'et', 'est', 'il', 'elle', 'je', 'tu', 'de', 'du'],
    'Base commune': ['est', 'et', 'un', 'une', 'le', 'la', 'les', 'de', 'du', 'des', 'dans', 'sur', 
                     'avec', 'pour', 'par', 'il', 'elle', 'ils', 'elles', 'ont', 'sont', 'a', 'à', 
                     'au', 'aux', 'ce', 'cette', 'ces', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses']
}

POLICES = ['Arial', 'Comic Sans MS', 'OpenDyslexic', 'Quicksand Book', 'Belle Allure', 'Helvetica']

# Fonctions utilitaires
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return RGBColor(*tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)))

def pretraiter_image(image, qualite_ocr):
    """Prépare l'image pour une meilleure lecture par l'OCR"""
    img = image.copy()
    
    # Convertir en niveaux de gris
    img = ImageOps.grayscale(img)
    
    # Si qualité maximale, appliquer des filtres
    if qualite_ocr == "Maximale":
        # Réduire le bruit
        img = img.filter(ImageFilter.MedianFilter(size=3))
        # Améliorer le contraste (binarisation)
        img = img.point(lambda p: 255 if p > 180 else 0)
    
    return img

def detecter_lettre_muette(mot, position):
    if position == len(mot) - 1:
        lettre = mot[position].lower()
        if lettre in lettres_muettes_fin:
            return True
        if len(mot) >= 3 and mot[-3:].lower() == 'ent':
            return True
    if position == 0 and mot[position].lower() == 'h':
        return True
    return False

def extraire_mot_complet(texte, position):
    debut = position
    while debut > 0 and texte[debut - 1].isalpha():
        debut -= 1
    fin = position
    while fin < len(texte) and texte[fin].isalpha():
        fin += 1
    return texte[debut:fin], debut, fin

def est_son_nasal_valide(texte, position, son):
    pos_apres = position + len(son)
    if pos_apres >= len(texte):
        return True
    char_apres = texte[pos_apres].lower()
    if char_apres in voyelles:
        return False
    if son[-1] == 'n' and char_apres == 'n':
        return False
    if son[-1] == 'm' and char_apres == 'm':
        return False
    return True

def remplacer_separateurs(texte):
    resultat = ""
    i = 0
    while i < len(texte):
        if texte[i] == '.':
            if i + 1 < len(texte):
                reste = texte[i+1:].lstrip()
                if reste and (reste[0].isupper() or reste[0] == '\n'):
                    resultat += '.'
                else:
                    resultat += ' •'
            else:
                resultat += '.'
            i += 1
        else:
            resultat += texte[i]
            i += 1
    return resultat

def mettre_majuscules_phrases(texte):
    """Met une majuscule au début de chaque phrase"""
    resultat = []
    debut_phrase = True
    
    for char in texte:
        if debut_phrase and char.isalpha():
            resultat.append(char.upper())
            debut_phrase = False
        else:
            resultat.append(char)
            if char in '.!?':
                debut_phrase = True
    
    return ''.join(resultat)

def ajouter_espaces_entre_mots(texte):
    resultat = ""
    for i, char in enumerate(texte):
        if char == ' ':
            if i > 0 and texte[i-1] != ' ':
                resultat += '  '
            elif i == 0:
                resultat += '  '
        else:
            resultat += char
    return resultat

def colorier_texte(texte, mots_outils, couleurs_config, activer_muettes=True):
    resultat_word = []
    mots_outils_lower = [mot.lower() for mot in mots_outils]
    mots_outils_upper = [mot.upper() for mot in mots_outils]
    tous_mots_outils = mots_outils + mots_outils_lower + mots_outils_upper
    
    i = 0
    while i < len(texte):
        char = texte[i]
        
        if not char.isalpha():
            resultat_word.append((char, None))
            i += 1
            continue
        
        mot_complet, debut_mot, fin_mot = extraire_mot_complet(texte, i)
        position_dans_mot = i - debut_mot
        
        if mot_complet in tous_mots_outils:
            for c in mot_complet:
                resultat_word.append((c, 'mots_outils'))
            i = fin_mot
            continue
        
        if activer_muettes and detecter_lettre_muette(mot_complet, position_dans_mot):
            resultat_word.append((char, 'muettes'))
            i += 1
            continue
        
        trouve = False
        for son in sons_complexes:
            if texte[i:i+len(son)].lower() == son:
                segment = texte[i:i+len(son)]
                for c in segment:
                    resultat_word.append((c, 'graphemes'))
                i += len(son)
                trouve = True
                break
        
        if not trouve:
            for son in sons_nasals:
                if texte[i:i+len(son)].lower() == son:
                    if est_son_nasal_valide(texte, i, son):
                        segment = texte[i:i+len(son)]
                        for c in segment:
                            resultat_word.append((c, 'graphemes'))
                        i += len(son)
                        trouve = True
                        break
        
        if not trouve:
            if char.lower() in voyelles:
                resultat_word.append((char, 'voyelles'))
            else:
                resultat_word.append((char, 'consonnes'))
            i += 1
    
    return resultat_word

def colorier_graphemes_cibles(texte, graphemes_cibles, couleur_cible):
    resultat_word = []
    graphemes_lower = [g.lower() for g in graphemes_cibles]
    
    i = 0
    while i < len(texte):
        trouve = False
        for grapheme in graphemes_lower:
            if texte[i:i+len(grapheme)].lower() == grapheme:
                segment = texte[i:i+len(grapheme)]
                for c in segment:
                    resultat_word.append((c, 'cible'))
                i += len(grapheme)
                trouve = True
                break
        
        if not trouve:
            resultat_word.append((texte[i], 'black'))
            i += 1
    
    return resultat_word

def creer_word(texte_traite, police, couleurs_config, casse, taille_pt=25):
    doc = Document()
    
    couleurs_rgb = {}
    for key, hex_val in couleurs_config.items():
        couleurs_rgb[key] = hex_to_rgb(hex_val)
    
    titre = f'{casse.upper()}'
    titre_para = doc.add_heading(titre, level=1)
    titre_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    for char, couleur in texte_traite:
        run = para.add_run(char)
        run.font.size = Pt(taille_pt)
        run.font.name = police
        if couleur and couleur in couleurs_rgb:
            run.font.color.rgb = couleurs_rgb[couleur]
    
    return doc

def generer_preview_html(texte_traite, couleurs_config, police):
    """Génère un aperçu HTML du texte coloré"""
    mapping = {
        'voyelles': couleurs_config.get('voyelles', '#FF0000'),
        'consonnes': couleurs_config.get('consonnes', '#0000FF'),
        'graphemes': couleurs_config.get('graphemes', '#008000'),
        'muettes': couleurs_config.get('muettes', '#808080'),
        'mots_outils': couleurs_config.get('mots_outils', '#8B4513'),
        'cible': couleurs_config.get('cible', '#069494'),
        'black': '#000000',
        None: '#000000'
    }
    
    html = f"<div style='font-family:{police}; font-size:20px; line-height:1.8; padding:20px; background:#f9f9f9; border-radius:10px;'>"
    for char, couleur in texte_traite:
        color = mapping.get(couleur, '#000000')
        safe_char = char.replace(' ', '&nbsp;').replace('\n', '<br/>')
        html += f"<span style='color:{color};'>{safe_char}</span>"
    html += "</div>"
    return html

# Interface Streamlit
st.title("📚 Lecture Colorée pour CP")
st.markdown("**Application d'adaptation de textes pour enfants dys et TSA**")
st.markdown("*Pour les enseignants et les parents*")

# Description de l'application
st.info("""
📖 **Comment ça marche ?**
1. Uploadez une photo/scan de votre texte de lecture
2. Personnalisez les couleurs et choisissez votre liste de mots-outils
3. Choisissez majuscules ou minuscules
4. Générez et téléchargez votre document Word coloré !

🎨 **Code couleur :** 🔴 Voyelles • 🔵 Consonnes • 🟢 Graphèmes complexes • ⚫ Lettres muettes • 🟤 Mots-outils

🎯 **Option graphèmes ciblés :** Créez un second document avec uniquement le(s) son(s) travaillé(s) dans votre leçon en couleur, le reste en noir
""")

with st.expander("ℹ️ En savoir plus sur l'application"):
    st.markdown("""
    ### Pourquoi cette application ?
    Cette application a été créée par une enseignante de CP pour faciliter l'adaptation des textes pour les élèves dys et TSA.
    
    ### Fonctionnalités
    - ✅ Code couleur basé sur la phonétique
    - ✅ Listes de mots-outils par manuel (Taoki, Pilotis, Léo et Léa...)
    - ✅ Détection des lettres muettes
    - ✅ Espacement entre les mots pour faciliter la lecture
    - ✅ Export en Word avec police adaptée
    - ✅ Prévisualisation avant téléchargement
    
    *Application gratuite et open source* 💚
    """)

st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Paramètres généraux")
    
    police = st.selectbox("📝 Police d'écriture", POLICES, index=0)
    
    taille_police = st.slider("📏 Taille de la police", min_value=12, max_value=40, value=25, step=1,
                              help="Taille en points (pt) pour tous les documents")
    
    st.markdown("---")
    st.subheader("🔍 Qualité de lecture (OCR)")
    
    qualite_ocr = st.select_slider(
        "Choisissez la qualité",
        options=["Standard", "Bonne", "Maximale"],
        value="Bonne",
        help="Standard = lecture rapide | Bonne = recommandé | Maximale = pour images de mauvaise qualité"
    )
    
    st.info("""
    💡 **Aide au choix :**
    - **Standard** : Pour photos nettes de bonne qualité
    - **Bonne** : Recommandé pour la plupart des cas
    - **Maximale** : Si votre photo est floue ou mal éclairée
    """)
    
    st.markdown("---")
    st.subheader("🎨 Couleurs - Document complet")
    
    col_voyelles = st.color_picker("Voyelles", "#FF0000")
    col_consonnes = st.color_picker("Consonnes", "#0000FF")
    col_graphemes = st.color_picker("Graphèmes complexes", "#008000")
    col_muettes = st.color_picker("Lettres muettes", "#808080")
    col_mots_outils = st.color_picker("Mots-outils", "#8B4513")
    
    couleurs_config = {
        'voyelles': col_voyelles,
        'consonnes': col_consonnes,
        'graphemes': col_graphemes,
        'muettes': col_muettes,
        'mots_outils': col_mots_outils
    }
    
    activer_muettes = st.checkbox("Détecter les lettres muettes", value=True)
    
    st.markdown("---")
    st.subheader("📝 Mots-outils")
    
    manuel_choisi = st.selectbox("Choisir une liste prédéfinie", list(LISTES_MANUELS.keys()))
    
    mots_outils_base = LISTES_MANUELS[manuel_choisi].copy()
    
    if manuel_choisi == 'Ma liste perso':
        st.info("💡 Vous pouvez créer votre propre liste ci-dessous")
    
    mots_perso = st.text_area(
        "Ajouter/modifier des mots (séparés par des virgules)",
        value=", ".join(mots_outils_base) if manuel_choisi == 'Ma liste perso' else "",
        placeholder="Exemple: car, mais, donc, or..."
    )
    
    mots_outils_finaux = mots_outils_base.copy()
    if mots_perso:
        mots_ajout = [m.strip() for m in mots_perso.split(',') if m.strip()]
        mots_outils_finaux.extend(mots_ajout)
    
    mots_outils_finaux = list(set(mots_outils_finaux))

# Zone principale
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Upload de l'image")
    uploaded_file = st.file_uploader(
        "Choisissez une image (PNG, JPG, JPEG)",
        type=['png', 'jpg', 'jpeg']
    )
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Image uploadée", use_column_width=True)

with col2:
    st.header("⚙️ Options de génération")
    
    casse = st.radio("📝 Casse du texte", ['Minuscules', 'Majuscules'], horizontal=True)
    
    st.markdown("---")
    st.subheader("📄 Documents à générer")
    st.markdown("*Activez les documents que vous souhaitez créer*")
    
    # Option 1 : Texte simple
    creer_texte_simple = st.toggle("📃 Texte simple (sans couleur)", value=False,
                                    help="Génère un document Word avec le texte extrait, sans code couleur")
    
    # Option 2 : Texte avec code couleur complet
    creer_texte_colore = st.toggle("🎨 Texte avec code couleur complet", value=True,
                                    help="Génère un document avec voyelles, consonnes, graphèmes, etc. en couleur")
    
    # Option 3 : Graphèmes ciblés
    creer_doc_cible = st.toggle("🎯 Graphèmes ciblés", value=False,
                                 help="Génère un document avec uniquement certains graphèmes en couleur")
    
    if creer_doc_cible:
        st.success("✨ Un document avec graphèmes ciblés sera créé !")
        graphemes_input = st.text_input(
            "🔤 Graphèmes à cibler (séparés par des virgules)",
            placeholder="Exemple: ou, ch, ain",
            help="Ces graphèmes seront colorés, le reste du texte sera en noir"
        )
        couleur_cible = st.color_picker("🎨 Couleur des graphèmes ciblés", "#069494")

st.markdown("---")

if st.button("🚀 GÉNÉRER LES DOCUMENTS", type="primary", use_container_width=True):
    if not uploaded_file:
        st.error("❌ Veuillez uploader une image d'abord !")
    else:
        with st.spinner("⏳ Extraction et traitement en cours..."):
            try:
                # Prétraiter l'image selon la qualité choisie
                image_pretrait = pretraiter_image(image, qualite_ocr)
                
                # Configuration OCR selon la qualité
                if qualite_ocr == "Standard":
                    config_ocr = '--psm 6 -l fra'
                elif qualite_ocr == "Bonne":
                    config_ocr = '--psm 6 -l fra'
                else:  # Maximale
                    config_ocr = '--psm 3 -l fra'
                
                # Extraction du texte
                texte_brut = pytesseract.image_to_string(image_pretrait, config=config_ocr)
                
                texte_brut = remplacer_separateurs(texte_brut)
                texte_brut = ajouter_espaces_entre_mots(texte_brut)
                
                if casse == 'Minuscules':
                    texte_final = texte_brut.lower()
                    texte_final = mettre_majuscules_phrases(texte_final)
                else:
                    texte_final = texte_brut.upper()
                
                st.success("✅ Texte extrait avec succès !")
                
                with st.expander("👀 Voir le texte extrait"):
                    st.text(texte_brut)
                
                # Document 1 : Texte simple (optionnel)
                if creer_texte_simple:
                    st.info("📄 Génération du document texte simple...")
                    
                    texte_simple = [(char, None) for char in texte_final]
                    doc_simple = creer_word(texte_simple, police, {}, casse, taille_pt=taille_police)
                    
                    buffer_simple = io.BytesIO()
                    doc_simple.save(buffer_simple)
                    buffer_simple.seek(0)
                    
                    st.download_button(
                        label="📥 Télécharger - Texte simple",
                        data=buffer_simple,
                        file_name=f"texte_simple_{casse.lower()}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                # Document 2 : Code complet (optionnel)
                if creer_texte_colore:
                    st.info("📄 Génération du document avec code couleur complet...")
                    texte_colorie = colorier_texte(texte_final, mots_outils_finaux, couleurs_config, activer_muettes)
                
                    # Prévisualisation
                    st.subheader("👁️ Aperçu du document coloré")
                    preview_html = generer_preview_html(texte_colorie, couleurs_config, police)
                    st.markdown(preview_html, unsafe_allow_html=True)
                    
                    doc_complet = creer_word(texte_colorie, police, couleurs_config, casse, taille_pt=taille_police)
                    
                    buffer1 = io.BytesIO()
                    doc_complet.save(buffer1)
                    buffer1.seek(0)
                    
                    st.download_button(
                        label="📥 Télécharger - Code couleur complet",
                        data=buffer1,
                        file_name=f"texte_code_complet_{casse.lower()}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                # Document 3 : Graphèmes ciblés (optionnel)
                if creer_doc_cible and graphemes_input:
                    graphemes_cibles = [g.strip() for g in graphemes_input.split(',') if g.strip()]
                    
                    if graphemes_cibles:
                        st.info(f"📄 Génération du document avec graphèmes ciblés : {', '.join(graphemes_cibles)}")
                        
                        couleurs_cible = {'cible': couleur_cible, 'black': '#000000'}
                        texte_cible = colorier_graphemes_cibles(texte_final, graphemes_cibles, couleur_cible)
                        
                        # Prévisualisation graphèmes ciblés
                        st.subheader("👁️ Aperçu graphèmes ciblés")
                        preview_html_cible = generer_preview_html(texte_cible, couleurs_cible, police)
                        st.markdown(preview_html_cible, unsafe_allow_html=True)
                        
                        doc_cible = creer_word(texte_cible, police, couleurs_cible, casse, taille_pt=taille_police)
                        
                        buffer2 = io.BytesIO()
                        doc_cible.save(buffer2)
                        buffer2.seek(0)
                        
                        st.download_button(
                            label=f"📥 Télécharger - Graphèmes ciblés",
                            data=buffer2,
                            file_name=f"texte_graphemes_cibles_{casse.lower()}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                
                # Message de succès global
                if creer_texte_simple or creer_texte_colore or creer_doc_cible:
                    st.success("🎉 Tous les documents ont été générés avec succès !")
                else:
                    st.warning("⚠️ Aucun document sélectionné. Activez au moins une option !")
                
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")

st.markdown("---")
st.markdown("*Créé avec ❤️ pour aider les enseignants et les élèves - Projet open source*")
