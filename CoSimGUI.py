import sys
sys.path.append('cosim/src/')

import io, os, uuid, time, shutil, yaml, socket, datetime
#from datetime import datetime
import numpy as np
import pandas as pd
import subprocess

# Import docker and docker-compose
import docker
import compose
from compose.cli.main import TopLevelCommand, project_from_options
from compose.cli import docker_client
from compose.cli.command import get_project
from compose.service import ImageType

from cosim.src.CoSimCore import CoSimCore
from cosim.src.CoSimDict import DATA, CONTROL, SETTING
from cosim.src.CoSimUtils import get_record_template, update_record

# Import occupant model
from cosim.src.occupant_model.src.model import OccupantModel
from cosim.src.thermostat import thermostat
import socket, time, timeit, sys, socket

# Use dash-extensions instead of dash to use ServerSideOutput: Not store data as web-browser cache, but inside the server (file_system_store)
from dash_extensions.enrich import DashProxy, Output, Input, State, ServersideOutput, html, dcc, ServersideOutputTransform
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Import parallelization
from joblib import Parallel, delayed


def id(name):
    return '-' + name + '-'

class CoSimGUI:
    def __init__(self,
                 cosim_sessions: list[CoSimCore],
                 test_gui_only=False,
                 test_default_model=False,
                 debug=False):
        self.test_default_model = test_default_model
        self.debug = debug
        self.test_gui_only = test_gui_only

        # Use DashProxy instead of Dash to use ServerSideOutput
        #app = Dash(__name__)
        app = DashProxy(transforms=[ServersideOutputTransform()])
        self.app = app

        # Initialize GUI & callbacks
        if self.debug: print("\n==Initialize GUI:", end=" ")

        #self.cosim_sessions = cosim_sessions
        self.initialized = dict()
        
        # Speed comparison of cosim_session.initialize() with and without parallelization
        # Tested on desktop (10 models)
        #  -without parallelization: 89 sec
        #  -with parallelization: 19 sec
        # --> decieded to perform with parallelization
        if not self.test_gui_only:
            self.cosim_sessions = Parallel(n_jobs=len(cosim_sessions))\
                                          (delayed(cosim_session.initialize)\
                                                  () for cosim_session in cosim_sessions)
        else:
            if self.debug: print("=Skipping initial simulation to just test GUI!")

        self.create_app_layout()
        self.initialize_callbacks()

    def run(self):
        # debug flag should be False to prevent 1) memory issue, 2) running twice
        self.app.run_server(debug=False)

    def create_app_layout(self):
        if self.test_gui_only:
            output_step = None
        else:
            # Record is dictionary, where record for each model can be retrived with its alias
            self.record_initial = dict()
            list_alias = []
            for cosim_session in self.cosim_sessions:
                output_step = cosim_session.retrieve_outputs()
                list_alias.append(cosim_session.alias)

                time_start = str(cosim_session.time_start) if not self.test_gui_only else str(datetime(2019, 1, 3, 0, 0, 0))
                time_end = str(cosim_session.time_end) if not self.test_gui_only else str(datetime(2019, 1, 4, 0, 0, 0))
                heating_setpoint = str(output_step[DATA.HEATING_SETPOINT_BASE]) if output_step else '0'
                heating_deadband_up = '2.0'
                heating_deadband_down = '2.0'
                cooling_setpoint = str(output_step[DATA.COOLING_SETPOINT_BASE]) if output_step else '0'
                cooling_deadband_up = '2.0'
                cooling_deadband_down = '2.0'

                # For each model, get initial record and assign initialization flag
                self.initialized[cosim_session.alias] = False
                self.record_initial[cosim_session.alias] = get_record_template(name=cosim_session.alias,
                                                                               time_start=time_start, 
                                                                               time_end=time_end, 
                                                                               conditioned_zones=cosim_session.conditioned_zones, 
                                                                               unconditioned_zones=cosim_session.unconditioned_zones, 
                                                                               is_initial_record=True) if self.test_gui_only else \
                                                           get_record_template(name=cosim_session.alias,
                                                                               time_start=time_start, 
                                                                               time_end=time_end, 
                                                                               conditioned_zones=cosim_session.conditioned_zones, 
                                                                               unconditioned_zones=cosim_session.unconditioned_zones, 
                                                                               is_initial_record=True, 
                                                                               output_step=cosim_session.retrieve_outputs())

            # Styles for label and input of information
            style_label_information = {'display': 'inline-block', 'width': '21em'}
            style_input_information = {'display': 'inline-block', 'width': '10em'}

            # Styles for label and input of control
            style_dropdown_label = {'display': 'inline-block', 'width': '16em'}
            style_dropdown_input = {'display': 'inline-block', 'width': '50em'}

            # Styles for label and input of control
            style_control_label = {'display': 'inline-block', 'width': '20em'}
            style_control_input = {'display': 'inline-block', 'width': '30em'}

            # Styles for panes
            style_pane_model = {'display': 'flex', 'flex-direction': 'column'}
            style_pane_input = {'display': 'flex', 'flex-direction': 'row'}

            style_input_model = {'display': 'inline-block', 'width': '65em'}
            style_input_radio = {'display': 'inline-block', 'width': '25em'}
            style_input_upload = {'width': '20em', 'height': '50px', 'lineHeight': '50px', 'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px'}
            style_input_control = {'display': 'inline-block', 'width': '40em'}

            style_pane_plot = {'display': 'inline-block', 'width': '100%', 'padding': 10, 'flex': 1}

            style_overall = {'display': 'flex', 'flex-direction': 'column'}
            self.app.layout = html.Div([
                # Top pane: Command input
                html.Div(children=[
                    html.Div(children=[
                        html.H3('Command'),
                        # NOTE: control mode is string in radio button, but enum outside of the radio button
                        dcc.RadioItems(id='=mode_setpoint=',
                                    options=[CONTROL.PASSTHROUGH, CONTROL.SETPOINTS, CONTROL.SCHEDULE, CONTROL.OCCUPANT_MODEL,CONTROL.SCHEDULE_AND_OCCUPANT_MODEL],
                                    value=CONTROL.SCHEDULE_AND_OCCUPANT_MODEL,
                                    labelStyle={'display': 'block'}),   # labelStyle to make each radio button in each row
                        html.Br(),
                        dcc.Upload(id='=upload_schedule=',
                                children=html.Div(['Drag and Drop or ', html.A('Select a Schedule File (csv)')]),
                                style=style_input_upload,
                                # Do not allow multiple files to be uploaded
                                multiple=False
                                ), html.Br(),
                    ], style=style_input_radio),

                    html.Div(children=[
                        html.Br(), html.Br(),
                        html.Label(DATA.HEATING_SETPOINT_NEW, style=style_control_label), dcc.Input(id=id(DATA.HEATING_SETPOINT_NEW), value=heating_setpoint, type='number', readOnly=False, disabled=False, style=style_control_input), html.Br(),
                        html.Label(DATA.HEATING_SETPOINT_DEADBAND_UP, style=style_control_label), dcc.Input(id=id(DATA.HEATING_SETPOINT_DEADBAND_UP), value=heating_deadband_up, type='number', readOnly=False, disabled=False, style=style_control_input), html.Br(),
                        html.Label(DATA.HEATING_SETPOINT_DEADBAND_DOWN, style=style_control_label), dcc.Input(id=id(DATA.HEATING_SETPOINT_DEADBAND_DOWN), value=heating_deadband_down, type='number', readOnly=False, disabled=False, style=style_control_input), html.Br(),
                        html.Br(),
                        html.Label(DATA.COOLING_SETPOINT_NEW, style=style_control_label), dcc.Input(id=id(DATA.COOLING_SETPOINT_NEW), value=cooling_setpoint, type='number', readOnly=False, disabled=False, style=style_control_input), html.Br(),
                        html.Label(DATA.COOLING_SETPOINT_DEADBAND_UP, style=style_control_label), dcc.Input(id=id(DATA.COOLING_SETPOINT_DEADBAND_UP), value=cooling_deadband_up, type='number', readOnly=False, disabled=False, style=style_control_input), html.Br(),
                        html.Label(DATA.COOLING_SETPOINT_DEADBAND_DOWN, style=style_control_label), dcc.Input(id=id(DATA.COOLING_SETPOINT_DEADBAND_DOWN), value=cooling_deadband_down, type='number', readOnly=False, disabled=False, style=style_control_input), html.Br(),
                        html.Br(),
                        html.Label('Steps to proceed', style=style_control_label), dcc.Input(id=id(DATA.STEP_NEW), value=100, min=1, type='number', readOnly=False, disabled=False, style=style_control_input), html.Br(),
                        html.Button('Proceed to next step', id='=proceed=', n_clicks=0),
                        html.Button('Exit', id='=exit=', n_clicks=0),
                        html.Button('Export data', id='=export=', n_clicks=0),
                    ], style=style_input_control),

                    # This Div is used to store hidden information
                    html.Div(children=[
                        dcc.Input(id='-exit_test-', value=1, min=1, type='hidden', readOnly=True, disabled=True, style=style_input_information),
                        dcc.Input(id='-control_mode-', value=CONTROL.SCHEDULE_AND_OCCUPANT_MODEL, min=1, type='hidden', readOnly=True, disabled=True, style=style_input_information),
                        
                        # ddc elements to store schedule and export historical data
                        dcc.Store(id='-schedule-'),
                        dcc.Download(id="-exported_data-"),

                        # ddc elements to store historical data
                        dcc.Store(id='-record-'),
                    ], hidden=True),

                ], style=style_pane_input),

                # Middle pane: Model select
                html.Div(children=[
                    html.H3('Model'),
                    html.Label('Model to Visualize', style=style_dropdown_label),
                    dcc.Dropdown(id='=model_select=',
                                 options=list_alias,
                                 value=list_alias[0], style=style_dropdown_input),
                    html.Br(),
                    html.Label('Model to Control (Multi-dropdown)', style=style_dropdown_label),
                    dcc.Dropdown(id='=model_control=',
                                 options=list_alias,
                                 value=[list_alias[0]],
                                 multi=True, style=style_dropdown_input),
                    html.Br(),
                    # This Div is used to store hidden information
                    html.Div(children=[
                        #dcc.Input(id='-model_alias-', value=1, min=1, type='hidden', readOnly=True, disabled=True, style=style_input_information),
                        dcc.Input(id='-model_alias-', type='hidden', readOnly=True, disabled=True, style=style_input_information),
                    ], hidden=True),

                ], style=style_pane_model),

                html.Div(children=[
                    html.H3('Visualization'),
                    dcc.Tabs(id="tabs-plots", value='tab-plot1', children=[
                        dcc.Tab(label='Temperatures', value='tab-plot1'),
                        dcc.Tab(label='Humidity', value='tab-plot2'),
                        dcc.Tab(label='Runtime Fractions', value='tab-plot3'),
                        dcc.Tab(label='Airflow', value='tab-plot4'),
                        dcc.Tab(label='Occupancy', value='tab-plot5'),
                        dcc.Tab(label='Thermal Frustration', value='tab-plot6'),
                        dcc.Tab(label='HVAC Energy', value='tab-plot7'),
                    ]),
                    html.Div(id='tabs-plots-content'),

                ], style=style_pane_plot)

            ], style=style_overall)
        return

    def update_output(self, n_clicks,
                      heating_setpoint_new, heating_deadband_up, heating_deadband_down,
                      cooling_setpoint_new, cooling_deadband_up, cooling_deadband_down,
                      steps_to_proceed, tab, control_mode, schedule_contents, schedule_filename,
                      alias, dropdown_multi, record):
        print("update_output:entering callback")
        print(f"update_output:dropdown_multi: {dropdown_multi} and alias: {alias}")

        ## Copy initial record, if record is not initialized yet
        model_to_control = dropdown_multi.copy() if len(dropdown_multi) > 0 else [alias].copy()
        print(f"update_output:model_to_control: {model_to_control}")
        
        # If record has not been initialized yet, initialize
        if not any(self.initialized.values()):
            record = dict()
            print(f'update_output:global data record initialized')

        # Initialize all the cosim_session if it has not been initialized
        for cosim_session in self.cosim_sessions:
            if not self.initialized[cosim_session.alias]:
                record[cosim_session.alias] = self.record_initial[cosim_session.alias].copy()
                self.initialized[cosim_session.alias] = True
                print(f'update_output:data record initialized for model: {cosim_session.alias}')


        time_start = time.time_ns()
        # Speed comparison with and without parallelization, before return statement
        # Tested on surface laptop (500 steps, 3 models):
        #  -Without parallelization: 240.1542451 sec
        #  -With parallelization: 86.0608628 sec
        # Tested on surface laptop (100 steps, 3 models):
        #  -Without parallelization: 47.9603716 sec
        #  -With parallelization:  18.2678293 sec
        def update_model_each(cosim_session: CoSimCore, steps_to_proceed):
            #record_each = dict()
            output_step = cosim_session.retrieve_outputs()
            time_sim_input = output_step[DATA.TIME_SIM]
            record_each = get_record_template(name=cosim_session.alias,
                                              time_start=None, 
                                              time_end=None, 
                                              conditioned_zones=cosim_session.conditioned_zones,
                                              unconditioned_zones=cosim_session.unconditioned_zones,
                                              is_initial_record=False, 
                                              output_step=output_step)
            for _ in range(int(np.floor(float(steps_to_proceed)))):
                control_input, control_information = \
                    cosim_session.compute_control(time_sim=time_sim_input,
                                                    control_mode=control_mode,
                                                    setpoints_manual={DATA.HEATING_SETPOINT_NEW: heating_setpoint_new,
                                                                      DATA.HEATING_SETPOINT_DEADBAND_UP: heating_deadband_up,
                                                                      DATA.HEATING_SETPOINT_DEADBAND_DOWN: heating_deadband_down,
                                                                      DATA.COOLING_SETPOINT_NEW: cooling_setpoint_new,
                                                                      DATA.COOLING_SETPOINT_DEADBAND_UP: cooling_deadband_up,
                                                                      DATA.COOLING_SETPOINT_DEADBAND_DOWN: cooling_deadband_down},
                                                    schedule_info={'contents': schedule_contents,
                                                                    'filename': schedule_filename},
                                                    output_step=output_step)
                output_step = cosim_session.proceed_simulation(control_input=control_input,
                                                               control_information=control_information)

                output_step = cosim_session.retrieve_outputs(control_information=control_information)
                time_sim_input = output_step[DATA.TIME_SIM]
                update_record(output_step=output_step,
                              record=record_each,
                              conditioned_zones=cosim_session.conditioned_zones,
                              unconditioned_zones=cosim_session.unconditioned_zones)

                update_record(output_step=output_step,
                              record=record_each,
                              conditioned_zones=cosim_session.conditioned_zones,
                              unconditioned_zones=cosim_session.unconditioned_zones)
            return cosim_session.alias, record_each

        record_aggregated = Parallel(n_jobs=len(self.cosim_sessions))\
                                    (delayed(update_model_each)\
                                            (cosim_session, steps_to_proceed)
                                                for cosim_session in self.cosim_sessions if cosim_session.alias in model_to_control)

        record_current = dict()
        for alias, record_each in record_aggregated:
            record_current[alias] = record_each.copy()
        """
        # Not parallelized version of simulation running
        record_current = dict()
        for cosim_session in self.cosim_sessions:
            if cosim_session.alias in model_to_control:
                record_current[cosim_session.alias] = get_record_template(name=cosim_session.alias,
                                                                          time_start=None, 
                                                                          time_end=None, 
                                                                          conditioned_zones=cosim_session.conditioned_zones,
                                                                          unconditioned_zones=cosim_session.unconditioned_zones,
                                                                          is_initial_record=False, 
                                                                          output_step=None)

                for _ in range(int(np.floor(float(steps_to_proceed)))):
                    time_sim_input = cosim_session.alfalfa_client.get_sim_time(cosim_session.model_id)
                    control_input, control_information = \
                        cosim_session.compute_control(time_sim=time_sim_input,
                                                      control_mode=control_mode,
                                                      setpoints_manual={DATA.HEATING_SETPOINT_NEW: heating_setpoint_new,
                                                                        DATA.HEATING_SETPOINT_DEADBAND_UP: heating_deadband_up,
                                                                        DATA.HEATING_SETPOINT_DEADBAND_DOWN: heating_deadband_down,
                                                                        DATA.COOLING_SETPOINT_NEW: cooling_setpoint_new,
                                                                        DATA.COOLING_SETPOINT_DEADBAND_UP: cooling_deadband_up,
                                                                        DATA.COOLING_SETPOINT_DEADBAND_DOWN: cooling_deadband_down},
                                                      schedule_info={'contents': schedule_contents,
                                                                     'filename': schedule_filename},
                                                      output_step=)
                    output_step = cosim_session.proceed_simulation(control_input=control_input,
                                                                   control_information=control_information)
                    update_record(output_step=output_step,
                                  record=record_current[cosim_session.alias],
                                  conditioned_zones=cosim_session.conditioned_zones,
                                  unconditioned_zones=cosim_session.unconditioned_zones)
        """
        
        # Record elapsed time for simulation?
        time_end = time.time_ns()
        print(f'elapsed time to collect export data: {(time_end - time_start)/1000000000}')

        ## Append global record with current record (except for DATA.SETTING)
        for cosim_session in self.cosim_sessions:
            if cosim_session.alias in model_to_control:
                for category in [DATA.INPUT, DATA.STATUS]:
                    for key in record_current[cosim_session.alias][category]:
                        record[cosim_session.alias][category][key].extend(record_current[cosim_session.alias][category][key])

        print("update_output:refresh tab --> add a whitespace to change tab value triggerring graph update callback")
        tab_with_whitespace = tab + ' '
        print("tab_with_whitespace:", tab_with_whitespace)
        print("update_output:finishing callback")

        # Only return the last values
        return tab_with_whitespace, record


    def tear_down(self, n_clicks):
        print("exit:entering callback")
        print("n_clicks:", n_clicks)
        for cosim_session in self.cosim_sessions:
            cosim_session.alfalfa_client.stop(
                cosim_session.model_id     # site_id
            )
        print("exit:finishing callback")
        exit()
        return n_clicks


    def render_plots(self, alias, tab, record):
        print("render_plots:entering callback")
        print(f"render_plots:alias: {alias} and tab: {tab}")
        ## Note: graph reference --> https://plotly.com/javascript/reference/
        tab_stripped = tab.strip()

        ## Use empty initial record, if not initialized yet (initialization is done at update_output, as this function does not save record)
        if record == None:
            record = dict()
            record[alias] = self.record_initial[alias].copy()
        elif not self.initialized[alias]:
            record[alias] = self.record_initial[alias].copy()
            print('render_plots:initial empty record is used (note: initialization will be done at update_output()')

        figure = make_subplots(
            rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.02,
            subplot_titles=(
                'Plot 1: Temperatures',
                'Plot 2: Humidity',
                'Plot 3: Runtime Fractions',
                'Plot 4: Airflow',
                'Plot 5: Occupancy',
                'Plot 6: Thermal frustration',
                'Plot 7: HVAC Energy'
            ),
            specs=[
                [{'secondary_y': True}],
                [{'secondary_y': True}],
                [{'secondary_y': True}],
                [{'secondary_y': True}],
                [{'secondary_y': True}],
                [{'secondary_y': True}],
                [{'secondary_y': True}]
            ])
        figure.update_layout({'autosize': True, 'height': 3000, 'margin_b': 8,
                              'legend_groupclick': 'toggleitem',
                              'xaxis_showticklabels': True,
                              'xaxis2_showticklabels': True,
                              'xaxis3_showticklabels': True,
                              'xaxis4_showticklabels': True,
                              'xaxis5_showticklabels': True,
                              'xaxis6_showticklabels': True,
                              'xaxis7_showticklabels': True
                              })

        ## Subplot 1: Temperature Plot
        # Add zone mean temperature for each zone
        for key_record in record[alias][DATA.STATUS]:
            if DATA.ZONE_MEAN_TEMP in key_record:
                figure.add_trace(
                    go.Scatter(name=key_record,
                               legendgroup='temperature', legendgrouptitle_text='Plot 1: Temperatures',
                               x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][key_record]),
                    row=1, col=1, secondary_y=False
                )

        figure.add_trace(
            go.Scatter(name=DATA.HEATING_SETPOINT_DEADBAND_APPLIED,
                       legendgroup='temperature',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.HEATING_SETPOINT_DEADBAND_APPLIED]),
            row=1, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.HEATING_SETPOINT_BASE,
                       legendgroup='temperature',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.HEATING_SETPOINT_BASE]),
            row=1, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.COOLING_SETPOINT_DEADBAND_APPLIED,
                       legendgroup='temperature',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.COOLING_SETPOINT_DEADBAND_APPLIED]),
            row=1, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.COOLING_SETPOINT_BASE,
                       legendgroup='temperature',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.COOLING_SETPOINT_BASE]),
            row=1, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.SYSTEM_NODE_TEMPERATURE,
                       legendgroup='temperature',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.SYSTEM_NODE_TEMPERATURE]),
            row=1, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE,
                       legendgroup='temperature',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.OUTDOOR_AIR_DRYBULB_TEMPERATURE]),
            row=1, col=1, secondary_y=False
        )

        indices_habitual_override = np.where(np.array(record[alias][DATA.STATUS][DATA.OCCUPANT_HABITUAL_OVERRIDE]) == True)[0]
        indices_discomfort_override = np.where(np.array(record[alias][DATA.STATUS][DATA.OCCUPANT_DISCOMFORT_OVERRIDE]) == True)[0]

        x_coord_habitual_override = []
        y_coord_habitual_override = []
        for index_habitual_override in indices_habitual_override:
            x_coord_habitual_override.append(record[alias][DATA.STATUS][DATA.TIME_SIM][index_habitual_override])
            y_coord_habitual_override.append(record[alias][DATA.STATUS][DATA.HEATING_SETPOINT_BASE][index_habitual_override])

            x_coord_habitual_override.append(record[alias][DATA.STATUS][DATA.TIME_SIM][index_habitual_override])
            y_coord_habitual_override.append(record[alias][DATA.STATUS][DATA.COOLING_SETPOINT_BASE][index_habitual_override])
        figure.add_trace(
            go.Scatter(name=DATA.OCCUPANT_HABITUAL_OVERRIDE, mode='markers',
                       legendgroup='temperature',
                       marker={'color': 'blue', 'symbol': 'circle'},
                       x=x_coord_habitual_override, y=y_coord_habitual_override),
            row=1, col=1, secondary_y=False
        )

        x_coord_discomfort_override = []
        y_coord_discomfort_override = []
        for index_discomfort_override in indices_discomfort_override:
            x_coord_discomfort_override.append(record[alias][DATA.STATUS][DATA.TIME_SIM][index_discomfort_override])
            y_coord_discomfort_override.append(
                record[alias][DATA.STATUS][DATA.HEATING_SETPOINT_BASE][index_discomfort_override])

            x_coord_discomfort_override.append(record[alias][DATA.STATUS][DATA.TIME_SIM][index_discomfort_override])
            y_coord_discomfort_override.append(
                record[alias][DATA.STATUS][DATA.COOLING_SETPOINT_BASE][index_discomfort_override])
        figure.add_trace(
            go.Scatter(name=DATA.OCCUPANT_DISCOMFORT_OVERRIDE, mode='markers',
                       legendgroup='temperature',
                       marker={'color': 'red', 'symbol': 'x'},
                       x=x_coord_discomfort_override, y=y_coord_discomfort_override),
            row=1, col=1, secondary_y=False
        )

        ## Subplot 2: Humidity Plot
        for key_record in record[alias][DATA.STATUS]:
            if DATA.ZONE_RELATIVE_HUMIDITY in key_record:
                figure.add_trace(
                    go.Scatter(name=key_record,
                               legendgroup='humidity', legendgrouptitle_text='Plot 2: Humidity',
                               x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][key_record]),
                    row=2, col=1, secondary_y=False
                )

        ## Subplot 3: Runtime Fraction Plot
        figure.add_trace(
            go.Scatter(name=DATA.HEATING_COIL_RUNTIME_FRACTION,
                       legendgroup='runtime', legendgrouptitle_text='Plot 3: Runtime Fraction',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.HEATING_COIL_RUNTIME_FRACTION]),
            row=3, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.COOLING_COIL_RUNTIME_FRACTION,
                       legendgroup='runtime',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.COOLING_COIL_RUNTIME_FRACTION]),
            row=3, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.SUPPLY_FAN_AIR_MASS_FLOW_RATE,
                       legendgroup='runtime',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.SUPPLY_FAN_AIR_MASS_FLOW_RATE]),
            row=3, col=1, secondary_y=False
        )

        ## Subplot 4: Airflow Plot
        figure.add_trace(
            go.Scatter(name=DATA.SYSTEM_NODE_CURRENT_DENSITY_VOLUME_FLOW_RATE,
                       legendgroup='airflow', legendgrouptitle_text='Plot 4: Airflow',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.SYSTEM_NODE_CURRENT_DENSITY_VOLUME_FLOW_RATE]),
            row=4, col=1, secondary_y=False
        )

        ## Subplot 5: Occupancy Plot
        # Remove 'None' from the data using backfill
        data_thermostat_schedule = np.array(record[alias][DATA.STATUS][DATA.THERMOSTAT_SCHEDULE]).copy()
        data_thermostat_mode = np.array(record[alias][DATA.STATUS][DATA.THERMOSTAT_MODE]).copy()

        indices_none_thermostat_schedule = np.where(data_thermostat_schedule == 'None')[0]
        indices_none_thermostat_mode = np.where(data_thermostat_mode == 'None')[0]

        if len(data_thermostat_schedule) > 1:
            for index_none_thermostat_schedule in indices_none_thermostat_schedule:
                data_thermostat_schedule[index_none_thermostat_schedule] = data_thermostat_schedule[
                    index_none_thermostat_schedule + 1]

        if len(data_thermostat_mode) > 1:
            for index_none_thermostat_mode in indices_none_thermostat_mode:
                data_thermostat_mode[index_none_thermostat_mode] = data_thermostat_mode[index_none_thermostat_mode + 1]

        figure.add_trace(
            go.Scatter(name=DATA.THERMOSTAT_SCHEDULE,
                       legendgroup='occupancy', legendgrouptitle_text='Plot 5: Occupancy',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=data_thermostat_schedule),
            row=5, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.THERMOSTAT_MODE,
                       legendgroup='occupancy',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=data_thermostat_mode),
            row=5, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.OCCUPANT_MOTION,
                       legendgroup='occupancy',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.OCCUPANT_MOTION]),
            row=5, col=1, secondary_y=False
        )

        ## Subplot 6: Thermal Frustration Plot
        figure.add_trace(
            go.Scatter(name=DATA.OCCUPANT_THERMAL_FRUSTRATION,
                       legendgroup='sensation', legendgrouptitle_text='Plot 6: Thermal Frustration',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.OCCUPANT_THERMAL_FRUSTRATION]),
            row=6, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.OCCUPANT_COMFORT_DELTA,
                       legendgroup='sensation',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=record[alias][DATA.STATUS][DATA.OCCUPANT_COMFORT_DELTA]),
            row=6, col=1, secondary_y=True
        )

        ## Subplot 7: HVAC Energy Plot
        data_cooling_coil_energy = np.array(record[alias][DATA.STATUS][DATA.COOLING_COIL_ELECTRICITY_ENERGY]).copy()
        data_heating_coil_electricity_energy = np.array(record[alias][DATA.STATUS][DATA.HEATING_COIL_ELECTRICITY_ENERGY]).copy()
        data_heating_coil_fuel_energy = np.array(record[alias][DATA.STATUS][DATA.HEATING_COIL_FUEL_ENERGY]).copy()
        data_fan_energy = np.array(record[alias][DATA.STATUS][DATA.FAN_ELECTRICITY_ENERGY]).copy()
        data_hvac_energy = data_cooling_coil_energy + \
                           data_heating_coil_electricity_energy + \
                           data_heating_coil_fuel_energy + \
                           data_fan_energy

        figure.add_trace(
            go.Scatter(name=DATA.COOLING_COIL_ELECTRICITY_ENERGY,
                       legendgroup='energy', legendgrouptitle_text='Plot 7: Energy Usage',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=data_cooling_coil_energy),
            row=7, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.HEATING_COIL_ELECTRICITY_ENERGY,
                       legendgroup='energy',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=data_heating_coil_electricity_energy),
            row=7, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.HEATING_COIL_FUEL_ENERGY,
                       legendgroup='energy',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=data_heating_coil_fuel_energy),
            row=7, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name=DATA.FAN_ELECTRICITY_ENERGY,
                       legendgroup='energy',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=data_fan_energy),
            row=7, col=1, secondary_y=False
        )
        figure.add_trace(
            go.Scatter(name='HVAC total energy input',
                       legendgroup='energy',
                       x=record[alias][DATA.STATUS][DATA.TIME_SIM], y=data_hvac_energy),
            row=7, col=1, secondary_y=False
        )

        return html.Div([
            dcc.Graph(
                id='-plot_dcc-',
                figure=figure,
            )
        ])

    def change_control_mode(self, value_radio, control_mode, debug=True):
        ## Note: graph reference --> https://plotly.com/javascript/reference/
        if value_radio == CONTROL.PASSTHROUGH:
            control_mode_previous = control_mode
            control_mode_updated = CONTROL.PASSTHROUGH
            if debug: print(f"control mode change from {control_mode_previous} to {control_mode_updated}")
        elif value_radio == CONTROL.SETPOINTS:
            control_mode_previous = control_mode
            control_mode_updated = CONTROL.SETPOINTS
            if debug: print(f"control mode change from {control_mode_previous} to {control_mode_updated}")
        elif value_radio == CONTROL.SCHEDULE:
            control_mode_previous = control_mode
            control_mode_updated = CONTROL.SCHEDULE
            if debug: print(f"control mode change from {control_mode_previous} to {control_mode_updated}")
        elif value_radio == CONTROL.OCCUPANT_MODEL:
            control_mode_previous = control_mode
            control_mode_updated = CONTROL.OCCUPANT_MODEL
            if debug: print(f"control mode change from {control_mode_previous} to {control_mode_updated}")
        elif value_radio == CONTROL.SCHEDULE_AND_OCCUPANT_MODEL:
            control_mode_previous = control_mode
            control_mode_updated = CONTROL.SCHEDULE_AND_OCCUPANT_MODEL
            if debug: print(f"control mode change from {control_mode_previous} to {control_mode_updated}")
        return control_mode_updated

    def upload_schedule(self, content_schedule, filename_schedule, debug=True):
        return html.Div([f'Uploaded schedule: {filename_schedule}'])     # return upload children

    def export_data(self, n_clicks, record):
        print("export_data:entering callback")
        # Speed comparison with and without parallelization of export process, before return statement
        # Tested on surface laptop (1000 steps, 3 models):
        #  -Without parallelization: 2.4612064 sec
        #  -With parallelization: 4.6281084
        # --> decieded to perform without parallelization
        output = io.BytesIO()
        writer = pd.ExcelWriter(path=output, engine='openpyxl')
        for cosim_session in self.cosim_sessions:
            sheet_prefix = cosim_session.alias.split(':')[0]
            record_setting = pd.DataFrame.from_dict(record[cosim_session.alias][DATA.SETTING])
            record_data = pd.DataFrame.from_dict({**record[cosim_session.alias][DATA.INPUT], **record[cosim_session.alias][DATA.STATUS]})
            record_setting.to_excel(writer, sheet_name=sheet_prefix + '_' + DATA.SETTING, index=False)  # writes to BytesIO buffer
            record_data.to_excel(writer, sheet_name=sheet_prefix + '_' + DATA.DATA, index=False)

        writer.save()
        data = output.getvalue()

        print("export_data:exiting callback")
        return dcc.send_bytes(data, 'exported_data.xlsx')

    def initialize_callbacks(self):
        self.app.callback(
            Output('tabs-plots', 'value'),
            ServersideOutput('-record-', 'data'),
            Input('=proceed=', 'n_clicks'),
            State(id(DATA.HEATING_SETPOINT_NEW), 'value'),
            State(id(DATA.HEATING_SETPOINT_DEADBAND_UP), 'value'),
            State(id(DATA.HEATING_SETPOINT_DEADBAND_DOWN), 'value'),
            State(id(DATA.COOLING_SETPOINT_NEW), 'value'),
            State(id(DATA.COOLING_SETPOINT_DEADBAND_UP), 'value'),
            State(id(DATA.COOLING_SETPOINT_DEADBAND_DOWN), 'value'),
            State(id(DATA.STEP_NEW), 'value'),
            State('tabs-plots', 'value'),
            State('-control_mode-', 'value'),
            State('=upload_schedule=', 'contents'),
            State('=upload_schedule=', 'filename'),
            State('=model_select=', 'value'),
            State('=model_control=', 'value'),
            State('-record-', 'data'),
            prevent_initial_call=True)(self.update_output)

        self.app.callback(Output('-exit_test-', 'value'),
                          Input('=exit=', 'n_clicks'),
                          prevent_initial_call=True)(self.tear_down)

        self.app.callback(Output('tabs-plots-content', 'children'),
                          Input('=model_select=', 'value'),
                          Input('tabs-plots', 'value'),
                          State('-record-', 'data'))(self.render_plots)

        self.app.callback(Output('-control_mode-', 'value'),
                          Input('=mode_setpoint=', 'value'),
                          State('-control_mode-', 'value'),
                          prevent_initial_call=True)(self.change_control_mode)

        self.app.callback(Output('=upload_schedule=', 'children'),
                          Input('=upload_schedule=', 'contents'),
                          State('=upload_schedule=', 'filename'),
                          prevent_initial_call=True)(self.upload_schedule)

        self.app.callback(Output('-exported_data-', 'data'),
                          Input('=export=', 'n_clicks'),
                          State('-record-', 'data'),
                          prevent_initial_call=True)(self.export_data)



if __name__ == "__main__":
    ## Setting parameters
    debug = True                # set this True to print additional information to the console
    test_gui_only = False       # if True, create GUI without connecting to Alfalfa for testing

    # Resolve the IP address of another container by its name
    alfalfa_url = 'http://localhost'

    ## Simulation Time
    time_start = datetime.datetime(2019, 1, 1, 0, 0, 0)
    time_end = datetime.datetime(2019, 12, 31, 0, 0, 0)
    time_step_size = 1

    ## Create building model information: pair of 'model_name' and 'conditioned_zone_name'
    # model_name: location of the building model, under 'cosim/idf_files' folder
    # conditioned_zone_names: list of the names of conditioned zone (Note: not tested with multi-zone case)
    # unconditioned_zone_names: list of the names of unconditioned zone
    """
    model_name, conditioned_zones, unconditioned_zones =\
        'husky', \
        ['Zone Conditioned', ], \
        ['Zone Unconditioned Attic', 'Zone Unconditioned Basement']
    model_name, conditioned_zones, unconditioned_zones =\
        'green_husky', \
        ['living_1', ], \
        ['garage', 'unfinishedattic', 'Dummy', 'RA Duct Zone_1']
    model_name, conditioned_zones, unconditioned_zones =\
        'small_green_husky', \
        ['living_1', ], \
        ['garage', 'unfinishedattic', 'Dummy', 'RA Duct Zone_1']
    """
    model_name, conditioned_zones, unconditioned_zones =\
        'green_husky_v96', \
        ['living_1', ], \
        ['garage', 'unfinishedattic', 'Dummy', 'RA Duct Zone_1']

    ## Create input list
    list_input = []
    num_duplicates = 1
    for _ in range(num_duplicates):
        # building model and simulation information
        building_model_information = {
            SETTING.ALFALFA_URL: alfalfa_url,
            SETTING.NAME_BUILDING_MODEL: model_name,
            SETTING.PATH_BUILDING_MODEL: os.path.join('cosim', 'idf_files', model_name),
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
            SETTING.PATH_OCCUPANT_MODEL_DATA: {SETTING.PATH_CSV_DIR: 'cosim/src/occupant_model/input_data/csv_files/',
                                               SETTING.PATH_MODEL_DIR: 'cosim/src/occupant_model/input_data/model_files/'},
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


    cosim_sessions = []
    for index_input, input_each in enumerate(list_input):
        ## Create CoSimCore and GUI
        cosim_sessions.append(CoSimCore(alias='Model' + str(index_input+1) + ': ' + input_each[SETTING.BUILDING_MODEL_INFORMATION][SETTING.NAME_BUILDING_MODEL],
                                        building_model_information=input_each[SETTING.BUILDING_MODEL_INFORMATION],
                                        simulation_information=input_each[SETTING.SIMULATION_INFORMATION],
                                        occupant_model_information=input_each[SETTING.OCCUPANT_MODEL_INFORMATION],
                                        thermostat_model_information=input_each[SETTING.THERMOSTAT_MODEL_INFORMATION],
                                        test_default_model=False,
                                        debug=debug))


    print(f'=Running GUI mode...\n')
    ## Create Co-Simulation Framework and Run
    dash_gui = CoSimGUI(cosim_sessions=cosim_sessions,
                        test_gui_only=test_gui_only,
                        test_default_model=False,
                        debug=debug)
    dash_gui.run()
    print("Terminated!")