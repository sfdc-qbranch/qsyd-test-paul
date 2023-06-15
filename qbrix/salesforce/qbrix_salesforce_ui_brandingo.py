import base64
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

class Brandingo(BaseSalesforceApiTask, ABC):

  salesforce_task = True

  task_docs = """
  Used to set the logo and branding for an org from the cli. Inspired by the work of Brian Ricter and Ellie Rinehart from salesforce.org
  """

  task_options = {
        "org": {
          "description": "Org Alias for the target org",
          "required": False
        },
        "theme": {
          "description": "The name of the theme to update. Defaults to Q Brix Theme",
          "required": False
        },
        "PrimaryColour": {
          "description": "Hex Code for the Primary Color",
          "required": False
        },
        "SecondaryColor": {
          "description": "Hex Code for the Secondary color",
          "required": False
        },
        "LogoPath": {
          "description": "Path to image file for the logo",
          "required": False
        },
        "experience_cloud_sites": {
          "description": "List of experience cloud sites you also want to update",
          "required": False
        }
  }

  def _init_options(self, kwargs):
    super(Brandingo, self)._init_options(kwargs)
    self.theme = self.options["theme"] if "theme" in self.options else "QBrix"
    self.PrimaryColour = self.options["PrimaryColour"] if "PrimaryColour" in self.options else None
    self.SecondaryColor = self.options["SecondaryColor"] if "SecondaryColor" in self.options else None
    self.LogoPath = self.options["LogoPath"] if "LogoPath" in self.options else None
    self.experience_cloud_sites = self.options["experience_cloud_sites"] if "experience_cloud_sites" in self.options else []

  def _run_task(self):

    image_path = self.LogoPath

    # Upload the image file
    with open(image_path, "rb") as file:
        encoded_image = base64.b64encode(file.read()).decode("utf-8")
    logo_id = self.sf.ContentVersion.create({
        "Title": os.path.basename(image_path),
        "PathOnClient": image_path,
        "VersionData": encoded_image,
        "IsMajorVersion": True
    })["ContentDocumentId"]

    # Check if a DefaultBrandingSet with the name "Theme4d" already exists
    existing_branding_sets = self.sf.BrandingSet.select("Id", "Name").where(f"Name = '{self.theme}'")
    if existing_branding_sets:
        # Update the existing DefaultBrandingSet with the new logo and color settings
        branding_set_id = existing_branding_sets[0]["Id"]
        self.sf.DefaultBrandingSet.update(branding_set_id, {
            "PrimaryColor": self.PrimaryColour,
            "SecondaryColor": self.SecondaryColor,
            "SmallLogoId": logo_id,
            "MediumLogoId": logo_id,
            "LargeLogoId": logo_id
        })
    else:
        # Create a new DefaultBrandingSet with the specified name and logo and color settings
        branding_set_id = self.sf.BrandingSet.create({
            "Name": f"{self.theme}",
            "DefaultBrandingSet": {
                "PrimaryColor": self.PrimaryColour,
                "SecondaryColor": self.SecondaryColor,
                "SmallLogoId": logo_id,
                "MediumLogoId": logo_id,
                "LargeLogoId": logo_id
            }
        })["DefaultBrandingSetId"]

    # Update the org UI settings to use the new DefaultBrandingSet
    org_settings = self.sf.Organization.get()
    org_settings["InstanceName"] = self.sf.sf_instance[:-3]
    org_settings["UiSkin"] = self.theme
    org_settings["DefaultBrandingSetId"] = branding_set_id
    self.sf.Organization.update(self.sf.Organization.get()["Id"], org_settings)

    if len(self.experience_cloud_sites) > 0:

      # Retrieve the Experience Site's configuration settings
      site_config = self.sf.ExperienceSite.get_by_name(self.sitename)["SiteConfiguration"]

      # Update the configuration settings with the new logo and color settings
      site_config["brandingSet"] = {
          "primaryColor": self.PrimaryColour,
          "secondaryColor": self.SecondaryColor,
          "logoSmallAssetId": logo_id,
          "logoMediumAssetId": logo_id,
          "logoLargeAssetId": logo_id
      }

      # Update the Experience Site's configuration settings
      self.sf.ExperienceSite.update(self.sitename, {
          "SiteConfiguration": site_config
      })       
