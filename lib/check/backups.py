import logging
from libprobe.asset import Asset
from libprobe.check import Check
from ..query import query_multi, query
from ..utils import str_to_timestamp


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
        jobs = {}
        jobs_includes = []
        for result in results:
            jobs[result['id']] = {
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
            }

            job_id = result['id']
            for incl in result.get('virtualMachines', {}).get('includes', []):
                obj = incl.get('inventoryObject')
                if obj is not None:
                    # this is because the example shows an inventoryObject,
                    # but the API description lacks this layer. We don't know
                    # what is true
                    incl.update(obj)

                object_id_or_name = incl.get('objectId', incl['name'])
                jobs_includes.append({
                    'name': f'{job_id}_{object_id_or_name}',  # str (id)
                    'jobId': job_id,
                    'platform': incl.get('platform'),  # str
                    'size': incl.get('size'),  # str
                    'hostName': incl.get('hostName'),  # str
                    'objectName': incl.get('name'),  # str
                    'type': incl.get('type'),  # str
                    'objectId': incl.get('objectId'),  # str?
                    'urn': incl.get('urn'),  # str?
                })

        req = '/jobs/states'
        params = {
            'limit': 2000,
        }
        results = await query_multi(asset, local_config, config, req, params)
        for result in results:
            if result['id'] not in jobs:
                logging.debug(f'missing job for state: {result["id"]}')
                jobs[result['id']] = {
                    'name': result['id'],  # str (id)
                    'displayName': result.get('name'),  # str (name)
                    'type': result.get('type'),  # str
                    'isDisabled': result.get('isDisabled'),  # bool
                    'description': result.get('description'),  # str?
                    'isHighPriority': result.get('isHighPriority'),  # bool
                    'scheduleRunAutomatically':  # bool
                    result.get('schedule', {}).get('runAutomatically'),
                    'scheduleBackupWindowEnabled':
                    result.get('schedule', {}).get(
                        'backupWindow', {}).get('isEnabled'),  # bool | None
                    'scheduleRetryEnabled':
                    result.get('schedule', {}).get(
                        'retry', {}).get('isEnabled'),  # bool | None
                    'repositoryId':
                    result.get('storage', {}).get('backupRepositoryId'),  # str
                }

            jobs[result['id']].update({
                'status': result['status'],  # str
                'lastRun': str_to_timestamp(result['lastRun']),  # int
                'lastResult': result['lastResult'],  # str
                'nextRun': str_to_timestamp(result.get('nextRun')),  # int?
                'workload': result['workload'],  # str
                'objectsCount': result['objectsCount'],  # int
                'sessionId': result.get('sessionId'),  # str?
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
                'objectId': result.get('objectId'),  # str?
                'viType': result.get('viType'),  # str
                'path': result.get('path'),  # str
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

        return {
            'backupObjects': backup_objects,
            'backupRepositories': backup_repositories,
            'jobVMsIncludes': jobs_includes,
            'jobs': list(jobs.values()),
        }
