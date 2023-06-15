# SETUP TASKS (DELETE THIS SECTION ONCE COMPLETE)

TO DO (CAN BE COMPLETED LATER IF NEEDED): [Create a Documentation for this Q Brix.](https://salesforce.quip.com/6D2eA9ft6x2O)

TO DO: Run the Q Brix Setup Task

    cci task run setup_qbrix

# Q Brix Title

## Table of Contents

- [About](#about)
- [Getting Started](#getting_started)
- [Quick Examples](#usage)
- [Metadata Support](#support)

## About <a name = "about"></a>

Write a few words describing your Q Brix.

## Getting Started <a name = "getting_started"></a>

If you have not worked on Q Brix before, check out this guide: https://confluence.internal.salesforce.com/display/QNEXTGENDEMOS/Prerequisites

### Prerequisites

MacOS and Linux Users: https://confluence.internal.salesforce.com/display/QNEXTGENDEMOS/Required+Setup

Windows Users: https://confluence.internal.salesforce.com/display/QNEXTGENDEMOS/Windows+Users

### Development

To work on this project in a scratch org:

Get help on naming and building Q Brix from here: https://confluence.internal.salesforce.com/pages/viewpage.action?pageId=487362018

1. [Set up CumulusCI](https://cumulusci.readthedocs.io/en/latest/tutorial.html)
2. Run `cci flow run dev_org --org dev` to deploy this project.
3. Run `cci org browser dev` to open the org in your browser.

Make changes in the org

4. Run `cci task run list_changes --org dev` to list changes made in the org. Use the list_changes and retrieve_changes task sections to exclude anything you don't want
5. Run `cci task run retrieve_changes --org dev` to retrieve the changes made.
6. Remember to review source code which has been pulled down.

QA Test

7. Run `cci org remove qa` to remove any previous qa orgs. Then `cci flow run qa_org --org qa` to create a new QA org and test the deployment.
8. Repair any issues if any are noted until the deployment works. To test small changes/fixes, just re-run `cci flow run qa_org --org qa`
9. Run `cci org remove qa` and `cci org remove dev` once complete.

Create Pull Request

10. Once you are happy with the changes made, create a Pull Request for your branch. This will be reviewed by the Solution Development team and you will be notified when the changes have been merged into the main branch

Create Trialforce Template

11. If you don't have your TSO already connected, then connect to your TSO org using `cci org connect OrgNameHere` (replacing orgNamehere with your chosen name for the org - it can be anything!)
12. Run `cci flow run tso_deploy --org OrgNameHere` to deploy your latest updates into the TSO.
13. Create a new Trialforce template in the TSO. Tip: You can quickly login to your TSO using `cci org browser OrgNameHere`

## Metadata Type Support <a name = "support"></a>

You will see these exclusions in the cumulusci.yml file, within the tasks > list_changes and tasks > retrieve_changes sections.

Some Metadata types are not supported with these packs or have been replaced with other types. See list below for notes:

- Profile - These are not supported as they don't pull all related information, fields etc. Use Permission Sets instead.
- FeatureParameter - Currently not supported if they are managed.
- 'AuraDefinition:' - Replaced by AuraDefinitionPack
- SiteDotCom - Replaced by ExperienceCloudPack (remember to enable ExperienceBundle API!)
- ManagedTopics - Not Supported
- AppMenu - Currently a Known Issue - Track here: https://trailblazer.salesforce.com/issues_view?id=a1p30000000T5dqAAC
