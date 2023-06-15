from qbrix.tools.bundled.sam import script
import time
import os


def migrate():
    os.chdir("qbrix/tools/bundled/sam")
    start_time = time.time()
    limit = 1000000
    suffix, template_name, template_API_name, auto_install = script.initiate()
    migrate_type = script.migrate_type()
    org_details = script.proj_auth(template_API_name)
    username = org_details["username"]
    # username = "morgancurry@sfservicecrma.demo"
    auth_info = script.get_access_token(username=username)
    if migrate_type is True:
        dashboard, dashboard_list = script.get_app_list(username=auth_info["username"])
    else:
        dashboard, dashboard_list = script.get_dashboard_list(username=auth_info["username"])
    final_db_list = []
    checked_dependency = []
    db_dump = {}
    # dashboard_list = [{
    #     "dashboardid": "0FK3t000000IWUFGA4",
    #     "name": "Pipeline_Report",
    #     "label": "Pipeline Report",
    #     "folderid": "00l3t0000020HLOAA2",
    #     "foldername": "BofA_Business"
    # },{
    #     "dashboardid": "0FK3t000000IWUKGA4",
    #     "name": "New_Markets_Prospecting",
    #     "label": "Analytics by Market - Q2-2022",
    #     "folderid": "00l3t0000020HLOAA2",
    #     "foldername": "BofA_Business"
    # },{
    #     "dashboardid": "0FK3t000000IXknGAG",
    #     "name": "Cross_Sell_Dashboard",
    #     "label": "Cross Sell Dashboard",
    #     "folderid": "00l3t0000020HLOAA2",
    #     "foldername": "BofA_Business"
    # },{
    #     "dashboardid": "0FK3t000000IpwMGAS",
    #     "name": "Account_Embed1",
    #     "label": "Account_Embed",
    #     "folderid": "00l3t0000020HLOAA2",
    #     "foldername": "BofA_Business"
    # }]
    # dashboard =[{
    #     "dashboardid": "0FK3t000000IWUFGA4",
    #     "name": "Pipeline_Report",
    #     "label": "Pipeline Report",
    #     "folderid": "00l3t0000020HLOAA2",
    #     "foldername": "BofA_Business"
    # },{
    #     "dashboardid": "0FK3t000000IWUKGA4",
    #     "name": "New_Markets_Prospecting",
    #     "label": "Analytics by Market - Q2-2022",
    #     "folderid": "00l3t0000020HLOAA2",
    #     "foldername": "BofA_Business"
    # },{
    #     "dashboardid": "0FK3t000000IXknGAG",
    #     "name": "Cross_Sell_Dashboard",
    #     "label": "Cross Sell Dashboard",
    #     "folderid": "00l3t0000020HLOAA2",
    #     "foldername": "BofA_Business"
    # },{
    #     "dashboardid": "0FK3t000000IpwMGAS",
    #     "name": "Account_Embed1",
    #     "label": "Account_Embed",
    #     "folderid": "00l3t0000020HLOAA2",
    #     "foldername": "BofA_Business"
    # }]
    final_db_list = script.check_dependency(dashboard = dashboard, instance_url=auth_info["instance_url"],
                                                auth_header=auth_info["auth_header"], final_db_list=final_db_list, checked_dependency=checked_dependency, db_dump=db_dump)
    dashboard_list = [i for i in dashboard_list if i['name'] in final_db_list]

    bundle = []

    answer = None
    if dashboard_list == dashboard:
        answer = "yes"
    while answer == None:
        answer_prompt = input(
            "Dependent Dashboards (in Link Widgets) found!!!\nType [y]es to download all dashboards : \n" + "\n".join(
                [i["label"] for i in
                 dashboard_list]) + "\nor type [n]o to download the below dashboards : \n" + "\n".join(
                [i["label"] for i in
                 dashboard]) + "\nWarning : Choosing no will result in invalid Dashboard Links\n>>>")
        if answer_prompt.lower() == "yes" or answer_prompt.lower() == "y":
            answer = answer_prompt.lower()
            dashboard_list = dashboard_list
        elif answer_prompt.lower() == "no" or answer_prompt.lower() == "n":
            dashboard_list = dashboard
            answer = answer_prompt.lower()
        else:
            print("Please enter [y]es or [n]o.")
    print("Downloading Dashboards : " + ",".join([i["label"] for i in dashboard_list]) + " ... ")

    for db in dashboard_list:
        bundle_json = db_dump[db["name"]]
        bundle.append(bundle_json)

    new_bundle = script.merge_bundles(bundle)
    xmd_json = new_bundle["xmds"]
    try:
        components = new_bundle["components"]
    except KeyError:
        pass

    datasets = new_bundle["datasets"]
    fields, ds_list = script.get_field_names(xmd_json, datasets, suffix)

    for ds in datasets:
        print("For Dataset : " + ds)
        script.get_dataset_external_files(datasets[ds]["id"], datasets[ds]["name"], xmd_json, datasets,fields,username, suffix, limit)

    for comp in new_bundle["components"]:
        component_json = new_bundle["components"][comp]
        component_xmd_json = new_bundle["xmds"][new_bundle["components"][comp]["id"]]
        script.modify_json(suffix, component_json, component_xmd_json, components, dashboard_list, fields)

    for db in new_bundle["dashboards"]:
        dashboard_json = new_bundle["dashboards"][db]
        dashboard_xmd_json = new_bundle["xmds"][new_bundle["dashboards"][db]["id"]]
        modified_dashboard_json = script.modify_json(suffix, dashboard_json, dashboard_xmd_json, components, dashboard_list, fields)
    info_json = script.get_template_info(template_name, template_API_name, suffix, datasets, dashboard_list, components)
    ActionFramework = script.action_framework(fields, ds_list, info_json, suffix)
    script.af_related_changes(info_json, ActionFramework)
    script.deploy(template_API_name, template_name, auto_install, ActionFramework)

    runtime = "%.2f seconds" % (time.time() - start_time)
    print("\n\n--- %.2f seconds ---\n\n" % (time.time() - start_time))
    print("Dashboards : " + str(len(new_bundle["dashboards"])))
    print("Components : " + str(len(new_bundle["components"])))
    print("Datasets : " + str(len(new_bundle["datasets"])))
    print("-- DONE!")
    return (runtime, len(new_bundle["dashboards"]), len(new_bundle["components"]), len(new_bundle["datasets"]))


if __name__ == '__main__':
    migrate()