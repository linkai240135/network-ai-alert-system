from . import api_bp
from ..services.training_service import get_latest_training, get_training_history, get_training_trends, run_training
from ..utils.response import success


@api_bp.get("/training/latest")
def latest_training():
    return success(get_latest_training())


@api_bp.get("/training/history")
def training_history():
    return success({"items": get_training_history()})


@api_bp.post("/training/run")
def training_run():
    return success(run_training(), message="模型训练完成")


@api_bp.get("/training/trends")
def training_trends():
    return success(get_training_trends())
