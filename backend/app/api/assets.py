from flask import request

from . import api_bp
from ..services.asset_service import get_asset_overview, get_asset_topology
from ..utils.response import success


@api_bp.get("/assets")
def assets_overview():
    limit = int(request.args.get("limit", 20))
    return success(get_asset_overview(limit=limit))


@api_bp.get("/assets/topology")
def assets_topology():
    return success(get_asset_topology())
