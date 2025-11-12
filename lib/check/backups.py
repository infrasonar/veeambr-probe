from datetime import datetime, timedelta
from typing import Any
from libprobe.asset import Asset
from ..query import query_multi
from ..utils import str_to_timestamp


async def check_backups(
        asset: Asset,
        asset_config: dict,
        config: dict) -> dict[str, list[dict[str, Any]]]:
    req = '/backups'
    max_age_days = config.get('backupMaxAge', 7)
    after = datetime.now() - timedelta(days=max_age_days)
    params = {
        'limit': 2000,
        'createdAfterFilter': after.isoformat()
    }
    results = await query_multi(asset, asset_config, config, req, params)
    backups = []
    for result in results:
        backups.append({
            'name': result['id'],  # str
            'jobId': result['jobId'],  # str | None
            'policyUniqueId': result['policyUniqueId'],  # str | None
            'displayName': result['name'],  # str (name)
            'platformName': result['platformName'],  # str
            'platformId': result['platformId'],  # str
            'creationTime': str_to_timestamp(result['creationTime']),  # int
            'repositoryId': result['repositoryId'],  # str
        })

    return {
        'backups': backups,
    }
