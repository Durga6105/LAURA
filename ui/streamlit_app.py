"""
LAURA - Legal AI Understanding & Risk Analyzer

Streamlit frontend.

Features:
- NDA upload
- NDA analysis
- Analysis summary
- Rule validation
- Corrections
- Separate corrected NDA download
- Separate PDF report download
- Ask LAURA
- Analysis progress sidebar

The Rule Book is constant and is not uploaded by the user.
"""

from __future__ import annotations


import html
import os
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import streamlit as st


# =========================================================
# CONFIGURATION
# =========================================================

API_URL = os.getenv(
    "LAURA_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

BASE_DIR = Path(__file__).resolve().parent

# Resolve the LAURA image robustly.
# Works when Streamlit is launched from the project directory
# or when the script is located one level differently.
_LAURA_IMAGE_CANDIDATES = [
    BASE_DIR / "assets" / "laura.png",
    Path.cwd() / "assets" / "laura.png",
    BASE_DIR.parent / "assets" / "laura.png",
]

LAURA_IMAGE = next(
    (
        candidate
        for candidate in _LAURA_IMAGE_CANDIDATES
        if candidate.exists()
    ),
    _LAURA_IMAGE_CANDIDATES[0],
)

ALLOWED_TYPES = ["pdf", "docx"]


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="LAURA | Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# HELPERS
# =========================================================

def safe_text(value: Any) -> str:
    """Safely escape text for HTML."""

    if value is None:
        return ""

    return html.escape(str(value))


def get_greeting() -> str:
    """Return greeting based on current time."""

    hour = datetime.now().hour

    if 5 <= hour < 12:
        return "Good Morning"

    if 12 <= hour < 17:
        return "Good Afternoon"

    if 17 <= hour < 22:
        return "Good Evening"

    return "Good Night"





def reset_analysis() -> None:
    """Reset current analysis state."""

    st.session_state.analysis_result = None
    st.session_state.analysis_id = None

    st.session_state.corrected_data = None
    st.session_state.corrected_filename = None
    st.session_state.corrected_mime = None

    st.session_state.report_data = None
    st.session_state.report_filename = None

    st.session_state.qa_history = []

    st.session_state.progress_state = "start"
    st.session_state.uploaded_filename = None


# =========================================================
# SESSION STATE
# =========================================================

DEFAULT_STATE = {
    "analysis_result": None,
    "analysis_id": None,
    "corrected_data": None,
    "corrected_filename": None,
    "corrected_mime": None,
    "report_data": None,
    "report_filename": None,
    "qa_history": [],
    "progress_state": "start",
    "uploaded_filename": None,
}

for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# CSS
# =========================================================

st.markdown(
    textwrap.dedent(
        """
        <style>

        /* =====================================================
           GLOBAL
           ===================================================== */

        .stApp {
            background:
                radial-gradient(
                    circle at 10% 5%,
                    rgba(25, 91, 180, 0.14),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 90% 10%,
                    rgba(112, 54, 220, 0.13),
                    transparent 30%
                ),
                #080b14;

            color: #f5f7ff;
        }

        .main .block-container {
            max-width: 1500px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* =====================================================
           SIDEBAR
           ===================================================== */

        [data-testid="stSidebar"] {
            background:
                radial-gradient(
                    circle at 50% 0%,
                    rgba(42, 95, 210, 0.13),
                    transparent 30%
                ),
                linear-gradient(
                    180deg,
                    #090e1c 0%,
                    #070a12 100%
                );

            border-right:
                1px solid
                rgba(105, 130, 255, 0.17);
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 1.2rem;
            padding-left: 1.1rem;
            padding-right: 1.1rem;
        }

        .sidebar-brand {
            font-size: 2rem;
            font-weight: 900;
            letter-spacing: -0.04em;

            background:
                linear-gradient(
                    90deg,
                    #20ddff,
                    #7c68ff,
                    #c579ff
                );

            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .sidebar-subtitle {
            color: #798399;
            font-size: 0.73rem;
            line-height: 1.45;
            margin-top: -2px;
        }

        .sidebar-divider {
            height: 1px;
            background:
                linear-gradient(
                    90deg,
                    transparent,
                    rgba(110, 125, 180, 0.25),
                    transparent
                );
            margin: 20px 0;
        }

        .sidebar-heading {
            color: #e7ebf7;
            font-size: 0.83rem;
            font-weight: 800;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            margin-bottom: 16px;
        }

        .progress-row {
            display: flex;
            align-items: flex-start;
            gap: 11px;
            min-height: 36px;
        }

        .progress-icon {
            width: 23px;
            height: 23px;
            min-width: 23px;
            border-radius: 50%;

            display: flex;
            align-items: center;
            justify-content: center;

            font-size: 0.7rem;
            font-weight: 800;
        }

        .progress-complete {
            background: rgba(36, 229, 178, 0.11);
            border: 1px solid rgba(36, 229, 178, 0.42);
            color: #42eab9;
        }

        .progress-current {
            background: rgba(35, 208, 255, 0.12);
            border: 1px solid rgba(35, 208, 255, 0.55);
            color: #31ddff;
            box-shadow:
                0 0 15px
                rgba(35, 208, 255, 0.20);
        }

        .progress-pending {
            background: rgba(100, 110, 140, 0.07);
            border: 1px solid rgba(100, 110, 140, 0.22);
            color: #596278;
        }

        .progress-text {
            padding-top: 1px;
        }

        .progress-name {
            color: #dce2f0;
            font-size: 0.76rem;
            font-weight: 650;
        }

        .progress-description {
            color: #68738a;
            font-size: 0.62rem;
            margin-top: 2px;
        }

        .progress-connector {
            height: 11px;
            width: 1px;
            background: rgba(98, 117, 190, 0.22);
            margin-left: 11px;
        }

        /* =====================================================
           HERO
           ===================================================== */

        .hero {
            position: relative;
            overflow: hidden;

            min-height: 385px;

            border-radius: 28px;

            border:
                1px solid
                rgba(104, 127, 255, 0.22);

            background:
                radial-gradient(
                    circle at 17% 60%,
                    rgba(18, 204, 255, 0.12),
                    transparent 31%
                ),
                radial-gradient(
                    circle at 80% 25%,
                    rgba(132, 72, 255, 0.14),
                    transparent 32%
                ),
                linear-gradient(
                    135deg,
                    #0b1429,
                    #090d18 55%,
                    #11102a
                );

            box-shadow:
                0 25px 90px
                rgba(0, 0, 0, 0.35);
        }

        .hero-glow {
            position: absolute;
            width: 450px;
            height: 450px;
            border-radius: 50%;

            left: -180px;
            bottom: -230px;

            background:
                rgba(21, 203, 255, 0.10);

            filter: blur(90px);
        }

        .hero-image {
            position: absolute;

            left: 2%;
            bottom: 0;

            width: 48%;
            height: 100%;

            object-fit: contain;
            object-position: center bottom;

            filter:
                drop-shadow(
                    0 0 32px
                    rgba(25, 197, 255, 0.23)
                );
        }

        .hero-content {
            position: relative;
            z-index: 3;

            margin-left: 50%;

            padding:
                64px
                52px
                48px
                20px;
        }

        .hero-greeting {
            color: #929cb2;
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 4px;
        }

        .hero-name {
            font-size: clamp(2rem, 3.3vw, 3.2rem);
            font-weight: 850;
            line-height: 1.05;
            letter-spacing: -0.04em;

            background:
                linear-gradient(
                    90deg,
                    #f5f8ff 0%,
                    #dceaff 45%,
                    #77ddff 100%
                );

            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-welcome {
            color: #d9e0ef;
            font-size: 1.2rem;
            margin-top: 22px;
        }

        .hero-brand {
            color: #24ddff;
            font-weight: 850;
        }

        .hero-description {
            color: #929db2;
            max-width: 550px;
            line-height: 1.65;
            font-size: 0.93rem;
            margin-top: 9px;
        }

        .hero-badge {
            display: inline-block;

            margin-top: 21px;
            padding: 8px 14px;

            border-radius: 999px;

            border:
                1px solid
                rgba(30, 215, 255, 0.25);

            background:
                rgba(30, 215, 255, 0.055);

            color: #9deeff;
            font-size: 0.74rem;
        }

        /* =====================================================
           SECTION
           ===================================================== */

        .section-title {
            color: #f3f6ff;
            font-size: 1.45rem;
            font-weight: 800;
            margin-top: 1.5rem;
            margin-bottom: 3px;
        }

        .section-subtitle {
            color: #7f899e;
            font-size: 0.84rem;
            margin-bottom: 14px;
        }

        /* =====================================================
           CARDS
           ===================================================== */

        .glass-card {
            background:
                linear-gradient(
                    145deg,
                    rgba(18, 27, 50, 0.92),
                    rgba(10, 15, 29, 0.94)
                );

            border:
                1px solid
                rgba(101, 122, 220, 0.18);

            border-radius: 19px;

            padding: 20px;

            box-shadow:
                0 15px 55px
                rgba(0, 0, 0, 0.18);
        }

        .metric-card {
            min-height: 120px;

            padding: 19px;

            border-radius: 17px;

            background:
                linear-gradient(
                    145deg,
                    rgba(19, 30, 57, 0.96),
                    rgba(11, 16, 31, 0.96)
                );

            border:
                1px solid
                rgba(95, 119, 230, 0.18);
        }

        .metric-label {
            color: #858fa5;
            font-size: 0.76rem;
        }

        .metric-value {
            color: #f4f7ff;
            font-size: 1.95rem;
            font-weight: 850;
            margin-top: 5px;
        }

        .metric-description {
            color: #606b82;
            font-size: 0.67rem;
            margin-top: 3px;
        }

        /* =====================================================
           STATUS
           ===================================================== */

        .status-box {
            padding: 16px;
            border-radius: 14px;
            text-align: center;
            font-weight: 750;
        }

        .status-pass {
            color: #54edbd;
            background: rgba(33, 229, 177, 0.07);
            border: 1px solid rgba(33, 229, 177, 0.27);
        }

        .status-fail {
            color: #ff7c8e;
            background: rgba(255, 76, 96, 0.07);
            border: 1px solid rgba(255, 76, 96, 0.27);
        }

        .status-low {
            color: #54edbd;
            background: rgba(33, 229, 177, 0.07);
            border: 1px solid rgba(33, 229, 177, 0.27);
        }

        .status-medium {
            color: #ffc65a;
            background: rgba(255, 185, 50, 0.07);
            border: 1px solid rgba(255, 185, 50, 0.27);
        }

        .status-high {
            color: #ff7c8e;
            background: rgba(255, 76, 96, 0.07);
            border: 1px solid rgba(255, 76, 96, 0.27);
        }

        /* =====================================================
           UPLOAD
           ===================================================== */

        [data-testid="stFileUploaderDropzone"] {
            background:
                linear-gradient(
                    145deg,
                    rgba(12, 26, 54, 0.90),
                    rgba(10, 15, 29, 0.95)
                ) !important;

            border:
                1px dashed
                rgba(43, 207, 255, 0.42) !important;

            border-radius: 16px !important;
        }

        .upload-info {
            margin-top: 10px;
            padding: 12px 15px;

            border-radius: 12px;

            background:
                rgba(30, 210, 255, 0.045);

            border:
                1px solid
                rgba(30, 210, 255, 0.14);

            color: #91d9eb;
            font-size: 0.78rem;
        }

        /* =====================================================
           CORRECTIONS
           ===================================================== */

        .correction-box {
            padding: 19px;
            margin-bottom: 13px;

            border-radius: 17px;

            background:
                rgba(12, 18, 35, 0.82);

            border:
                1px solid
                rgba(100, 120, 210, 0.18);
        }

        .correction-title {
            color: #edf2ff;
            font-weight: 750;
            margin-bottom: 15px;
        }

        .correction-label {
            color: #737e96;
            font-size: 0.69rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 7px;
        }

        .correction-original {
            color: #d7dce8;
            padding: 12px 14px;

            border-left:
                3px solid
                #ff6878;

            border-radius: 0 9px 9px 0;

            background:
                rgba(255, 76, 96, 0.045);
        }

        .correction-modified {
            color: #d7dce8;
            padding: 12px 14px;

            border-left:
                3px solid
                #39e5b2;

            border-radius: 0 9px 9px 0;

            background:
                rgba(39, 229, 178, 0.045);
        }

        .correction-reason {
            color: #9ca5b8;
            line-height: 1.55;
        }

        /* =====================================================
           DOWNLOAD
           ===================================================== */

        .download-card {
            min-height: 120px;
            padding: 19px;

            border-radius: 17px;

            background:
                linear-gradient(
                    145deg,
                    rgba(19, 29, 55, 0.95),
                    rgba(10, 15, 29, 0.95)
                );

            border:
                1px solid
                rgba(96, 119, 225, 0.19);
        }

        .download-title {
            color: #edf2ff;
            font-size: 1rem;
            font-weight: 750;
        }

        .download-description {
            color: #7c879d;
            font-size: 0.73rem;
            margin-top: 5px;
            margin-bottom: 13px;
        }

        /* =====================================================
           Q&A
           ===================================================== */

        .qa-card {
            padding: 22px;

            border-radius: 20px;

            background:
                linear-gradient(
                    145deg,
                    rgba(17, 27, 52, 0.95),
                    rgba(9, 14, 27, 0.96)
                );

            border:
                1px solid
                rgba(102, 124, 235, 0.20);
        }

        .qa-name {
            color: #f0f4ff;
            font-weight: 800;
            font-size: 0.95rem;
        }

        .qa-online {
            color: #48e6b5;
            font-size: 0.66rem;
            margin-top: 2px;
        }

        .qa-answer {
            padding: 17px;

            margin-top: 8px;

            border-radius: 14px;

            background:
                linear-gradient(
                    135deg,
                    rgba(25, 192, 255, 0.055),
                    rgba(125, 72, 255, 0.055)
                );

            border-left:
                3px solid
                #2bdcff;

            color: #dce2ee;

            line-height: 1.65;
        }

        /* =====================================================
           INPUTS / BUTTONS
           ===================================================== */

        .stTextInput input,
        .stTextArea textarea {
            background: #141823 !important;
            color: #f4f6ff !important;

            border:
                1px solid
                rgba(101, 117, 160, 0.24) !important;

            border-radius: 11px !important;
        }

        .stButton > button {
            border-radius: 11px !important;

            border:
                1px solid
                rgba(96, 120, 230, 0.28) !important;

            background:
                linear-gradient(
                    135deg,
                    #142c58,
                    #30245f
                ) !important;

            color: #f3f6ff !important;

            font-weight: 700 !important;
        }

        .stButton > button:hover {
            border-color:
                rgba(35, 218, 255, 0.62) !important;

            box-shadow:
                0 0 22px
                rgba(35, 195, 255, 0.12) !important;
        }

        /* =====================================================
           DIVIDER / FOOTER
           ===================================================== */

        hr {
            border-color:
                rgba(105, 120, 165, 0.13) !important;
        }

        .footer {
            text-align: center;
            color: #515c73;
            font-size: 0.68rem;
            padding-top: 35px;
        }

        </style>
        """
    ),
    unsafe_allow_html=True,
)


# =========================================================
# API FUNCTIONS
# =========================================================

def run_analysis(
    uploaded_file: Any,
) -> dict:
    """Start NDA analysis and return the analysis ID."""

    response = requests.post(
        f"{API_URL}/analysis/run",
        files={
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type,
            )
        },
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


def get_analysis_status(
    analysis_id: str,
) -> dict:
    """Get the current live analysis status."""

    response = requests.get(
        f"{API_URL}/analysis/status/{analysis_id}",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def download_file(
    endpoint: str,
) -> tuple[bytes, str, str]:
    """Download a generated file."""

    response = requests.get(
        f"{API_URL}{endpoint}",
        timeout=120,
    )

    response.raise_for_status()

    content_disposition = response.headers.get(
        "content-disposition",
        "",
    )

    filename = "download"

    if "filename=" in content_disposition:

        filename = (
            content_disposition
            .split("filename=", 1)[1]
            .strip()
            .strip('"')
            .strip("'")
        )

    content_type = response.headers.get(
        "content-type",
        "application/octet-stream",
    )

    return (
        response.content,
        filename,
        content_type,
    )


def ask_laura(
    analysis_id: str,
    question: str,
) -> dict:
    """Send question to LAURA."""

    response = requests.post(
        f"{API_URL}/qa/ask",
        json={
            "analysis_id": analysis_id,
            "question": question,
        },
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# PROGRESS
# =========================================================

PROGRESS_STEPS = [
    (
        "start",
        "Start",
        "Ready to analyze",
    ),
    (
        "nda_uploaded",
        "NDA Uploaded",
        "File received",
    ),
    (
        "ingestion",
        "Ingestion",
        "Document processed",
    ),
    (
        "rule_book_retrieval",
        "Rule Book Retrieval",
        "Rules retrieved",
    ),
    (
        "validation",
        "Validation",
        "Rules evaluated",
    ),
    (
        "correction",
        "Correction",
        "Required changes applied",
    ),
    (
        "revalidation",
        "Re-validation",
        "Final validation",
    ),
    (
        "report_generation",
        "Report Generation",
        "Report prepared",
    ),
    (
        "completed",
        "Completed",
        "Analysis finished",
    ),
]


def get_progress_index(
    state: str,
) -> int:

    for index, step in enumerate(
        PROGRESS_STEPS
    ):

        if step[0] == state:
            return index

    return 0


def render_sidebar(
    container: Any = None,
) -> None:
    """Render LAURA progress sidebar."""

    target = container or st.sidebar

    with target:

        st.markdown(
            '<div class="sidebar-brand">LAURA</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-subtitle">
                Legal AI Understanding & Risk Analyzer
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="sidebar-divider"></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="sidebar-heading">'
            'Analysis Progress'
            '</div>',
            unsafe_allow_html=True,
        )

        current = get_progress_index(
            st.session_state.progress_state
        )

        for index, (
            key,
            name,
            description,
        ) in enumerate(PROGRESS_STEPS):

            if index < current:
                icon_class = "progress-complete"
                icon = "✓"

            elif index == current:
                icon_class = "progress-current"
                icon = "●"

            else:
                icon_class = "progress-pending"
                icon = "○"

            st.html(
                f"""
                <div class="progress-row">
                    <div class="progress-icon {icon_class}">{icon}</div>
                    <div class="progress-text">
                        <div class="progress-name">{safe_text(name)}</div>
                        <div class="progress-description">{safe_text(description)}</div>
                    </div>
                </div>
                """
            )

            if index < len(PROGRESS_STEPS) - 1:
                st.markdown(
                    '<div class="progress-connector"></div>',
                    unsafe_allow_html=True,
                )

        st.markdown(
            '<div class="sidebar-divider"></div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "＋  New Analysis",
            use_container_width=True,
        ):
            reset_analysis()
            st.rerun()

        st.markdown(
            """
            <div style="
                color:#5f6a81;
                font-size:0.65rem;
                margin-top:13px;
                text-align:center;
            ">
                Rule Book • Pre-configured
            </div>
            """,
            unsafe_allow_html=True,
        )


# A single placeholder lets the sidebar progress update in-place
# during the live polling loop instead of creating duplicate bars.
_sidebar_placeholder = st.sidebar.empty()
render_sidebar(_sidebar_placeholder)


# =========================================================
# HERO
# =========================================================

hero_left, hero_right = st.columns(
    [1, 1],
    gap="large",
)

with hero_left:

    # Render the actual image directly with Streamlit.
    if LAURA_IMAGE.exists():
        st.image(
            str(LAURA_IMAGE),
            width=360,
        )
    else:
        st.warning(
            f"LAURA image not found: {LAURA_IMAGE}"
        )


with hero_right:

    # IMPORTANT:
    # Use st.html() for custom HTML. Do not use st.markdown()
    # here, otherwise the indentation can be displayed as
    # a literal Markdown code block.
    st.html(
        f"""
<div style="
    padding-top:55px;
    padding-left:20px;
    padding-right:35px;
">

    <div style="
        color:#929cb2;
        font-size:1rem;
        font-weight:500;
        margin-bottom:5px;
    ">
        {safe_text(get_greeting())},
    </div>

    <div style="
        font-size:clamp(2rem,3.3vw,3.2rem);
        font-weight:850;
        line-height:1.05;
        letter-spacing:-0.04em;
        background:linear-gradient(
            90deg,
            #f5f8ff,
            #dceaff 45%,
            #77ddff
        );
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
    ">
        Peddimeni Durga Prasad 👋
    </div>

    <div style="
        color:#d9e0ef;
        font-size:1.2rem;
        margin-top:22px;
    ">
        Welcome to
        <span style="
            color:#24ddff;
            font-weight:850;
        ">
            LAURA
        </span>
    </div>

    <div style="
        color:#929db2;
        max-width:550px;
        line-height:1.65;
        font-size:0.93rem;
        margin-top:9px;
    ">
        Your intelligent legal AI assistant for
        NDA analysis, validation, risk assessment,
        corrections and contract intelligence.
    </div>

    <div style="
        display:inline-block;
        margin-top:21px;
        padding:8px 14px;
        border-radius:999px;
        border:1px solid rgba(30,215,255,0.25);
        background:rgba(30,215,255,0.055);
        color:#9deeff;
        font-size:0.74rem;
    ">
        ✦ AI-powered NDA intelligence
    </div>

</div>
"""
    )


# =========================================================
# UPLOAD
# =========================================================

st.markdown(
    '<div class="section-title">1. Upload NDA</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-subtitle">
        Upload the NDA you want LAURA to analyze.
        Supported formats: PDF and DOCX.
    </div>
    """,
    unsafe_allow_html=True,
)

nda_file = st.file_uploader(
    "Choose NDA",
    type=ALLOWED_TYPES,
    label_visibility="collapsed",
    key="nda_uploader",
)

if nda_file:

    st.session_state.uploaded_filename = (
        nda_file.name
    )

    size_kb = round(
        len(nda_file.getvalue()) / 1024,
        1,
    )

    st.markdown(
        f"""
        <div class="upload-info">
            ✓ <b>{safe_text(nda_file.name)}</b>
            &nbsp; • &nbsp;
            {size_kb} KB
            &nbsp; • &nbsp;
            {safe_text(nda_file.type)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# ANALYSIS
# =========================================================

st.markdown(
    '<div class="section-title">2. Analyze NDA</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-subtitle">
        LAURA will ingest the document, retrieve the
        Rule Book requirements, validate the NDA,
        apply corrections and perform final validation.
    </div>
    """,
    unsafe_allow_html=True,
)

if nda_file:

    if st.button(
        "✦  Analyze NDA",
        type="primary",
        use_container_width=True,
    ):

        # Reset previous result.
        st.session_state.analysis_result = None
        st.session_state.analysis_id = None

        st.session_state.corrected_data = None
        st.session_state.corrected_filename = None
        st.session_state.corrected_mime = None

        st.session_state.report_data = None
        st.session_state.report_filename = None

        st.session_state.qa_history = []
        st.session_state.progress_state = "nda_uploaded"

        try:

            # -------------------------------------------------
            # Start the backend job.
            # -------------------------------------------------

            started = run_analysis(
                nda_file
            )

            analysis_id = started.get(
                "analysis_id"
            )

            if not analysis_id:
                raise RuntimeError(
                    "Backend did not return an analysis ID."
                )

            st.session_state.analysis_id = (
                analysis_id
            )

            # -------------------------------------------------
            # Poll the REAL backend progress.
            #
            # The sidebar is updated in-place after every
            # status response. No fake timed progress.
            # -------------------------------------------------

            while True:

                status_data = get_analysis_status(
                    analysis_id
                )

                stage = status_data.get(
                    "stage",
                    "start",
                )

                status_value = status_data.get(
                    "status",
                    "queued",
                )

                st.session_state.progress_state = (
                    stage
                )

                render_sidebar(
                    _sidebar_placeholder
                )

                if status_value == "completed":

                    result = status_data.get(
                        "result"
                    )

                    if not result:
                        raise RuntimeError(
                            "Analysis completed, but the "
                            "backend did not return the "
                            "analysis result."
                        )

                    st.session_state.analysis_result = (
                        result
                    )

                    st.session_state.progress_state = (
                        "completed"
                    )

                    render_sidebar(
                        _sidebar_placeholder
                    )

                    break

                if status_value == "failed":

                    raise RuntimeError(
                        status_data.get(
                            "message",
                            "NDA analysis failed.",
                        )
                    )

                time.sleep(0.7)

            # -------------------------------------------------
            # Download generated files only AFTER the backend
            # reports completion.
            # -------------------------------------------------

            downloads = (
                result.get(
                    "downloads",
                    {},
                )
            )

            corrected_endpoint = (
                downloads.get(
                    "corrected_nda"
                )
            )

            if corrected_endpoint:

                (
                    data,
                    filename,
                    mime,
                ) = download_file(
                    corrected_endpoint
                )

                st.session_state.corrected_data = data
                st.session_state.corrected_filename = filename
                st.session_state.corrected_mime = mime

            report_endpoint = (
                downloads.get(
                    "analysis_report"
                )
            )

            if report_endpoint:

                (
                    data,
                    filename,
                    mime,
                ) = download_file(
                    report_endpoint
                )

                st.session_state.report_data = data
                st.session_state.report_filename = filename

            st.success(
                "✓ LAURA has completed the NDA analysis."
            )

        except requests.HTTPError as exc:

            response = getattr(
                exc,
                "response",
                None,
            )

            detail = str(exc)

            if response is not None:
                try:
                    detail = response.json().get(
                        "detail",
                        detail,
                    )
                except Exception:
                    pass

            st.session_state.progress_state = "start"
            render_sidebar(
                _sidebar_placeholder
            )

            st.error(
                f"Analysis failed: {detail}"
            )

        except requests.RequestException as exc:

            st.session_state.progress_state = "start"
            render_sidebar(
                _sidebar_placeholder
            )

            st.error(
                f"Could not connect to LAURA backend: {exc}"
            )

        except Exception as exc:

            st.session_state.progress_state = "start"
            render_sidebar(
                _sidebar_placeholder
            )

            st.error(
                f"Unexpected error: {exc}"
            )

else:

    st.info(
        "Upload an NDA to begin."
    )


# =========================================================
# RESULT
# =========================================================

result = st.session_state.analysis_result

if result:

    st.markdown(
        '<div class="section-title">'
        '3. Analysis Summary'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Final validation and risk assessment.
        </div>
        """,
        unsafe_allow_html=True,
    )

    final_summary = result.get(
        "final_summary",
        {},
    )

    original_summary = result.get(
        "original_summary",
        {},
    )

    final_status = str(
        final_summary.get(
            "overall_status",
            "UNKNOWN",
        )
    )

    final_risk = str(
        final_summary.get(
            "overall_risk",
            "UNKNOWN",
        )
    )

    if final_status == "PASS":
        status_class = "status-pass"
        status_icon = "✓"
    else:
        status_class = "status-fail"
        status_icon = "✕"

    if final_risk == "LOW":
        risk_class = "status-low"
    elif final_risk == "HIGH":
        risk_class = "status-high"
    else:
        risk_class = "status-medium"

    c1, c2 = st.columns(2)

    with c1:

        st.markdown(
            f"""
            <div class="status-box {status_class}">
                {status_icon}
                NDA {safe_text(final_status)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:

        st.markdown(
            f"""
            <div class="status-box {risk_class}">
                Overall Risk:
                {safe_text(final_risk)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='height:12px'></div>",
        unsafe_allow_html=True,
    )

    total_rules = final_summary.get(
        "total_rules",
        0,
    )

    passed_rules = final_summary.get(
        "passed_rules",
        0,
    )

    failed_rules = final_summary.get(
        "failed_rules",
        0,
    )

    high_risk_failures = final_summary.get(
        "high_risk_failures",
        0,
    )

    m1, m2, m3, m4 = st.columns(4)

    metrics = [
        (
            m1,
            "Total Rules",
            total_rules,
            "Rule Book requirements",
        ),
        (
            m2,
            "Passed",
            passed_rules,
            "Requirements satisfied",
        ),
        (
            m3,
            "Failed",
            failed_rules,
            "Requirements requiring attention",
        ),
        (
            m4,
            "High-Risk Failures",
            high_risk_failures,
            "High-risk findings",
        ),
    ]

    for column, label, value, description in metrics:

        with column:

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-label">
                        {safe_text(label)}
                    </div>

                    <div class="metric-value">
                        {safe_text(value)}
                    </div>

                    <div class="metric-description">
                        {safe_text(description)}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


    # =====================================================
    # ORIGINAL SUMMARY
    # =====================================================

    st.markdown(
        "<div style='height:12px'></div>",
        unsafe_allow_html=True,
    )

    with st.expander(
        "View Original NDA Validation",
        expanded=False,
    ):

        o1, o2, o3, o4 = st.columns(4)

        o1.metric(
            "Status",
            original_summary.get(
                "overall_status",
                "UNKNOWN",
            ),
        )

        o2.metric(
            "Risk",
            original_summary.get(
                "overall_risk",
                "UNKNOWN",
            ),
        )

        o3.metric(
            "Failed",
            original_summary.get(
                "failed_rules",
                0,
            ),
        )

        o4.metric(
            "Mandatory Failures",
            original_summary.get(
                "mandatory_failures",
                0,
            ),
        )


    # =====================================================
    # RULE RESULTS
    # =====================================================

    rule_results = result.get(
        "validation_results",
        result.get(
            "results",
            [],
        ),
    )

    if rule_results:

        st.markdown(
            '<div class="section-title">'
            'Rule-by-Rule Validation'
            '</div>',
            unsafe_allow_html=True,
        )

        for rule in rule_results:

            rule_id = rule.get(
                "rule_id",
                "Unknown",
            )

            rule_status = rule.get(
                "status",
                "UNKNOWN",
            )

            rule_risk = rule.get(
                "risk",
                "UNKNOWN",
            )

            with st.expander(
                f"{rule_id}  •  "
                f"{rule_status}  •  "
                f"{rule_risk}"
            ):

                st.write(
                    f"**NDA Section:** "
                    f"{rule.get('nda_section', '')}"
                )

                st.write(
                    f"**Mandatory:** "
                    f"{rule.get('mandatory', '')}"
                )

                st.write(
                    f"**Evidence:** "
                    f"{rule.get('evidence', '')}"
                )

                st.write(
                    f"**Reason:** "
                    f"{rule.get('reason', '')}"
                )

                if rule.get(
                    "required_change"
                ):

                    st.write(
                        f"**Required Change:** "
                        f"{rule.get('required_change')}"
                    )


    # =====================================================
    # CORRECTIONS
    # =====================================================

    st.markdown(
        '<div class="section-title">'
        '4. Corrections Made'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Changes applied by LAURA to satisfy the
            Rule Book requirements.
        </div>
        """,
        unsafe_allow_html=True,
    )

    corrections = result.get(
        "corrections",
        [],
    )

    if not corrections:

        st.success(
            "✓ No corrections were required."
        )

    else:

        st.info(
            f"{len(corrections)} correction(s) applied."
        )

        for index, correction in enumerate(
            corrections,
            start=1,
        ):

            rule_id = safe_text(
                correction.get(
                    "rule_id",
                    "",
                )
            )

            original = safe_text(
                correction.get(
                    "original_text",
                    "",
                )
            )

            modified = safe_text(
                correction.get(
                    "modified_text",
                    "",
                )
            )

            reason = safe_text(
                correction.get(
                    "reason",
                    "",
                )
            )
            st.html(
                f"""
                <div class="correction-box">
                    <div class="correction-title">
                        Correction {index} &nbsp;•&nbsp; {rule_id}
                    </div>
                    <div class="correction-label">Original</div>
                    <div class="correction-original">{original}</div>
                    <div style="text-align:center;color:#39dfff;padding:10px;font-size:1.2rem;">↓</div>
                    <div class="correction-label">Corrected</div>
                    <div class="correction-modified">{modified}</div>
                    <div style="margin-top:15px">
                        <div class="correction-label">Why LAURA changed it</div>
                        <div class="correction-reason">{reason}</div>
                    </div>
                </div>
                """
            )


    # =====================================================
    # DOWNLOADS
    # =====================================================

    st.markdown(
        '<div class="section-title">'
        '5. Downloads'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Download each generated file separately.
        </div>
        """,
        unsafe_allow_html=True,
    )

    d1, d2 = st.columns(2)

    with d1:

        st.markdown(
            """
            <div class="download-card">

                <div class="download-title">
                    📄 Corrected NDA
                </div>

                <div class="download-description">
                    Your corrected NDA document.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.corrected_data:

            st.download_button(
                "↓  Download Corrected NDA",
                data=st.session_state.corrected_data,
                file_name=(
                    st.session_state.corrected_filename
                    or "corrected_nda"
                ),
                mime=(
                    st.session_state.corrected_mime
                    or "application/octet-stream"
                ),
                use_container_width=True,
                key="corrected_download",
            )

        else:

            st.warning(
                "Corrected NDA unavailable."
            )

    with d2:

        st.markdown(
            """
            <div class="download-card">

                <div class="download-title">
                    📑 Analysis Report
                </div>

                <div class="download-description">
                    Complete PDF analysis report.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.report_data:

            st.download_button(
                "↓  Download Analysis Report",
                data=st.session_state.report_data,
                file_name=(
                    st.session_state.report_filename
                    or "LAURA_analysis_report.pdf"
                ),
                mime="application/pdf",
                use_container_width=True,
                key="report_download",
            )

        else:

            st.warning(
                "Analysis report unavailable."
            )


    # =====================================================
    # ASK LAURA
    # =====================================================

    st.markdown(
        '<div class="section-title">'
        '6. Ask LAURA'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Ask follow-up questions about your NDA,
            validation, corrections, rules, risks,
            report or the analysis process.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="qa-card">',
        unsafe_allow_html=True,
    )

    q1, q2 = st.columns(
        [1, 5]
    )

    with q1:

        if LAURA_IMAGE.exists():

            st.image(
                str(LAURA_IMAGE),
                width=120,
            )

        st.markdown(
            """
            <div class="qa-name">
                LAURA
            </div>

            <div class="qa-online">
                ● Online
            </div>
            """,
            unsafe_allow_html=True,
        )

    with q2:

        question = st.text_input(
            "Ask LAURA",
            placeholder=(
                "Ask anything about your NDA, "
                "analysis or corrections..."
            ),
            label_visibility="collapsed",
            key="qa_question",
        )

        ask = st.button(
            "✦  Ask LAURA",
            type="primary",
            use_container_width=True,
            key="ask_button",
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


    # =====================================================
    # ASK PROCESS
    # =====================================================

    if ask:

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        elif not st.session_state.analysis_id:

            st.error(
                "Analysis context is unavailable."
            )

        else:

            try:

                with st.spinner(
                    "LAURA is thinking..."
                ):

                    answer = ask_laura(
                        st.session_state.analysis_id,
                        question.strip(),
                    )

                st.session_state.qa_history.append(
                    {
                        "question": question.strip(),
                        "answer": answer,
                    }
                )

                st.rerun()

            except requests.HTTPError as exc:

                response = getattr(
                    exc,
                    "response",
                    None,
                )

                detail = str(exc)

                if response is not None:

                    try:

                        detail = response.json().get(
                            "detail",
                            detail,
                        )

                    except Exception:
                        pass

                st.error(
                    f"Q&A failed: {detail}"
                )

            except requests.RequestException as exc:

                st.error(
                    f"Could not connect to LAURA backend: {exc}"
                )

            except Exception as exc:

                st.error(
                    f"Q&A failed: {exc}"
                )


    # =====================================================
    # CONVERSATION
    # =====================================================

    if st.session_state.qa_history:

        st.markdown(
            '<div class="section-title">'
            'Conversation'
            '</div>',
            unsafe_allow_html=True,
        )

        for item in st.session_state.qa_history:

            question_text = safe_text(
                item.get(
                    "question",
                    "",
                )
            )

            answer = item.get(
                "answer",
                "",
            )

            if isinstance(
                answer,
                dict,
            ):

                answer_text = (
                    answer.get(
                        "answer",
                        answer.get(
                            "response",
                            str(answer),
                        ),
                    )
                )

            else:

                answer_text = str(
                    answer
                )

            answer_text = safe_text(
                answer_text
            )

            st.markdown(
                f"""
                <div style="
                    margin-top:15px;
                    padding:15px;
                    border-radius:14px;
                    background:rgba(18,24,42,0.65);
                    border:
                        1px solid
                        rgba(100,120,180,0.14);
                ">

                    <div style="
                        color:#8deaff;
                        font-weight:750;
                        font-size:0.75rem;
                        margin-bottom:7px;
                    ">
                        YOU
                    </div>

                    <div style="
                        color:#dce2ee;
                        line-height:1.5;
                    ">
                        {question_text}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="qa-answer">

                    <div style="
                        color:#38ddff;
                        font-weight:800;
                        margin-bottom:7px;
                    ">
                        LAURA
                    </div>

                    {answer_text}

                </div>
                """,
                unsafe_allow_html=True,
            )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        ✦ LAURA • Legal AI Understanding & Risk Analyzer
    </div>
    """,
    unsafe_allow_html=True,
)