'''
thermostat.py

This file contains the thermostat class that is used to control the heating and cooling setpoints of the building model.
'''
# Import libraries
import datetime  # For working with datetime objects
import pandas as pd  # For data manipulation

# Define thermostat class
class thermostat():
    '''
    This class contains the thermostat object that is used to control the heating and cooling setpoints of the building model.
    '''
    # Define class methods
    def __init__(self,units='c', schedule_type:str = 'default',
                    db:float = 0.0, experiments=None,path_2_exp_schedule='',days_per_exp=1) -> None:
        '''
        Initialize the thermostat object.
        '''
        # Set the schedule type (lowercase)
        self.schedule_type = schedule_type.lower()
        if self.schedule_type != 'default':
            raise ValueError('Only default schedule is supported at this time.')
        
        # Initialize various parameters and settings
        self.schedule = None
        self.mode = None  # Mode of operation (e.g., 'auto', 'manual')
        self.tstp_heat = None  # Heating setpoint
        self.tstp_cool = None  # Cooling setpoint
        self.next_schedule_datetime = None  # The next schedule's datetime
        self.units = units.upper()  # Temperature units ('C' or 'F')
        self.db = db  # Deadband
        self.last_msc_datetime = None  # Last datetime when mode was manually changed
        self.exp_2_run = experiments  # Experiments to run

        # Read experiment schedule if there are experiments to run
        if self.exp_2_run is not None:
            self.exp_name = None  # Current experiment name
            self.exp_next_idx = 0  # Index of next experiment
            self.exp_days_passed = 0  # Days passed in the current experiment
            self.days_per_exp = days_per_exp  # Days per experiment
            self.exp_schedule = pd.read_excel(path_2_exp_schedule)
            # Initialize experiment-specific parameters
            self.exp_tstp_heat = None
            self.exp_tstp_cool = None      
            self.exp_sb_offset = None
            self.exp_sb_start = None
            self.exp_sb_duration = None
            self.exp_pc_start = None
            self.exp_pc_deg = None
            self.exp_pc_dur = None
            self.pc_start_datetime = None
            self.sb_start_datetime = None

            self.exp_name = self.exp_2_run[self.exp_next_idx]
            self.assign_exp_schedule_params()

    # Conversion methods between Celsius and Fahrenheit
    def C_to_F(self, T):
        return (T * 9/5) + 32
    
    def F_to_C(self, T):
        return (T - 32) * 5/9

    # Method to check if the setpoints are valid (cooling setpoint should be higher than heating setpoint)
    def check_stp_db(self):
        if self.tstp_cool - self.db > self.tstp_heat:
            pass
        else:
            raise ValueError(f"stp_cool({self.tstp_cool}) - db({self.db}) !> stp_heat({self.tstp_heat})")
    
    # Method to set the default schedule
    def set_default_schedule(self):
        self.mode = 'auto'
        self.schedule = self.exp_name
        self.tstp_heat = round(self.F_to_C(self.exp_tstp_heat))
        self.tstp_cool = round(self.F_to_C(self.exp_tstp_cool))
    
    # Method to assign experiment-specific parameters
    def assign_exp_schedule_params(self):
        # Assign properties based on the experiment schedule
        self.schedule_type = self.exp_name
        self.exp_tstp_cool = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'setpoint_cool'].values[0]
        self.exp_tstp_heat = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'setpoint_heat'].values[0]
        self.exp_sb_offset = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'sb_offset'].values[0]
        self.exp_sb_start = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'sb_start'].values[0]
        self.exp_sb_duration = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'sb_duration'].values[0]
        self.exp_pc_deg = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'pc_deg'].values[0]
        self.exp_pc_dur = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'pc_dur'].values[0]
        self.exp_pc_start = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'pc_start'].values[0]
        self.set_default_schedule()
    pass

    # Methods to check and start/stop 'pc' and 'sb' modes
    def check_and_start_pc(self, current_datetime:datetime):
        if current_datetime.hour == self.exp_pc_start and current_datetime.minute == 0 and current_datetime.second == 0:
                self.mode = 'pc'
                self.schedule = self.exp_name
                self.tstp_heat = round(self.F_to_C(self.exp_tstp_heat))
                self.tstp_cool = round(self.F_to_C(self.exp_tstp_cool + self.exp_pc_deg))
                self.pc_start_datetime = current_datetime
                self.last_msc_datetime = None
    def check_and_start_sb(self, current_datetime:datetime):
        if current_datetime.hour == self.exp_sb_start and current_datetime.minute == 0 and current_datetime.second == 0:
            self.mode = 'sb'
            self.schedule = self.exp_name
            self.tstp_heat = round(self.F_to_C(self.exp_tstp_heat))
            self.tstp_cool = round(self.F_to_C(self.exp_tstp_cool + self.exp_sb_offset))
            self.sb_start_datetime = current_datetime
            self.last_msc_datetime = None
    def check_and_end_pc(self, current_datetime:datetime):
        if self.pc_start_datetime is not None:
            print(f"current_datetime: {current_datetime}")
            print(f"pc_start_datetime: {self.pc_start_datetime}")

            if current_datetime.hour == self.pc_start_datetime.hour + self.exp_pc_dur and current_datetime.minute == 0 and current_datetime.second == 0:
                self.set_default_schedule()
                self.pc_start_datetime = None
    def check_and_end_sb(self, current_datetime:datetime):
        if self.sb_start_datetime is not None:
            if current_datetime.hour == self.sb_start_datetime.hour + self.exp_sb_duration and current_datetime.minute == 0 and current_datetime.second == 0:
                self.set_default_schedule()
                self.sb_start_datetime = None
    
    # Method to end 'manual' mode after 3 hours
    def check_and_end_msc(self, current_datetime:datetime):
        # Resume to regular schedule when the thermostat is manually overridden for more than 3 hours.
        if self.mode == 'manual':
            if current_datetime - self.last_msc_datetime > datetime.timedelta(hours=3):
                self.set_default_schedule()
                self.last_msc_datetime = None
        
    # Method to update thermostat parameters based on time and mode
    def update_tstat_schedule_params(self, current_datetime:datetime):
        '''
        This function returns the heating and cooling setpoints for the thermostat for the current time.
        '''
        if self.exp_2_run is None:
            if self.schedule_type == 'default':
                self.mode = 'auto'
                if current_datetime.hour >= 6 and current_datetime.hour < 22:
                    self.schedule = 'home'
                    tstp_heat = 69
                    tstp_cool = 78
                    
                elif current_datetime.hour >= 22 or current_datetime.hour < 6:
                    self.schedule = 'sleep'
                    tstp_heat = 67
                    tstp_cool = 80
            if self.units == 'C':
                self.tstp_heat = round(self.F_to_C(tstp_heat))
                self.tstp_cool = round(self.F_to_C(tstp_cool))
        else:
            self.check_and_end_msc(current_datetime)
            self.check_and_start_pc(current_datetime)
            self.check_and_end_pc(current_datetime)
            self.check_and_start_sb(current_datetime)
            self.check_and_end_sb(current_datetime)
        pass 
    
    # Method for manual override of thermostat settings
    def manual_override(self, tstp_heat:float, tstp_cool:float,current_datetime:datetime):
        '''
        This function allows the user to manually override the thermostat.
        '''
        self.check_stp_db()
        # Reset the start datetimes for the precool and setback when the thermostat is manually overridden.
        if self.mode == 'pc' or self.mode == 'sb':
            self.pc_start_datetime = None
            self.sb_start_datetime = None

        self.mode = 'manual'
        self.tstp_heat = tstp_heat
        self.tstp_cool = tstp_cool
        self.last_msc_datetime = current_datetime

        print(f'Occupant has manually overridden the thermostat.\nNew heating setpoint: {self.tstp_heat}{self.units}\nNew cooling setpoint: {self.tstp_cool}{self.units}')
        return self.mode, self.schedule, self.tstp_cool, self.tstp_heat
    
    # Method to update the current experiment
    def update_current_exp(self,current_datetime):
        '''
        This function updates the current experiment that the thermostat is running.
        '''
        if self.exp_days_passed >= self.days_per_exp:
            self.exp_name = self.exp_2_run[self.exp_next_idx]
            self.exp_next_idx += 1
            self.exp_days_passed = 0

            if self.exp_next_idx == len(self.exp_2_run):
                self.exp_next_idx = 0
                self.exp_days_passed += 1
            
            self.assign_exp_schedule_params()
        else:
            if current_datetime.hour == 0 and current_datetime.minute == 0 and current_datetime.second == 0:
                self.exp_days_passed += 1
        pass
    
    # Method to update the thermostat output based on time and experiment
    def update_output(self, current_datetime:datetime):
        '''
        This function updates the thermostat output based on the current time and the next time the thermostat will return to its regular schedule.
        '''
        if self.exp_2_run is None:
            self.mode, self.schedule, self.tstp_cool, self.tstp_heat = self.update_tstat_schedule_params(current_datetime)
        else:
            self.update_current_exp(current_datetime)
            self.update_tstat_schedule_params(current_datetime)

        return self.mode, self.schedule, self.tstp_cool, self.tstp_heat
    