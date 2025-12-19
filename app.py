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
    img = ImageOps.grayscale(img)
    
    if qualite_ocr == "Maximale":
        img = img.filter(ImageFilter.MedianFilter(size=3))
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

def colorier_texte_simple_options(texte, mots_outils, col_graphemes, col_mots_outils, 
                                   activer_graphemes=False, activer_mots_outils=False):
    """Colorie uniquement graphèmes et/ou mots-outils selon options"""
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
        
        if activer_mots_outils and mot_complet in tous_mots_outils:
            for c in mot_complet:
                resultat_word.append((c, 'mots_outils'))
            i = fin_mot
            continue
        
        trouve = False
        if activer_graphemes:
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
            resultat_word.append((char, None))
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
    
    html = f"<div style='font-family:{police}; font-size:18px; line-height:1.8; padding:15px; background:#f9f9f9; border-radius:10px;'>"
    for char, couleur in texte_traite:
        color = mapping.get(couleur, '#000000')
        safe_char = char.replace(' ', '&nbsp;').replace('\n', '<br/>')
        html += f"<span style='color:{color};'>{safe_char}</span>"
    html += "</div>"
    return html

# Interface Streamlit
st.title("📚 Lecture Colorée pour CP")
st.markdown("*Pour les enseignants et les parents*")

# Description
st.info("""
📖 **Comment ça marche ?**
1. Uploadez une photo/scan OU tapez/collez votre texte
2. Choisissez les documents à générer (texte simple, coloré, graphèmes ciblés)
3. Personnalisez les options pour chaque type de document
4. Téléchargez vos documents Word !

🎨 **Code couleur :** 🔴 Voyelles • 🔵 Consonnes • 🟢 Graphèmes complexes • ⚫ Lettres muettes • 🟤 Mots-outils
""")

with st.expander("ℹ️ En savoir plus"):
    st.markdown("""
    ### Fonctionnalités
    - ✅ OCR (lecture d'image) ou saisie manuelle
    - ✅ Code couleur basé sur la phonétique
    - ✅ Listes de mots-outils par manuel
    - ✅ 3 types de documents au choix
    - ✅ Prévisualisation avant téléchargement
    
    *Application gratuite et open source* 💚
    """)

st.markdown("---")

# Sidebar - Paramètres généraux
with st.sidebar:
    st.header("⚙️ Paramètres généraux")
    
    police = st.selectbox("📝 Police", POLICES, index=0)
    taille_police = st.slider("📏 Taille (pt)", 12, 40, 25, 1)
    casse = st.radio("📝 Casse", ['Minuscules', 'Majuscules'], horizontal=True)
    
    st.markdown("---")
    st.subheader("🔍 Qualité OCR")
    
    qualite_ocr = st.select_slider(
        "Qualité",
        ["Standard", "Bonne", "Maximale"],
        "Bonne",
        help="Standard = photo nette | Bonne = recommandé | Maximale = photo floue"
    )

# Zone input (image ou texte)
st.header("📥 Votre texte")

tab1, tab2 = st.tabs(["📤 Upload d'image", "✍️ Saisie manuelle"])

texte_source = None
source_type = None

with tab1:
    uploaded_file = st.file_uploader("Image (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Image uploadée", use_column_width=True)
        source_type = "image"

with tab2:
    texte_saisi = st.text_area(
        "Tapez ou collez votre texte ici",
        height=200,
        placeholder="Exemple: Le chat mange une souris. Il est content."
    )
    if texte_saisi:
        source_type = "texte"
        texte_source = texte_saisi

st.markdown("---")

# Options de génération empilées verticalement
st.header("📄 Documents à générer")
st.markdown("*Activez les documents que vous souhaitez créer*")

# OPTION 1 : Texte coloré (en premier maintenant)
st.markdown("### 🎨 Texte avec code couleur complet")
creer_texte_colore = st.toggle("Activer le document avec code couleur complet", key="toggle_colore", value=True)

if creer_texte_colore:
    st.info("📖 Code couleur pour aider à la lecture : voyelles, consonnes, graphèmes complexes, lettres muettes et mots-outils sont colorés différemment.")
    
    st.markdown("**Personnalisation des couleurs :**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        col_voyelles = st.color_picker("🔴 Voyelles", "#FF0000", key="col_voy")
        col_consonnes = st.color_picker("🔵 Consonnes", "#0000FF", key="col_cons")
    with col2:
        col_graphemes = st.color_picker("🟢 Graphèmes complexes", "#008000", key="col_graph")
        col_muettes = st.color_picker("⚫ Lettres muettes", "#808080", key="col_muet")
    with col3:
        col_mots_outils = st.color_picker("🟤 Mots-outils", "#8B4513", key="col_mots")
        activer_muettes = st.checkbox("Détecter lettres muettes", True, key="muettes")
    
    st.markdown("**Mots-outils :**")
    col1, col2 = st.columns([1, 2])
    with col1:
        manuel_colore = st.selectbox("Liste prédéfinie", list(LISTES_MANUELS.keys()), key="manuel_colore")
    with col2:
        mots_base_colore = LISTES_MANUELS[manuel_colore].copy()
        if manuel_colore == 'Ma liste perso':
            mots_perso_colore = st.text_area("Vos mots (séparés par des virgules)", "", key="perso_colore",
                                             placeholder="mot1, mot2, mot3...", height=60)
            if mots_perso_colore:
                mots_base_colore.extend([m.strip() for m in mots_perso_colore.split(',') if m.strip()])
    
    couleurs_config = {
        'voyelles': col_voyelles,
        'consonnes': col_consonnes,
        'graphemes': col_graphemes,
        'muettes': col_muettes,
        'mots_outils': col_mots_outils
    }

st.markdown("---")

# OPTION 2 : Texte simple
st.markdown("### 📃 Texte simple")
creer_texte_simple = st.toggle("Activer le document texte simple", key="toggle_simple", value=False)

if creer_texte_simple:
    st.info("📝 Texte en noir et blanc avec possibilité de colorer uniquement les graphèmes complexes et/ou les mots-outils.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        simple_graphemes = st.checkbox("Colorer les graphèmes complexes (ou, ch, ain...)", key="simple_graph")
        if simple_graphemes:
            col_graphemes_simple = st.color_picker("Couleur des graphèmes complexes", "#008000", key="col_graph_simple")
        else:
            col_graphemes_simple = "#008000"
    
    with col2:
        simple_mots = st.checkbox("Colorer les mots-outils", key="simple_mots")
        if simple_mots:
            col_mots_simple = st.color_picker("Couleur des mots-outils", "#8B4513", key="col_mots_simple")
            manuel_simple = st.selectbox("Liste de mots-outils", list(LISTES_MANUELS.keys()), key="manuel_simple")
            mots_base_simple = LISTES_MANUELS[manuel_simple].copy()
            
            if manuel_simple == 'Ma liste perso':
                mots_perso_simple = st.text_area("Vos mots (séparés par des virgules)", "", key="perso_simple", 
                                                  placeholder="mot1, mot2, mot3...")
                if mots_perso_simple:
                    mots_base_simple.extend([m.strip() for m in mots_perso_simple.split(',') if m.strip()])
        else:
            col_mots_simple = "#8B4513"
            mots_base_simple = []

st.markdown("---")

# OPTION 3 : Graphèmes ciblés
st.markdown("### 🎯 Document avec graphèmes ciblés")
creer_doc_cible = st.toggle("Activer le document avec graphèmes ciblés", key="toggle_cible", value=False)

if creer_doc_cible:
    st.info("🎯 Parfait pour travailler un son spécifique : seuls les graphèmes choisis sont colorés, le reste du texte est en noir.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        graphemes_input = st.text_input(
            "🔤 Graphèmes à cibler (séparés par des virgules)",
            placeholder="Exemple: ou, ch, ain",
            key="graphemes",
            help="Ces graphèmes seront colorés, le reste du texte sera en noir"
        )
    with col2:
        couleur_cible = st.color_picker("🎨 Couleur", "#069494", key="col_cible")

st.markdown("---")

# Bouton de génération
if st.button("🚀 GÉNÉRER LES DOCUMENTS", type="primary", use_container_width=True):
    if source_type is None:
        st.error("❌ Veuillez uploader une image OU saisir un texte !")
    elif not (creer_texte_simple or creer_texte_colore or creer_doc_cible):
        st.warning("⚠️ Activez au moins un type de document !")
    else:
        with st.spinner("⏳ Traitement en cours..."):
            try:
                # Extraction du texte
                if source_type == "image":
                    image_pretrait = pretraiter_image(image, qualite_ocr)
                    if qualite_ocr == "Standard":
                        config_ocr = '--psm 6 -l fra'
                    elif qualite_ocr == "Bonne":
                        config_ocr = '--psm 6 -l fra'
                    else:
                        config_ocr = '--psm 3 -l fra'
                    texte_brut = pytesseract.image_to_string(image_pretrait, config=config_ocr)
                else:
                    texte_brut = texte_source
                
                texte_brut = remplacer_separateurs(texte_brut)
                texte_brut = ajouter_espaces_entre_mots(texte_brut)
                
                if casse == 'Minuscules':
                    texte_final = texte_brut.lower()
                    texte_final = mettre_majuscules_phrases(texte_final)
                else:
                    texte_final = texte_brut.upper()
                
                st.success("✅ Texte traité !")
                
                with st.expander("👀 Texte extrait"):
                    st.text(texte_brut)
                
                # Document 1 : Texte simple
                if creer_texte_simple:
                    st.info("📄 Génération texte simple...")
                    
                    couleurs_simple = {
                        'graphemes': col_graphemes_simple,
                        'mots_outils': col_mots_simple
                    }
                    
                    texte_simple = colorier_texte_simple_options(
                        texte_final, mots_base_simple, col_graphemes_simple, col_mots_simple,
                        simple_graphemes, simple_mots
                    )
                    
                    st.subheader("👁️ Aperçu - Texte simple")
                    preview = generer_preview_html(texte_simple, couleurs_simple, police)
                    st.markdown(preview, unsafe_allow_html=True)
                    
                    doc_simple = creer_word(texte_simple, police, couleurs_simple, casse, taille_police)
                    buffer = io.BytesIO()
                    doc_simple.save(buffer)
                    buffer.seek(0)
                    
                    st.download_button(
                        "📥 Télécharger - Texte simple",
                        buffer,
                        f"texte_simple_{casse.lower()}.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                # Document 2 : Texte coloré
                if creer_texte_colore:
                    st.info("📄 Génération texte coloré...")
                    
                    texte_colorie = colorier_texte(texte_final, mots_base_colore, couleurs_config, activer_muettes)
                    
                    st.subheader("👁️ Aperçu - Texte coloré")
                    preview = generer_preview_html(texte_colorie, couleurs_config, police)
                    st.markdown(preview, unsafe_allow_html=True)
                    
                    doc_colore = creer_word(texte_colorie, police, couleurs_config, casse, taille_police)
                    buffer = io.BytesIO()
                    doc_colore.save(buffer)
                    buffer.seek(0)
                    
                    st.download_button(
                        "📥 Télécharger - Texte coloré",
                        buffer,
                        f"texte_colore_{casse.lower()}.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                # Document 3 : Graphèmes ciblés
                if creer_doc_cible and graphemes_input:
                    st.info("📄 Génération graphèmes ciblés...")
                    
                    graphemes_list = [g.strip() for g in graphemes_input.split(',') if g.strip()]
                    
                    if graphemes_list:
                        couleurs_cible = {'cible': couleur_cible, 'black': '#000000'}
                        texte_cible = colorier_graphemes_cibles(texte_final, graphemes_list, couleur_cible)
                        
                        st.subheader("👁️ Aperçu - Graphèmes ciblés")
                        preview = generer_preview_html(texte_cible, couleurs_cible, police)
                        st.markdown(preview, unsafe_allow_html=True)
                        
                        doc_cible = creer_word(texte_cible, police, couleurs_cible, casse, taille_police)
                        buffer = io.BytesIO()
                        doc_cible.save(buffer)
                        buffer.seek(0)
                        
                        st.download_button(
                            "📥 Télécharger - Graphèmes ciblés",
                            buffer,
                            f"texte_graphemes_{casse.lower()}.docx",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                
                st.success("🎉 Tous les documents générés !")
                
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")

st.markdown("---")
st.markdown("*Créé avec ❤️ pour aider les enseignants et les élèves - Projet open source*")
