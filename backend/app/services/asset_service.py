from __future__ import annotations

from datetime import datetime

from ..extensions import db
from ..models import Asset, SecurityIncident


def derive_asset_context(service_profile: dict, result: dict, features: dict) -> dict:
    port = int(service_profile.get("port", 0))
    protocol = service_profile.get("protocol", "N/A")
    service_name = service_profile.get("name", "Unknown Service")
    packet_rate = int(float(features.get("packet_rate", 0)))
    byte_rate = int(float(features.get("byte_rate", 0)))
    flow_duration = int(float(features.get("flow_duration", 0)))
    src_octet = 10 + (packet_rate % 180)
    dst_octet = 20 + (byte_rate % 180)
    zone_index = 1 + (flow_duration % 6)
    source_ip = f"10.{zone_index}.{src_octet}.{(port % 200) + 10}"
    destination_ip = f"172.16.{zone_index}.{dst_octet}"
    asset_code = f"ASSET-{protocol}-{port}"
    asset_name = f"{service_name}-{zone_index:02d}"
    business_unit = "通信核心业务区" if port in {80, 443, 3306} else "接入与运维区"
    asset_type = "database" if port == 3306 else "application"
    return {
        "asset_code": asset_code,
        "asset_name": asset_name,
        "ip_address": destination_ip,
        "business_unit": business_unit,
        "owner_team": "网络安全运营中心",
        "asset_type": asset_type,
        "service_name": service_name,
        "protocol": protocol,
        "port": port,
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "risk_score": min(1.0, float(result.get("confidence", 0)) * (1.1 if result.get("risk_level") == "高" else 0.8)),
        "tags": [service_profile.get("keywords", ""), result.get("attack_stage", ""), result.get("label", "")],
    }


def upsert_asset(asset_context: dict) -> Asset:
    asset = Asset.query.filter_by(asset_code=asset_context["asset_code"]).first()
    if not asset:
        asset = Asset(
            asset_code=asset_context["asset_code"],
            asset_name=asset_context["asset_name"],
            ip_address=asset_context["ip_address"],
            business_unit=asset_context["business_unit"],
            owner_team=asset_context["owner_team"],
            asset_type=asset_context["asset_type"],
            service_name=asset_context["service_name"],
            protocol=asset_context["protocol"],
            port=asset_context["port"],
            risk_score=asset_context["risk_score"],
            tags=asset_context["tags"],
            last_seen_at=datetime.utcnow(),
        )
        db.session.add(asset)
    else:
        asset.asset_name = asset_context["asset_name"]
        asset.ip_address = asset_context["ip_address"]
        asset.business_unit = asset_context["business_unit"]
        asset.owner_team = asset_context["owner_team"]
        asset.asset_type = asset_context["asset_type"]
        asset.service_name = asset_context["service_name"]
        asset.protocol = asset_context["protocol"]
        asset.port = asset_context["port"]
        asset.risk_score = max(asset.risk_score, asset_context["risk_score"])
        asset.tags = sorted({*(asset.tags or []), *(asset_context["tags"] or [])})
        asset.last_seen_at = datetime.utcnow()
    db.session.flush()
    return asset


def get_asset_overview(limit: int = 20) -> dict:
    assets = Asset.query.order_by(Asset.risk_score.desc(), Asset.last_seen_at.desc()).limit(limit).all()
    risky_assets = Asset.query.filter(Asset.risk_score >= 0.7).count()
    incident_bound_assets = (
        db.session.query(Asset.id)
        .join(SecurityIncident, SecurityIncident.asset_id == Asset.id)
        .distinct()
        .count()
    )
    return {
        "stats": {
            "total": Asset.query.count(),
            "riskyAssets": risky_assets,
            "incidentBoundAssets": incident_bound_assets,
        },
        "items": [item.to_dict() for item in assets],
    }


def get_asset_topology() -> dict:
    assets = Asset.query.order_by(Asset.risk_score.desc(), Asset.last_seen_at.desc()).limit(20).all()
    incidents = SecurityIncident.query.order_by(SecurityIncident.last_seen_at.desc()).limit(40).all()

    nodes = []
    links = []
    source_seen = set()
    asset_seen = set()

    for asset in assets:
        nodes.append(
            {
                "id": asset.asset_code,
                "name": asset.asset_name,
                "category": "asset",
                "symbolSize": 34 + min(int(asset.risk_score * 20), 18),
                "riskScore": round(asset.risk_score, 4),
                "protocol": asset.protocol,
                "port": asset.port,
            }
        )
        asset_seen.add(asset.asset_code)

    for incident in incidents:
        if incident.source_ip not in source_seen:
            nodes.append(
                {
                    "id": incident.source_ip,
                    "name": incident.source_ip,
                    "category": "source",
                    "symbolSize": 42,
                    "riskScore": 1 if incident.severity == "高" else 0.6,
                }
            )
            source_seen.add(incident.source_ip)
        if incident.asset and incident.asset.asset_code in asset_seen:
            links.append(
                {
                    "source": incident.source_ip,
                    "target": incident.asset.asset_code,
                    "label": incident.attack_type,
                    "severity": incident.severity,
                }
            )

    return {
        "nodes": nodes,
        "links": links,
        "stats": {
            "nodeCount": len(nodes),
            "linkCount": len(links),
        },
    }
