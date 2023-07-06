# Import utilities
import datetime, os, shutil, yaml, time
import subprocess

# Import docker and docker-compose
import docker
import compose
from compose.cli.main import TopLevelCommand, project_from_options
from compose.cli import docker_client
from compose.cli.command import get_project
from compose.service import ImageType

# Import CoSim scripts
from CoSimCore import CoSimCore
from CoSimGUI import CoSimGUI
from CoSimDict import SETTING

# Import occupant model
from occupant_model.src.model import OccupantModel
from thermostat import thermostat

GUI = 'GUI'
NoGUI = 'NoGUI'

if __name__ == "__main__":
    ## Setting parameters
    debug = True                # set this True to print additional information to the console
    alfalfa_url = 'http://localhost'    # "http://192.168.99.126"
    mode_framework = NoGUI              # GUI: with GUI / NoGUI: without GUI

    test_gui_only = False       # if True, create GUI without connecting to Alfalfa for testing
    test_default_model = False  # set this True when you play with the model 'alfalfa_default_***'


    ## Simulation Time
    time_start = datetime.datetime(2019, 1, 1, 0, 0, 0)
    time_end = datetime.datetime(2019, 12, 31, 0, 0, 0)
    time_step_size = 1

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
    num_duplicates = 1
    for _ in range(num_duplicates):
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


    ## Deploy Alfalfa with custom setting
    # Docker-compose setting for Alfalfa
    name_alfalfa = 'alfalfa'
    network_alfalfa = 'alfalfa_default'
    dir_workspace = os.path.dirname(__file__)
    dir_alfalfa = os.path.join(dir_workspace, name_alfalfa)
    dir_alfalfa_compose = os.path.join(dir_alfalfa, 'docker-compose.yml')
    dir_alfalfa_compose_exec = os.path.join(dir_alfalfa, 'docker-compose')
    dir_alfalfa_compose_modified = os.path.join(dir_workspace, 'temporary_data', 'docker-compose-modified.yml')
    print(f'=Wokring directories:\n\t--> Workspace location:{dir_workspace}\n\t--> Alfalfa location:{dir_alfalfa}\n\t--> Alfalfa-compose-modified: {dir_alfalfa_compose_modified}\n')

    # Copy docker-compose.yml to the workspace
    shutil.copy2(
        src=dir_alfalfa_compose,
        dst=dir_alfalfa_compose_modified
    )

    # Modify yml and re-write, to control the number of alfalfa_worker containers
    yml_alfalfa_compose_modified = yaml.safe_load(open(dir_alfalfa_compose_modified, 'r'))
    yml_alfalfa_compose_modified['services']['worker']['deploy'] = {'replicas': len(list_input)}
    yaml.dump(yml_alfalfa_compose_modified, open(dir_alfalfa_compose_modified, 'w'))

    # Call docker client & create a project using docker-compose
    project_alfalfa = get_project(project_dir=dir_alfalfa,
                                  config_path=[dir_alfalfa_compose_modified],
                                  project_name=name_alfalfa)

    # Stop and clean the containers before running
    print(f'=Stop and clean Alfalfa before running')
    project_alfalfa.down(
        remove_image_type=ImageType.local,
        include_volumes=True)
    print(f'\t--> Alfalfa stopped and cleaned\n')
    
    # Run Alfalfa (docker-compose), as subprocess
    print(f'=Run Alfalfa')

    #subprocess.run(['./alfalfa/docker-compose', '-f', dir_alfalfa_compose_modified, '-p', name_alfalfa, 'up', '-d'])
    #subprocess.run([dir_alfalfa_compose_exec, '-f', dir_alfalfa_compose_modified, '-p', name_alfalfa, 'up', '-d'])
    subprocess.run([dir_alfalfa_compose_exec, 'up', '-d'])
    time_sleep = len(list_input) * 6
    print(f'=Wait for {time_sleep} seconds to allow enough time for Alfalfa to be ready')
    time.sleep(time_sleep)
    #containers = project_alfalfa.up()
    print(f'\t--> Alfalfa is up!')


    # Enumerate container properties, and retrieve the ip address of 'alfalfa_web'
    # Note: Alfalfa bridge will communicate with Alfalfa via 'alfalfa_web'
    """
    address_alfalfa_web = None
    for container in containers:
        if '_web' in container.name:
            address_alfalfa_web = 'http://' + container.inspect()['NetworkSettings']['Networks'][network_alfalfa]['IPAddress']
            print(f'\t--> Note: IP address of {container.name}: {address_alfalfa_web}\n')
            break
    """

    # Proceed if address is identified
    """
    if address_alfalfa_web is not None:
        # Wait until Alfalfa is up
        time_sleep = len(list_input) * 6
        print(f'=Wait for {time_sleep} seconds to allow enough time for Alfalfa to be ready')
        time.sleep(time_sleep)
    """

    cosim_sessions = []
    for index_input, input_each in enumerate(list_input):
        ## Create CoSimCore and GUI
        cosim_sessions.append(CoSimCore(alias='Model' + str(index_input+1) + ': ' + input_each[SETTING.BUILDING_MODEL_INFORMATION][SETTING.NAME_BUILDING_MODEL],
                                        building_model_information=input_each[SETTING.BUILDING_MODEL_INFORMATION],
                                        simulation_information=input_each[SETTING.SIMULATION_INFORMATION],
                                        occupant_model_information=input_each[SETTING.OCCUPANT_MODEL_INFORMATION],
                                        thermostat_model_information=input_each[SETTING.THERMOSTAT_MODEL_INFORMATION],
                                        test_default_model=test_default_model,
                                        debug=debug))


    if mode_framework == GUI:
        print(f'=Running GUI mode...\n')
        ## Create Co-Simulation Framework and Run
        dash_gui = CoSimGUI(cosim_sessions=cosim_sessions,
                            test_gui_only=test_gui_only,
                            test_default_model=test_default_model,
                            debug=debug)
        dash_gui.run()
    elif mode_framework == NoGUI:
        print(f'=Launching No-GUI mode...\n')
        import io, uuid
        import pandas as pd
        import numpy as np
        from CoSimDict import DATA, SETTING, CONTROL
        from CoSimUtils import get_record_template, update_record
        from joblib import Parallel, delayed

        record = dict()
        #steps_to_run = 86400
        steps_to_run = 10
        print(f'=Initializing cosim-sessions...')
        for cosim_session in cosim_sessions:
            cosim_session.initialize()
            record[cosim_session.alias] = get_record_template(
                name=cosim_session.alias,
                time_start=time_start,
                time_end=time_end,
                conditioned_zones=cosim_session.conditioned_zones,
                unconditioned_zones=cosim_session.unconditioned_zones,
                is_initial_record=True,
                output_step=cosim_session.retrieve_outputs())
        print(f'\t--> Complete!\n')

        print(f'=Start running simulations...')
        def update_model_each(cosim_session, steps_to_proceed):
            record_each = get_record_template(name=cosim_session.alias,
                                              time_start=time_start,
                                              time_end=time_end,
                                              conditioned_zones=cosim_session.conditioned_zones,
                                              unconditioned_zones=cosim_session.unconditioned_zones,
                                              is_initial_record=True,
                                              output_step=cosim_session.retrieve_outputs())
            for _ in range(int(np.floor(float(steps_to_run)))):
                time_sim_input = cosim_session.alfalfa_client.get_sim_time(cosim_session.model_id)
                control_input, control_information = \
                    cosim_session.compute_control(time_sim=time_sim_input,
                                                    control_mode=CONTROL.SCHEDULE_AND_OCCUPANT_MODEL,
                                                    setpoints_manual=None,
                                                    schedule_info=None,
                                                    record=record[cosim_session.alias])
                output_step = cosim_session.proceed_simulation(control_input=control_input,
                                                                control_information=control_information)
                update_record(output_step=output_step,
                                record=record_each,
                                conditioned_zones=cosim_session.conditioned_zones,
                                unconditioned_zones=cosim_session.unconditioned_zones)
            return cosim_session.alias, record_each

        record_aggregated = Parallel(n_jobs=len(cosim_sessions))\
                                    (delayed(update_model_each)\
                                            (cosim_session, steps_to_run) for cosim_session in cosim_sessions)

        record = dict()
        for alias, record_each in record_aggregated:
            record[alias] = record_each.copy()

        """
        for cosim_session in cosim_sessions:
            for _ in range(int(np.floor(float(steps_to_run)))):
                time_sim_input = cosim_session.alfalfa_client.get_sim_time(cosim_session.model_id)
                control_input, control_information = \
                    cosim_session.compute_control(time_sim=time_sim_input,
                                                  control_mode=CONTROL.SCHEDULE_AND_OCCUPANT_MODEL,
                                                  setpoints_manual=None,
                                                  schedule_info=None,
                                                  record=record[cosim_session.alias])
                output_step = cosim_session.proceed_simulation(control_input=control_input,
                                                               control_information=control_information)
                update_record(output_step=output_step,
                              record=record[cosim_session.alias],
                              conditioned_zones=cosim_session.conditioned_zones,
                              unconditioned_zones=cosim_session.unconditioned_zones)
        """

        name_output_dir = 'output'
        dir_output = os.path.join(dir_workspace, name_output_dir)
        dir_output_file = os.path.join(dir_output, str(uuid.uuid4()) + '.xlsx')
        print(dir_output_file)
        
        print(f'=Start exporting data...')
        writer = pd.ExcelWriter(path=dir_output_file, engine='openpyxl')
        for cosim_session in cosim_sessions:
            sheet_prefix = cosim_session.alias.split(':')[0]
            record_setting = pd.DataFrame.from_dict(record[cosim_session.alias][DATA.SETTING])
            record_data = pd.DataFrame.from_dict({**record[cosim_session.alias][DATA.INPUT], **record[cosim_session.alias][DATA.STATUS]})
            record_setting.to_excel(writer, sheet_name=sheet_prefix + '_' + DATA.SETTING, index=False)  # writes to BytesIO buffer
            record_data.to_excel(writer, sheet_name=sheet_prefix + '_' + DATA.DATA, index=False)

        writer.save()
        print(f"\t--> Data exported to: {dir_output_file}")
    else:
        raise ValueError(f'mode_framework:{mode_framework} is invalid')

    print("Terminated!")