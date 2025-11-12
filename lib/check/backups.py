from datetime import datetime, timedelta
from typing import Any
from libprobe.asset import Asset
from ..query import query_multi
from ..utils import str_to_timestamp


async def check_backups(
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
            'scheduleRunAutomatically':
                result['schedule']['runAutomatically'],  # bool
            'scheduleBackupWindowEnabled': result['schedule'].get(
                'backupWindow', {}).get('isEnabled'),  # bool | None
            'scheduleRetryEnabled': result['schedule'].get(
                'retry', {}).get('isEnabled'),  # bool | None
            'repositoryId': result['storage']['backupRepositoryId'],  # str
        })

    req = '/backupObjects'
    params = {
        'limit': 2000,
    }
    results = await query_multi(asset, asset_config, config, req, params)
    backup_objects = []
    for result in results:
        backup_objects.append({
            'name': result['id'],  # str (id)
            'displayName': result['name'],  # str (name)
            'description': result['description'],  # str
            'type': result['type'],  # str
            'platformName': result['platformName'],  # str
            'platformId': result['platformId'],  # str
            'restorePointsCount': result['restorePointsCount'],  # str
            'objectId': result['objectId'],  # str
            'viType': result['viType'],  # str
            'path': result['path'],  # str
        })

    req = '/backupInfrastructure/repositories'
    params = {
        'limit': 2000,
    }
    results = await query_multi(asset, asset_config, config, req, params)
    backup_repositories = []
    for result in results:
        backup_repositories.append({
            'name': result['id'],  # str (id)
            'displayName': result['name'],  # str (name)
            'description': result['description'],  # str
            'uniqueId': result['uniqueId'],  # str
            'type': result['type'],  # str
            'hostId': result['hostId'],  # str
        })

    max_age_days = config.get('backupMaxAge', 7)
    after = datetime.utcnow() - timedelta(days=max_age_days)
    req = '/backups'
    params = {
        'limit': 2000,
        'createdAfterFilter': after.isoformat()
    }
    results = await query_multi(asset, asset_config, config, req, params)
    backups = []
    for result in results:
        backups.append({
            'name': result['id'],  # str
            'jobId': result['jobId'],  # str
            'policyUniqueId': result['policyUniqueId'],  # str
            'displayName': result['name'],  # str (name)
            'platformName': result['platformName'],  # str
            'platformId': result['platformId'],  # str
            'creationTime': str_to_timestamp(result['creationTime']),  # int
            'repositoryId': result['repositoryId'],  # str
        })

    max_age_days = config.get('malwareMaxAge', 7)
    after = datetime.utcnow() - timedelta(days=max_age_days)
    malware_events = '/malwareDetection/events'
    params = {
        'limit': 2000,
        'detectedAfterTimeUtcFilter': after.isoformat()
    }
    results = await query_multi(asset, asset_config, config, req, params)
    malware_events = []
    for result in results:
        malware_events.append({
            'name': result['id'],  # str (id)
            'type': result['type'],  # str
            'detectionTimeUtc':
                str_to_timestamp(result['detectionTimeUtc']),  # int
            'machineUuid': result.get('machine', {}).get('uuid'),  # str
            'machineName': result.get('machine', {}).get('displayName'),  # str
            'machineBackupObjectId':
                result.get('machine', {}).get('backupObjectId'),  # str
            'state': result['state'],  # str
            'details': result['details'],  # str
            'source': result['source'],  # str
            'severity': result['severity'],  # str
            'createdBy': result['createdBy'],  # str
            'engine': result['engine'],  # str
        })

    return {
        'backupObjects': backup_objects,
        'backupRepositories': backup_repositories,
        'backups': backups,
        'jobs': jobs,
        'malwareEvents': malware_events,
    }
