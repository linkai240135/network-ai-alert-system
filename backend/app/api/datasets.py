from flask import request

from . import api_bp
from ..services.dataset_service import get_dataset_overview, get_import_overview
from ..services.import_service import import_cicids_file, import_cicids_files
from ..services.settings_service import get_setting_map
from ..services.training_service import run_training
from ..utils.response import failure, success


@api_bp.get("/datasets/overview")
def dataset_overview():
    return success(get_dataset_overview())


@api_bp.get("/datasets/import-jobs")
def dataset_import_jobs():
    return success(get_import_overview())


@api_bp.post("/datasets/import-cicids")
def dataset_import_cicids():
    if "file" not in request.files:
        return failure("请上传 CICIDS2017 CSV 文件")
    file = request.files["file"]
    job = import_cicids_file(file)
    settings = get_setting_map()
    training = None
    if settings.get("auto_train_after_import", "true").lower() == "true":
        training = run_training()
    return success({"job": job, "training": training}, message="CICIDS2017 数据导入完成")


@api_bp.post("/datasets/import-cicids-batch")
def dataset_import_cicids_batch():
    files = request.files.getlist("files")
    if not files:
        return failure("请至少上传一个 CICIDS2017 CSV 文件")
    result = import_cicids_files(files)
    settings = get_setting_map()
    training = None
    if settings.get("auto_train_after_import", "true").lower() == "true":
        training = run_training()
    return success({"import": result, "training": training}, message="CICIDS2017 多文件导入完成")
