from . import api_bp
from ..services.dashboard_service import build_dashboard_summary
from ..utils.response import success


@api_bp.get("/dashboard/summary")
def dashboard_summary():
    return success(build_dashboard_summary())
