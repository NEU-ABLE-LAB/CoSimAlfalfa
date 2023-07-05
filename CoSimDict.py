class SETTING():
    # Building model information
    BUILDING_MODEL_INFORMATION = 'building_model_information'
    ALFALFA_URL = 'alfalfa_url'
    NAME_BUILDING_MODEL = 'name_building_model'
    PATH_BUILDING_MODEL = 'path_building_model'
    CONDITIONED_ZONES = 'conditioned_zones'
    UNCONDITIONED_ZONES = 'unconditioned_zones'

    # Simulation information
    SIMULATION_INFORMATION = 'simulation_information'
    TIME_START = 'time_start'
    TIME_END = 'time_end'
    TIME_STEP_SIZE = 'time_step_size'
    TIME_SCALE_BUILDING_SIMULATION = 'time_scale'
    EXTERNAL_CLOCK = 'external_clock'

    # Occupant model information
    OCCUPANT_MODEL_INFORMATION = 'occupant_model_information'
    PATH_CSV_DIR = 'path_csv_dir'
    PATH_MODEL_DIR = 'path_model_dir'
    PATH_OCCUPANT_MODEL_DATA = 'path_occupant_model_data'

    OCCUPANT_MODEL = 'occupant_model'
    NUM_OCCUPANT = 'num_occupant'
    NUM_HOME = 'num_home'
    DISCOMFORT_THEORY = 'discomfort_theory'
    OCCUP_COMFORT_TEMPERATURE = 'occup_comfort_temperature'
    DISCOMFORT_THEORY_THRESHOLD = 'discomfort_theory_threshold'
    TFT_BETA = 'tft_beta'
    TFT_ALPHA = 'tft_alpha'

    # Thermostat model information
    THERMOSTAT_MODEL_INFORMATION = 'thermostat_model_information'
    THERMOSTAT_MODEL = 'thermostat'
    THERMOSTAT_SCHEDULE_TYPE = 'schedule_type'
    CURRENT_DATETIME = 'current_datetime'

class DATA:
    ## Settings
    SETTING = 'setting'
    TIME_START = 'time_start'
    TIME_END = 'time_end'
    STEP_SIM = 'step_sim'
    MODEL_NAME = 'model_name'

    ## DATA
    DATA = 'data'   # this is aggregation of DATA.INPUT and DATA.STATUS

    ## Inputs
    INPUT = 'input'

    ## Status
    STATUS = 'status'
    TIME_SIM = 'time_sim'
    STEP_NEW = 'step_new'
    OUTDOOR_AIR_DRYBULB_TEMPERATURE = 'Outdoor Air Drybulb Temperature'
    
    # Note: ZONE_MEAN_TEMP and ZONE_RELATIVE_HUMIDITY and ZONE_TEMPERATURE_SETPOINT are created PER each zone
    ZONE_MEAN_TEMP = 'Air Temperature'
    ZONE_RELATIVE_HUMIDITY = 'Humidity'
    ZONE_TEMPERATURE_SETPOINT = 'Temperature Setpoint'
    ZONE_CONDITIONED = '(CONDITIONED)'
    ZONE_UNCONDITIONED = '(UNCONDITIONED)'

    SYSTEM_NODE_CURRENT_DENSITY_VOLUME_FLOW_RATE = 'System Node Current Density Volume Flow Rate'
    SYSTEM_NODE_TEMPERATURE = 'System Node Temperature'

    HEATING_SETPOINT_BASE = 'Heating Setpoint'
    HEATING_SETPOINT_NEW = 'Heating Setpoint (New)'
    HEATING_SETPOINT_DEADBAND_APPLIED = 'Heating Setpoint (Deadband)'
    HEATING_SETPOINT_DEADBAND_UP = 'Heating Deadband Up'
    HEATING_SETPOINT_DEADBAND_DOWN = 'Heating Deadband Down'

    COOLING_SETPOINT_BASE = 'Cooling Setpoint'
    COOLING_SETPOINT_NEW = 'Cooling Setpoint (New)'
    COOLING_SETPOINT_DEADBAND_APPLIED = 'Cooling Setpoint (Deadband)'
    COOLING_SETPOINT_DEADBAND_UP = 'Cooling Deadband Up'
    COOLING_SETPOINT_DEADBAND_DOWN = 'Cooling Deadband Down'

    HEATING_COIL_RUNTIME_FRACTION = 'Heating Coil Runtime Fraction'
    COOLING_COIL_RUNTIME_FRACTION = 'Cooling Coil Runtime Fraction'
    SUPPLY_FAN_AIR_MASS_FLOW_RATE = 'Fan Air Mass Flow Rate'           # For Some house models
    #SUPPLY_FAN_AIR_MASS_FLOW_RATE = 'Supply Fan Runtime Fraction'       # For ThermalAR models

    ## Thermostat
    THERMOSTAT_SCHEDULE = 'Thermostat Schedule'
    THERMOSTAT_MODE = 'Thermostat Mode'

    ## Occupancy
    OCCUPANT_MOTION = 'Occupant Motion'
    OCCUPANT_THERMAL_FRUSTRATION = 'Occupant Thermal Frustration'
    OCCUPANT_COMFORT_DELTA = 'Occupant Comfort Delta'
    OCCUPANT_HABITUAL_OVERRIDE = 'Occupant Habitual Override'
    OCCUPANT_DISCOMFORT_OVERRIDE = 'Occupant Discomfort Override'

    ## HVAC Energy
    COOLING_COIL_ELECTRICITY_ENERGY = 'Cooling Coil Electricity Energy'
    FAN_ELECTRICITY_ENERGY = 'Fan Electricity Energy'
    HEATING_COIL_FUEL_ENERGY = 'Heating Coil FuelOilNo2 Energy'
    HEATING_COIL_ELECTRICITY_ENERGY = 'Heating Coil Electricity Energy'


class CONTROL():
    HEATING = 'mode_heating'
    COOLING = 'mode_cooling'

    PASSTHROUGH = 'Pass through'
    SETPOINTS = 'Manual setpoint'
    SCHEDULE = 'Scheduled setpoint'
    OCCUPANT_MODEL = 'Occupant model'
    SCHEDULE_AND_OCCUPANT_MODEL = 'Schedule and occupant model'

    HEATING_SETPOINT_TO_ALFALFA = 'Heating Setpoint'
    COOLING_SETPOINT_TO_ALFALFA = 'Cooling Setpoint'




