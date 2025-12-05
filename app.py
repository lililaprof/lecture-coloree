import streamlit as st
import pytesseract
from PIL import Image
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

# Liste de mots-outils de base
MOTS_OUTILS_BASE = [
    'est', 'et', 'un', 'une', 'le', 'la', 'les', 'de', 'du', 'des',
    'dans', 'sur', 'avec', 'pour', 'par', 'il', 'elle', 'ils', 'elles',
    'ont', 'sont', 'a', 'à', 'au', 'aux', 'ce', 'cette', 'ces',
    'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses'
]

# Polices disponibles
POLICES = [
    'OpenDyslexic',
    'Quicksand Book',
    'Belle Allure',
    'Arial',
    'Comic Sans MS',
    'Helvetica'
]

def hex_to_rgb(hex_color):
    """Convertit une couleur hex en RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

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

def colorier_texte(texte, mots_outils, couleurs_config):
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
        
        if detecter_lettre_muette(mot_complet, position_dans_mot):
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

def colorier_grapheme_unique(texte, grapheme_cible):
    resultat_word = []
    grapheme_lower = grapheme_cible.lower()
    
    i = 0
    while i < len(texte):
        if texte[i:i+len(grapheme_cible)].lower() == grapheme_lower:
            segment = texte[i:i+len(grapheme_cible)]
            for c in segment:
                resultat_word.append((c, 'teal'))
            i += len(grapheme_cible)
        else:
            resultat_word.append((texte[i], 'black'))
            i += 1
    
    return resultat_word

def creer_word(texte_minuscule, texte_majuscule, police, couleurs_config, type_doc):
    doc = Document()
    
    # Convertir les couleurs hex en RGB
    couleurs_rgb = {}
    for key, hex_val in couleurs_config.items():
        r, g, b = hex_to_rgb(hex_val)
        couleurs_rgb[key] = RGBColor(r, g, b)
    
    # Ajouter couleurs fixes
    couleurs_rgb['teal'] = RGBColor(6, 148, 148)
    couleurs_rgb['black'] = RGBColor(0, 0, 0)
    
    if type_doc == 'complet':
        titre_page1 = 'CAPITALES - Code couleur complet'
        titre_page2 = 'minuscules - Code couleur complet'
    else:
        titre_page1 = 'CAPITALES - Graphème ciblé'
        titre_page2 = 'minuscules - Graphème ciblé'
    
    # PAGE 1 : CAPITALES
    titre_maj = doc.add_heading(titre_page1, level=1)
    titre_maj.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    para_maj = doc.add_paragraph()
    for char, couleur in texte_majuscule:
        run = para_maj.add_run(char)
        run.font.size = Pt(25)
        run.font.name = police
        if couleur and couleur in couleurs_rgb:
            run.font.color.rgb = couleurs_rgb[couleur]
    
    doc.add_page_break()
    
    # PAGE 2 : minuscules
    titre_min = doc.add_heading(titre_page2, level=1)
    titre_min.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    para_min = doc.add_paragraph()
    for char, couleur in texte_minuscule:
        run = para_min.add_run(char)
        run.font.size = Pt(25)
        run.font.name = police
        if couleur and couleur in couleurs_rgb:
            run.font.color.rgb = couleurs_rgb[couleur]
    
    return doc

# Interface Streamlit
st.title("📚 Lecture Colorée pour CP")
st.markdown("**Application d'adaptation de textes pour enfants dys et TSA**")
st.markdown("---")

# Sidebar pour les paramètres
with st.sidebar:
    st.header("⚙️ Paramètres")
    
    # Choix de la police
    police = st.selectbox("📝 Police d'écriture", POLICES, index=1)
    
    st.markdown("---")
    
    # Personnalisation des couleurs
    st.subheader("🎨 Personnaliser les couleurs")
    
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
    
    st.markdown("---")
    
    # Mots-outils
    st.subheader("📝 Mots-outils")
    
    utiliser_base = st.checkbox("Utiliser la liste de base", value=True)
    
    if utiliser_base:
        with st.expander("Voir la liste de base"):
            st.write(", ".join(MOTS_OUTILS_BASE))
    
    mots_perso = st.text_area(
        "Ajouter vos mots (séparés par des virgules)",
        placeholder="Exemple: car, mais, donc, or..."
    )
    
    # Construire la liste finale
    mots_outils_finaux = []
    if utiliser_base:
        mots_outils_finaux.extend(MOTS_OUTILS_BASE)
    if mots_perso:
        mots_ajout = [m.strip() for m in mots_perso.split(',') if m.strip()]
        mots_outils_finaux.extend(mots_ajout)

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
    st.header("🎯 Graphème ciblé")
    grapheme = st.text_input(
        "Pour le document avec un seul graphème coloré",
        placeholder="Exemple: ou, ch, ain..."
    )
    
    st.info("💡 Ce graphème sera coloré en bleu canard (RGB: 6, 148, 148) dans le second document")

st.markdown("---")

# Bouton de génération
if st.button("🚀 GÉNÉRER LES DOCUMENTS", type="primary", use_container_width=True):
    if not uploaded_file:
        st.error("❌ Veuillez uploader une image d'abord !")
    elif not grapheme:
        st.error("❌ Veuillez indiquer un graphème ciblé !")
    else:
        with st.spinner("⏳ Extraction et traitement en cours..."):
            try:
                # Extraire le texte
                texte_brut = pytesseract.image_to_string(image, lang='eng')
                
                # Traiter le texte
                texte_brut = remplacer_separateurs(texte_brut)
                texte_minuscule = texte_brut.lower()
                texte_majuscule = texte_brut.upper()
                texte_minuscule = ajouter_espaces_entre_mots(texte_minuscule)
                texte_majuscule = ajouter_espaces_entre_mots(texte_majuscule)
                
                st.success("✅ Texte extrait avec succès !")
                
                with st.expander("👀 Voir le texte extrait"):
                    st.text(texte_brut)
                
                # Document 1 : Code complet
                st.info("📄 Génération du document avec code couleur complet...")
                texte_min_complet = colorier_texte(texte_minuscule, mots_outils_finaux, couleurs_config)
                texte_maj_complet = colorier_texte(texte_majuscule, mots_outils_finaux, couleurs_config)
                doc_complet = creer_word(texte_min_complet, texte_maj_complet, police, couleurs_config, 'complet')
                
                buffer1 = io.BytesIO()
                doc_complet.save(buffer1)
                buffer1.seek(0)
                
                # Document 2 : Graphème ciblé
                st.info(f"📄 Génération du document avec le graphème '{grapheme}'...")
                texte_min_grapheme = colorier_grapheme_unique(texte_minuscule, grapheme)
                texte_maj_grapheme = colorier_grapheme_unique(texte_majuscule, grapheme)
                doc_grapheme = creer_word(texte_min_grapheme, texte_maj_grapheme, police, {}, 'grapheme')
                
                buffer2 = io.BytesIO()
                doc_grapheme.save(buffer2)
                buffer2.seek(0)
                
                st.success("🎉 Documents générés avec succès !")
                
                # Téléchargements
                col_dl1, col_dl2 = st.columns(2)
                
                with col_dl1:
                    st.download_button(
                        label="📥 Télécharger - Code complet",
                        data=buffer1,
                        file_name="texte_code_complet.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                with col_dl2:
                    st.download_button(
                        label=f"📥 Télécharger - Graphème '{grapheme}'",
                        data=buffer2,
                        file_name=f"texte_grapheme_{grapheme}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")

st.markdown("---")
st.markdown("*Créé avec ❤️ pour aider les enseignants et les élèves - Projet open source*")
