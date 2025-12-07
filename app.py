# streamlit_app.py
import streamlit as st
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import tempfile
import typing
import re

# ---------- Paramètres / constantes de base (ta base conservée + compléments) ----------
st.set_page_config(page_title="Lecture Colorée CP — Améliorée", page_icon="📚", layout="wide")

# Sons / graphèmes (TA BASE)
sons_complexes = [
    'ouil', 'euil', 'aille', 'eille', 'ille', 'ouille',
    'ain', 'aim', 'ein', 'eim', 'oin', 'ien', 'eau', 'oeu',
    'ch', 'ph', 'gn', 'ill', 'ail', 'eil', 'ou', 'au', 'eu', 'oi', 'oy',
    'ai', 'ei'
]

sons_nasals = ['an', 'am', 'en', 'em', 'on', 'om', 'in', 'im', 'un', 'um', 'yn', 'ym']
voyelles = 'aeiouyàâäéèêëïîôùûüÿæœAEIOUYÀÂÄÉÈÊËÏÎÔÙÛÜŸÆŒ'
lettres_muettes_fin = ['s', 't', 'd', 'p', 'x', 'z']

# Listes par manuels (ta base)
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

# ---------- Utilitaires ----------
def hex_to_rgb_tuple(hex_color: str):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def hex_to_rgb(hex_color):
    r, g, b = hex_to_rgb_tuple(hex_color)
    return RGBColor(r, g, b)

def detecter_lettre_muette(mot: str, position: int):
    """
    Amélioration de la détection :
    - 'ent' final
    - 'e' final muet si précédé d'une consonne (heuristique)
    - h initial muet (heuristique)
    """
    mot_low = mot.lower()
    if position == len(mot) - 1:
        lettre = mot[position].lower()
        if lettre in lettres_muettes_fin:
            return True
        if len(mot) >= 3 and mot_low.endswith('ent'):
            return True
        # heuristique e muet final (par ex. "porte" -> e muet)
        if lettre == 'e' and len(mot) >= 2 and mot[-2].lower() not in voyelles:
            return True
    if position == 0 and mot[position].lower() == 'h':
        # On marque le 'h' initial comme muet ; si tu veux gérer l'aspiré, ajouter une liste
        return True
    return False

def extraire_mot_complet(texte: str, position: int):
    debut = position
    while debut > 0 and texte[debut - 1].isalpha():
        debut -= 1
    fin = position
    while fin < len(texte) and texte[fin].isalpha():
        fin += 1
    return texte[debut:fin], debut, fin

def est_son_nasal_valide(texte: str, position: int, son: str):
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

def remplacer_separateurs(texte: str):
    # garde ta logique d'origine mais légèrement plus robuste
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

def ajouter_espaces_entre_mots(texte: str, double_space: bool=True):
    # optionnelle : double espace entre mots
    if not double_space:
        return texte
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

# Ta fonction principale de coloriage (gardée mais légèrement nettoyée)
def colorier_texte(texte: str, mots_outils: typing.List[str], couleurs_config: dict, activer_muettes=True):
    resultat_word = []
    # Normaliser listes
    mots_outils_lower = [mot.lower() for mot in mots_outils]
    mots_outils_upper = [mot.upper() for mot in mots_outils]
    tous_mots_outils = set(mots_outils + mots_outils_lower + mots_outils_upper)
    
    i = 0
    L = len(texte)
    while i < L:
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
        # graphèmes complexes d'abord
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

def colorier_graphemes_cibles(texte: str, graphemes_cibles: typing.List[str], couleur_cible: str):
    resultat_word = []
    graphemes_lower = [g.lower() for g in graphemes_cibles]
    i = 0
    L = len(texte)
    while i < L:
        trouve = False
        for grapheme in sorted(graphemes_lower, key=lambda x: -len(x)):
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

def creer_word(texte_traite: typing.List[typing.Tuple[str, typing.Optional[str]]],
               police: str, couleurs_config: dict, casse: str, taille_pt: int=25):
    doc = Document()
    # Préparer couleurs en RGB
    couleurs_rgb = {}
    for key, hex_val in couleurs_config.items():
        try:
            couleurs_rgb[key] = hex_to_rgb(hex_val)
        except Exception:
            # valeur invalide -> noir par défaut
            couleurs_rgb[key] = RGBColor(0, 0, 0)
    
    titre = f'{casse.upper()}'
    titre_para = doc.add_heading(titre, level=1)
    titre_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    for char, couleur in texte_traite:
        run = para.add_run(char)
        run.font.size = Pt(taille_pt)
        # set the font name (Word will use it if available)
        run.font.name = police
        if couleur and couleur in couleurs_rgb:
            run.font.color.rgb = couleurs_rgb[couleur]
    
    return doc

# ---------- Prétraitements OCR ----------
def preprocess_image_for_ocr(pil_img: Image.Image, resize_width: int = 1600, grayscale=True, threshold=False):
    """
    - resize pour améliorer OCR
    - conversion en niveaux de gris
    - optional threshold (binarisation simple)
    - léger sharpen/blurring adaptatif possible
    """
    img = pil_img.copy()
    # convertir en RGB si nécessaire
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGB")
    # resize si trop petit
    w, h = img.size
    if w < resize_width:
        ratio = resize_width / w
        new_size = (resize_width, int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    if grayscale:
        img = ImageOps.grayscale(img)
    # appliquer un filtre léger pour réduire bruit
    img = img.filter(ImageFilter.MedianFilter(size=3))
    if threshold:
        # binariser : heuristique simple
        img = img.point(lambda p: 255 if p > 180 else 0)
    return img

# ---------- UI Streamlit (interface) ----------
st.title("📚 Lecture Colorée pour CP — Version améliorée")
st.markdown("**Application d'adaptation de textes pour enfants dys et TSA** — amélioration conservant ta logique phonologique.")

# Info rapide
with st.expander("ℹ️ Ce que fait l'app (résumé)"):
    st.write("""
    - OCR (pytesseract) avec pré-traitement pour améliorer l'extraction.
    - Prévisualisation HTML du texte coloré avant export.
    - Export DOCX (taille police paramétrable). Option : tentative de conversion en PDF si docx2pdf est installé.
    - Possibilité d'uploader une police (ex : OpenDyslexic) pour indiquer son nom dans le .docx.
    - Tous les réglages de ta version d'origine sont conservés.
    """)

st.markdown("---")

# Sidebar paramétrage
with st.sidebar:
    st.header("⚙️ Paramètres globaux")
    police = st.selectbox("📝 Police (nom affiché dans le .docx)", POLICES, index=0)
    police_upload = st.file_uploader("⚠️ (Optionnel) Upload police .ttf (OpenDyslexic)", type=['ttf', 'otf'])
    taille_police = st.slider("Taille police (pt) pour le Word", min_value=12, max_value=48, value=25)
    double_space = st.checkbox("Double espace entre mots (pour aider la lecture)", value=True)
    
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
    st.markdown("---")
    st.subheader("📝 Mots-outils")
    manuel_choisi = st.selectbox("Choisir une liste prédéfinie", list(LISTES_MANUELS.keys()))
    mots_outils_base = LISTES_MANUELS[manuel_choisi].copy()
    if manuel_choisi == 'Ma liste perso':
        st.info("Crée ta propre liste ci-dessous")
    mots_perso = st.text_area("Ajouter/modifier des mots (séparés par des virgules)",
                              value=", ".join(mots_outils_base) if manuel_choisi == 'Ma liste perso' else "",
                              placeholder="Exemple: car, mais, donc, or...")
    mots_outils_finaux = mots_outils_base.copy()
    if mots_perso:
        mots_ajout = [m.strip() for m in mots_perso.split(',') if m.strip()]
        mots_outils_finaux.extend(mots_ajout)
    mots_outils_finaux = list(dict.fromkeys(mots_outils_finaux))  # garder ordre, enlever doublons
    
    st.markdown("---")
    st.subheader("🔎 OCR / Pré-traitement")
    psm_choice = st.selectbox("Tesseract page segmentation mode (psm)", ['3 (auto)', '6 (single block)', '11 (sparse text)'], index=1)
    psm_value = int(psm_choice.split()[0])
    do_threshold = st.checkbox("Appliquer binarisation (threshold) avant OCR", value=False)
    resize_width = st.slider("Largeur cible (px) pour redimensionnement OCR", min_value=800, max_value=3000, value=1600, step=100)

# Main columns
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Upload / Image")
    uploaded_file = st.file_uploader("Image (PNG/JPG/JPEG)", type=['png', 'jpg', 'jpeg'])
    option_demo = st.checkbox("Utiliser image démo (exemple)", value=False)
    if option_demo and not uploaded_file:
        # essayer de charger une image locale si tu veux ; ici on laisse vide si aucun fichier
        st.info("Active une image de démonstration manuellement.")
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Image uploadée", use_column_width=True)

with col2:
    st.header("⚙️ Options de génération")
    casse = st.radio("Casse du document", ['Minuscules', 'Majuscules'], horizontal=True)
    creer_doc_cible = st.checkbox("Créer document avec graphèmes ciblés", value=False)
    graphemes_input = ""
    couleur_cible = "#069494"
    if creer_doc_cible:
        graphemes_input = st.text_input("Graphèmes à cibler (séparés par des virgules)", placeholder="ou, ch, ain")
        couleur_cible = st.color_picker("Couleur des graphèmes ciblés", "#069494")
    st.markdown("---")
    st.markdown("Prévisualisation :")
    preview_scale = st.slider("Taille de prévisualisation (zoom)", min_value=80, max_value=200, value=120)

st.markdown("---")

# Génération
if st.button("🚀 GÉNÉRER LES DOCUMENTS", type="primary", use_container_width=True):
    if not uploaded_file:
        st.error("❌ Veuillez uploader une image d'abord !")
    else:
        with st.spinner("Extraction et traitement en cours..."):
            try:
                # Prétraitement
                pil_img = Image.open(uploaded_file)
                pil_pre = preprocess_image_for_ocr(pil_img, resize_width=resize_width, grayscale=True, threshold=do_threshold)
                
                # Option : montrer image prétraitée
                st.subheader("🔎 Image prétraitée pour OCR")
                st.image(pil_pre, use_column_width=True)
                
                # OCR
                tesseract_config = f'--psm {psm_value} -l fra'
                texte_brut = pytesseract.image_to_string(pil_pre, config=tesseract_config)
                # nettoyage minimal
                texte_brut = texte_brut.replace('\r', '\n')
                texte_brut = re.sub(r'\n{3,}', '\n\n', texte_brut)
                
                # Post traitements (ta logique)
                texte_brut = remplacer_separateurs(texte_brut)
                texte_brut = ajouter_espaces_entre_mots(texte_brut, double_space=double_space)
                
                if casse == 'Minuscules':
                    texte_final = texte_brut.lower()
                else:
                    texte_final = texte_brut.upper()
                
                st.success("✅ Texte extrait avec succès !")
                with st.expander("👀 Voir le texte extrait (brut)"):
                    st.text_area("Texte brut OCR", value=texte_brut, height=200)
                
                # Colorisation complète (ton algorithme)
                texte_colorie = colorier_texte(texte_final, mots_outils_finaux, couleurs_config, activer_muettes=True)
                
                # Prévisualisation HTML
                def render_html_from_texte(texte_trait, couleurs_config_local, preview_font='Arial', taille=20):
                    # map couleur keys to hex
                    mapping = {
                        'voyelles': couleurs_config_local.get('voyelles', '#FF0000'),
                        'consonnes': couleurs_config_local.get('consonnes', '#0000FF'),
                        'graphemes': couleurs_config_local.get('graphemes', '#008000'),
                        'muettes': couleurs_config_local.get('muettes', '#808080'),
                        'mots_outils': couleurs_config_local.get('mots_outils', '#8B4513'),
                        None: '#000000'
                    }
                    html = f"<div style='font-family:{preview_font}; font-size:{taille}px; line-height:1.4;'>"
                    for ch, cl in texte_trait:
                        color = mapping.get(cl, '#000000')
                        safe = ch.replace(' ', '&nbsp;').replace('\n', '<br/>')
                        # afficher les caractères spéciaux sans altération
                        html += f"<span style='color:{color};'>{safe}</span>"
                    html += "</div>"
                    return html
                
                preview_font_name = police
                if police_upload:
                    # enregistrer la police temporairement - note : ne force pas le rendu dans le navigateur
                    ttf_bytes = police_upload.read()
                    temp_dir = tempfile.mkdtemp()
                    font_path = os.path.join(temp_dir, police_upload.name)
                    with open(font_path, 'wb') as f:
                        f.write(ttf_bytes)
                    st.info(f"Police uploadée : {police_upload.name} (Word utilisera le nom de police si installée sur la machine destinataire).")
                    # navigateur ne chargera pas la police locale automatiquement dans st.markdown HTML. C'est surtout pour stockage.
                
                html_preview = render_html_from_texte(texte_colorie, couleurs_config, preview_font=preview_font_name, taille=int(taille_police*0.7))
                st.subheader("🔤 Prévisualisation du texte coloré")
                st.markdown(html_preview, unsafe_allow_html=True)
                
                # Création .docx complet
                st.info("📄 Génération du document .docx (code couleur complet)...")
                doc_complet = creer_word(texte_colorie, police, couleurs_config, casse, taille_pt=taille_police)
                buffer1 = io.BytesIO()
                doc_complet.save(buffer1)
                buffer1.seek(0)
                st.success("🎉 Document .docx généré !")
                st.download_button(
                    label="📥 Télécharger - Code couleur complet (.docx)",
                    data=buffer1,
                    file_name=f"texte_code_complet_{casse.lower()}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
                # tentative conversion PDF (optionnelle)
                try:
                    from docx2pdf import convert as docx2pdf_convert
                    # sauver temporairement
                    tmp_docx = os.path.join(tempfile.gettempdir(), f"tmp_texte_{os.getpid()}.docx")
                    with open(tmp_docx, 'wb') as f:
                        f.write(buffer1.getvalue())
                    tmp_pdf = tmp_docx.replace('.docx', '.pdf')
                    docx2pdf_convert(tmp_docx, tmp_pdf)
                    with open(tmp_pdf, 'rb') as pdf_f:
                        pdf_bytes = pdf_f.read()
                    st.success("✅ Conversion PDF réussie (docx2pdf).")
                    st.download_button(
                        label="📥 Télécharger - Code couleur (PDF)",
                        data=pdf_bytes,
                        file_name=f"texte_code_complet_{casse.lower()}.pdf",
                        mime="application/pdf"
                    )
                except Exception:
                    # conversion non disponible : on ne bloque pas
                    st.info("ℹ️ Conversion PDF automatique non disponible (docx2pdf non installé ou environnement non compatible). Tu peux convertir le .docx en PDF sur ta machine si tu veux préserver la police.")
                
                # Document graphèmes ciblés
                if creer_doc_cible and graphemes_input:
                    graphemes_cibles = [g.strip() for g in graphemes_input.split(',') if g.strip()]
                    if graphemes_cibles:
                        st.info(f"📄 Génération du document graphèmes ciblés : {', '.join(graphemes_cibles)}")
                        texte_cible = colorier_graphemes_cibles(texte_final, graphemes_cibles, couleur_cible)
                        couleurs_cible = {'cible': couleur_cible, 'black': '#000000'}
                        doc_cible = creer_word(texte_cible, police, couleurs_cible, casse, taille_pt=taille_police)
                        buffer2 = io.BytesIO()
                        doc_cible.save(buffer2)
                        buffer2.seek(0)
                        st.download_button(
                            label=f"📥 Télécharger - Graphèmes ciblés (.docx)",
                            data=buffer2,
                            file_name=f"texte_graphemes_cibles_{casse.lower()}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")
                import traceback
                st.text(traceback.format_exc())
