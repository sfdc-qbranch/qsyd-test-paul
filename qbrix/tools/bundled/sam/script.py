import html
import sys
import subprocess
import os
import io
import json
from operator import itemgetter
import shutil
import copy
from datetime import datetime
import re
import csv
import random
import string


def initiate():
    suffix = "_" + ''.join(random.choices(string.ascii_uppercase, k=3))
    template_name = input('Enter a name for the Template : ')
    template_API_name = template_name.replace(" ", "_") + suffix

    auto_install = None
    while auto_install == None:
        auto_install_prompt = input(
            "Would you like the template to be auto-installed in the destination org? \nType [y]es to auto-install or [n]o to install the app manually >>> ")
        if auto_install_prompt.lower() in ["yes", "y"]:
            auto_install = True
            shutil.copy("config/auto_install_boilerplate.json", "TemplateWorkingFolder/auto-install.json")
        elif auto_install_prompt.lower() in ["no", "n"]:
            auto_install = False
        else:
            print("Please enter [y]es or [n]o.")
    return(suffix, template_name, template_API_name, auto_install)


def proj_auth(name):
    proj_folder = name
    os.chdir("Local_Repo")
    print("\nCreating temporary local Salesforce project: " + proj_folder + "\n")
    subprocess.run(["sfdx","force:project:create","--projectname",proj_folder, "--template", "analytics"], check=True)
    swd = os.getcwd()
    twd = swd + "/" + name + "/force-app/main/default/waveTemplates/" + name
    shutil.copytree("../TemplateWorkingFolder", twd)
    os.chdir(twd)
    for item in ["components","dashboards","external_files","recipes"]:
        os.mkdir(item)


    print("===== Login to Org A (the Source org) via your web browser and then return to this window...")
    orga_auth_proc = subprocess.Popen(["sfdx", "auth:web:login"],stdout=subprocess.PIPE)
    orga_auth_proc.wait()
    orga_un = "UN"
    orga_id = "ID"
    for line in io.TextIOWrapper(orga_auth_proc.stdout, encoding="utf-8"):
        orga_un = line.split()[2]
        orga_id = line.split()[6]
        break
    print('\nSuccessfully authorized ' + orga_un + ' with org ID ' + orga_id)
    org_details = {}
    org_details["username"] = orga_un
    org_details["id"] = orga_id
    return org_details


def get_access_token(username):
    # Obtain access token for org for REST API interaction
    print('\nObtaining access token (sfdx force:org:display) to use for REST API calls ... ')
    orga_display_proc = subprocess.Popen(["sfdx", "force:org:display", "-u",username],stdout=subprocess.PIPE)
    orga_display_proc.wait()
    std_out_string = ""
    for line in io.TextIOWrapper(orga_display_proc.stdout,encoding="utf-8"):
        std_out_string += line
    std_out_obj = {}
    for row in std_out_string.splitlines():
        if len(row.rsplit(maxsplit=1))>1:
            key, value = row.rsplit(maxsplit=1)
            std_out_obj[key.strip()] = value.strip()
    #access_token = std_out_string.splitlines()[5].split()[2]
    access_token = std_out_obj['Access Token']
    # instance_url = std_out_string.splitlines()[9].split()[2]
    instance_url = std_out_obj['Instance Url']
    auth_header = "'Authorization: Bearer 00Dxx000" + access_token + "'"
    auth_info_keys = ['instance_url', 'username', 'auth_header', 'access_token']
    auth_info = dict.fromkeys(auth_info_keys, None)
    auth_info['instance_url'] = instance_url
    auth_info['username'] = username
    auth_info['auth_header'] = auth_header
    auth_info['access_token'] = access_token
    return auth_info


def migrate_type():
    migrate_type = None
    while migrate_type == None:
        migrate_prompt = input(
            "What Asset Type would you like to migrate? \nType [A]pp to migrate all Dashboards in an App or [D]ashboard to migrate multiple Dashboards >>> ")
        if migrate_prompt.lower() in ["a", "app"]:
            migrate_type = True
        elif migrate_prompt.lower() in ["dashboard", "d"]:
            migrate_type = False
        else:
            print("Please enter [A]pp or [D]ashboard.")
    return migrate_type


def get_app_list(username):
    app_list_proc = subprocess.Popen(["sfdx", "analytics:app:list", "-u", username, "--json"], stdout=subprocess.PIPE)
    app_list_proc.wait()
    std_out_string = ""
    for line in io.TextIOWrapper(app_list_proc.stdout, encoding="utf-8"):
        std_out_string += line
    app_list = json.loads(std_out_string)['result']
    app_list = sorted(app_list, key=itemgetter("label"))
    select_app_message = "\nSelect a Dashboard from Org A to migrate:\n"
    for index, item in enumerate(app_list):
        select_app_message += f'{index+1}) {item["label"]} \n\tAPI Name : {item["name"]}\n'
    select_app_message += '\nSpecify the App by number(or comma separated numbers) and then press ENTER >>> '
    user_input = input(select_app_message).split(",")
    app = []
    for item in user_input:
        a = app_list[int(item) - 1]["folderid"]
        app.append(a)
    dashboard_list_proc = subprocess.Popen(["sfdx", "analytics:dashboard:list", "-u", username, "--json"], stdout=subprocess.PIPE)
    dashboard_list_proc.wait()
    std_out_string = ""

    for line in io.TextIOWrapper(dashboard_list_proc.stdout, encoding="utf-8"):
        std_out_string += line
    db_list = json.loads(std_out_string)['result']
    dashboard = [a for a in db_list if a["folderid"] in app]
    return dashboard, db_list


def get_dashboard_list(username):
    dashboard_list_proc = subprocess.Popen(["sfdx", "analytics:dashboard:list", "-u", username, "--json"], stdout=subprocess.PIPE)
    dashboard_list_proc.wait()
    orga_dashboard_options = []
    std_out_string = ""
    db_list = []
    for line in io.TextIOWrapper(dashboard_list_proc.stdout, encoding="utf-8"):
        std_out_string += line
    db_list = json.loads(std_out_string)['result']
    db_list = sorted(db_list, key=itemgetter("label"))
    db_name = ''
    user_input = []
    # user_input = '-1'
    select_a_dashboard_message = "\nSelect a Dashboard from Org A to migrate:\n"
    for item in db_list:
        try:
            item["foldername"] = item["foldername"]
        except KeyError:
            item["foldername"] = "Private Folder"

    for index, item in enumerate(db_list):
        select_a_dashboard_message += f'{index+1}) {item["label"]} \n\tAPI Name : {item["name"]} \n\tApp : {item["foldername"]}\n'
    select_a_dashboard_message += '\nSpecify the Dashboard by number(or comma separated numbers) and then press ENTER >>> '

    user_input = input(select_a_dashboard_message).split(",")
    dashboard = []

    for item in user_input:
        a = db_list[int(item) - 1]
        dashboard.append(a)
    if len(dashboard) > 0:
        a = []
        for db in dashboard:
            label = db["label"]
            a.append(label)
        s = ', '.join(a)
        print("You Selected : " + s)
    else:
        print("Invalid Selection")

    return dashboard, db_list


def check_dependency(dashboard, instance_url, auth_header, final_db_list, checked_dependency, db_dump):
    dashboard_list = []
    for db in dashboard:
        dashboard_list.append(db["name"])
    for db in dashboard_list:
        dependency_db = []
        if db in db_dump.keys():
            pass
        else:
            db_dump[db] = get_dashboard_json(db, instance_url, auth_header)
        db_json = db_dump[db]
        dependency_db.append(db)
        for widget in db_json["asset"]["state"]["widgets"]:
            try:
                if db_json["asset"]["state"]["widgets"][widget]["type"] == "link" and \
                        db_json["asset"]["state"]["widgets"][widget]["parameters"]["destinationType"] == "dashboard":
                    a = {}
                    a["name"] = db_json["asset"]["state"]["widgets"][widget]["parameters"]["destinationLink"]["name"]
                    if a["name"] not in dependency_db:
                        dependency_db.append(a["name"])
                else:
                    pass
            except KeyError:
                pass
        try:
            components = db_json["components"]
        except KeyError:
            components = []
        for comp in components:
            for widget in db_json["components"][comp]["state"]["widgets"]:
                if db_json["components"][comp]["state"]["widgets"][widget]["type"] == "link" and \
                        db_json["components"][comp]["state"]["widgets"][widget]["parameters"][
                            "destinationType"] == "dashboard":
                    a = {}
                    a["name"] = db_json["components"][comp]["state"]["widgets"][widget]["parameters"]["destinationLink"]["name"]
                    if a["name"] not in dependency_db:
                        dependency_db.append(a)
                else:
                    pass

        checked_dependency.append(db)
        final_db_list.append(db)
        for x in checked_dependency:
            if x in dependency_db:
                dependency_db.remove(x)
        for db in dependency_db:
            a = {}
            a["name"] = db
            b = []
            b.append(a)
            check_dependency(b, instance_url, auth_header, final_db_list, checked_dependency, db_dump)

    return(final_db_list)


def get_dashboard_json(dashboardId, instance_url, auth_header):
    std_out_string = ""
    print("\t\tObtaining Dashboard JSON...")
    get_dashboard_curl_cmd = ["curl", "-X", "GET", instance_url + "/services/data/v56.0/wave/dashboards/" + dashboardId + "/bundle", "-H", auth_header]
    print("\t\t\t" + " ".join(get_dashboard_curl_cmd))
    std_out_string = ""
    get_dashboard_curl_proc = subprocess.Popen(" ".join(get_dashboard_curl_cmd), shell=True, stdout=subprocess.PIPE)
    for line in io.TextIOWrapper(get_dashboard_curl_proc.stdout, encoding="utf-8"):
        std_out_string += line
    get_dashboard_curl_proc.wait()
    std_out_string = std_out_string.replace("&quot;", "\\\"")
    std_out_string = std_out_string.replace("&#92;", "\\\\")
    std_out_string = html.unescape(std_out_string)
    dashboard_json_bundle = json.loads(std_out_string)
    return dashboard_json_bundle


def get_dataset_external_files(datasetId, datasetName, xmds_json,datasets,fields,username, suffix, limit):
    swd = os.getcwd()
    os.chdir(swd+'/external_files')
    print("\t\tObtaining Dataset CSV for " + datasetName + " ...")
    with open(datasetName + suffix + ".csv", "wb") as out:
        std_err_string = ""
        dataset_fetch_proc = subprocess.Popen(
            ["sfdx", "analytics:dataset:rows:fetch", "-u", username, "-n", datasetName, "-r", "csv", "--limit", str(limit)],
            stdout=out, stderr=subprocess.PIPE)
        for line in io.TextIOWrapper(dataset_fetch_proc.stderr, encoding="utf-8"):
            std_err_string += line
        while "Your dataset has not been queried in a while" in std_err_string:
            std_err_string = ""
            dataset_fetch_proc = subprocess.Popen(["sfdx", "analytics:dataset:rows:fetch", "-u", username, "-n",
                                                   datasetName, "-r", "csv", "--limit", "1000000"], stdout=out,
                                                  stderr=subprocess.PIPE)
            for line in io.TextIOWrapper(dataset_fetch_proc.stderr, encoding="utf-8"):
                std_err_string += line
        dataset_fetch_proc.wait()

    # Change column header periods to underscores in CSV file
    dataset_fieldnames_list = []
    with open(datasetName + suffix + ".csv") as csv_in_file, open(datasetName + suffix + ".out", "w") as csv_out_file:
        reader = csv.reader(csv_in_file)
        writer = csv.writer(csv_out_file)
        dataset_fieldnames_list = next(reader)  # Read the header
        dataset_fieldnames_list = [h.replace(".", "_") for h in dataset_fieldnames_list]
        writer.writerow(dataset_fieldnames_list)
        for row in reader:
            writer.writerow(row)
    os.rename(datasetName + suffix + ".out", datasetName + suffix + ".csv")
    with open(datasetName + suffix + ".csv") as csvfile:
        csvreader = csv.DictReader(csvfile)
        dataset_first100rows_list = list(csvreader)[0:100]
    with open(datasetName + suffix + ".csv") as csvfile:
        csvreader = csv.DictReader(csvfile)
        dataset_csv_fields_dict = dict(list(csvreader)[0])
        dataset_csv_fields = list(dataset_csv_fields_dict.keys())
    # print("\t\t\tDataset Id: " + dataset_id)
    # print("\t\tObtaining Main XMD for Dataset...")
    std_out_string = ""
    s1 = json.dumps(xmds_json[datasetId])
    try:
        s2 = json.dumps(datasets[datasetName]["userXmd"])
    except KeyError:
        s2 = json.dumps(xmds_json[datasetId])
    ds_mainxmd_file_obj = json.loads(s1)
    ds_userxmd_file_obj = json.loads(s2)
    ds_userxmd_file_obj["dates"] = []

    for keys in ["createdBy", "createdDate", "dataset", "language", "lastModifiedBy", "lastModifiedDate", "type", "url"]:
        try:
            ds_userxmd_file_obj.pop(keys)
            ds_mainxmd_file_obj.pop(keys)
        except KeyError:
            pass
    for key in ["derivedDimensions", "derivedMeasures", "measures", "dimensions"]:
        i = 0
        try:
            while i < len(ds_userxmd_file_obj[key]):
                for keys in ["customActionsEnabled", "fullyQualifiedName", "isMultiValue", "linkTemplateEnabled", "origin",
                             "salesforceActionsEnabled", "showInExplorer"]:
                    try:
                        ds_userxmd_file_obj[key][i].pop(keys)
                    except KeyError:
                        pass
                i += 1
        except KeyError:
            pass
        i = 0
        while i < len(ds_mainxmd_file_obj[key]):
            for keys in ["customActionsEnabled", "fullyQualifiedName", "isMultiValue", "linkTemplateEnabled", "origin",
                         "salesforceActionsEnabled", "showInExplorer"]:
                try:
                    ds_mainxmd_file_obj[key][i].pop(keys)
                except KeyError:
                    pass
            i += 1
    for items in ["dimensions","derived_dimensions"]:
        try:
            for field in ds_userxmd_file_obj[items]:
                for member in field["members"]:
                    a = ""
                    b = ""
                    try:
                        a = member["label"]
                    except KeyError:
                        pass
                    try:
                        b = member["member"]
                    except KeyError:
                        pass
                    if a == "":
                        member["label"] = b
                    if b == "":
                        member["member"] = a
        except KeyError:
            pass
    ds_userxmd_file_lines = json.dumps(ds_userxmd_file_obj, indent=0)
    ds_userxmd_file_underscores = ""
    for line in ds_userxmd_file_lines.splitlines():
        # Don't replace periods in customFormat
        if "\"customFormat\"" in line:
            ds_userxmd_file_underscores += line
            continue
        # Don't replace period after row in linkTemplate
        if "\"linkTemplate\"" in line:
            ds_userxmd_file_underscores += (line.replace(".", "_")).replace("row_", "row.")
        else:
            ds_userxmd_file_underscores += line.replace(".", "_")

    # Save updated User XMD file
    with open(datasetName + suffix + "_XMD.json", "w") as f:
        f.writelines(ds_userxmd_file_underscores)

    # CREATE DATASET SCHEMA FILE FOR THE CSV based on Main XMD
    # Create schema JSON for the dataset based on boilerplate
    shutil.copy("../../../../../../../../config/dataset_schema_boilerplate.json", datasetName + suffix + ".json")

    ds_schema_file_obj = {}
    with open(datasetName + suffix + ".json", "r") as f:
        ds_schema_file_obj = json.load(f)

    # Create XMD python dict from file
    ds_xmd_file_obj = ds_mainxmd_file_obj

    # Update schema top-level info
    ds_schema_file_obj["objects"][0]["fullyQualifiedName"] = datasetName + suffix + "_csv"
    ds_schema_file_obj["objects"][0]["label"] = datasetName + suffix + ".csv"
    ds_schema_file_obj["objects"][0]["name"] = datasetName + suffix + "_csv"

    ds_fields = [k for k in fields if k["dataset"] == datasetName+ suffix and k["type"] in ["dimension", "measure", "Date_date"]]

    ds_mainxmd_measures = ds_mainxmd_file_obj["measures"]
    ds_mainxmd_derived_measures = ds_mainxmd_file_obj["derivedMeasures"]
    ds_mainxmd_all_measures = ds_mainxmd_measures + ds_mainxmd_derived_measures
    ds_mainxmd_dates = ds_mainxmd_file_obj["dates"]
    ds_mainxmd_dimensions = ds_mainxmd_file_obj["dimensions"]
    ds_mainxmd_derived_dimensions = ds_mainxmd_file_obj["derivedDimensions"]
    ds_mainxmd_all_dimensions = ds_mainxmd_dimensions + ds_mainxmd_derived_dimensions


    for idx, field in enumerate(dataset_csv_fields):
        # print("Searching for matches in XMD for field: " + field)
        # Find matches in User XMD...
        # Check for field in Measures
        matches_measure_in_xmd = False
        matches_date_in_xmd = False
        matches_dimension_in_xmd = False

        # MEASURES : Does the field have a match in MAIN XMD - Measures or Derived Measures?
        for measure in ds_mainxmd_all_measures:
            # if match, add appropriate field boilerplate to fields section of schema
            if field == measure["field"].replace(".", "_"):
                matches_measure_in_xmd = True
                # Check if decimal?
                if ("decimalDigits" in measure["format"]) and (measure["format"]["decimalDigits"] > 0):
                    this_measure_decimal = copy.deepcopy(
                        ds_schema_file_obj["objects"][0]["fields_boilerplate"]["measure_decimal"])
                    this_measure_decimal["fullyQualifiedName"] = field
                    this_measure_decimal["name"] = field
                    this_measure_decimal["label"] = measure["label"]
                    this_measure_decimal["scale"] = measure["format"]["decimalDigits"]
                    this_measure_decimal["format"] = "0." + "#" * measure["format"]["decimalDigits"]
                    ds_schema_file_obj["objects"][0]["fields"].append(this_measure_decimal)
                # Else its integer
                else:
                    this_measure_integer = copy.deepcopy(
                        ds_schema_file_obj["objects"][0]["fields_boilerplate"]["measure_integer"])
                    this_measure_integer["fullyQualifiedName"] = field
                    this_measure_integer["name"] = field
                    try:
                        this_measure_integer["label"] = measure["label"]
                    except KeyError:
                        this_measure_integer["label"] = field
                    # print(this_measure_integer)
                    ds_schema_file_obj["objects"][0]["fields"].append(this_measure_integer)

        # DATES : Does the field have a match in MAIN XMD - Dates?
        with open("../../../../../../../../config/date_config.json", "r") as f:
            datearray = json.load(f)

        if not matches_measure_in_xmd:
            for date in ds_mainxmd_dates:
                if field == date["fields"]["fullField"].replace(".", "_"):
                    matches_date_in_xmd = True
                    this_date = copy.deepcopy(ds_schema_file_obj["objects"][0]["fields_boilerplate"]["date_timestamp"])
                    # this_date["fullyQualifiedName"] = date["fullyQualifiedName"].replace(".","_")
                    this_date["fullyQualifiedName"] = field
                    this_date["name"] = field
                    this_date["label"] = date["label"]
                    sample_successful = False
                    for row in dataset_first100rows_list:
                        if row[field] != '':
                            sample_successful = True
                            sampled_date_value = row[field]
                            for dateformat in datearray:
                                try:
                                    datetime.strptime(sampled_date_value, dateformat["python"])
                                    this_date["format"] = dateformat["crma"]
                                except ValueError:
                                    pass
                    try:
                        this_date["format"]
                    except KeyError:
                        this_date["format"] = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
                    ds_schema_file_obj["objects"][0]["fields"].append(this_date)

        # DIMENSIONS : Does the field have a match in MAIN XMD - Dimensions or Derived Dimensions?
        if not matches_measure_in_xmd and not matches_date_in_xmd:
            for dimension in ds_mainxmd_all_dimensions:
                if field == dimension["field"].replace(".", "_"):
                    matches_dimension_in_xmd = True
                    this_dimension = copy.deepcopy(ds_schema_file_obj["objects"][0]["fields_boilerplate"]["dimension"])
                    this_dimension["fullyQualifiedName"] = field
                    this_dimension["name"] = field
                    this_dimension["label"] = dimension["label"]
                    ds_schema_file_obj["objects"][0]["fields"].append(this_dimension)


        # Field had no match in Main XMD -- assume it's a Dimension
        if not matches_dimension_in_xmd and not matches_date_in_xmd and not matches_measure_in_xmd:
            this_dimension = copy.deepcopy(ds_schema_file_obj["objects"][0]["fields_boilerplate"]["dimension"])
            this_dimension["fullyQualifiedName"] = field
            this_dimension["name"] = field
            this_dimension["label"] = field
            ds_schema_file_obj["objects"][0]["fields"].append(this_dimension)


    # remove fields_boilerplate from JSON
    del ds_schema_file_obj["objects"][0]["fields_boilerplate"]
    # final XMD Check
    xfields = ds_schema_file_obj["objects"][0]["fields"]
    xfield_list = []
    for xfield in xfields:
        xfield_list.append(xfield["name"])

    with open(datasetName + suffix + "_XMD.json", "r") as f:
        userxmd = json.load(f)
    for k,v in userxmd.items():
        if k in ["derivedDimensions", "derivedMeasures"]:
            for item in v:
                if item["field"] in xfield_list:
                    v.remove(item)
    with open(datasetName + suffix + "_XMD.json", "w") as f:
        json.dump(userxmd, f)


    for key in ["derivedDimensions", "derivedMeasures"]:
        s = [a for a in ds_xmd_file_obj[key] if a["field"] in xfield_list]
        ds_xmd_file_obj[key] = s

    # Save updated schema file
    with open(datasetName + suffix + ".json", "w") as f:
        json.dump(ds_schema_file_obj, f)

    os.chdir("..")


def merge_bundles(bundle):
    new_bundle = {}
    xmds = {}
    components = {}
    datasets = {}
    dashboards = {}
    for item in bundle:
        try:
            key = [item["xmds"].keys()]
            for key in item["xmds"]:
                xmds[key] = item["xmds"][key]
        except KeyError:
            pass
        try:
            key = [item["components"].keys()]
            for key in item["components"]:
                components[key] = item["components"][key]
        except KeyError:
            pass
        try:
            for k in item["datasets"]:
                datasets[k["name"]] = k
        except KeyError:
            pass
        try:
            dashboards[item["asset"]["name"]] = item["asset"]
        except KeyError:
            pass
    new_bundle["xmds"] = xmds
    new_bundle["components"] = components
    new_bundle["datasets"] = datasets
    new_bundle["dashboards"] = dashboards

    return new_bundle


def get_field_names(xmd_json, datasets, suffix):
    ds_list = {}

    for k,v in datasets.items():
        ds_list[v["id"]] = k


    ds_json = {key:val for key,val in xmd_json.items() if val["type"]=="main"}
    fields = []

    for k,v in ds_json.items():
        for date in v["dates"]:
            field = {}
            field["dataset"] = ds_list[k]
            field["type"] = "date"
            field["name"] = date["fields"]["fullField"]
            field["name_before_replace"] = str(date["fields"]["fullField"]).replace(".", "<##REPLACE_WITH_PERIOD##>")
            field["name_after_replace"] = str(date["fields"]["fullField"]).replace(".", "_")
            field["length"] = len(field["name"])
            fields.append(field)
        for dimension in v["dimensions"]:
            field = {}
            field["dataset"] = ds_list[k]
            field["type"] = "dimension"
            field["name"] = dimension["field"]
            field["name_before_replace"] = str(dimension["field"]).replace(".", "<##REPLACE_WITH_PERIOD##>")
            field["name_after_replace"] = str(dimension["field"]).replace(".", "_")
            field["length"] = len(field["name"])
            fields.append(field)
        for measure in v["measures"]:
            field = {}
            field["dataset"] = ds_list[k]
            field["type"] = "measure"
            field["name"] = measure["field"]
            field["name_before_replace"] = str(measure["field"]).replace(".", "<##REPLACE_WITH_PERIOD##>")
            field["name_after_replace"] = str(measure["field"]).replace(".", "_")
            field["length"] = len(field["name"])
            fields.append(field)
    for date in fields:
        date["dataset"] = date["dataset"] + suffix
        if date["type"]=="date":
            for type in ["","_day_epoch", "_sec_epoch", "_Second", "_Minute", "_Hour", "_Day", "_Week", "_Month", "_Quarter", "_Year"]:
                subField = date["name"] + type
                for field in fields:
                    if field["name"] ==subField:
                        field["type"] = "Date_"+field["type"]



    fields = sorted(fields, key=lambda d:d['length'], reverse=True)

    return fields, ds_list


def get_template_info(name, api_name, suffix, datasets, dashboards, components):
    with open("template-info.json", "r") as info:
        info_json = json.load(info)
        info_json["templateType"] = 'app'
        info_json["label"] = api_name
        info_json["name"] = api_name
        info_json["description"] = "This is an SE Analytics Migration Template that is optimized for fully automated selection process"
        info_json["autoInstallDefinition"]="auto-install.json"
        info_json["externalFiles"] = []
        for ds in datasets:
            a = {}
            a["label"] = datasets[ds]["label"]
            a["name"] = datasets[ds]["name"] + suffix
            a["condition"] = "${Variables.Overrides.createAllExternalFiles}"
            a["userXmd"] = "external_files/" + datasets[ds]["name"] + suffix + "_XMD.json"
            a["file"] = "external_files/" + datasets[ds]["name"] + suffix + ".csv"
            a["schema"] = "external_files/" + datasets[ds]["name"] + suffix + ".json"
            a["type"] = "CSV"
            info_json["externalFiles"].append(a)
        info_json["dashboards"] = []
        for db in dashboards:
            a = {}
            a["label"] = db["label"]
            a["name"] = db["name"] + suffix
            a["file"] = "dashboards/" + db["name"] + suffix + ".json"
            a["condition"] = "${Variables.Overrides.createAllDashboards}"
            info_json["dashboards"].append(a)
        info_json["components"] = []
        for comp in components:
            a = {}
            a["label"] = components[comp]["label"]
            a["name"] = components[comp]["name"] + suffix
            a["file"] = "components/" + components[comp]["name"] + suffix+ ".json"
            a["condition"] = "${Variables.Overrides.createAllComponents}"
            info_json["components"].append(a)
    with open("template-info.json", "w") as overwrite:
        json.dump(info_json, overwrite)

    folder_json = {"name": api_name, "label": api_name}
    with open("folder.json", "w") as overwrite:
        json.dump(folder_json, overwrite)
    return info_json


def modify_json(suffix, asset_json, asset_xmd_json, components, dashboards, columns):
    type = asset_json["type"]
    os.chdir(type+"s")
    dashboard_json = asset_json
    dashboard_xmd_json = asset_xmd_json
    datasets = dashboard_json["datasets"]
    dashboard_string = json.dumps(dashboard_json)
    filtered_fields = [d for d in columns if d["name"] != d["name_after_replace"]]
    for field in filtered_fields:
        dashboard_string = dashboard_string.replace(field["name"], field["name_after_replace"])
    dashboard_json = json.loads(dashboard_string)

    if type == "dashboard":
        for widget in dashboard_json["state"]["widgets"].values():
            if widget["type"] == "component":
                for comp in components:
                    if str(components[comp]["name"]).replace(suffix, "") == widget["parameters"]["source"]["name"]:
                        widget["parameters"]["source"]["name"] = "${App.Components['" + components[comp][
                            "label"] + "'].Name}"
                        widget["parameters"]["source"]["namespace"] = "${Org.Namespace}"
            if widget["type"] == "link" and widget["parameters"]["destinationType"]=="component":
                for comp in components:
                    if str(components[comp]["name"]).replace(suffix, "") == widget["parameters"]["destinationLink"]["name"]:
                        widget["parameters"]["destinationLink"]["name"] = "${App.Components['" + components[comp][
                            "label"] + "'].Name}"
            if widget["type"] == "chart":
                try:
                    for item in widget["parameters"]["referenceLines"]:
                        item.pop("compact")
                except KeyError:
                    pass
            else:
                pass

    for keys in ["createdBy", "createdDate", "datasets", "files", "historiesUrl", "id", "lastAccessedDate", "lastModifiedBy", "lastModifiedDate", "permissions",
                 "refreshDate", "templateAssetSourceName", "templateSourceId", "type", "url", "visibility", "allowPreview", "assetSharingUrl"]:
        try:
            dashboard_json.pop(keys)
        except KeyError:
            pass
    for keys in ["label", "name", "url"]:
        try:
            dashboard_json["folder"].pop(keys)
        except KeyError:
            pass
    dashboard_json["folder"]["id"] = "${App.Folder.Id}"
    dashboard_json["name"] = dashboard_json["name"] + suffix
    for keys in ["createdBy", "createdDate", "dataset", "language", "lastModifiedBy", "lastModifiedDate", "type", "url"]:
        try:
            dashboard_xmd_json.pop(keys)
        except KeyError:
            pass
    dashboard_json["xmd"] = dashboard_xmd_json

    for widget in dashboard_json["state"]["widgets"]:
        if dashboard_json["state"]["widgets"][widget]["type"] in ["filterpanel"]:
            for filter in dashboard_json["state"]["widgets"][widget]["parameters"]["filters"]:
                try:
                    filter["dataset"]["name"] = "${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>"+filter["dataset"]["name"]+suffix+"<##REPLACE_WITH_PERIOD##>Name}"
                except KeyError:
                    pass
        if dashboard_json["state"]["widgets"][widget]["type"] in ["image", "container"]:
            try:
                dashboard_json["state"]["widgets"][widget]["parameters"].pop("image")
            except KeyError:
                pass
        if dashboard_json["state"]["widgets"][widget]["type"] == "link" and dashboard_json["state"]["widgets"][widget]["parameters"]["destinationType"] == "lens":
            try:
                dashboard_json["state"]["widgets"][widget]["parameters"].pop("destinationLink")
            except KeyError:
                pass
        if dashboard_json["state"]["widgets"][widget]["type"] == "link" and dashboard_json["state"]["widgets"][widget]["parameters"]["destinationType"] == "dashboard":
            try:
                b = [i["label"] for i in dashboards if i["name"] == dashboard_json["state"]["widgets"][widget]["parameters"]["destinationLink"]["name"]]
                if len(b) > 0:
                    a = "${App.Dashboards['" + b[0] + "'].Name}"
                dashboard_json["state"]["widgets"][widget]["parameters"]["destinationLink"]["name"] = a
            except KeyError:
                pass

    queries_list = list(dashboard_json["state"]["steps"].keys())

    dashboard_string = json.dumps(dashboard_json)

    ##Replace periods that Tempalate Dashboard rules shouldn't replace, with appropriate tokens
    # Binding treament #1 : .result or .selection
    dashboard_string = re.sub('(\w+)\.(result|selection)', '\\1<##REPLACE_WITH_PERIOD##>\\2',
                                        dashboard_string)
    # Binding treament #2 : .asXXXX()
    dashboard_string = re.sub('\.(as\w+\(.*?\)}})', '<##REPLACE_WITH_PERIOD##>\\1',
                                        dashboard_string)
    # Any ranges (two periods in a row)...
    dashboard_string = re.sub('\.\.', '<##REPLACE_WITH_PERIOD##><##REPLACE_WITH_PERIOD##>',
                                        dashboard_string)
    # SOQL queries... any period in a SOQL query shouldn't be replaced
    dashboard_json = json.loads(dashboard_string)
    for step in dashboard_json["state"]["steps"].values():
        if step["type"] in ["soql", "saql"]:
            step["query"] = step["query"].replace(".", '<##REPLACE_WITH_PERIOD##>')
        if step["type"] in ["soql"]:
            for field in filtered_fields:
                step["query"] = step["query"].replace(field["name_after_replace"], field["name_before_replace"])

    dashboard_string = json.dumps(dashboard_json)

    for this_query in queries_list:
        # <##REMOVE_PRECEDING_PERIOD##> is needed to keep a period at Template deploy time to pass template validation
        # The Dashboard XMD needs to have a valid reference to a query for the template to successfull deploy
        dashboard_string = dashboard_string.replace('"' + this_query + '.',
                                                    '"' + this_query + '.<##REMOVE_PRECEDING_PERIOD##><##REPLACE_WITH_PERIOD##>')
    dashboard_json = json.loads(dashboard_string)


    filters = dashboard_json["state"]["filters"]
    for filter in filters:
        a = {}
        a["name"] = "${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>"+filter["dataset"]["name"]+suffix+"<##REPLACE_WITH_PERIOD##>Name}"
        filter["dataset"] = a

    ds_links = dashboard_json["state"]["dataSourceLinks"]
    for link in ds_links:
        new_fields = []
        fields = link["fields"]
        for field in fields:
            if field["dataSourceType"] == "dataset":
                a = {}
                a["dataSourceName"] = "${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>"+field["dataSourceName"]+suffix+"<##REPLACE_WITH_PERIOD##>Name}"
                a["dataSourceNamespace"] = "${Org.Namespace}"
                a["dataSourceType"] = "dataset"
                a["fieldName"] = field["fieldName"]
                new_fields.append(a)
            else:
                pass
        link["fields"] = new_fields

    steps = dashboard_json["state"]["steps"]
    for k,v in steps.items():
        if v["type"] == "aggregateflex":
            for key in ["measures","columns","sources","query"]:
                try:
                    string = json.dumps(v["query"][key])
                    string = re.sub("\.([0-9])","<REPLACE_WITH_PERIOD>\\1",string)
                    v["query"][key] = json.loads(string)
                except KeyError:
                    pass
            query_ds = v["datasets"]
            new_ds = []
            for ds in query_ds:
                a = {}
                a["name"] = "${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>" + ds["name"] + suffix + "<##REPLACE_WITH_PERIOD##>Name}"
                new_ds.append(a)
            v["datasets"] = new_ds
            try:
                source_ds = v["query"]["sources"]
            except KeyError:
                source_ds = []
            for source in source_ds:
                try:
                    source["name"] = "${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>" + source["name"] + suffix + "<##REPLACE_WITH_PERIOD##>Name}"
                except KeyError:
                    pass
        if v["type"] == "grain":
            for key in ["measures","columns","sources","query"]:
                try:
                    string = json.dumps(v["query"][key])
                    string = re.sub("\.([0-9])","<##REPLACE_WITH_PERIOD##>\\1",string)
                    v["query"][key] = json.loads(string)
                except KeyError:
                    pass
            query_ds = v["datasets"]
            new_ds = []
            for ds in query_ds:
                a = {}
                a["name"] = "${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>" + ds["name"] + suffix + "<##REPLACE_WITH_PERIOD##>Name}"
                new_ds.append(a)
            v["datasets"] = new_ds
            try:
                source_ds = v["query"]["sources"]
            except KeyError:
                source_ds = []
            for source in source_ds:
                try:
                    source["name"] = "${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>" + source["name"] + suffix + "<##REPLACE_WITH_PERIOD##>Name}"
                except KeyError:
                    pass
        if v["type"] == "saql":
            query_ds = datasets
            query = v["query"]
            for ds in query_ds:
                name = ds["name"]
                query = query.replace("load \"" + name + "\"", "load \"${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>" + name + suffix + "<##REPLACE_WITH_PERIOD##>FullyQualifiedName}\"")
            v["query"] = query
        if v["type"] == "staticflex":
            fields = v["columns"]
            for i, j in fields.items():
                try:
                    query_ds = j["dataset"]
                    new_ds = {}
                    new_ds["name"] = "${App<##REPLACE_WITH_PERIOD##>Datasets<##REPLACE_WITH_PERIOD##>" + query_ds["name"] + suffix + "<##REPLACE_WITH_PERIOD##>Name}"
                    j["dataset"] = new_ds
                except KeyError:
                    pass



    with open(dashboard_json["name"] + ".json", "w") as dashboard_file:
        json.dump(dashboard_json, dashboard_file)
    os.chdir("..")
    return dashboard_json


def action_framework(fields, ds_list, template_info, suffix):
    action_framework_template_prompts = {}
    done_adding_action_framework = False
    action_framework_field_count = 0
    with open("variables.json", "r") as f:
        variables = json.load(f)
    a = []
    for k,v in variables.items():
        if k!= "Overrides":
            a.append(k)
    for item in a:
        variables.pop(item)
    with open("variables.json", "w") as f:
        json.dump(variables,f)
    print("\n\n========== Optional: Instant Action Framework Set-Up (Quick Actions/Open Record from the Dashboard) ...")
    print("\n\nWhen spinning up the App, the App Template wizard will prompt to associate a Salesforce Record Id with any specified fields. These fields will have Quick Actions enabled (based on the Object) and Open Record will point to Record Id for every row.")
    print("\n\nIf you have chosen to Auto Install the App, you will be prompted to provide the Salesforce Record ID along with the chosen dimension to pass on to the Template while installation. These fields will have Quick Actions enabled (based on the Object) and Open Record will point to this Record Id for every row within the Dataset.")
    print("\nCurrent list of fields w/ instant Action Framework set up: ")

    while not done_adding_action_framework:
        [print(dataset + "." + field) for dataset in action_framework_template_prompts for field in
         action_framework_template_prompts[dataset]]
        yes_to_af = input(
            "\nPress ENTER to proceed/skip, or type [y]es before pressing ENTER to specify an additional field which the App Template wizard will prompt for>>>> ").lower()
        if yes_to_af not in ['y', 'yes']:
            done_adding_action_framework = True
            break
        dataset_input = []
        dimension_input = []
        user_input = "-1"
        select_a_dataset_message = "\nSelect Dataset:\n"
        ds = []
        for k,v in ds_list.items():
            a = {}
            a["id"] = k
            a["name"] = v + suffix
            ds.append(a)
        for index, item in enumerate(ds):
            item_name = item["name"]
            select_a_dataset_message += f'{index + 1}) {item_name}\n'
        select_a_dataset_message += "\nSpecify the Dataset by number and then press ENTER (or 'q' to cancel)>>> "
        while user_input != 'q' and int(user_input) not in (range(1, len(ds) + 1)):
            user_input = input(select_a_dataset_message).lower()
        if user_input == 'q':
            continue
        ds_fields = [k for k in fields if k["dataset"]==ds[int(user_input) - 1]["name"] and k["type"]=="dimension"]

        dataset_input = ds[int(user_input) - 1]["name"]
        dataset_index = int(user_input) - 1
        user_input = '-1'
        select_a_dimension_message = "\nSelect Dimension:\n"
        for index, item in enumerate(ds_fields):
            select_a_dimension_message += f'{index + 1}) {item["name_after_replace"]}\n'
        select_a_dimension_message += "\nSpecify the Dimension by number and then press ENTER (or 'q' to cancel)>>> "
        if len(ds_fields) > 0:
            while user_input != 'q' and int(user_input) not in (range(1, len(ds_fields) + 1)):
                user_input = input(select_a_dimension_message).lower()
            if user_input == 'q':
                continue

            dimension_input = ds_fields[int(user_input) - 1]["name_after_replace"]

            action_framework_field_count += 1
            action_framework_field_variable_id = "zAction_Framework_ID_" + str(action_framework_field_count)
            dataset_name = dataset_input
            field_name = dimension_input
            if dataset_name not in action_framework_template_prompts:
                action_framework_template_prompts[dataset_name] = {}
            action_framework_template_prompts[dataset_name].update(
                {field_name: {"af_var_id": action_framework_field_variable_id}})
            action_framework_template_prompts[dataset_name][field_name]["count"] = len(
                action_framework_template_prompts[dataset_name])
        else:
            print("No Dimensions found for " + dataset_input)
    if action_framework_field_count > 0:
        print("\nAdding Instant Action Framework prompt for the following fields...")
        [print(dataset + "." + field) for dataset in action_framework_template_prompts for field in
         action_framework_template_prompts[dataset]]
        # If action framework fields were provided, set-up baseline AF files.... Replace UI file with boilerplate and create new Recipe
        # Create initial ui.json
        ui_boilerplate_file = open("../../../../../../../config/ui_boilerplate.json")
        ui_boilerplate_obj = json.load(ui_boilerplate_file)
        with open("ui.json", "w") as f:
            json.dump(ui_boilerplate_obj, f)
        # Create initial Recipe
        recipe_af_boilerplate_file = open("../../../../../../../config/recipe_af_boilerplate.json")
        recipe_af_boilerplate_obj = json.load(recipe_af_boilerplate_file)
        this_recipe_name = template_info["name"] + "_af"
        recipe_af_boilerplate_obj["name"] = this_recipe_name
        recipe_af_boilerplate_obj["label"] = this_recipe_name
        recipe_af_boilerplate_obj["recipeDefinition"]["version"] = str(template_info["assetVersion"])
        if not os.path.exists("recipes"):
            os.mkdir("recipes")
        with open("recipes/" + this_recipe_name + ".json", "w") as f:
            json.dump(recipe_af_boilerplate_obj, f)
        template_info_file = open("template-info.json")
        template_info_obj = json.load(template_info_file)
        template_info_obj["recipes"] = []
        this_recipe_template_info = {
            "label": this_recipe_name,
            "name": this_recipe_name,
            "condition": "${Variables.Overrides.createAllRecipes}",
            "file": "recipes/" + this_recipe_name + ".json"
        }
        template_info_obj["recipes"].append(this_recipe_template_info)
        rules_file = open("template-to-app-rules.json")
        rules_obj = json.load(rules_file)
        try:
            rules_obj["rules"].pop(1)
        except IndexError:
            pass
        with open("template-info.json", "w") as f:
            json.dump(template_info_obj, f)
            ### FOR LOOP #1: Each Dataset = add new stream to Recipe
            # Recipe stream boilerplate
            for dataset_name in action_framework_template_prompts:
                recipe_af_ds_stream_boilerplate_file = open(
                    "../../../../../../../config/recipe_af_ds_stream_boilerplate.json")
                recipe_af_ds_stream_boilerplate_obj = json.load(recipe_af_ds_stream_boilerplate_file)
                recipe_af_ds_stream_boilerplate_string = json.dumps(recipe_af_ds_stream_boilerplate_obj)
                recipe_af_ds_stream_boilerplate_string = recipe_af_ds_stream_boilerplate_string.replace(
                    "<#DATASET_NAME#>", dataset_name)
                recipe_af_ds_stream_boilerplate_obj = json.loads(recipe_af_ds_stream_boilerplate_string)
                recipe_file = open("recipes/" + this_recipe_name + ".json")
                recipe_obj = json.load(recipe_file)
                recipe_obj["recipeDefinition"]["nodes"].update(recipe_af_ds_stream_boilerplate_obj["nodes"])
                recipe_obj["recipeDefinition"]["ui"]["nodes"].update(recipe_af_ds_stream_boilerplate_obj["ui"]["nodes"])
                recipe_obj["recipeDefinition"]["ui"]["connectors"].extend(
                    recipe_af_ds_stream_boilerplate_obj["ui"]["connectors"])
                with open("recipes/" + this_recipe_name + ".json", "w") as f:
                    json.dump(recipe_obj, f)
                ### FOR LOOP #2: Add field within the Dataset
                for field_name in action_framework_template_prompts[dataset_name]:
                    ##Dynamically generate new Recipe formula for this field and add it to the appropriate stream in the Recipe
                    recipe_af_formula_boilerplate_file = open(
                        "../../../../../../../config/recipe_af_formula_boilerplate.json")
                    recipe_af_formula_boilerplate_obj = json.load(recipe_af_formula_boilerplate_file)
                    recipe_af_formula_boilerplate_string = json.dumps(recipe_af_formula_boilerplate_obj)
                    recipe_af_formula_boilerplate_string = recipe_af_formula_boilerplate_string.replace("<#COUNT#>",
                                                                                                        str(
                                                                                                            action_framework_template_prompts[
                                                                                                                dataset_name][
                                                                                                                field_name][
                                                                                                                "count"]))
                    recipe_af_formula_boilerplate_string = recipe_af_formula_boilerplate_string.replace(
                        "<#COUNTMINUSONE#>",
                        str(action_framework_template_prompts[dataset_name][field_name]["count"] - 1))
                    recipe_af_formula_boilerplate_string = recipe_af_formula_boilerplate_string.replace(
                        "<#DATASET_NAME#>", dataset_name)
                    recipe_af_formula_boilerplate_string = recipe_af_formula_boilerplate_string.replace("<#AF_VAR_ID#>",
                                                                                                        action_framework_template_prompts[
                                                                                                            dataset_name][
                                                                                                            field_name][
                                                                                                            "af_var_id"])
                    recipe_af_formula_boilerplate_obj = json.loads(recipe_af_formula_boilerplate_string)
                    recipe_file = open("recipes/" + this_recipe_name + ".json")
                    recipe_obj = json.load(recipe_file)
                    # Add new Formula node NODE_<#COUNT#>_<#DATASET_NAME#> to the Recipe , with source NODE_<#COUNTMINUSONE#>_<#DATASET_NAME#>
                    recipe_obj["recipeDefinition"]["nodes"].update(recipe_af_formula_boilerplate_obj["nodes"])
                    # Transform node should now reference this new Formula node
                    recipe_obj["recipeDefinition"]["ui"]["nodes"]["TRANSFORM_" + dataset_name]["graph"].update(
                        recipe_af_formula_boilerplate_obj["ui"]["nodes"]["TRANSFORM_" + dataset_name]["graph"])
                    # Re-create Transform node connectors list as keys from graph
                    transform_node_connectors = []
                    formula_names_list = list(
                        recipe_obj["recipeDefinition"]["ui"]["nodes"]["TRANSFORM_" + dataset_name]["graph"].keys())
                    formula_names_zip = zip(formula_names_list, formula_names_list[1:])
                    for x, y in formula_names_zip:
                        transform_node_connectors.append({"source": x, "target": y})
                    recipe_obj["recipeDefinition"]["ui"]["nodes"]["TRANSFORM_" + dataset_name][
                        "connectors"] = copy.deepcopy(transform_node_connectors)
                    # New Source for the SAVE node should be latest FORMULA
                    # print(recipe_obj["recipeDefinition"]["nodes"]["SAVE_" + dataset_name]["sources"])
                    recipe_obj["recipeDefinition"]["nodes"]["SAVE_" + dataset_name]["sources"][0] = "NODE_" + str(
                        action_framework_template_prompts[dataset_name][field_name]["count"]) + "_" + dataset_name
                    with open("recipes/" + this_recipe_name + ".json", "w") as f:
                        json.dump(recipe_obj, f)

                    ##Add variable to variables.json
                    variables_boilerplate_file = open("../../../../../../../config/variables_boilerplate.json")
                    variables_boilerplate_obj = json.load(variables_boilerplate_file)
                    this_variable = {
                        action_framework_template_prompts[dataset_name][field_name]["af_var_id"]: copy.deepcopy(
                            variables_boilerplate_obj["action_framework_variable_boilerplate"])}
                    this_variable[action_framework_template_prompts[dataset_name][field_name]["af_var_id"]]["label"] = \
                    this_variable[action_framework_template_prompts[dataset_name][field_name]["af_var_id"]][
                        "label"].replace("<#DATASET_NAME#>.<#FIELD_NAME#>", dataset_name + "." + field_name)
                    variables_file = open("variables.json")
                    variables_obj = json.load(variables_file)
                    variables_obj.update(this_variable)
                    with open("variables.json", "w") as f:
                        json.dump(variables_obj, f)

                    ##Add variable to ui.json
                    this_ui_variable = {
                        "name": action_framework_template_prompts[dataset_name][field_name]["af_var_id"]}
                    ui_file = open("ui.json")
                    ui_obj = json.load(ui_file)
                    ui_obj["pages"][0]["variables"].append(this_ui_variable)
                    with open("ui.json", "w") as f:
                        json.dump(ui_obj, f)

                    ##User XMD file
                    userxmd_file = open("external_files/" + dataset_name + "_XMD.json")
                    userxmd_obj = json.load(userxmd_file)

                    # Remove Action Framework from existing file and Add this field as Action Framework
                    # print(userxmd_obj)
                    dimension_already_in_userxmd = False
                    for dimension in userxmd_obj["dimensions"]:
                        # print(dimension)
                        # print(field_name)
                        if dimension["field"] == field_name:
                            dimension_already_in_userxmd = True
                            # Strip out any previous action framework
                            dimension["linkTemplate"] = ""
                            dimension["linkTooltip"] = ""
                            dimension["salesforceActions"] = []
                            # Add action framework for this field
                            dimension["recordIdField"] = action_framework_template_prompts[dataset_name][field_name][
                                "af_var_id"]
                            dimension["linkTemplateEnabled"] = True
                            dimension["salesforceActionsEnabled"] = True
                    if not dimension_already_in_userxmd:
                        userxmd_obj["dimensions"].append({
                            "field": field_name,
                            "recordIdField": action_framework_template_prompts[dataset_name][field_name]["af_var_id"],
                            "linkTemplateEnabled": True,
                            "salesforceActionsEnabled": True,
                            "linkTemplate": "",
                            "linkTooltip": "",
                            "salesforceActions": []
                        })

                    with open("external_files/" + dataset_name + "_XMD.json", "w") as f:
                        json.dump(userxmd_obj, f)

                    ##Add variable replacement rule to template-to-app-rules.json ...
                    # actionframework_rules_boilerplate_file = open(
                    #     "../config/actionframework_rules_boilerplate.json")
                    # actionframework_rules_boilerplate_obj = json.load(actionframework_rules_boilerplate_file)
                    # actionframework_rules_boilerplate_string = json.dumps(actionframework_rules_boilerplate_obj)
                    # # print(actionframework_rules_boilerplate_string)
                    # actionframework_rules_boilerplate_string = actionframework_rules_boilerplate_string.replace(
                    #     "<#AF_VAR_ID#>", action_framework_template_prompts[dataset_name][field_name]["af_var_id"])
                    # actionframework_rules_boilerplate_obj = json.loads(actionframework_rules_boilerplate_string)
                    # rules_obj["rules"].extend(actionframework_rules_boilerplate_obj["rules"])
                    # with open("template-to-app-rules.json", "w") as f:
                    #     json.dump(rules_obj, f)


    if action_framework_field_count == 0:
        af = False
    else:
        af = True
    return(af)


def af_related_changes(info_json, af):
    if not af:
        info_json["recipes"] = []
        with open("template-info.json", "w") as f:
            json.dump(info_json, f)
        ui={}
        with open("ui.json", "w") as f:
            json.dump(ui, f)
    else:
        pass
    return True


def deploy(name, label, auto_install, af):

    if auto_install == True:

        a = {}
        with open("variables.json", "r") as f:
            variables = json.load(f)
        variables.pop("Overrides")
        a = {}
        if af:
            for k,v in variables.items():
                a[k] = str(input(v["label"] + " >>> "))
            with open("recipes/"+name+"_af.json", "r") as f:
                recipe_object = json.load(f)
            recipe_string=json.dumps(recipe_object)
            for k,v in a.items():
                recipe_string = recipe_string.replace("${Variables."+k+"}", v)
            recipe_object = json.loads(recipe_string)

            with open("recipes/"+name+"_af.json", "w") as f:
                json.dump(recipe_object,f)

        # with open("auto-install.json", "r") as f:
        #     auto_install_obj = json.load(f)
        # auto_install_obj["configuration"]["appConfiguration"]["values"] = a
        # with open("auto-install.json", "w") as f:
        #     json.dump(auto_install_obj, f)
        # os.chdir(swd + "/Local_Repo/" + name)
        # Now, prompt for authentication for Org B
        print("\n===== Login to Org B in your web browser and then return to this window...")
        orgb_auth_proc = subprocess.Popen(["sfdx", "auth:web:login"], stdout=subprocess.PIPE)
        orgb_auth_proc.wait()
        orgb_un = "UN"
        orgb_id = "PW"
        for line in io.TextIOWrapper(orgb_auth_proc.stdout, encoding="utf-8"):
            orgb_un = line.split()[2]
            orgb_id = line.split()[6]
            break

        print(
            'Successfully authorized ' + orgb_un + ' with org ID ' + orgb_id + '\n\nDeploying SAM Template ' + name + ' to Org B...\n')
        os.chdir("../../../../../")

        subprocess.run(["sfdx", "force:source:deploy", "-m", "WaveTemplateBundle:" + name, "-u", orgb_un],
                       check=True)


        print(
            '\n*****Success!*****\n\nMigration Complete. \n'
        )

        print("The Template will be Auto Installed shortly. \nOnce installed, Analytics Studio will open automatically. \nCheck for all the related assets in the App " +name)

        orgb_auto_install = subprocess.Popen(["sfdx", "analytics:autoinstall:app:create", "-n", name, "-u", orgb_un], stdout=subprocess.PIPE)
        orgb_auth_proc.wait()

        for line in io.TextIOWrapper(orgb_auto_install.stdout, encoding="utf-8"):
            message = line.split()[4]
            message = message[1:19]
        path = "analytics/application/" + message + "/edit"

        subprocess.run(["sfdx", "force:org:open", "-p", path, "-u", orgb_un], check=True)
    if auto_install == False:
        # Now, prompt for authentication for Org B
        print("\n===== Login to Org B in your web browser and then return to this window...")
        orgb_auth_proc = subprocess.Popen(["sfdx", "auth:web:login"], stdout=subprocess.PIPE)
        orgb_auth_proc.wait()
        orgb_un = "UN"
        orgb_id = "PW"
        for line in io.TextIOWrapper(orgb_auth_proc.stdout, encoding="utf-8"):
            orgb_un = line.split()[2]
            orgb_id = line.split()[6]
            break

        print(
            'Successfully authorized ' + orgb_un + ' with org ID ' + orgb_id + '\n\nDeploying SAM Template ' + name + ' to Org B...\n')
        os.chdir("../../../../../")
        subprocess.run(["sfdx", "force:source:deploy", "-m", "WaveTemplateBundle:" + name, "-u", orgb_un],
                       check=True)



        print(
            '\n*****Success!*****\n\nMigration Complete. \n'
        )

        print('\tYou chose to install the Template Manually. Analytics Studio will automatically open. Follow the below steps to install the template - \n\t1) Copy the App Template name below to your clipboard: \n\n\t\t' + name)
        print(
            "\n\t2) From Org B's Analytics Studio Home, select Create > App. \n\t3) Paste the name into the Search bar to find in Template Gallery, then click to select it.\n\t4) Select Continue twice, give the App a name, then select Create.\n\t5) Wait for Astro to finish his joyous skipping through the forest (Application Complete! will appear), then refresh the page.\n\t6) Have fun with your newly deployed CRMA assets in Org B!\n\n")
        keypress = input("Press any key to open Analytics Studio >>> ")
        if keypress != None:
            subprocess.run(["sfdx", "force:org:open", "-p", "analytics", "-u", orgb_un], check=True)

    return

