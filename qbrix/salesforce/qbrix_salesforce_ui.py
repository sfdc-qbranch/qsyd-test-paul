import json
import os
import pathlib
from abc import ABC
from cumulusci.tasks.sfdx import SFDXOrgTask
from cumulusci.core.tasks import BaseTask
from qbrix.tools.shared.qbrix_console_utils import init_logger
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.config import ScratchOrgConfig
from qbrix.salesforce.qbrix_salesforce_tasks import salesforce_query

log = init_logger()

# UI API DEFAULTS
UI_FAV_PATH = 'ui-api/favorites'


class UpsertFavorite(BaseSalesforceApiTask, ABC):
    salesforce_task = True

    task_docs = """
    Upserts a Favorite (aka Bookmark) in the target org.
    """

    task_options = {
        "org": {
            "description": "Org Alias for the target org",
            "required": False
        },
        "name": {
            "description": "The name of the favorite.",
            "required": False
        },
        "sortOrder": {
            "description": "The sort order of the favorite, from 1 to N.",
            "required": False
        },
        "targetType": {
            "description": "The type of favorite. One of these values: ListView, ObjectHome, Record or Tab",
            "required": False
        },
        "objectType": {
            "description": "If Record or ObjectHome is used at Type, a ObjectType must also be defined",
            "required": False
        }
    }

    def _init_options(self, kwargs):
        super(UpsertFavorite, self)._init_options(kwargs)
        self.name = self.options["name"] if "name" in self.options else None
        self.sortOrder = self.options["sortOrder"] if "sortOrder" in self.options else 1
        self.targetType = self.options["targetType"] if "targetType" in self.options else None
        self.objectType = self.options["objectType"] if "objectType" in self.options else None

    def _get_favs(self):
        api = self.sf
        current_favs_response = api.restful(UI_FAV_PATH, method="GET")
        if current_favs_response:
            current_favs = current_favs_response['favorites']
            if current_favs:
                return current_favs
        return None

    def _get_id(self, name, targetType, objectType=None):
        api = self.sf

        table_name = targetType

        if targetType.lower() == 'record' or targetType.lower() == 'objecthome':
            table_name = objectType

        if targetType.lower() == 'tab':
            table_name = "TabDefinition"

        response = api.query(f"SELECT Id FROM {table_name} WHERE Name = '{name}' LIMIT 1")

        if response["totalSize"] == 0:
            log.error("No Record was found in the target org. Make sure it has been deployed.")
            return None
        else:
            return response["records"][0]["Id"]

    def _create_fav(self, name, sortOrder, targetType, objectType=None):
        api = self.sf
        try:
            id = self._get_id(name, targetType, objectType)
            if id:
                api.restful(
                    UI_FAV_PATH,
                    data=json.dumps({
                        "name": name,
                        "sortOrder": sortOrder,
                        "target": id,
                        "targetType": targetType
                    }),
                    method="POST",
                )
                return True
            else:
                raise Exception("Unable to find target for Favorite within target org.")
        except Exception as e:
            log.error(f"Creation Failed: Message details: {e}")
            return False

    def _update_fav(self, name, sortOrder, fav_id):
        api = self.sf
        try:
            if fav_id:
                api.restful(
                    f"{UI_FAV_PATH}/{fav_id}",
                    data=json.dumps({
                        "name": name,
                        "sortOrder": sortOrder
                    }),
                    method="PATCH",
                )
                return True
            else:
                raise Exception("Unable to find target for Favorite within target org.")
        except Exception as e:
            log.error(f"Update Failed: Message details: {e}")
            return False

    def _run_task(self):
        log.info(f"Checking {self.name}")
        current_favorites_list = self._get_favs()
        if current_favorites_list:
            if current_favorites_list:
                result = "INSERT"
                fav_id = None

                for fav in list(current_favorites_list):
                    # Check for object based match
                    if self.targetType.lower() == 'record' or self.targetType.lower() == 'objecthome':
                        if fav['name'] == self.name and fav['targetType'] == self.targetType and fav['objectType'] == self.objectType:
                            if fav['sortOrder'] == self.sortOrder:
                                log.info(f"{self.name} is already in the favorite list. Skipping.")
                                result = None
                                break
                            else:
                                result = "UPDATE"
                                fav_id = fav['id']
                                break

                    # Check for non-sObject based Match
                    if self.targetType.lower() == 'listview' or self.targetType.lower() == 'tab':
                        if fav['name'] == self.name and fav['targetType'] == self.targetType:
                            if fav['sortOrder'] == self.sortOrder:
                                log.info(f"{self.name} is already in the favorite list. Skipping.")
                                result = None
                                break
                            else:
                                result = "UPDATE"
                                fav_id = fav['id']
                                break

                if result == "UPDATE":
                    if self._update_fav(self.name, self.sortOrder, fav_id):
                        log.info(f"{self.name} has been updated in the favorite list")

                if result == "INSERT":
                    if self._create_fav(self.name, self.sortOrder, self.targetType, self.objectType):
                        log.info(f"{self.name} has been created in the favorite list")
