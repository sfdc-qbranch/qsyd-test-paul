from qbrix.tools.shared.qbrix_cci_tasks import run_cci_task
from qbrix.tools.shared.qbrix_project_tasks import check_and_update_setting


# Einstein Checks
def run_einstein_checks():
    # Check Bot Settings Exist in force-app folder
    check_and_update_setting(
        "force-app/main/default/settings/Bot.settings-meta.xml",
        "BotSettings",
        "enableBots",
        "true"
    )


# Experience Cloud Checks
def run_experience_cloud_checks():
    # Check Experience Cloud Settings Exist in force-app folder
    check_and_update_setting(
        "force-app/main/default/settings/Communities.settings-meta.xml",
        "CommunitiesSettings",
        "enableNetworksEnabled",
        "true"
    )
    check_and_update_setting(
        "force-app/main/default/settings/ExperienceBundle.settings-meta.xml",
        "ExperienceBundleSettings",
        "enableExperienceBundleMetadata",
        "true"
    )


def run_crm_analytics_checks(org_name):
    # Check that datasets are downloaded
    if org_name:
        run_cci_task("analytics_manager", org_name, mode="d", generate_metadata_desc=True)
