import streamlit as st
import re
from io import BytesIO

# ------------------------------
# PAGE TITLE
# ------------------------------
st.title("📚 Lecture Colorée pour CP — Version améliorée")

# ------------------------------
# INTRODUCTION (placée juste après le titre — Option 4)
# ------------------------------
st.markdown("""
### 👋 Bienvenue !
Cet outil permet d’adapter automatiquement des textes pour vos élèves grâce au **code couleur dyslexie CP** :

- **Voyelles** : rouge  
- **Consonnes** : bleu  
- **Graphèmes complexes** (an, on, in, ain, eau, oi, etc.) : vert  
- **Lettres muettes** : gris  
- **Mot outil spécifique :** est (en noir)

👉 L’objectif : **aider la lecture**, faciliter la **segmentation phonologique** et soutenir les élèves présentant des troubles du langage écrit, tout en respectant les choix pédagogiques de votre classe.

Renseignez simplement votre texte ci-dessous, ajustez les paramètres, et laissez l’outil faire le reste.
""")

# ------------------------------
# PARAMÈTRES DE L’OUTIL
# ------------------------------
st.header("⚙️ Paramètres")
with st.expander("Graphèmes complexes pris en charge"):
    st.write("""
    Liste des graphèmes colorés en **vert** :
    - an, en  
    - on  
    - in, ain, ein, un  
    - oi  
    - eau  
    - ou  
    - ch  
    - ph  
    - gn  
    """)

complex_graphs = [
    "eau", "ain", "ein", "ion", "oin",
    "an", "en", "on", "in", "un",
    "ch", "ph", "gn", "ou", "oi"
]

mute_letters_pattern = r"(e?t?s?$|ent$|h)"

# ------------------------------
# FONCTIONS
# ------------------------------
def apply_color(text, graphs, mute_pattern):
    # 1) Graphèmes complexes
    for g in sorted(graphs, key=len, reverse=True):
        text = re.sub(
            g,
            rf"<span style='color:green;font-weight:bold'>{g}</span>",
            text
        )

    # 2) Lettres muettes
    text = re.sub(
        mute_pattern,
        lambda m: f"<span style='color:grey'>{m.group()}</span>",
        text
    )

    # 3) Voyelles (hors graphèmes complexes)
    text = re.sub(
        r"[aeiouyàâäéèêëîïôöùûü]",
        lambda m: f"<span style='color:red'>{m.group()}</span>",
        text
    )

    # 4) Consonnes
    text = re.sub(
        r"[bcdfghjklmnpqrstvwxyz]",
        lambda m: f"<span style='color:blue'>{m.group()}</span>",
        text
    )

    # 5) Mot outil "est" à remettre en noir (prioritaire)
    text = re.sub(
        r"<span style='[^>]+'>e</span><span style='[^>]+'>s</span><span style='[^>]+'>t</span>",
        "est",
        text
    )

    return text

# ------------------------------
# ZONE DE TEXTE À ADAPTER
# ------------------------------
st.header("✍️ Texte à transformer")
input_text = st.text_area("Entrez votre texte ici :", height=200)

# ------------------------------
# TRANSFORMATION
# ------------------------------
if st.button("🔄 Transformer le texte"):
    if not input_text.strip():
        st.warning("Veuillez entrer un texte.")
    else:
        colored_text = apply_color(input_text, complex_graphs, mute_letters_pattern)

        st.subheader("📘 Résultat (aperçu)")
        st.markdown(f"<div style='font-size:18px; font-family:OpenDyslexic;'>{colored_text}</div>", unsafe_allow_html=True)

        # Téléchargement
        buffer = BytesIO(colored_text.encode('utf-8'))
        st.download_button(
            label="📥 Télécharger en HTML",
            data=buffer,
            file_name="texte_coloré.html",
            mime="text/html"
        )

# ------------------------------
# TEXTE DE FIN (PLACÉ TOUT EN BAS DE L’APPLICATION)
# ------
