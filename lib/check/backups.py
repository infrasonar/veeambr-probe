from datetime import datetime, timedelta, UTC
from libprobe.asset import Asset
from libprobe.check import Check
from ..query import query_multi
from ..utils import str_to_timestamp, iso_fmt


class CheckBackups(Check):
    key = 'backups'
    unchanged_eol = 14400

    @staticmethod
    async def run(asset: Asset, local_config: dict, config: dict) -> dict:

        req = '/jobs'
        params = {
            'limit': 2000,
        }
        results = await query_multi(asset, local_config, config, req, params)
        jobs = []
        for result in results:
            jobs.append({
                'name': result['id'],  # str (id)
                'displayName': result['name'],  # str (name)
                'type': result['type'],  # str
                'isDisabled': result['isDisabled'],  # bool
                'description': result.get('description'),  # str?
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
        results = await query_multi(asset, local_config, config, req, params)
        backup_objects = []
        for result in results:
            backup_objects.append({
                'name': result['id'],  # str (id)
                'displayName': result['name'],  # str (name)
                'description': result.get('description'),  # str?
                'type': result['type'],  # str
                'platformName': result['platformName'],  # str
                'platformId': result['platformId'],  # str
                'restorePointsCount': result['restorePointsCount'],  # int
                'objectId': result['objectId'],  # str
                'viType': result['viType'],  # str
                'path': result['path'],  # str
            })

        req = '/backupInfrastructure/repositories'
        params = {
            'limit': 2000,
        }
        results = await query_multi(asset, local_config, config, req, params)
        backup_repositories = []
        for result in results:
            backup_repositories.append({
                'name': result['id'],  # str (id)
                'displayName': result['name'],  # str (name)
                'description': result.get('description'),  # str?
                'uniqueId': result['uniqueId'],  # str
                'type': result['type'],  # str
                'hostId': result.get('hostId'),  # str?
            })

        max_age_days = config.get('backupMaxAge', 7)
        after = datetime.now(UTC) - timedelta(days=max_age_days)
        req = '/backups'
        params = {
            'limit': 2000,
            'createdAfterFilter': iso_fmt(after)
        }
        results = await query_multi(asset, local_config, config, req, params)
        backups = []
        for result in results:
            backups.append({
                'name': result['id'],  # str
                'jobId': result['jobId'],  # str
                'jobName': result['name'],  # str
                'policyUniqueId': result['policyUniqueId'],  # str
                'platformName': result['platformName'],  # str
                'platformId': result['platformId'],  # str
                'creationTime':
                    str_to_timestamp(result['creationTime']),  # int
                'repositoryId': result['repositoryId'],  # str
            })

        return {
            'backupObjects': backup_objects,
            'backupRepositories': backup_repositories,
            'backups': backups,
            'jobs': jobs,
        }
