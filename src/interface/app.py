# ==============================================================================
# app.py — Ponto de entrada principal da aplicação Farmazzini BI
# Como executar: cd src/interface && streamlit run app.py
# ==============================================================================

import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import streamlit as st

st.set_page_config(
    page_title="Farmazzini BI",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injeta credenciais AWS vindas dos Secrets do Streamlit Cloud
os.environ["AWS_ACCESS_KEY_ID"]     = st.secrets.get("AKIA5GEDNRAITXHZNSXF", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets.get("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", "")
os.environ["AWS_DEFAULT_REGION"]    = st.secrets.get("AWS_DEFAULT_REGION", "us-east-2")

# ── CSS do arquivo externo ────────────────────────────────────────────────────
_css_path = os.path.join(_here, "styles", "custom.css")
with open(_css_path, "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Sidebar redimensionável por arraste do mouse ──────────────────────────────
st.markdown("""
<script>
(function() {
    function initResize() {
        const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) { setTimeout(initResize, 300); return; }

        // Cria a alça de arraste
        const handle = window.parent.document.createElement('div');
        handle.id = 'sidebar-resize-handle';
        Object.assign(handle.style, {
            position:  'absolute',
            top:       '0',
            right:     '-4px',
            width:     '8px',
            height:    '100%',
            cursor:    'col-resize',
            zIndex:    '9999',
            background: 'transparent',
        });
        sidebar.style.position = 'relative';
        sidebar.appendChild(handle);

        // Linha visual ao hover
        handle.addEventListener('mouseenter', () => {
            handle.style.background = 'rgba(139,26,26,0.5)';
        });
        handle.addEventListener('mouseleave', () => {
            if (!handle._dragging) handle.style.background = 'transparent';
        });

        let startX, startW;

        handle.addEventListener('mousedown', (e) => {
            handle._dragging = true;
            startX = e.clientX;
            startW = sidebar.getBoundingClientRect().width;
            handle.style.background = 'rgba(139,26,26,0.9)';

            // Overlay para não perder o cursor ao mover rápido
            const overlay = window.parent.document.createElement('div');
            overlay.id = 'resize-overlay';
            Object.assign(overlay.style, {
                position: 'fixed', top: '0', left: '0',
                width: '100vw', height: '100vh',
                zIndex: '99999', cursor: 'col-resize',
            });
            window.parent.document.body.appendChild(overlay);

            function onMove(e) {
                const delta = e.clientX - startX;
                const newW  = Math.min(600, Math.max(180, startW + delta));
                sidebar.style.minWidth = newW + 'px';
                sidebar.style.maxWidth = newW + 'px';
                sidebar.style.width    = newW + 'px';
                const inner = sidebar.querySelector('div:first-child');
                if (inner) {
                    inner.style.minWidth = newW + 'px';
                    inner.style.width    = newW + 'px';
                }
            }

            function onUp() {
                handle._dragging = false;
                handle.style.background = 'transparent';
                const ov = window.parent.document.getElementById('resize-overlay');
                if (ov) ov.remove();
                window.parent.document.removeEventListener('mousemove', onMove);
                window.parent.document.removeEventListener('mouseup',   onUp);
            }

            window.parent.document.addEventListener('mousemove', onMove);
            window.parent.document.addEventListener('mouseup',   onUp);
            e.preventDefault();
        });
    }

    // Aguarda o DOM do Streamlit estar pronto
    if (window.parent.document.readyState === 'loading') {
        window.parent.document.addEventListener('DOMContentLoaded', initResize);
    } else {
        initResize();
    }
})();
</script>
""", unsafe_allow_html=True)

from components.sidebar import render_sidebar
from components.chat import render_chat

filtros = render_sidebar()
render_chat(filtros)