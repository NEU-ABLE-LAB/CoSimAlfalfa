# Import utilities
import datetime, os, uuid, time
import pandas as pd
import numpy as np
from joblib import Parallel, delayed

# Import CoSim scripts
from CoSimCore import CoSimCore
from CoSimDict import DATA, SETTING, CONTROL
from CoSimUtils import get_record_template, update_record

# Import occupant model
from occupant_model.src.model import OccupantModel
from thermostat import thermostat
import requests, socket, time, timeit, sys, socket


if __name__ == "__main__":
    start = timeit.default_timer()
    ## Workplace configuration
    dir_workspace = os.path.dirname(__file__)
    alfalfa_url = 'http://localhost'    # "http://192.168.99.126"
    name_output_dir = 'output'
    dir_output = os.path.join(dir_workspace, name_output_dir)    
    dir_output_log_filename = os.path.join(dir_output, "logfile_{}.log".format(datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))

    ## Simulation settings
    debug = True                # set this True to print additional information to the console
    time_start = datetime.datetime(2019, 1, 1, 0, 0, 0)
    time_end = datetime.datetime(2019, 12, 31, 0, 0, 0)
    time_step_size = 1
    #steps_to_run = 86400    # 60 days
    #steps_to_run = 86400 * 3    # 180 days
    steps_to_run = 60 # 60 minutes

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
    num_models = 4
    num_parallel_process = 2


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


    def run_each_session(index_input, input_each, steps_to_proceed):
        # Initialization of CoSimCore
        print(f'=Initializing cosim-session')
        cosim_session = CoSimCore(alias='Model' + str(index_input+1) + ': ' + input_each[SETTING.BUILDING_MODEL_INFORMATION][SETTING.NAME_BUILDING_MODEL],
                                  building_model_information=input_each[SETTING.BUILDING_MODEL_INFORMATION],
                                  simulation_information=input_each[SETTING.SIMULATION_INFORMATION],
                                  occupant_model_information=input_each[SETTING.OCCUPANT_MODEL_INFORMATION],
                                  thermostat_model_information=input_each[SETTING.THERMOSTAT_MODEL_INFORMATION],
                                  test_default_model=False,
                                  debug=debug)
        cosim_session.initialize()
        print(f'\t--> Complete (alias: {cosim_session.alias}\n')
        
        # Run part (1): Initialize the record
        print(f'=Running simulation (alias: {cosim_session.alias})...')
        output_step = cosim_session.retrieve_outputs()
        time_sim_input = output_step[DATA.TIME_SIM]
        record_each = get_record_template(name=cosim_session.alias,
                                        time_start=time_start,
                                        time_end=time_end,
                                        conditioned_zones=cosim_session.conditioned_zones,
                                        unconditioned_zones=cosim_session.unconditioned_zones,
                                        is_initial_record=True,
                                        output_step=output_step)
        
        # Run part (2): Run the simulations
        for index_step in range(int(np.floor(float(steps_to_proceed)))):
            print(f'\t--> Step {index_step + 1} (alias: {cosim_session.alias})')
            control_input, control_information = \
                cosim_session.compute_control(time_sim=time_sim_input,
                                            control_mode=current_control_mode,
                                            setpoints_manual=setpoint_manual_test,
                                            schedule_info=None,
                                            output_step=output_step)

            cosim_session.proceed_simulation(control_input=control_input,
                                            control_information=control_information)

            output_step = cosim_session.retrieve_outputs(control_information=control_information)
            time_sim_input = output_step[DATA.TIME_SIM]
            update_record(output_step=output_step,
                        record=record_each,
                        conditioned_zones=cosim_session.conditioned_zones,
                        unconditioned_zones=cosim_session.unconditioned_zones)

        # Export the simulation result
        print(f'\n=Exporting results (alias: {cosim_session.alias})...')
        uuid_prefix = str(uuid.uuid4())
        model_prefix = cosim_session.alias.split(':')[0]
        model_name = record_each[DATA.SETTING]['model_name'][0].replace(": ","_")
        alpha_value = "a" + str(occupant_model_information[SETTING.TFT_ALPHA]).replace(".","")+ "_"
        dir_output_file = os.path.join(dir_output, model_name + '_' + uuid_prefix + '_' +  alpha_value +'.gzip')
        record_data = pd.DataFrame.from_dict({**record_each[DATA.INPUT], **record_each[DATA.STATUS]})
        record_data.to_parquet(dir_output_file,compression='gzip')
        print(f"\t--> File path (alias: {cosim_session.alias}): {dir_output_file}")
        print(f"\t--> Data exported (alias: {cosim_session.alias}) to: {dir_output}")    

        # Tear down
        print(f'\n=Tearing down the model (alias: {cosim_session.alias})...')
        cosim_session.alfalfa_client.stop(
            cosim_session.model_id     # site_id
        )
        print(f'\t--> Tear down complete (alias: {cosim_session.alias})!\n')    
        return

    if num_parallel_process > 1:
        Parallel(n_jobs=num_parallel_process)\
                (delayed(run_each_session)\
                        (index_input, input_each, steps_to_run) for (index_input, input_each) in enumerate(list_input))
    else:
        for index_input, input_each in enumerate(list_input):
            run_each_session(index_input=index_input,
                             input_each=input_each,
                             steps_to_proceed=steps_to_run)

    print("\n\n=Every simulation terminated!")
    stop = timeit.default_timer()
    print(f'\t--> Total Time: {stop - start} seconds')