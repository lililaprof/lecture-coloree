import streamlit as st
from PIL import Image
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

def creer_word(texte_traite, police, couleurs_config, casse):
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
        run.font.size = Pt(25)
        run.font.name = police
        if couleur and couleur in couleurs_rgb:
            run.font.color.rgb = couleurs_rgb[couleur]
    
    return doc

# Interface Streamlit
st.title("📚 Lecture Colorée pour CP")
st.markdown("**Application d'adaptation de textes pour enfants dys et TSA**")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Paramètres")
    
    police = st.selectbox("📝 Police d'écriture", POLICES, index=0)
    
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
    
    casse = st.radio("Casse du document", ['Minuscules', 'Majuscules'], horizontal=True)
    
    st.markdown("---")
    
    creer_doc_cible = st.checkbox("Créer un document avec graphèmes ciblés", value=False)
    
    if creer_doc_cible:
        graphemes_input = st.text_input(
            "Graphèmes à cibler (séparés par des virgules)",
            placeholder="Exemple: ou, ch, ain"
        )
        couleur_cible = st.color_picker("Couleur des graphèmes ciblés", "#069494")

st.markdown("---")

if st.button("🚀 GÉNÉRER LES DOCUMENTS", type="primary", use_container_width=True):
    if not uploaded_file:
        st.error("❌ Veuillez uploader une image d'abord !")
    else:
        with st.spinner("⏳ Extraction et traitement en cours..."):
            try:
                texte_brut = pytesseract.image_to_string(image, lang='fra')
                
                texte_brut = remplacer_separateurs(texte_brut)
                texte_brut = ajouter_espaces_entre_mots(texte_brut)
                
                if casse == 'Minuscules':
                    texte_final = texte_brut.lower()
                else:
                    texte_final = texte_brut.upper()
                
                st.success("✅ Texte extrait avec succès !")
                
                with st.expander("👀 Voir le texte extrait"):
                    st.text(texte_brut)
                
                # Document 1 : Code complet
                st.info("📄 Génération du document avec code couleur complet...")
                texte_colorie = colorier_texte(texte_final, mots_outils_finaux, couleurs_config, activer_muettes)
                doc_complet = creer_word(texte_colorie, police, couleurs_config, casse)
                
                buffer1 = io.BytesIO()
                doc_complet.save(buffer1)
                buffer1.seek(0)
                
                st.success("🎉 Document généré avec succès !")
                
                st.download_button(
                    label="📥 Télécharger - Code couleur complet",
                    data=buffer1,
                    file_name=f"texte_code_complet_{casse.lower()}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
                # Document 2 : Graphèmes ciblés (optionnel)
                if creer_doc_cible and graphemes_input:
                    graphemes_cibles = [g.strip() for g in graphemes_input.split(',') if g.strip()]
                    
                    if graphemes_cibles:
                        st.info(f"📄 Génération du document avec graphèmes ciblés : {', '.join(graphemes_cibles)}")
                        
                        couleurs_cible = {'cible': couleur_cible, 'black': '#000000'}
                        texte_cible = colorier_graphemes_cibles(texte_final, graphemes_cibles, couleur_cible)
                        doc_cible = creer_word(texte_cible, police, couleurs_cible, casse)
                        
                        buffer2 = io.BytesIO()
                        doc_cible.save(buffer2)
                        buffer2.seek(0)
                        
                        st.download_button(
                            label=f"📥 Télécharger - Graphèmes ciblés",
                            data=buffer2,
                            file_name=f"texte_graphemes_cibles_{casse.lower()}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")

st.markdown("---")
st.markdown("*Créé avec ❤️ pour aider les enseignants et les élèves - Projet open source*")
