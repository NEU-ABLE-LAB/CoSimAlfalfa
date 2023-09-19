from CoSimUtils import is_convertable_to_float, create_model_archive, initialize_control_information, apply_deadband

import base64
import pandas as pd
import pickle
import io
from datetime import datetime, timedelta
import time
import pathlib

from alfalfa_client import alfalfa_client as ac
from CoSimDict import SETTING, DATA, CONTROL

class CoSimCore:
    def __init__(self,
                 alias: str,
                 building_model_information: dict,
                 simulation_information: dict,
                 occupant_model_information: dict,
                 thermostat_model_information: dict,
                 test_default_model=False,
                 debug=False):
        self.test_default_model = test_default_model
        self.debug = debug
        
        # Name of the simulation session
        self.alias = alias
        
        # Import building model settings
        self.alfalfa_url = building_model_information[SETTING.ALFALFA_URL]
        self.model_path = building_model_information[SETTING.PATH_BUILDING_MODEL]
        self.conditioned_zones = building_model_information[SETTING.CONDITIONED_ZONES]
        self.unconditioned_zones = building_model_information[SETTING.UNCONDITIONED_ZONES]

        # Import simulation settings
        self.time_start = simulation_information[SETTING.TIME_START]
        self.time_end = simulation_information[SETTING.TIME_END]
        self.time_step_size = simulation_information[SETTING.TIME_STEP_SIZE]
        self.time_scale = simulation_information[SETTING.TIME_SCALE_BUILDING_SIMULATION]
        self.external_clock = simulation_information[SETTING.EXTERNAL_CLOCK]
        self.time_sim = self.time_start # Initial simulation time == time_start

        # Import occupant model settings
        self.o_occupant_model = occupant_model_information[SETTING.OCCUPANT_MODEL]
        self.o_num_occupants = occupant_model_information[SETTING.NUM_OCCUPANT]
        self.o_num_homes = occupant_model_information[SETTING.NUM_HOME]
        self.o_discomfort_theory = occupant_model_information[SETTING.DISCOMFORT_THEORY]
        self.o_occup_comfort_temperature = occupant_model_information[SETTING.OCCUP_COMFORT_TEMPERATURE]
        self.o_discomfort_theory_threshold = occupant_model_information[SETTING.DISCOMFORT_THEORY_THRESHOLD]
        self.o_TFT_alpha = occupant_model_information[SETTING.TFT_ALPHA]
        self.o_TFT_beta = occupant_model_information[SETTING.TFT_BETA]
        self.o_occupant_model_data_paths = occupant_model_information[SETTING.PATH_OCCUPANT_MODEL_DATA]
        self.o_tstat_db = thermostat_model_information[SETTING.IDF_DB]

        # Import thermostat model settings
        self.thermostat_model = thermostat_model_information[SETTING.THERMOSTAT_MODEL]
        self.thermostat_schedule_type = thermostat_model_information[SETTING.THERMOSTAT_SCHEDULE_TYPE]
        self.current_datetime = thermostat_model_information[SETTING.CURRENT_DATETIME]
        self.idf_db = thermostat_model_information[SETTING.IDF_DB]
        self.experiments = thermostat_model_information[SETTING.EXPERIMENTS]
        self.path_exp_schedule = thermostat_model_information[SETTING.PATH_EXP_SCHEDULE]
        self.days_per_exp = thermostat_model_information[SETTING.DAYS_PER_EXP]

    def initialize(self):
        self.thermostat_model = self.thermostat_model(schedule_type=self.thermostat_schedule_type, db=self.idf_db,
                                                      experiments=self.experiments, path_2_exp_schedule=self.path_exp_schedule, days_per_exp=self.days_per_exp)
        init_data_dir = pathlib.Path(self.o_occupant_model_data_paths[SETTING.PATH_CSV_DIR]).resolve()
        models_dir = pathlib.Path(self.o_occupant_model_data_paths[SETTING.PATH_MODEL_DIR]).resolve()
        data_files = list(init_data_dir.iterdir())
        model_files = list(models_dir.iterdir())
        init_data = {}
        for file in data_files:
            init_data[file.stem] = pd.read_csv(file)
        models = {}
        for model_file in model_files:
            models[model_file.stem] = pickle.load(open(model_file,'rb'))
        self.o_occupant_model = self.o_occupant_model(units="c",
                                                      N_homes=self.o_num_homes,
                                                      N_occupants_in_home=self.o_num_occupants,
                                                      sampling_frequency=self.time_step_size,
                                                      init_data=init_data,
                                                      models=models, 
                                                      discomfort_theory_name=self.o_discomfort_theory, 
                                                      comfort_temperature=self.o_occup_comfort_temperature,
                                                      threshold=self.o_discomfort_theory_threshold,
                                                      TFT_alpha=self.o_TFT_alpha,
                                                      TFT_beta=self.o_TFT_beta,
                                                      start_datetime=self.time_start,
                                                      tstat_db = self.o_tstat_db)

        if self.debug: print(f"\n==Initializing alfalfa client, connecting to the Alfalfa at: {self.alfalfa_url}")
        self.alfalfa_client = ac.AlfalfaClient(host=self.alfalfa_url)
        if self.debug: print(f"\t--> Complete!\n")

        self.model_archive_path = create_model_archive(self.model_path)  ## Example from Alfalfa as is
        
        if self.debug: print(f"\n=Submitting building model <{self.model_path}> from <{self.model_archive_path}>", end="\n")
        
        ## Note: Do not put argument names for alfalfa_client.submit(), as it will raise error for the GUI version
        self.model_id = self.alfalfa_client.submit(
            self.model_archive_path,    # model_path
            True                        # wait_for_status
        )
        """
        self.alfalfa_client.wait(
            self.model_id,  # site_id
            "ready"         # desired_status
        )
        """
        
        ## This alias is to test bacnet bridge and/or multiple model test
        self.alfalfa_client.set_alias(
            alias=self.alias,
            site_id=self.model_id
        )
        site_id_check = self.alfalfa_client.get_alias(self.alias)
        if self.debug: print(f"\t--> Complete! (site_id: {self.model_id}, alias: {self.alias}), compare with site_id: {site_id_check}")

        if self.debug: print(f"\n=Warming up the building model...", end="\n")
        self.alfalfa_client.wait(
            self.model_id,  # site_id
            "ready"         # desired_status
        )
        self.alfalfa_client.start(
            self.model_id,          # site_id
            self.time_start,        # start_datatime: time to start the model from
            self.time_end,          # end_datetime: time to stop the model at (may not be honored for external_clock=True)
            self.time_scale,        # timescale: multiple of real time to run model at (for external_clock=False)
            self.external_clock,    # external_clock
            False,                  # Realtime flag (time_scale = 1)
            True                    # wait_for_status
        )
        if self.debug: print(f"\t--> site_id: {self.model_id} with alias: {self.alias} is warmed up! (status: {self.alfalfa_client.status(self.model_id)})\n")

        # This is required to start advancing the simulation only after Alfalfa is ready
        if self.debug: print(f"--> Complete!\n")

        # Check various stats before the simulation
        #if self.debug: print("\n==BEFORE SIMULATION==")
        #if self.debug: print("\tList of inputs:", self.alfalfa_client.get_inputs(self.model_id))
        #if self.debug: print("\tList of outputs:", self.alfalfa_client.get_outputs(self.model_id))

        #self.output_step = self.retrieve_outputs()
        return self


    def retrieve_outputs(self, control_information: dict = None, debug=False):
        # Retrieve outputs from alfalfa_client
        output_step = self.alfalfa_client.get_outputs(
            self.model_id   # site_id
        )

        # Update simulation time
        self.sim_time = self.alfalfa_client.get_sim_time(
            self.model_id   # site_id
        )
        output_step[DATA.TIME_SIM] = self.sim_time

        #if debug: print("alfalfa_client.get_inputs:", self.alfalfa_client.get_inputs(self.model_id))
        #if debug: print("alfalfa_client.get_outputs:", self.alfalfa_client.get_outputs(self.model_id))
        #if debug: print("output_step:", output_step)
        if self.test_default_model:
            output_step[DATA.HEATING_SETPOINT_BASE] = 0.0
            output_step[DATA.COOLING_SETPOINT_BASE] = 0.0
            output_step[DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE] = 15.0

            for zone_name in self.conditioned_zones:    
                output_step[zone_name + '::' + DATA.ZONE_MEAN_TEMP + ' ' + DATA.ZONE_CONDITIONED] = output_step[zone_name + ' ' + DATA.ZONE_MEAN_TEMP]
                output_step[zone_name + '::' + DATA.ZONE_RELATIVE_HUMIDITY + ' ' + DATA.ZONE_CONDITIONED] = output_step[zone_name + ' ' + DATA.ZONE_RELATIVE_HUMIDITY]
                output_step[zone_name + '::' + DATA.ZONE_TEMPERATURE_SETPOINT + ' ' + DATA.ZONE_CONDITIONED] = output_step[zone_name + ' ' + DATA.ZONE_TEMPERATURE_SETPOINT]

            for zone_name in self.unconditioned_zones:    
                output_step[zone_name + '::' + DATA.ZONE_MEAN_TEMP + ' ' + DATA.ZONE_UNCONDITIONED] = output_step[zone_name + ' ' + DATA.ZONE_MEAN_TEMP]
                output_step[zone_name + '::' + DATA.ZONE_RELATIVE_HUMIDITY + ' ' + DATA.ZONE_UNCONDITIONED] = output_step[zone_name + ' ' + DATA.ZONE_RELATIVE_HUMIDITY]

            output_step[DATA.SYSTEM_NODE_CURRENT_DENSITY_VOLUME_FLOW_RATE] = 0.0
            output_step[DATA.SYSTEM_NODE_TEMPERATURE] = 0.0

            output_step[DATA.HEATING_COIL_RUNTIME_FRACTION] = 0.0
            output_step[DATA.COOLING_COIL_RUNTIME_FRACTION] = 0.0
            output_step[DATA.SUPPLY_FAN_AIR_MASS_FLOW_RATE] = 0.0

        if control_information != None:
            for key in control_information.keys():
                output_step[key] = control_information[key]
        else:
            output_step[DATA.HEATING_SETPOINT_NEW] = output_step[DATA.HEATING_SETPOINT_BASE]
            output_step[DATA.HEATING_SETPOINT_DEADBAND_UP] = 0.0
            output_step[DATA.HEATING_SETPOINT_DEADBAND_DOWN] = 0.0

            output_step[DATA.COOLING_SETPOINT_NEW] = output_step[DATA.COOLING_SETPOINT_BASE]
            output_step[DATA.COOLING_SETPOINT_DEADBAND_UP] = 0.0
            output_step[DATA.COOLING_SETPOINT_DEADBAND_DOWN] = 0.0

            output_step[DATA.THERMOSTAT_SCHEDULE] = 'None'
            output_step[DATA.THERMOSTAT_MODE] = 'None'
            
            output_step[DATA.OCCUPANT_MOTION] = False
            output_step[DATA.OCCUPANT_THERMAL_FRUSTRATION] = 0
            output_step[DATA.OCCUPANT_COMFORT_DELTA] = 0
            output_step[DATA.OCCUPANT_HABITUAL_OVERRIDE] = False
            output_step[DATA.OCCUPANT_DISCOMFORT_OVERRIDE] = False

        if debug: print("output_step:", output_step)
        return output_step


    def compute_control(self, time_sim, control_mode, setpoints_manual, schedule_info, output_step, debug=True):
        """
        y has any of the accessible model outputs such as the cooling power etc.
        costs are the caclulated costs for the latest timestep, including PMV

        :param y: Temperature of zone, K
        :param heating_setpoint: Temperature Setpoint, C
        :return: dict, control input to be used for the next step {<input_name> : <input_value>}
        """
        # retrieve zone_mean_temperature and zone_relative_humidity from the first conditioned zone (Note: Currently only consider single zone)
        zone_mean_temperature, zone_relative_humidity = None, None
        for key_output_step in output_step:
            if not(zone_mean_temperature is None) and not(zone_relative_humidity is None):
                break
            elif self.conditioned_zones[0] in key_output_step:
                if DATA.ZONE_MEAN_TEMP in key_output_step:
                    zone_mean_temperature = output_step[key_output_step]
                elif DATA.ZONE_RELATIVE_HUMIDITY in key_output_step:
                    zone_relative_humidity = output_step[key_output_step]

        state = {DATA.HEATING_SETPOINT_BASE: output_step[DATA.HEATING_SETPOINT_BASE],
                 DATA.COOLING_SETPOINT_BASE: output_step[DATA.COOLING_SETPOINT_BASE],
                 # TODO: change the input here to humidity only
                 DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE: output_step[DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE],
                 DATA.HEATING_COIL_RUNTIME_FRACTION: output_step[DATA.HEATING_COIL_RUNTIME_FRACTION],
                 DATA.COOLING_COIL_RUNTIME_FRACTION: output_step[DATA.COOLING_COIL_RUNTIME_FRACTION]}
        
        datetime_time_sim = time_sim
        control_information = initialize_control_information()

        # Pass-through: Do not provide any control input (normally previous setpoints are reused)
        if control_mode == CONTROL.PASSTHROUGH:
            control_input = {}
            control_input['u'] = {}

        # Setpoints: Use user-provided setpoint as control input
        elif control_mode == CONTROL.SETPOINTS:
            control_input = {}
            control_input['u'] = {}
            control_information = setpoints_manual

            if is_convertable_to_float(setpoints_manual[DATA.HEATING_SETPOINT_NEW]):
                control_input['u'][CONTROL.HEATING_SETPOINT_TO_ALFALFA] = \
                    apply_deadband(mode=CONTROL.HEATING,
                                   zone_mean_temperature=zone_mean_temperature,
                                   state=state,
                                   setpoints=setpoints_manual)

            if is_convertable_to_float(setpoints_manual[DATA.COOLING_SETPOINT_NEW]):
                control_input['u'][CONTROL.COOLING_SETPOINT_TO_ALFALFA] = \
                    apply_deadband(mode=CONTROL.COOLING,
                                   zone_mean_temperature=zone_mean_temperature,
                                   state=state,
                                   setpoints=setpoints_manual)

        # Schedule: Use the setpoint values from schedule. If not, use previous schedule value or pass-through
        elif control_mode == CONTROL.SCHEDULE:
            control_input = {}
            control_input['u'] = {}

            schedule_filename = schedule_info['filename']
            schedule_contents = schedule_info['contents']
            schedule_type, schedule_content_splitted = schedule_contents.split(',')
            schedule_content_decoded = base64.b64decode(schedule_content_splitted)
            try:
                # Assume that the user uploaded a CSV file
                if 'csv' in schedule_filename:
                    schedule_dataframe = pd.read_csv(io.StringIO(schedule_content_decoded.decode('utf-8')))
                # Assume that the user uploaded an excel file
                elif 'xls' in schedule_filename:
                    schedule_dataframe = pd.read_excel(io.BytesIO(schedule_content_decoded))
            except Exception as e:
                print(e)
                #return html.Div(['There was an error processing this file.'])
                return 'There was an error processing this file.'

            #datetime_time_sim = datetime.strptime(time_sim, '%Y-%m-%d %H:%M:%S')

            index_exact_same = None
            index_same_except_for_year = None
            time_year = 1900
            for index, row in schedule_dataframe.iterrows():
                time_parsed = row['datetime'].split('  ')
                time_month_day = time_parsed[0].split('/')
                time_hour_minute_second = time_parsed[1].split(':')

                time_hour = int(time_hour_minute_second[0])
                time_month = int(time_month_day[0])
                time_day = int(time_month_day[1])
                time_minute = int(time_hour_minute_second[1])
                # print("Y/M/D/H/M:", time_year, time_month, time_day, time_hour, time_minute)

                # EP generate 24 O'clock, which is invalid time. It should be compensated to 0 O'clock of the next day
                if time_hour == 24:
                    time_hour = 0
                    # print("--Y/M/D/H/M:", time_year, time_month, time_day, time_hour, time_minute)
                    datetime_row = datetime(time_year, time_month, time_day, time_hour, time_minute)
                    datetime_row += timedelta(days=1)
                else:
                    datetime_row = datetime(time_year, time_month, time_day, time_hour, time_minute)

                if (datetime_row.month == datetime_time_sim.month) and \
                   (datetime_row.day == datetime_time_sim.day) and \
                   (datetime_row.hour == datetime_time_sim.hour) and \
                   (datetime_row.minute == datetime_time_sim.minute):

                    if (datetime_row.year == datetime_time_sim.year):
                        index_exact_same = index
                        break
                    else:
                        index_same_except_for_year = index

            # If there is a time exactly the same, use it
            if index_exact_same is not None:
                setpoints_schedule = dict()
                setpoints_schedule[DATA.HEATING_SETPOINT_NEW] = schedule_dataframe[DATA.HEATING_SETPOINT_NEW][index_exact_same]
                setpoints_schedule[DATA.HEATING_SETPOINT_DEADBAND_UP] = schedule_dataframe[DATA.HEATING_SETPOINT_DEADBAND_UP][index_exact_same]
                setpoints_schedule[DATA.HEATING_SETPOINT_DEADBAND_DOWN] = schedule_dataframe[DATA.HEATING_SETPOINT_DEADBAND_DOWN][index_exact_same]

                setpoints_schedule[DATA.COOLING_SETPOINT_NEW] = schedule_dataframe[DATA.COOLING_SETPOINT_NEW][index_exact_same]
                setpoints_schedule[DATA.COOLING_SETPOINT_DEADBAND_UP] = schedule_dataframe[DATA.COOLING_SETPOINT_DEADBAND_UP][index_exact_same]
                setpoints_schedule[DATA.COOLING_SETPOINT_DEADBAND_DOWN] = schedule_dataframe[DATA.COOLING_SETPOINT_DEADBAND_DOWN][index_exact_same]
                control_information = setpoints_schedule

                control_input['u'][CONTROL.HEATING_SETPOINT_TO_ALFALFA] = \
                    apply_deadband(mode=CONTROL.HEATING,
                                   zone_mean_temperature=zone_mean_temperature,
                                   state=state,
                                   setpoints=setpoints_schedule)

                control_input['u'][CONTROL.COOLING_SETPOINT_TO_ALFALFA] = \
                    apply_deadband(mode=CONTROL.COOLING,
                                   zone_mean_temperature=zone_mean_temperature,
                                   state=state,
                                   setpoints=setpoints_schedule)

            # If there is a time almost the same (except for year), use it
            elif index_same_except_for_year is not None:
                setpoints_schedule = dict()
                setpoints_schedule[DATA.HEATING_SETPOINT_NEW] = schedule_dataframe[DATA.HEATING_SETPOINT_NEW][index_same_except_for_year]
                setpoints_schedule[DATA.HEATING_SETPOINT_DEADBAND_UP] = schedule_dataframe[DATA.HEATING_SETPOINT_DEADBAND_UP][index_same_except_for_year]
                setpoints_schedule[DATA.HEATING_SETPOINT_DEADBAND_DOWN] = schedule_dataframe[DATA.HEATING_SETPOINT_DEADBAND_DOWN][index_same_except_for_year]

                setpoints_schedule[DATA.COOLING_SETPOINT_NEW] = schedule_dataframe[DATA.COOLING_SETPOINT_NEW][index_same_except_for_year]
                setpoints_schedule[DATA.COOLING_SETPOINT_DEADBAND_UP] = schedule_dataframe[DATA.COOLING_SETPOINT_DEADBAND_UP][index_same_except_for_year]
                setpoints_schedule[DATA.COOLING_SETPOINT_DEADBAND_DOWN] = schedule_dataframe[DATA.COOLING_SETPOINT_DEADBAND_DOWN][index_same_except_for_year]
                control_information = setpoints_schedule

                control_input['u'][CONTROL.HEATING_SETPOINT_TO_ALFALFA] = \
                    apply_deadband(mode=CONTROL.HEATING,
                                   zone_mean_temperature=zone_mean_temperature,
                                   state=state,
                                   setpoints=setpoints_schedule)

                control_input['u'][CONTROL.COOLING_SETPOINT_TO_ALFALFA] = \
                    apply_deadband(mode=CONTROL.COOLING,
                                   zone_mean_temperature=zone_mean_temperature,
                                   state=state,
                                   setpoints=setpoints_schedule)

        # Occupant model: Calculate control input based on occupant behavior model
        elif control_mode == CONTROL.OCCUPANT_MODEL:
            self.o_occupant_model.step(ip_data_env={'T_in': zone_mean_temperature,
                                                    'T_stp_cool': state[DATA.COOLING_SETPOINT_BASE],
                                                    'T_stp_heat': state[DATA.HEATING_SETPOINT_BASE],
                                                    'hum': zone_relative_humidity,
                                                    'T_out': state[DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE],
                                                    'mo': None,
                                                    'equip_run_heat': True if state[DATA.HEATING_COIL_RUNTIME_FRACTION] != 0 else False,
                                                    'equip_run_cool': True if state[DATA.COOLING_COIL_RUNTIME_FRACTION] != 0 else False
                                                  }, T_var_names=['T_in', 'T_stp_cool', 'T_stp_heat', 'T_out'])

            for occupant in self.o_occupant_model.schedule.agents:
                control_input = {}
                control_input['u'] = {}
                control_input['u'][CONTROL.HEATING_SETPOINT_TO_ALFALFA] = occupant.output['T_stp_heat']
                control_input['u'][CONTROL.COOLING_SETPOINT_TO_ALFALFA] = occupant.output['T_stp_cool']

                control_information[DATA.HEATING_SETPOINT_NEW] = occupant.output['T_stp_heat']
                control_information[DATA.COOLING_SETPOINT_NEW] = occupant.output['T_stp_cool']
                
        elif control_mode == CONTROL.SCHEDULE_AND_OCCUPANT_MODEL:
            #datetime_time_sim = datetime.strptime(time_sim, '%Y-%m-%d %H:%M:%S')
            self.o_occupant_model.step(ip_data_env={'DateTime':datetime_time_sim, 
                                                    'T_in': zone_mean_temperature,
                                                    'T_stp_cool': state[DATA.COOLING_SETPOINT_BASE], 
                                                    'T_stp_heat': state[DATA.HEATING_SETPOINT_BASE], 
                                                    'hum': zone_relative_humidity,
                                                    'T_out': state[DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE], 
                                                    'mo': None, 
                                                    'equip_run_heat': True if state[DATA.HEATING_COIL_RUNTIME_FRACTION] != 0 else False, 
                                                    'equip_run_cool': True if state[DATA.COOLING_COIL_RUNTIME_FRACTION] != 0 else False
                                                    })
            for occupant in self.o_occupant_model.schedule.agents:
                control_input = {}
                control_input['u'] = {}
                
                control_information[DATA.OCCUPANT_MOTION] = occupant.output['Motion']
                control_information[DATA.OCCUPANT_THERMAL_FRUSTRATION] = occupant.output['Thermal Frustration']
                control_information[DATA.OCCUPANT_COMFORT_DELTA] = occupant.output['Comfort Delta']
                control_information[DATA.OCCUPANT_HABITUAL_OVERRIDE] = occupant.output['Habitual override']
                control_information[DATA.OCCUPANT_DISCOMFORT_OVERRIDE] = occupant.output['Discomfort override']

                if occupant.output['Habitual override'] or occupant.output['Discomfort override']:
                    tstat_mode, tstat_schedule, tstat_stp_cool, tstat_stp_heat = self.thermostat_model.manual_override(
                        tstp_heat = occupant.output['T_stp_heat'], 
                        tstp_cool = occupant.output['T_stp_cool'],
                        current_datetime=datetime_time_sim)
                else:
                    tstat_mode, tstat_schedule, tstat_stp_cool, tstat_stp_heat = self.thermostat_model.update_output(current_datetime=datetime_time_sim)
                
                # TODO: remove this statement once occupant model is updated to prevent setpoint issue.
                if tstat_stp_cool < tstat_stp_heat:
                    input(f"Heating SP ({tstat_stp_heat}) is higher than cooling SP ({tstat_stp_cool})! --> Adjust Cooling SP")
                    tstat_stp_cool = tstat_stp_heat + 2                

                control_input['u'][CONTROL.HEATING_SETPOINT_TO_ALFALFA] = tstat_stp_heat
                control_input['u'][CONTROL.COOLING_SETPOINT_TO_ALFALFA] = tstat_stp_cool

                control_information[DATA.HEATING_SETPOINT_NEW] = tstat_stp_heat
                control_information[DATA.COOLING_SETPOINT_NEW] = tstat_stp_cool
                
                control_information[DATA.THERMOSTAT_SCHEDULE] = tstat_schedule
                control_information[DATA.THERMOSTAT_MODE] = tstat_mode

        else:
            raise ValueError("Control mode not implemented. Provided mode is:", control_mode)

        if debug:
            print(
                f"[{self.alias}] For control_mode: [{control_mode}] at time: {time_sim}, zone mean temp is: {zone_mean_temperature}, zone relative humidity is: {zone_relative_humidity},"
                f"\n\t-Control input is: {control_input}"
                f"\n\t-Control information is: {control_information}"
            )
        #if debug: print("\talfalfa_client.get_inputs:", self.alfalfa_client.get_inputs(self.model_id))
        #if debug: print("\talfalfa_client.get_outputs:", self.alfalfa_client.get_outputs(self.model_id))

        # Currently pass-through the setpoints from the building model
        return control_input, control_information

    def proceed_simulation(self, control_input, control_information: dict):
        #print("before set_input", self.alfalfa_client.status(self.model_id))
        self.alfalfa_client.set_inputs(
            self.model_id,      # site_id
            control_input['u']  # inputs
        )
        ###### TODO: Here, we test what can be done to ensure that alfalfa_client is not inturrepted by background saving by REDIS #####
        """
        self.alfalfa_client.wait(
            self.model_id,  # site_id
            "running"         # desired_status
        )
        """
        ###############################################################################################################################
        #print("before advance", self.alfalfa_client.status(self.model_id))
        self.alfalfa_client.advance(
            [self.model_id]     # site_id
        )
        #print("before retrieve_outputs", self.alfalfa_client.status(self.model_id))
        #self.output_step = self.retrieve_outputs()

        #for key in control_information.keys():
            #self.output_step[key] = control_information[key]
            #self.output_step[key] = control_information[key]
        return #self.output_step
