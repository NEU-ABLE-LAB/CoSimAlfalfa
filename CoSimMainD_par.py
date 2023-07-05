# Import utilities
import datetime, os, uuid, time
import pandas as pd
import numpy as np
from joblib import Parallel, delayed

# Import CoSim scripts
from CoSimCore import CoSimCore
from CoSimGUI import CoSimGUI
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
   
    # Note: 'replicas' of docker-compose should be added to spawn multiple alfalfa_workers (# == number of models)
    #worker:
    #   deploy:
    #       replicas: 2 
    num_models = 3
    num_parallel_process = 3


    ## Create building model information: pair of 'model_name' and 'conditioned_zone_name'
    # model_name: location of the building model, under 'idf_files' folder
    # conditioned_zone_names: list of the names of conditioned zone (Note: not tested with multi-zone case)
    # unconditioned_zone_names: list of the names of unconditioned zone
    model_name, conditioned_zones, unconditioned_zones =\
        'husky', \
        ['Zone Conditioned', ], \
        ['Zone Unconditioned Attic', 'Zone Unconditioned Basement']

    ## Create input list
    list_input = []
    for _ in range(num_models):
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

        list_input.append({SETTING.BUILDING_MODEL_INFORMATION: building_model_information,
                           SETTING.SIMULATION_INFORMATION: simulation_information,
                           SETTING.OCCUPANT_MODEL_INFORMATION: occupant_model_information,
                           SETTING.THERMOSTAT_MODEL_INFORMATION: thermostat_model_information,
                           })


    ## Initialize Cosimulation Core
    print(f'=Initializing cosim-sessions...')
    time_tick = time.time_ns()
    def initialize_cosim_session_each(index_input, input_each):
        cosim_session = CoSimCore(alias='Model' + str(index_input+1) + ': ' + input_each[SETTING.BUILDING_MODEL_INFORMATION][SETTING.NAME_BUILDING_MODEL],
                                  building_model_information=input_each[SETTING.BUILDING_MODEL_INFORMATION],
                                  simulation_information=input_each[SETTING.SIMULATION_INFORMATION],
                                  occupant_model_information=input_each[SETTING.OCCUPANT_MODEL_INFORMATION],
                                  thermostat_model_information=input_each[SETTING.THERMOSTAT_MODEL_INFORMATION],
                                  test_default_model=False,
                                  debug=debug)
        cosim_session.initialize()
        return cosim_session
    cosim_sessions = Parallel(n_jobs=num_parallel_process)\
                             (delayed(initialize_cosim_session_each)\
                                     (index_input, input_each) for (index_input, input_each) in enumerate(list_input))
    print(f'\t--> Complete!\n')
    time_tock = time.time_ns()
    print(f'\t--> Elapsed time to initialize cosim_sessions for {num_models} models: {(time_tock - time_tick)/1000000000}')

    
    ## Launch Simulation
    # Note: EP error occurs when heating setpoint > cooling setpoint! --> Kunind needs to fix the occupant-based control to prevent this
    print(f'=Start running simulations...')
    time_tick = time.time_ns()
    record = dict()
    def update_model_each(cosim_session, steps_to_proceed):
        output_step = cosim_session.retrieve_outputs()
        time_sim_input = output_step[DATA.TIME_SIM]
        record_each = get_record_template(name=cosim_session.alias,
                                          time_start=time_start,
                                          time_end=time_end,
                                          conditioned_zones=cosim_session.conditioned_zones,
                                          unconditioned_zones=cosim_session.unconditioned_zones,
                                          is_initial_record=True,
                                          output_step=output_step)
        for _ in range(int(np.floor(float(steps_to_proceed)))):
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

            time_tick = time.time_ns()
            output_step = cosim_session.retrieve_outputs()
            time_sim_input = output_step[DATA.TIME_SIM]
            update_record(output_step=output_step,
                          record=record_each,
                          conditioned_zones=cosim_session.conditioned_zones,
                          unconditioned_zones=cosim_session.unconditioned_zones)
            time_tock = time.time_ns()
            elapsed_time_record = (time_tock - time_tick)/1000000000
            print(f'\t--> Elapsed time for control={elapsed_time_control}/proceed={elapsed_time_proceed}/record={elapsed_time_record}/total={elapsed_time_control+elapsed_time_proceed+elapsed_time_record}\n')
        return cosim_session.alias, record_each

    record_aggregated = Parallel(n_jobs=num_parallel_process)\
                                (delayed(update_model_each)\
                                        (cosim_session, steps_to_run) for cosim_session in cosim_sessions)

    for alias, record_each in record_aggregated:
        record[alias] = record_each.copy()

    time_tock = time.time_ns()
    print(f'\t--> Elapsed time to simulate {steps_to_run} steps ({num_models} models): {(time_tock - time_tick)/1000000000}')

    
    ## Export outputs
    print(f'=Start exporting data...')
    time_tick = time.time_ns()
    name_output_dir = 'output'
    dir_output = os.path.join(dir_workspace, name_output_dir)

    def export_record_each(uuid_prefix, cosim_session):
        model_prefix = cosim_session.alias.split(':')[0]
        dir_output_file = os.path.join(dir_output, uuid_prefix + '_' + model_prefix + '.xlsx')
        writer = pd.ExcelWriter(path=dir_output_file, engine='openpyxl')
        record_setting = pd.DataFrame.from_dict(record[cosim_session.alias][DATA.SETTING])
        record_data = pd.DataFrame.from_dict({**record[cosim_session.alias][DATA.INPUT], **record[cosim_session.alias][DATA.STATUS]})
        record_setting.to_excel(writer, sheet_name=model_prefix + '_' + DATA.SETTING, index=False)  # writes to BytesIO buffer
        record_data.to_excel(writer, sheet_name=model_prefix + '_' + DATA.DATA, index=False)
        writer.save()
        return
    uuid_prefix = str(uuid.uuid4())
    Parallel(n_jobs=num_parallel_process)\
            (delayed(export_record_each)\
                    (uuid_prefix, cosim_session) for cosim_session in cosim_sessions)
    time_tock = time.time_ns()
    print(f"\t--> Data exported to: {dir_output}")
    print(f'\t--> Elapsed time to export {steps_to_run} steps ({num_models} models): {(time_tock - time_tick)/1000000000}')
    print("\n\n=Terminated!")


