import streamlit as st

# Title of the streamlit app
st.title("Lecture Colorée")

# Instructions
st.write("This application visualizes colors associated with different lectures.")

# Color input
color = st.color_picker('Pick A Color')

if color:
    st.write(f'You selected: {color}')
    st.markdown(f'<div style="width:100px; height:100px; background-color:{color};"></div>', unsafe_allow_html=True)