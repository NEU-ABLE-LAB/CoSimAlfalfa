# Import utilities
import datetime, os, uuid, time
import pandas as pd
import numpy as np

# Import CoSim scripts
from CoSimCore import CoSimCore
from CoSimDict import DATA, SETTING, CONTROL
from CoSimUtils import get_record_template, update_record

# Import occupant model
from occupant_model.src.model import OccupantModel
from thermostat import thermostat


if __name__ == "__main__":
    ## Workplace configuration
    dir_workspace = os.path.dirname(__file__)
    alfalfa_url = 'http://localhost'    # "http://192.168.99.126"


    ## Simulation settings
    debug = True                # set this True to print additional information to the console
    time_start = datetime.datetime(2019, 1, 1, 0, 0, 0)
    time_end = datetime.datetime(2019, 12, 31, 0, 0, 0)
    time_step_size = 1
    #steps_to_run = 86400    # 60 days
    steps_to_run = 86400 * 3    # 180 days
    
    # Choose one of the control mode
    current_control_mode = CONTROL.SCHEDULE_AND_OCCUPANT_MODEL
    #current_control_mode = CONTROL.PASSTHROUGH
    #current_control_mode = CONTROL.SETPOINTS

    # Manual setpoints, if CONTROL.SETPOINTS is chosen
    setpoint_manual_test = {DATA.HEATING_SETPOINT_NEW: 20,
                            DATA.HEATING_SETPOINT_DEADBAND_UP: 1.5,
                            DATA.HEATING_SETPOINT_DEADBAND_DOWN: 1.5,
                            DATA.COOLING_SETPOINT_NEW: 30,
                            DATA.COOLING_SETPOINT_DEADBAND_UP: 1.5,
                            DATA.COOLING_SETPOINT_DEADBAND_DOWN: 1.5}


    ## Create building model information: pair of 'model_name' and 'conditioned_zone_name'
    # model_name: location of the building model, under 'idf_files' folder
    # conditioned_zone_names: list of the names of conditioned zone (Note: not tested with multi-zone case)
    # unconditioned_zone_names: list of the names of unconditioned zone
    model_name, conditioned_zones, unconditioned_zones =\
        'husky', \
        ['Zone Conditioned', ], \
        ['Zone Unconditioned Attic', 'Zone Unconditioned Basement']

    # building model and simulation information
    building_model_information = {
        SETTING.ALFALFA_URL: alfalfa_url,
        SETTING.NAME_BUILDING_MODEL: model_name,
        SETTING.PATH_BUILDING_MODEL: os.path.join('idf_files', model_name),
        SETTING.CONDITIONED_ZONES: conditioned_zones,
        SETTING.UNCONDITIONED_ZONES: unconditioned_zones,
    }
    simulation_information = {
        SETTING.TIME_START: time_start,
        SETTING.TIME_END: time_end,
        SETTING.TIME_SCALE_BUILDING_SIMULATION: time_step_size,
        SETTING.TIME_STEP_SIZE: time_step_size,
        SETTING.EXTERNAL_CLOCK: True,
    }

    # occupant and thermostat model information
    occupant_model_information = {
        SETTING.OCCUPANT_MODEL: OccupantModel,
        SETTING.NUM_OCCUPANT: 1,
        SETTING.NUM_HOME: 1,
        SETTING.DISCOMFORT_THEORY: 'TFT',
        SETTING.OCCUP_COMFORT_TEMPERATURE: 24.0,
        SETTING.DISCOMFORT_THEORY_THRESHOLD: {'UL': 50, 'LL': -50},
        SETTING.TFT_BETA: 1,
        SETTING.TFT_ALPHA: 0.9,
        SETTING.PATH_OCCUPANT_MODEL_DATA: {SETTING.PATH_CSV_DIR: 'occupant_model/input_data/csv_files/',
                                           SETTING.PATH_MODEL_DIR: 'occupant_model/input_data/model_files/'},
    }
    thermostat_model_information = {
        SETTING.THERMOSTAT_MODEL: thermostat,
        SETTING.THERMOSTAT_SCHEDULE_TYPE: 'default',
        SETTING.CURRENT_DATETIME:time_start,
    }


    ## Initialize Cosimulation Core
    print(f'=Initializing cosim-sessions...')
    cosim_session = CoSimCore(alias='Model 1: ' + building_model_information[SETTING.NAME_BUILDING_MODEL],
                              building_model_information=building_model_information,
                              simulation_information=simulation_information,
                              occupant_model_information=occupant_model_information,
                              thermostat_model_information=thermostat_model_information,
                              test_default_model=False,
                              debug=debug)
    cosim_session.initialize()
    print(f'\t--> Complete!\n')

    
    ## Launch Simulation
    # Note: EP error occurs when heating setpoint > cooling setpoint! --> Kunind needs to fix the occupant-based control to prevent this
    print(f'=Start running simulations...')
    time_tick_simulation = time.time_ns()
    
    # Initialize output and simulation time
    output_step = cosim_session.retrieve_outputs()
    time_sim_input = output_step[DATA.TIME_SIM]
    record = get_record_template(name=cosim_session.alias,
                                 time_start=time_start,
                                 time_end=time_end,
                                 conditioned_zones=cosim_session.conditioned_zones,
                                 unconditioned_zones=cosim_session.unconditioned_zones,
                                 is_initial_record=True,
                                 output_step=output_step)
    for _ in range(int(np.floor(float(steps_to_run)))):
        time_tick = time.time_ns()
        control_input, control_information = \
            cosim_session.compute_control(time_sim=time_sim_input,
                                          control_mode=current_control_mode,
                                          setpoints_manual=setpoint_manual_test,
                                          schedule_info=None,
                                          output_step=output_step)
        time_tock = time.time_ns()
        elapsed_time_control = (time_tock - time_tick)/1000000000

        time_tick = time.time_ns()
        cosim_session.proceed_simulation(control_input=control_input,
                                         control_information=control_information)
        time_tock = time.time_ns()
        elapsed_time_proceed = (time_tock - time_tick)/1000000000
        
        # Update output and simulation time for the next step
        time_tick = time.time_ns()
        output_step = cosim_session.retrieve_outputs()
        time_sim_input = output_step[DATA.TIME_SIM]
        update_record(output_step=output_step,
                      record=record,
                      conditioned_zones=cosim_session.conditioned_zones,
                      unconditioned_zones=cosim_session.unconditioned_zones)
        time_tock = time.time_ns()
        elapsed_time_record = (time_tock - time_tick)/1000000000
        print(f'\t--> Elapsed time for control={elapsed_time_control}/proceed={elapsed_time_proceed}/record={elapsed_time_record}/total={elapsed_time_control+elapsed_time_proceed+elapsed_time_record}\n')

        if elapsed_time_proceed > 2:
            input(f'This is where simulation is delayed!')

    time_tock_simulation = time.time_ns()
    print(f'\t--> Elapsed time to simulate {steps_to_run} steps: {(time_tock_simulation - time_tick_simulation)/1000000000}')

    
    
    ## Export outputs
    print(f'=Start exporting data...')
    time_tick_export = time.time_ns()
    name_output_dir = 'output'
    dir_output = os.path.join(dir_workspace, name_output_dir)
    dir_output_file = os.path.join(dir_output, str(uuid.uuid4()) + '.xlsx')

    writer = pd.ExcelWriter(path=dir_output_file, engine='openpyxl')
    sheet_prefix = cosim_session.alias.split(':')[0]
    record_setting = pd.DataFrame.from_dict(record[DATA.SETTING])
    record_data = pd.DataFrame.from_dict({**record[DATA.INPUT], **record[DATA.STATUS]})
    record_setting.to_excel(writer, sheet_name=sheet_prefix + '_' + DATA.SETTING, index=False)  # writes to BytesIO buffer
    record_data.to_excel(writer, sheet_name=sheet_prefix + '_' + DATA.DATA, index=False)

    writer.save()
    time_tock_export = time.time_ns()
    print(f"\t--> Data exported to: {dir_output_file}")
    print(f'\t--> Elapsed time to export {steps_to_run} steps: {(time_tock_export - time_tick_export)/1000000000}')
    print("\n\n=Terminated!")