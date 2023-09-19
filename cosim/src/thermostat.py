'''
thermostat.py

This file contains the thermostat class that is used to control the heating and cooling setpoints of the building model.
'''
# Import libraries
import datetime
import pandas as pd

# Define thermostat class
class thermostat():
    '''
    This class contains the thermostat object that is used to control the heating and cooling setpoints of the building model.
    '''
    # Define class methods
    def __init__(self,units='c', schedule_type:str = 'default',
                    db:float = 0.0, experiments=[],path_2_exp_schedule='',days_per_exp=1) -> None:
        '''
        This function initializes the thermostat object.
        '''
        self.schedule_type = schedule_type.lower()
        self.schedule = None
        if self.schedule_type != 'default':
            raise ValueError('Only default schedule is supported at this time.')
        self.mode = None
        self.tstp_heat = None
        self.tstp_cool = None
        self.next_schedule_datetime = None
        self.first_run = True
        self.units = units.upper()
        self.db = db
        self.last_msc_datetime = None
        self.exp_2_run = experiments
        self.exp_name = None
        self.exp_next_idx = 0
        self.exp_days_passed = 11
        self.days_per_exp = days_per_exp
        
        if self.exp_2_run is not None:
            self.exp_schedule = pd.read_excel(path_2_exp_schedule)

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


    def C_to_F(self,T):
        return (T * 9/5) + 32
    
    def F_to_C(self,T):
        return (T - 32) * 5/9
    
    def check_stp_db(self):
        '''
        This function checks to make sure that the heating and cooling setpoints are valid.
        '''
        if self.tstp_cool - self.db > self.tstp_heat:
            pass
        else:
            raise ValueError(f"stp_cool({self.tstp_cool}) - db({self.db}) !> stp_heat({self.tstp_heat})")
    
    def get_tstat_schedule_params(self, current_datetime:datetime):
        '''
        This function returns the heating and cooling setpoints for the thermostat for the current time.
        '''
        if self.exp_2_run is None:
            if self.schedule_type == 'default':
                mode = 'auto'
                if current_datetime.hour >= 6 and current_datetime.hour < 22:
                    schedule = 'home'
                    tstp_heat = 69
                    tstp_cool = 78
                    
                elif current_datetime.hour >= 22 or current_datetime.hour < 6:
                    schedule = 'sleep'
                    tstp_heat = 67
                    tstp_cool = 80
            if self.units == 'C':
                tstp_heat = round(self.F_to_C(tstp_heat))
                tstp_cool = round(self.F_to_C(tstp_cool))
        else:
            
            tstp_heat = self.exp_tstp_heat
            tstp_cool = self.exp_tstp_cool
            mode = 'auto'
            schedule = self.exp_name

            if current_datetime.hour == self.exp_pc_start and current_datetime.minute == 0 and current_datetime.second == 0:
                mode = 'pc'
                schedule = self.exp_name
                tstp_heat = self.exp_tstp_heat
                tstp_cool = self.exp_tstp_cool + self.exp_pc_deg
                self.pc_start_datetime = current_datetime
                self.last_msc_datetime = None
            
            # Resume to regular schedule when the precool or setback is over.
            if self.pc_start_datetime is not None:
                print(f"current_datetime: {current_datetime.hour}")
                print(f"pc_start_datetime: {self.pc_start_datetime.hour}")

                if current_datetime.hour == self.pc_start_datetime.hour + self.exp_pc_dur and current_datetime.minute == 0 and current_datetime.second == 0:
                    mode = 'auto'
                    schedule = self.exp_name
                    tstp_heat = self.exp_tstp_heat
                    tstp_cool = self.exp_tstp_cool
                    self.pc_start_datetime = None

            if self.sb_start_datetime is not None:
                if current_datetime.hour == self.sb_start_datetime.hour + self.exp_sb_duration and current_datetime.minute == 0 and current_datetime.second == 0:
                    mode = 'auto'
                    schedule = self.exp_name
                    tstp_heat = self.exp_tstp_heat
                    tstp_cool = self.exp_tstp_cool
                    self.sb_start_datetime = None
                    
            if current_datetime.hour == self.exp_sb_start and current_datetime.minute == 0 and current_datetime.second == 0:
                mode = 'sb'
                schedule = self.exp_name
                tstp_heat = self.exp_tstp_heat
                tstp_cool = self.exp_tstp_cool + self.exp_sb_offset
                self.sb_start_datetime = current_datetime
                self.last_msc_datetime = None

            # Resume to regular schedule when the thermostat is manually overridden for more than 3 hours.
            if self.mode == 'manual':
                if current_datetime - self.last_msc_datetime > datetime.timedelta(hours=3):
                    mode = 'auto'
                    schedule = self.exp_name
                    tstp_heat = self.exp_tstp_heat
                    tstp_cool = self.exp_tstp_cool
                    self.last_msc_datetime = None

            if self.units == 'C':
                tstp_heat = round(self.F_to_C(tstp_heat))
                tstp_cool = round(self.F_to_C(tstp_cool))
        return mode, schedule, tstp_cool, tstp_heat
    
    def manual_override(self, tstp_heat:float, tstp_cool:float,current_datetime:datetime):
        '''
        This function allows the user to manually override the thermostat.
        '''
        self.check_stp_db()
        # Reset the start datetimes for the precool and setback when the thermostat is manually overridden.
        if self.mode == 'pc' or self.mode == 'sb':
            self.pc_start_datetime = 0
            self.sb_start_datetime = 0

        self.mode = 'manual'
        self.tstp_heat = tstp_heat
        self.tstp_cool = tstp_cool
        self.last_msc_datetime = current_datetime

        print(f'Occupant has manually overridden the thermostat.\nNew heating setpoint: {self.tstp_heat}{self.units}\nNew cooling setpoint: {self.tstp_cool}{self.units}')
        return self.mode, self.schedule, self.tstp_cool, self.tstp_heat
    
    # def check_to_change_schedule(self, current_datetime:datetime):
    #     '''
    #     This function checks to see if the thermostat should return to its regular schedule.
    #     '''
    #     if self.exp_2_run is not None:
    #         if current_datetime.hour == 6 and current_datetime.minute == 0 and current_datetime.second == 0:
    #             change_schedule = True
    #         elif current_datetime.hour == 22 and current_datetime.minute == 0 and current_datetime.second == 0:
    #             change_schedule =  True
    #         else:
    #             change_schedule = False
    #     # else:
            
    #     return change_schedule
    
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
            
            self.schedule_type = self.exp_name
            self.exp_tstp_cool = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'setpoint_cool'].values[0]
            self.exp_tstp_heat = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'setpoint_heat'].values[0]
            self.exp_sb_offset = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'sb_offset'].values[0]
            self.exp_sb_start = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'sb_start'].values[0]
            self.exp_sb_duration = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'sb_duration'].values[0]
            self.exp_pc_deg = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'pc_deg'].values[0]
            self.exp_pc_dur = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'pc_dur'].values[0]
            self.exp_pc_start = self.exp_schedule.loc[self.exp_schedule['exp_name'] == self.exp_name,'pc_start'].values[0]
        else:
            if current_datetime.hour == 0 and current_datetime.minute == 0 and current_datetime.second == 0:
                self.exp_days_passed += 1
        pass
    
    def update_output(self, current_datetime:datetime):
        '''
        This function updates the thermostat output based on the current time and the next time the thermostat will return to its regular schedule.
        '''
        if self.exp_2_run is None:
            if self.first_run:
                self.mode, self.schedule, self.tstp_cool, self.tstp_heat = self.get_tstat_schedule_params(current_datetime)
                self.first_run = False
            else:
                change_schedule = self.check_to_change_schedule(current_datetime)
                if change_schedule:
                    self.mode, self.schedule, self.tstp_cool, self.tstp_heat = self.get_tstat_schedule_params(current_datetime)
        else:
            self.update_current_exp(current_datetime)
            self.mode, self.schedule, self.tstp_cool, self.tstp_heat = self.get_tstat_schedule_params(current_datetime)

        return self.mode, self.schedule, self.tstp_cool, self.tstp_heat
    