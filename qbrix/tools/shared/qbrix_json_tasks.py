import json

from os.path import exists
from qbrix.tools.shared.qbrix_console_utils import init_logger

log = init_logger()


def remove_json_entry(file_location, key_name):
    """ Removes an entry from a json file.
    :param file_location: The path to the json file
    :param key_name: Text Json Key which identifies the key, value pair
    """

    if key_name is None or key_name == "":
        raise Exception("Error: Missing Key Name for JSON File Update. Please check you are passing a key name.")

    if not exists(file_location):
        raise Exception(f"Error: File Path does not exist. Check the file {file_location}")

    if not str(file_location).endswith(".json"):
        raise Exception(f"Error: File provided is not a json file. Check the file {file_location}")

    try:
        with open(file_location) as json_file:
            json_file_data = json.load(json_file)

        del json_file_data[key_name]

        with open(file_location, "w") as nFile:
            json.dump(json_file_data, nFile, indent=2)

        log.info(f"Removed entry with key: {key_name} from file : {file_location}")
    except Exception as e:
        log.error(f"Failed to update json file. Error: {e}")


def get_json_file_value(file_location, key_name):
    """ Reads a value from a json file based on key name. Returns None if nothing is found or error.
    :param file_location: Relative File Path to the file you want to read.
    :param key_name: Key name for entry in json file
    :return: Value from json file identified by key name
    """

    if key_name is None or key_name == "":
        raise Exception("Error: Missing Key Name for JSON File Update. Please check you are passing a key name.")

    if not exists(file_location):
        raise Exception(f"Error: File Path does not exist. Check the file {file_location}")

    if not str(file_location).endswith(".json"):
        raise Exception(f"Error: File provided is not a json file. Check the file {file_location}")

    try:
        with open(file_location) as json_file:
            json_file_data = json.load(json_file)

        if key_name in json_file_data:
            log.info(f"{key_name} value found in {file_location}.")
            return json_file_data[key_name]
        else:
            log.info(f"No value found for {key_name} in {file_location}.")
            return None
    except Exception as e:
        log.error(f"Failed to read json file value. Error: {e}")
        return None


def update_json_file_value(file_location, key_name, new_value):
    """ Updates a scratch org json file key value with a new value. Not designed to be used with a list
    :param file_location: Relative path and file name of the file you want to update
    :param key_name: Key for the value you want to update
    :param new_value: New value to be inserted for the given key
    """

    if key_name == "":
        raise Exception("Error: Missing Key Name for JSON File Update. Please check you are passing a key name.")

    if not exists(file_location):
        raise Exception(f"Error: File Path does not exist. Check the file {file_location}")

    if not str(file_location).endswith(".json"):
        raise Exception(f"Error: File provided is not a json file. Check the file {file_location}")

    log.info(f"Updating file: {file_location}, setting key: {key_name} to a new value of :{new_value}")

    try:
        with open(file_location) as json_file:
            json_file_data = json.load(json_file)

        json_file_data[key_name] = new_value

        with open(file_location, "w") as updated_json_file:
            json.dump(json_file_data, updated_json_file, indent=2)

        log.info(f"{file_location} has been updated!")
    except Exception as e:
        log.error(f".json File Update Failed to update file: {file_location}. Error Message: {e}")

