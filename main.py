from libprobe.probe import Probe
from lib.check.jobs import check_jobs
from lib.check.health import check_health
from lib.version import __version__ as version


if __name__ == '__main__':
    checks = {
        'jobs': check_jobs,
        'health': check_health,
    }

    probe = Probe("veeambr", version, checks)

    probe.start()
