"""Console entry point for the optional interactive demo."""

from __future__ import annotations


def main() -> None:
    """Start the workbench or explain how to install its optional dependencies."""

    try:
        from .demo_app import main as run_demo
    except ImportError as exc:
        if exc.name in {"fastapi", "uvicorn"}:
            raise SystemExit(
                "The testing app requires optional dependencies. "
                "Install them with: pip install 'model-tier-router[demo]'"
            ) from exc
        raise
    run_demo()


if __name__ == "__main__":
    main()
