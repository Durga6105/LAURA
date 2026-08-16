"""
LAURA - Legal AI Understanding & Risk Analyzer

Main application entry point.

Backend:
    FastAPI

Frontend:
    Streamlit
"""

from config.settings import settings


def main() -> None:
    """Display LAURA application information."""

    print("=" * 60)
    print("LAURA")
    print("Legal AI Understanding & Risk Analyzer")
    print("=" * 60)

    print(f"Environment : {settings.app_env}")
    print(f"Debug       : {settings.debug}")
    print(f"Gemini      : {settings.gemini_model}")
    print()
    print("Backend:")
    print("  uvicorn api.main:app --reload")
    print()
    print("Frontend:")
    print("  streamlit run ui/streamlit_app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()