from typing import Any
from libprobe.asset import Asset
from ..query import query_multi


async def check_jobs(
        asset: Asset,
        asset_config: dict,
        config: dict) -> dict[str, list[dict[str, Any]]]:
    req = '/jobs'
    params = {
        'limit': 2000,
    }
    results = await query_multi(asset, asset_config, config, req, params)
    jobs = []
    for result in results:
        jobs.append({
            'name': result['id'],  # str (id)
            'displayName': result['name'],  # str (name)
            'type': result['type'],  # str
            'isDisabled': result['isDisabled'],  # bool
            'description': result['description'],  # str
            'isHighPriority': result['isHighPriority'],  # bool
        })

    return {
        'jobs': jobs,
    }
