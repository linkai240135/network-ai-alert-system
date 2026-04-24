import os
from pathlib import Path

from backend.app import create_app
from backend.app.services.import_service import import_cicids_parquet_directory
from backend.app.services.training_service import run_training


def main() -> None:
    os.environ["SKIP_AUTO_BOOTSTRAP"] = "1"
    app = create_app()
    parquet_dir = Path("datasets") / "cicids2017" / "machine_learning"
    with app.app_context():
        import_result = import_cicids_parquet_directory(parquet_dir, reset_existing=True)
        training_result = run_training()
        print("IMPORT_RESULT", import_result)
        print("TRAINING_RESULT", training_result)


if __name__ == "__main__":
    main()
