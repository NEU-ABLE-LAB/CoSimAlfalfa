import tempfile
import zipfile
import os
from CoSimDict import DATA, SETTING, CONTROL


# Note: the keys of record and output_step are not necessarily 1-to-1 matched
#       e.g., record[DATA.STATUS][DATA.HEATING_SETPOINT_DEADBAND_APPLIED].append(output_step[DATA.HEATING_SETPOINT_BASE])
#             record[DATA.STATUS][DATA.HEATING_SETPOINT_BASE].append(output_step[DATA.HEATING_SETPOINT_NEW])
def update_record(output_step, record, conditioned_zones, unconditioned_zones, debug=False):
    ## Update records
    # Update data per zones
    # Data for each zone
    for zone_name in conditioned_zones:    
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_MEAN_TEMP + ' ' + DATA.ZONE_CONDITIONED].append(output_step[zone_name + ' ' + DATA.ZONE_MEAN_TEMP])
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_RELATIVE_HUMIDITY + ' ' + DATA.ZONE_CONDITIONED].append(output_step[zone_name + ' ' + DATA.ZONE_RELATIVE_HUMIDITY])
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_TEMPERATURE_SETPOINT + ' ' + DATA.ZONE_CONDITIONED].append(output_step[zone_name + ' ' + DATA.ZONE_TEMPERATURE_SETPOINT])

    for zone_name in unconditioned_zones:    
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_MEAN_TEMP + ' ' + DATA.ZONE_UNCONDITIONED].append(output_step[zone_name + ' ' + DATA.ZONE_MEAN_TEMP])
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_RELATIVE_HUMIDITY + ' ' + DATA.ZONE_UNCONDITIONED].append(output_step[zone_name + ' ' + DATA.ZONE_RELATIVE_HUMIDITY])

    record[DATA.STATUS][DATA.TIME_SIM].append(output_step[DATA.TIME_SIM])
    record[DATA.STATUS][DATA.SYSTEM_NODE_TEMPERATURE].append(output_step[DATA.SYSTEM_NODE_TEMPERATURE])
    record[DATA.STATUS][DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE].append(output_step[DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE])

    record[DATA.STATUS][DATA.HEATING_SETPOINT_DEADBAND_APPLIED].append(output_step[DATA.HEATING_SETPOINT_BASE])
    record[DATA.STATUS][DATA.HEATING_SETPOINT_BASE].append(output_step[DATA.HEATING_SETPOINT_NEW])
    record[DATA.STATUS][DATA.HEATING_SETPOINT_DEADBAND_UP].append(output_step[DATA.HEATING_SETPOINT_DEADBAND_UP])
    record[DATA.STATUS][DATA.HEATING_SETPOINT_DEADBAND_DOWN].append(output_step[DATA.HEATING_SETPOINT_DEADBAND_DOWN])

    record[DATA.STATUS][DATA.COOLING_SETPOINT_DEADBAND_APPLIED].append(output_step[DATA.COOLING_SETPOINT_BASE])
    record[DATA.STATUS][DATA.COOLING_SETPOINT_BASE].append(output_step[DATA.COOLING_SETPOINT_NEW])
    record[DATA.STATUS][DATA.COOLING_SETPOINT_DEADBAND_UP].append(output_step[DATA.COOLING_SETPOINT_DEADBAND_UP])
    record[DATA.STATUS][DATA.COOLING_SETPOINT_DEADBAND_DOWN].append(output_step[DATA.COOLING_SETPOINT_DEADBAND_DOWN])

    record[DATA.STATUS][DATA.HEATING_COIL_RUNTIME_FRACTION].append(output_step[DATA.HEATING_COIL_RUNTIME_FRACTION])
    record[DATA.STATUS][DATA.COOLING_COIL_RUNTIME_FRACTION].append(output_step[DATA.COOLING_COIL_RUNTIME_FRACTION])
    record[DATA.STATUS][DATA.SUPPLY_FAN_AIR_MASS_FLOW_RATE].append(output_step[DATA.SUPPLY_FAN_AIR_MASS_FLOW_RATE])
    record[DATA.STATUS][DATA.SYSTEM_NODE_CURRENT_DENSITY_VOLUME_FLOW_RATE].append(output_step[DATA.SYSTEM_NODE_CURRENT_DENSITY_VOLUME_FLOW_RATE])

    # Data about thermostat and
    record[DATA.STATUS][DATA.THERMOSTAT_SCHEDULE].append(output_step[DATA.THERMOSTAT_SCHEDULE])
    record[DATA.STATUS][DATA.THERMOSTAT_MODE].append(output_step[DATA.THERMOSTAT_MODE])

    record[DATA.STATUS][DATA.OCCUPANT_MOTION].append(output_step[DATA.OCCUPANT_MOTION])
    record[DATA.STATUS][DATA.OCCUPANT_THERMAL_FRUSTRATION].append(output_step[DATA.OCCUPANT_THERMAL_FRUSTRATION])
    record[DATA.STATUS][DATA.OCCUPANT_COMFORT_DELTA].append(output_step[DATA.OCCUPANT_COMFORT_DELTA])
    record[DATA.STATUS][DATA.OCCUPANT_HABITUAL_OVERRIDE].append(output_step[DATA.OCCUPANT_HABITUAL_OVERRIDE])
    record[DATA.STATUS][DATA.OCCUPANT_DISCOMFORT_OVERRIDE].append(output_step[DATA.OCCUPANT_DISCOMFORT_OVERRIDE])

    # Data about HVAC energy usage
    record[DATA.STATUS][DATA.COOLING_COIL_ELECTRICITY_ENERGY].append(output_step[DATA.COOLING_COIL_ELECTRICITY_ENERGY])
    record[DATA.STATUS][DATA.FAN_ELECTRICITY_ENERGY].append(output_step[DATA.FAN_ELECTRICITY_ENERGY])
    record[DATA.STATUS][DATA.HEATING_COIL_FUEL_ENERGY].append(output_step[DATA.HEATING_COIL_FUEL_ENERGY])
    record[DATA.STATUS][DATA.HEATING_COIL_ELECTRICITY_ENERGY].append(output_step[DATA.HEATING_COIL_ELECTRICITY_ENERGY])
    return


def get_record_template(name, time_start, time_end, conditioned_zones, unconditioned_zones, is_initial_record=False, output_step=None, debug=False):
    record = dict()

    if is_initial_record:
        record[DATA.SETTING] = dict()
        record[DATA.SETTING][DATA.TIME_START] = [time_start]
        record[DATA.SETTING][DATA.TIME_END] = [time_end]
        record[DATA.SETTING][DATA.MODEL_NAME] = [name]

    record[DATA.INPUT] = dict()
    record[DATA.STATUS] = dict()

    # Data for each zone
    for zone_name in conditioned_zones:    
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_MEAN_TEMP + ' ' + DATA.ZONE_CONDITIONED] = []
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_RELATIVE_HUMIDITY + ' ' + DATA.ZONE_CONDITIONED] = []
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_TEMPERATURE_SETPOINT + ' ' + DATA.ZONE_CONDITIONED] = []

    for zone_name in unconditioned_zones:    
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_MEAN_TEMP + ' ' + DATA.ZONE_UNCONDITIONED] = []
        record[DATA.STATUS][zone_name + '::' + DATA.ZONE_RELATIVE_HUMIDITY + ' ' + DATA.ZONE_UNCONDITIONED] = []


    # Data
    record[DATA.STATUS][DATA.TIME_SIM] = []
    record[DATA.STATUS][DATA.SYSTEM_NODE_TEMPERATURE] = []
    record[DATA.STATUS][DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE] = []

    record[DATA.STATUS][DATA.HEATING_SETPOINT_BASE] = []
    record[DATA.STATUS][DATA.HEATING_SETPOINT_DEADBAND_APPLIED] = []
    record[DATA.STATUS][DATA.HEATING_SETPOINT_DEADBAND_UP] = []
    record[DATA.STATUS][DATA.HEATING_SETPOINT_DEADBAND_DOWN] = []

    record[DATA.STATUS][DATA.COOLING_SETPOINT_BASE] = []
    record[DATA.STATUS][DATA.COOLING_SETPOINT_DEADBAND_APPLIED] = []
    record[DATA.STATUS][DATA.COOLING_SETPOINT_DEADBAND_UP] = []
    record[DATA.STATUS][DATA.COOLING_SETPOINT_DEADBAND_DOWN] = []

    record[DATA.STATUS][DATA.HEATING_COIL_RUNTIME_FRACTION] = []
    record[DATA.STATUS][DATA.COOLING_COIL_RUNTIME_FRACTION] = []
    record[DATA.STATUS][DATA.SUPPLY_FAN_AIR_MASS_FLOW_RATE] = []
    record[DATA.STATUS][DATA.SYSTEM_NODE_CURRENT_DENSITY_VOLUME_FLOW_RATE] = []

    # Data about thermostat and occupant model below
    record[DATA.STATUS][DATA.THERMOSTAT_SCHEDULE] = []
    record[DATA.STATUS][DATA.THERMOSTAT_MODE] = []

    record[DATA.STATUS][DATA.OCCUPANT_MOTION] = []
    record[DATA.STATUS][DATA.OCCUPANT_THERMAL_FRUSTRATION] = []
    record[DATA.STATUS][DATA.OCCUPANT_COMFORT_DELTA] = []
    record[DATA.STATUS][DATA.OCCUPANT_HABITUAL_OVERRIDE] = []
    record[DATA.STATUS][DATA.OCCUPANT_DISCOMFORT_OVERRIDE] = []

    # Data about HVAC energy usage
    record[DATA.STATUS][DATA.COOLING_COIL_ELECTRICITY_ENERGY] = []
    record[DATA.STATUS][DATA.FAN_ELECTRICITY_ENERGY] = []
    record[DATA.STATUS][DATA.HEATING_COIL_FUEL_ENERGY] = []
    record[DATA.STATUS][DATA.HEATING_COIL_ELECTRICITY_ENERGY] = []

    if output_step is not None:
        update_record(output_step=output_step,
                      record=record,
                      conditioned_zones=conditioned_zones,
                      unconditioned_zones=unconditioned_zones)

    return record


def is_convertable_to_float(input_string):
    if input_string == None:
        return False
    else:
        try:
            float(input_string)
            return True
        except ValueError:
            return False


def create_model_archive(model_path, debug=False):
    # Note: model_path == the location of osw file
    # (i.e., the directory containing the necessary files)
    def zip_model(path, zip_file_handler):
        # ziph is zipfile handle
        for root, dirs, files in os.walk(path):
            for file in files:
                source_location = os.path.join(root, file)
                archive_location = os.path.join(root, file).replace(path, "")
                zip_file_handler.write(source_location, archive_location)

    archive_fd, archive_path = tempfile.mkstemp(suffix='.zip')
    if debug:
        print("archive_fd:", archive_fd, "/ archive_path:", archive_path)
    zip_file = zipfile.ZipFile(archive_path, 'a', zipfile.ZIP_STORED)
    if debug:
        print("zip_file:", zip_file, "/ self.model_path:", model_path)
    zip_model(model_path, zip_file)
    if debug:
        print("archive created!")

    zip_file.close()
    if debug:
        print("archive closed!")
    return archive_path


def initialize_control_information():
    control_information = dict()
    control_information[DATA.HEATING_SETPOINT_NEW] = None
    control_information[DATA.HEATING_SETPOINT_DEADBAND_UP] = None
    control_information[DATA.HEATING_SETPOINT_DEADBAND_DOWN] = None

    control_information[DATA.COOLING_SETPOINT_NEW] = None
    control_information[DATA.COOLING_SETPOINT_DEADBAND_UP] = None
    control_information[DATA.COOLING_SETPOINT_DEADBAND_DOWN] = None

    control_information[DATA.THERMOSTAT_SCHEDULE] = None
    control_information[DATA.THERMOSTAT_MODE] = None

    control_information[DATA.OCCUPANT_MOTION] = False
    control_information[DATA.OCCUPANT_THERMAL_FRUSTRATION] = 0
    control_information[DATA.OCCUPANT_COMFORT_DELTA] = 0
    control_information[DATA.OCCUPANT_HABITUAL_OVERRIDE] = False
    control_information[DATA.OCCUPANT_DISCOMFORT_OVERRIDE] = False

    return control_information


def apply_deadband(mode, zone_mean_temperature, state, setpoints):
    deadband_tolerance = 0.005

    if mode == CONTROL.HEATING:
        setpoint_current = float(state[DATA.HEATING_SETPOINT_BASE])
        setpoint_new = float(setpoints[DATA.HEATING_SETPOINT_NEW])
        deadband_up = float(setpoints[DATA.HEATING_SETPOINT_DEADBAND_UP])
        deadband_down = float(setpoints[DATA.HEATING_SETPOINT_DEADBAND_DOWN])

        # Heating mode 1: Heat until the temperature approaches deadband up
        if zone_mean_temperature <= setpoint_new - deadband_down + deadband_tolerance:
            return setpoint_new + deadband_up
        # Heating mode 2: Wait until the temperature approaches deadband down
        elif zone_mean_temperature >= setpoint_new + deadband_up - deadband_tolerance:
            return setpoint_new - deadband_down
        # Heating mode 3: Otherwise, do not change the setpoint
        # If approached from deadband down, remain high setpoint, o/w remain low setpoint
        else:
            return setpoint_current
    elif mode == CONTROL.COOLING:
        setpoint_current = float(state[DATA.COOLING_SETPOINT_BASE])
        setpoint_new = float(setpoints[DATA.COOLING_SETPOINT_NEW])
        deadband_up = float(setpoints[DATA.COOLING_SETPOINT_DEADBAND_UP])
        deadband_down = float(setpoints[DATA.COOLING_SETPOINT_DEADBAND_DOWN])

        # Cooling mode 1: Cool until the temperature approaches deadband down
        if zone_mean_temperature >= setpoint_new + deadband_up - deadband_tolerance:
            return setpoint_new - deadband_down
        # Cooling mode 2: Wait until the temperature approaches deadband up
        elif zone_mean_temperature <= setpoint_new - deadband_down + deadband_tolerance:
            return setpoint_new + deadband_up
        # Cooling mode 3: Otherwise, do not change the setpoint
        # If approached from deadband up, remain low setpoint, o/w remain high setpoint
        else:
            return setpoint_current
    else:
        raise ValueError("Not valid mode:", mode)
