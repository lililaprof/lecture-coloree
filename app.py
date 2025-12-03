import streamlit as st
import easyocr
from PIL import Image
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import json
import os
# Initialiser le lecteur OCR (une seule fois)
lecteur = easyocr.Reader(['fr'])

# Chemin du fichier JSON pour sauvegarder les listes
CHEMIN_LISTES = "listes_mots_outils.json"

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

# Palettes daltoniennes
PALETTES = {
    "Standard": {
        'voyelles': "#FF0000",  # Rouge
        'consonnes': "#0000FF",  # Bleu
        'graphemes': "#008000",  # Vert
        'muettes': "#808080",    # Gris
        'mots_outils': "#8B4513" # Marron
    },
    "Daltonien (Deutan)": {
        'voyelles': "#0072B2",  # Bleu
        'consonnes': "#D55E00",  # Orange
        'graphemes': "#009E73",  # Vert
        'muettes': "#CC79A7",    # Rose
        'mots_outils': "#E69F00" # Jaune
    },
    "Daltonien (Protan)": {
        'voyelles': "#0072B2",
        'consonnes': "#CC79A7",
        'graphemes': "#009E73",
        'muettes': "#F0E442",    # Jaune
        'mots_outils': "#E69F00"
    },
    "Daltonien (Tritan)": {
        'voyelles': "#0072B2",
        'consonnes': "#E69F00",
        'graphemes': "#56B4E9",  # Bleu clair
        'muettes': "#009E73",    # Vert
        'mots_outils': "#F0E442"
    }
}

def charger_listes():
    """Charge les listes de mots-outils depuis le fichier JSON"""
    if os.path.exists(CHEMIN_LISTES):
        with open(CHEMIN_LISTES, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Liste par défaut si le fichier n'existe pas
        return {
            "Taoki": ["le", "la", "un", "une", "je", "tu"],
            "Noisette": ["je", "tu", "il", "elle", "nous"],
            "Fil et Lulu": ["le", "la", "les", "un", "une", "des"]
        }

def sauvegarder_listes(listes):
    """Sauvegarde les listes dans le fichier JSON"""
    with open(CHEMIN_LISTES, "w", encoding="utf-8") as f:
        json.dump(listes, f, indent=4, ensure_ascii=False)

# Charger les listes au démarrage
LISTES_MANUELS = charger_listes()

def hex_to_rgb(hex_color):
    """Convertit une couleur hex en RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def detecter_lettre_muette(mot, position):
    """Détecte si une lettre est muette (en vrai mot uniquement)"""
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
    """Extrait le mot complet autour d'une position donnée"""
    debut = position
    while debut > 0 and texte[debut - 1].isalpha():
        debut -= 1
    fin = position
    while fin < len(texte) and texte[fin].isalpha():
        fin += 1
    return texte[debut:fin], debut, fin

def est_son_nasal_valide(texte, position, son):
    """Vérifie si un son nasal est valide dans son contexte"""
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
    """Remplace les points par des séparateurs visuels si nécessaire"""
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
    """Ajoute des espaces entre les mots pour une meilleure lisibilité"""
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
    """Colorie le texte selon les règles définies"""
    resultat_word = []
    mots_outils_lower = {mot.lower() for mot in mots_outils}
    i = 0
    while i < len(texte):
        char = texte[i]
        if not char.isalpha():
            resultat_word.append((char, None))
            i += 1
            continue

        mot_complet, debut_mot, fin_mot = extraire_mot_complet(texte, i)
        position_dans_mot = i - debut_mot

        if mot_complet.lower() in mots_outils_lower:
            for c in mot_complet:
                resultat_word.append((c, 'mots_outils'))
            i = fin_mot
            continue

        if detecter_lettre_muette(mot_complet, position_dans_mot):
            for c in mot_complet[position_dans_mot:]:
                resultat_word.append((c, 'muettes'))
            i = fin_mot
            continue

        trouve = False
        # Vérifier les sons complexes
        for son in sorted(sons_complexes, key=len, reverse=True):
            if i + len(son) <= len(texte) and texte[i:i+len(son)].lower() == son:
                for c in texte[i:i+len(son)]:
                    resultat_word.append((c, 'graphemes'))
                i += len(son)
                trouve = True
                break

        if not trouve:
            # Vérifier les sons nasaux
            for son in sorted(sons_nasals, key=len, reverse=True):
                if i + len(son) <= len(texte) and texte[i:i+len(son)].lower() == son:
                    if est_son_nasal_valide(texte, i, son):
                        for c in texte[i:i+len(son)]:
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

def colorier_graphemes_cibles(texte, graphemes, couleur):
    """Colorie uniquement les graphèmes cibles"""
    resultat_word = []
    i = 0
    while i < len(texte):
        trouve = False
        for grapheme in sorted(graphemes, key=len, reverse=True):
            if i + len(grapheme) <= len(texte) and texte[i:i+len(grapheme)].lower() == grapheme.lower():
                for c in texte[i:i+len(grapheme)]:
                    resultat_word.append((c, couleur))
                i += len(grapheme)
                trouve = True
                break
        if not trouve:
            resultat_word.append((texte[i], 'black'))
            i += 1
    return resultat_word

def creer_word(texte, police, couleurs_config, type_doc, graphemes_cibles=None, couleur_graphemes="#069494"):
    """Crée un document Word avec le texte coloré"""
    doc = Document()

    # Convertir les couleurs hex en RGB
    couleurs_rgb = {}
    for key, hex_val in couleurs_config.items():
        r, g, b = hex_to_rgb(hex_val)
        couleurs_rgb[key] = RGBColor(r, g, b)
    couleurs_rgb['teal'] = hex_to_rgb(couleur_graphemes)
    couleurs_rgb['black'] = RGBColor(0, 0, 0)

    # Titre du document
    if type_doc == 'complet':
        titre = 'Code couleur complet'
    else:
        titre = f"Graphèmes cibles : {', '.join(graphemes_cibles)}"

    # Ajouter le texte
    para = doc.add_paragraph()
    for char, couleur in texte:
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

# Sidebar pour les paramètres
with st.sidebar:
    st.header("⚙️ Paramètres")

    # Choix de la casse
    type_casse = st.radio(
        "📄 Casse du document final",
        ["Minuscules", "Majuscules"],
        horizontal=True
    )

    # Choix de la police
    police = st.selectbox("📝 Police d'écriture", POLICES, index=1)

    # Aperçu des polices
    with st.expander("👀 Aperçu des polices"):
        exemple_texte = "Le chat mange une souris."
        for font in POLICES:
            st.markdown(f"**{font}**")
            st.markdown(f"<p style='font-family:{font}; font-size:20px;'>{exemple_texte}</p>", unsafe_allow_html=True)

    # Palette de couleurs
    palette = st.selectbox(
        "🎨 Palette de couleurs",
        list(PALETTES.keys())
    )
    couleurs_config = PALETTES[palette]

    # Mots-outils
    st.subheader("📝 Mots-outils")
    utiliser_base = st.checkbox("Utiliser la liste de base", value=True)
    manuel = st.selectbox("📚 Liste par manuel", ["Aucun"] + list(LISTES_MANUELS.keys()))

    mots_outils_finaux = []
    if utiliser_base:
        mots_outils_finaux.extend(MOTS_OUTILS_BASE)
    if manuel != "Aucun":
        mots_outils_finaux.extend(LISTES_MANUELS[manuel])

    mots_perso = st.text_area(
        "Ajouter vos mots (séparés par des virgules)",
        placeholder="Exemple: car, mais, donc, or..."
    )
    if mots_perso:
        mots_ajout = [m.strip() for m in mots_perso.split(',') if m.strip()]
        mots_outils_finaux.extend(mots_ajout)

    # Gestion des listes de mots-outils
    with st.expander("⚙️ Gérer les listes de mots-outils"):
        st.markdown("**Ajouter/Modifier une liste**")

        nom_liste = st.text_input("Nom de la liste (ex: Taoki 2024)", key="nom_liste")
        nouveaux_mots = st.text_area(
            "Mots de la liste (séparés par des virgules)",
            placeholder="Exemple: le, la, un, une, je, tu",
            key="nouveaux_mots"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Sauvegarder la liste", key="sauvegarder_liste"):
                if nom_liste and nouveaux_mots:
                    mots = [m.strip() for m in nouveaux_mots.split(",") if m.strip()]
                    LISTES_MANUELS[nom_liste] = mots
                    sauvegarder_listes(LISTES_MANUELS)
                    st.success(f"Liste '{nom_liste}' sauvegardée !")
                else:
                    st.warning("Veuillez remplir le nom et les mots.")

        with col2:
            if st.button("🗑️ Supprimer une liste", key="supprimer_liste"):
                if nom_liste in LISTES_MANUELS:
                    del LISTES_MANUELS[nom_liste]
                    sauvegarder_listes(LISTES_MANUELS)
                    st.success(f"Liste '{nom_liste}' supprimée.")
                else:
                    st.warning("Cette liste n'existe pas.")

        # Afficher les listes existantes
        st.markdown("**Listes existantes**")
        for nom, mots in LISTES_MANUELS.items():
            st.write(f"**{nom}** : {', '.join(mots)}")

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
    st.header("🎯 Graphèmes cibles")
    graphemes_cibles = st.text_area(
        "Graphèmes cibles (un par ligne)",
        placeholder="Exemple:\nou\nch\nain"
    )
    graphemes_cibles = [g.strip() for g in graphemes_cibles.split('\n') if g.strip()]

    couleur_graphemes = st.color_picker("Couleur des graphèmes cibles", "#069494")

# Bouton de génération
if st.button("🚀 GÉNÉRER LES DOCUMENTS", type="primary", use_container_width=True):
    if not uploaded_file:
        st.error("❌ Veuillez uploader une image d'abord !")
    elif not graphemes_cibles:
        st.error("❌ Veuillez indiquer au moins un graphème cible !")
    else:
        with st.spinner("⏳ Extraction et traitement en cours..."):
    try:
        # Extraire le texte
        resultat_ocr = lecteur.readtext(image, detail=0)
        texte_brut = " ".join(resultat_ocr)

        if not texte_brut.strip():
            st.error("❌ Aucun texte détecté dans l'image. Essayez une autre image ou améliorez la qualité.")
            st.stop()

        # Suite du traitement...
        texte_brut = remplacer_separateurs(texte_brut)
        texte_travail = ajouter_espaces_entre_mots(texte_brut)

        # ... (le reste de ton code)

    except Exception as e:
        st.error(f"❌ Erreur lors de l'extraction du texte : {str(e)}")


                # Traiter le texte
                texte_brut = remplacer_separateurs(texte_brut)
                texte_travail = ajouter_espaces_entre_mots(texte_brut)

                if type_casse == "Majuscules":
                    texte_travail = texte_travail.upper()
                else:
                    texte_travail = texte_travail.lower()

                st.success("✅ Texte extrait avec succès !")

                with st.expander("👀 Voir le texte extrait"):
                    st.text(texte_travail)

                # Document 1 : Code complet
                st.info("📄 Génération du document avec code couleur complet...")
                texte_complet = colorier_texte(texte_travail, mots_outils_finaux, couleurs_config)
                doc_complet = creer_word(texte_complet, police, couleurs_config, 'complet')

                buffer1 = io.BytesIO()
                doc_complet.save(buffer1)
                buffer1.seek(0)

                # Document 2 : Graphèmes cibles
                st.info(f"📄 Génération du document avec les graphèmes cibles...")
                texte_graphemes = colorier_graphemes_cibles(texte_travail, graphemes_cibles, "teal")
                doc_graphemes = creer_word(texte_graphemes, police, {}, 'graphemes', graphemes_cibles, couleur_graphemes)

                buffer2 = io.BytesIO()
                doc_graphemes.save(buffer2)
                buffer2.seek(0)

                # Aperçu
                st.subheader("👀 Aperçu du document")
                html_aperçu = """
                <style>
                .voyelles { color: {}; }
                .consonnes { color: {}; }
                .graphemes { color: {}; }
                .muettes { color: {}; }
                .mots_outils { color: {}; }
                .teal { color: {}; }
                </style>
                """.format(
                    couleurs_config['voyelles'],
                    couleurs_config['consonnes'],
                    couleurs_config['graphemes'],
                    couleurs_config['muettes'],
                    couleurs_config['mots_outils'],
                    couleur_graphemes
                )

                for char, couleur in texte_complet:
                    if couleur:
                        html_aperçu += f"<span class='{couleur}'>{char}</span>"
                    else:
                        html_aperçu += char
                st.markdown(html_aperçu, unsafe_allow_html=True)

                # Téléchargements
                st.success("🎉 Documents générés avec succès !")

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
                        label=f"📥 Télécharger - Graphèmes cibles",
                        data=buffer2,
                        file_name=f"texte_graphemes_cibles.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")

st.markdown("---")
st.markdown("*Créé avec ❤️ pour aider les enseignants et les élèves - Projet open source*")
