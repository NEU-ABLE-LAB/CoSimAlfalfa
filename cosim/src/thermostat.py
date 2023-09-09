'''
thermostat.py

This file contains the thermostat class that is used to control the heating and cooling setpoints of the building model.
'''
# Import libraries
import datetime

# Define thermostat class
class thermostat():
    '''
    This class contains the thermostat object that is used to control the heating and cooling setpoints of the building model.
    '''
    # Define class methods
    def __init__(self,units='c', schedule_type:str = 'default', current_datetime:datetime = datetime.datetime.now(), db:float = 0.0) -> None:
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
        return mode, schedule, tstp_cool, tstp_heat
    
    def manual_override(self, tstp_heat:float, tstp_cool:float):
        '''
        This function allows the user to manually override the thermostat.
        '''
        self.check_stp_db()
        self.mode = 'manual'
        self.tstp_heat = tstp_heat
        self.tstp_cool = tstp_cool

        print(f'Occupant has manually overridden the thermostat.\nNew heating setpoint: {self.tstp_heat}{self.units}\nNew cooling setpoint: {self.tstp_cool}{self.units}')
        return self.mode, self.schedule, self.tstp_cool, self.tstp_heat
    
    def check_to_change_schedule(self, current_datetime:datetime):
        '''
        This function checks to see if the thermostat should return to its regular schedule.
        '''
        if current_datetime.hour == 6 and current_datetime.minute == 0:
            change_schedule = True
        elif current_datetime.hour == 22 and current_datetime.minute == 0:
            change_schedule =  True
        else:
            change_schedule = False
        return change_schedule
    
    def update_output(self, current_datetime:datetime):
        '''
        This function updates the thermostat output based on the current time and the next time the thermostat will return to its regular schedule.
        '''
        if self.first_run:
            self.mode, self.schedule, self.tstp_cool, self.tstp_heat = self.get_tstat_schedule_params(current_datetime)
            self.first_run = False
        else:
            change_schedule = self.check_to_change_schedule(current_datetime)
            if change_schedule:
                self.mode, self.schedule, self.tstp_cool, self.tstp_heat = self.get_tstat_schedule_params(current_datetime)
        return self.mode, self.schedule, self.tstp_cool, self.tstp_heat
    