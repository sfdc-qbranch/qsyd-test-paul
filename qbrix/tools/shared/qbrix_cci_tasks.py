import os
import shutil
import subprocess
from abc import ABC

from cumulusci.core.utils import import_global
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import CURRENT_TASK, BaseTask
from cumulusci.cli.runtime import CliRuntime


def rebuild_cci_cache(cci_project_cache_directory: str = ".cci/projects") -> bool:
    """
    Rebuilds the CCI projects Cache folder using the dev_org flow from CCI

    Args:
        cci_project_cache_directory (str): Relative File Path to the CCI Projects Directory

    Returns:
        bool: True when complete
    """

    # Cleanup Current Directory
    if os.path.exists(cci_project_cache_directory):
        shutil.rmtree(cci_project_cache_directory)

    # Run dev_org flow to capture all requirements
    try:
        subprocess.run(["cci", "flow", "info", "dev_org"])
    except Exception as e:
        raise Exception(f"Failed to rebuild CCI cache. Error Message: {e}")

    # Return True to confirm completion
    return True


def _parse_task_options(options, task_class, task_config):
    """
    Task Option Parser
    """

    if "options" not in task_config.config:
        task_config.config["options"] = {}
    # Parse options and add to task config
    if options:
        for name, value in options.items():
            # Validate the option
            if name not in task_class.task_options:
                raise TaskOptionsError(
                    'Option "{}" is not available for task {}'.format(
                        name, task_class
                    )
                )

            # Override the option in the task config
            task_config.config["options"][name] = value

    return task_config


def _run_task(task):
    task()
    return task.return_values


def run_cci_task(task_name: str, org_name: str = None, **options) -> bool:
    """
    Runs a given task using the name of the task.

    Args:
        task_name (str): The name of the task to run
        org_name (str): The optional alias for the org, this defaults to "dev"
        options: Additional options for the task that you want to provide, for example the 'deploy' task has an option for path, so you can define path='my/path/here'

    Example Usage:

    run_cci_task('deploy', 'dev', path='force-app')
    """

    if not org_name:
        org_name = "dev"

    if getattr(CURRENT_TASK, "stack", None) and CURRENT_TASK.stack[0].project_config:
        _project_config = CURRENT_TASK.stack[0].project_config
    else:
        _project_config = CliRuntime().project_config

    if getattr(CURRENT_TASK, "stack", None) and CURRENT_TASK.stack[0].org_config:
        _org = CURRENT_TASK.stack[0].org_config
    else:
        _org = CliRuntime().project_config.keychain.get_org(org_name)

    task_config = CliRuntime().project_config.get_task(task_name)
    task_class = import_global(task_config.class_path)
    task_config = _parse_task_options(options, task_class, task_config)
    task = task_class(
        task_config.project_config or _project_config,
        task_config,
        org_config=_org,
    )

    try:
        _run_task(task)
        return True
    except Exception as e:
        raise Exception(f"Task Runner Failed. {e}")


def run_cci_flow(flow_name: str, org_name: str = None, **options) -> bool:
    """
    Runs a given flow using the flow name and optional org name along with optional options.

    Args:
        flow_name (str): The name of the flow to run, for example deploy_qbrix
        org_name (str): Optional alias for the org. This defaults to "dev"

    Returns:
        bool: True if the flow has executed without error

    Example Usage:
    run_cci_flow('deploy_qbrix', 'dev')
    """

    if not org_name:
        org_name = "dev"

    org_config = CliRuntime().project_config.keychain.get_org(org_name)
    flow_coordinator = CliRuntime().get_flow(flow_name, options=options)

    try:
        flow_coordinator.run(org_config)
        return True
    except Exception as e:
        raise Exception(f"Flow Runner Failed. {e}")


class TestRun(BaseTask, ABC):
    # This has been added and left as a general test runner for testing only
    task_options = {
        "org": {
            "description": "Org alias",
            "required": False
        },
    }

    def _run_task(self):
        pass
