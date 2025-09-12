import os, sys
import numpy as np
from math import sqrt
# import matplotlib.pyplot as plt

from flexseapython.fxUtil import *

import configparser
from scipy.signal import butter, lfilter


LEFT = 1
RIGHT = -1

ZEROING_CURRENT = 1800      ### mA
NO_SLACK_CURRENT = 1200
PEAK_CURRENT = 28000

### Data, Units & Conversion Formulas: https://dephy.com/wiki/flexsea/doku.php?id=units&s[]=ankle&s[]=torque
### One tick is equivalent to 360/2^14=0.02197 degrees.
TICKS_TO_ANGLE_COEFF =  0.02197
ANGLE_TO_TICKS_COEFF = 1 / TICKS_TO_ANGLE_COEFF

BIT_TO_GYRO_COEFF = 1 / 32.8

NUM_GAIT_TIMES_TO_AVERAGE = 3   # For the gait duration estimate how many gait cycles to average.

ARMED_DURATION_PERCENT = 10
HEELSTRIKE_THRESHOLD_ABOVE = 150 / BIT_TO_GYRO_COEFF    ### 4920.
HEELSTRIKE_THRESHOLD_BELOW = -300 / BIT_TO_GYRO_COEFF   ### -9840.

def Tick_to_Angle(ticks):
    return ticks * TICKS_TO_ANGLE_COEFF

def NM_TO_MNM(torque):
    return torque * 1000

def A_TO_MA(current):
    return current * 1000


class ExoBoot:

    ### When connected via Bluetooth, the frequency should not be over 100.
    def __init__(self, devSide, port, baudRate, frequency=1000, shouldLog=True):
        ### Connect to the ExoBoot.
        print('\nConnecting to ExoBoot...')
        self.port = port
        self.baudRate = baudRate
        self.side = devSide     ### LEFT:1  RIGHT:-1
        self.frequency = frequency
        self.shouldLog = shouldLog

        self.devId = fxOpen(self.port, self.baudRate, logLevel = 6)
        sleep(1)
        fxStartStreaming(self.devId, frequency=self.frequency, shouldLog=self.shouldLog)
        sleep(0.1)

        print('ExoBoot Connected Successfully!')
        print('ExoBoot ID: ', self.devId)


        ### Current State.
        self.num_gait = 0
        self.num_gait_in_block = 0
        self.percent_gait = -1

        self.motor_tick_offset = -1
        self.ankle_offset = -1
        self.past_stride_times = [-1] * NUM_GAIT_TIMES_TO_AVERAGE   # store the most recent gait times
        self.expected_duration = -1

        self.segmentation_trigger = False
        self.heelstrike_armed = False
        self.segmentation_arm_threshold = HEELSTRIKE_THRESHOLD_ABOVE
        self.segmentation_trigger_threshold = HEELSTRIKE_THRESHOLD_BELOW

        self.current_duration = -1
        self.heelstrike_timestamp_current = -1
        self.heelstrike_timestamp_previous = -1
        self.armed_timestamp = -1

        ### ExoBoot Data.
        self.current_time = -1
        self.accelx = -1
        self.accely = -1
        self.accelz = -1
        self.gyrox = -1
        self.gyroy = -1
        self.gyroz = -1

        self.motorTicksOffset = 0
        self.ankle_ticks_offset = 0

        self.tau = -1
        self.current = -1

        ### Collins Torque Profile Parameters
        self.t_rise = -1
        self.t_fall = -1
        self.t_peak = -1
        self.weight = -1
        self.peak_torque_norm = -1
        self.peak_torque = -1

        self.a1 = -1
        self.b1 = -1
        self.c1 = -1
        self.d1 = -1
        self.a2 = -1
        self.b2 = -1
        self.c2 = -1
        self.d2 = -1
        self.cnsts1 = [-1] * 4
        self.cnsts2 = [-1] * 4


        ### Filter.
        self.sampling_freq = 500
        self.b, self.a = butter(2, 12/(self.sampling_freq/2), 'low')

        self.ankleVel = [0.0]*3
        self.ankleVel_filt = [0.0]*3 

        self.kinematicCoeffs = np.array([-400, 0])
        self.magnitude = 40 * 45.5111

        ### Motor Parameters.
        self.kt = 0.14   ## 48

        ### Read in calibration data.
        cal_filename = 'bootCal.txt'
        config = configparser.ConfigParser()
        config.read(cal_filename)
        self.boot_id = config.get('ids', 'left' if self.side == LEFT else 'right')
        self.ankle_ticks_abs_offset_plantar = config.getint(self.boot_id, 'ankle_reading_55_deg')
        self.ankle_ticks_abs_offset = self.ankle_ticks_abs_offset_plantar - self.side * 55 * ANGLE_TO_TICKS_COEFF
        self.wm_wa_coeffs = [config.getfloat(self.boot_id,'poly4'), config.getfloat(self.boot_id,'poly3'), config.getfloat(self.boot_id,'poly2'), config.getfloat(self.boot_id,'poly1'),  config.getfloat(self.boot_id,'poly0')]
        self.wm_wa = 0 

        self.ank_mot_coeffs = [config.getfloat(self.boot_id,'poly4'), config.getfloat(self.boot_id,'poly3'), config.getfloat(self.boot_id,'poly2'), config.getfloat(self.boot_id,'poly1'), config.getfloat(self.boot_id,'poly0'),  0]

        ### Update the data for the first time.
        self.heelstrike_timestamp_current = self.current_time

        self.read_data()

        ### Calibrate the encoder-ankle mapping!!! IMPORTANT!!!
        input('Please Stand Still and Do NOT Move while Calibrating...')
        self.zero_boot()
        self.encoder_check()

        # self.printStatus()

    
    def read_data(self):
        ### Import Data.
        Exo_Data = fxReadDevice(self.devId)
        
        self.current_time = Exo_Data.state_time      ### ms.
        self.accelx = Exo_Data.accelx
        self.accely = Exo_Data.accely
        self.accelz = Exo_Data.accelz
        self.gyrox = Exo_Data.gyrox
        self.gyroy = Exo_Data.gyroy
        self.gyroz = Exo_Data.gyroz * self.side
        # print('gyroz: ', self.gyroz)
        
        self.motorTicksRaw = Exo_Data.mot_ang
        self.motorTicksZeroed = self.side * (self.motorTicksRaw - self.motorTicksOffset)    ### Set initial motor angle as 0.
        self.motorCurrent = Exo_Data.mot_cur

        self.ankleTicksRaw = Exo_Data.ank_ang
        self.ankleTicksZeroed = self.side * (self.ankleTicksRaw - self.ankle_ticks_offset)  ### Set initial ankle angle as 0.
        self.ankleTicksAbsZeroed = self.side * (self.ankleTicksRaw - self.ankle_ticks_abs_offset)   ### Set ankle perpendicular to ground as 0.

        self.ankleVelocity = Exo_Data.ank_vel

        ### Filter the velocity.
        # 0 is newest value, 1 is middle, 2 is oldest value
        self.ankleVel.pop() # remove last index
        self.ankleVel.insert(0, self.ankleVelocity) # add new value to index 0
        y_new = self.lpfilter(self.ankleVel, self.ankleVel_filt, self.a, self.b)
        self.ankleVel_filt.pop()
        self.ankleVel_filt.insert(0, y_new)



        ### Data Update.
        self.HeelStrike_Detect()
        if (self.segmentation_trigger):
            self.heelstrike_timestamp_previous = self.heelstrike_timestamp_current
            self.heelstrike_timestamp_current = self.current_time
            self.update_expected_duration()


        ### Uncomment if want fixed expected_duration and no heel strike detection.
        # if (self.percent_gait >= 100):
        #     self.heelstrike_timestamp_previous = self.heelstrike_timestamp_current
        #     self.heelstrike_timestamp_current = self.current_time
        # self.expected_duration = 1500

        
        self.percent_gait_calc()

        self.calc_wm_wa()

        # self.printStatus()
    
    def encoder_check(self):
        print('\nStart Encoder Checking for Boot: ', self.devId, '...')
        fxSetGains(self.devId, 175, 50, 0, 0, 0, 0)
        sleep(0.5)

        angleCheck = 0
        while angleCheck == 0:
            for i in range(0,3):    ### Check initial encoder angle three times.
                actPackState = fxReadDevice(self.devId)
                initialAngle = actPackState.mot_ang
                print('Encoder check ' + str(i) + ':' + str(initialAngle))
            actPackState = fxReadDevice(self.devId)
            initialAngle = actPackState.ank_ang
            initialMotor = actPackState.mot_ang
            initialMotor_des = np.floor(np.polyval(self.ank_mot_coeffs, initialAngle))    # calculate desired motor position from polynomial coefficients
            zeroing = initialMotor - initialMotor_des  # calculate difference between current motor position and desired motor position
            self.ank_mot_coeffs[-1] = self.ank_mot_coeffs[-1] + zeroing   # shift coefficients to meet current motor encoder value
            initialMotor_shift = np.floor(np.polyval(self.ank_mot_coeffs, initialAngle))     # check the interpolation worked correctly

            print('Initial Angle: ' + str(initialAngle))
            print('Initial Motor Actual: ' + str(initialMotor))
            print('Initial Motor Desired: ' + str(initialMotor_des))
            print('Offset to zero: ' + str(zeroing))
            print('Initial Motor: ' + str(initialMotor) + ', Initial Motor Desired (shifted): ' + str(initialMotor_shift))
            check = input("Is this correct? ")
            if check == 'y':
                angleCheck=1
                input('Press Enter to Continue...\n')
                fxSendMotorCommand(self.devId, FxNone, 0)
            else:
                angleCheck=0


    ### After Initializing, tighten the belt and record the initial data.
    def zero_encoders(self):
        self.read_data()
        self.motorTicksOffset = self.motorTicksRaw
        self.ankle_ticks_offset = self.ankleTicksRaw

    
    def calc_wm_wa (self) :
        self.wm_wa = 5 * self.ankleTicksRaw ** 4 * self.wm_wa_coeffs[0] + 4 * self.ankleTicksRaw ** 3 * self.wm_wa_coeffs[1] + 3 * self.ankleTicksRaw ** 2 * self.wm_wa_coeffs[2] + 2 * self.ankleTicksRaw * self.wm_wa_coeffs[3] + self.wm_wa_coeffs[4]
        if (self.wm_wa <= 0.5):     ### safety check to keep it from getting too large.
            self.wm_wa = 1
    

    ### Takes in torque in mNm, outputs current in A.
    ### q-axis_current =  Dephy_current/1000*0.537/sqrt(2)      Dephy_current in mA.
    ### q-axis_voltage =  Dephy_voltage/1000*sqrt(3/2)
    ### q-axis Kt, Kb = 0.14  (Nm/A)
    def ankle_torque_to_current(self, torque):
        # current = (torque / self.wm_wa) / self.kt
        q_axis_current = (torque / self.wm_wa) / 1000.0 / self.kt     ### A.
        Dephy_current = q_axis_current * sqrt(2) / 0.537
        return Dephy_current    ### A.
    

    ### Generate cnsts1 and cnsts2 for spline curve.
    def init_collins_profile(self, t_rise=None, t_fall=None, t_peak=None, weight=None, peak_torque_norm=None):
        if (t_rise != None):
            self.t_rise = t_rise
        if (t_fall != None):
            self.t_fall = t_fall
        if (t_peak != None):
            self.t_peak = t_peak
        if (weight != None):
            self.weight = weight
        if (peak_torque_norm != None):
            self.peak_torque_norm = peak_torque_norm
        
        if (self.t_rise != -1 and self.t_fall != -1 and self.t_peak != -1 and self.weight != -1 and self.peak_torque_norm != -1):
            self.peak_torque = self.peak_torque_norm * self.weight
            onset_torque = 0
            t0 = self.t_peak - self.t_rise
            t1 = self.t_peak + self.t_fall

            # ### Do linear algebra to solve for coefficients (cnsts)
            # m1 = np.array([[ (self.t_peak-self.t_rise)**3   ,  (self.t_peak-self.t_rise)**2 ,  (self.t_peak-self.t_rise) ,  1 ], \
            #                 [ self.t_peak**3                ,  self.t_peak**2               ,  self.t_peak               ,  1 ], \
            #                 [ 3*self.t_peak**2              ,  2*self.t_peak                ,  1                         ,  0 ], \
            #                 [ 3*(self.t_peak-self.t_rise)**2,  2*(self.t_peak-self.t_rise)  ,  1                         ,  0 ] ])
            # y1 = np.array([[0],[self.peak_torque],[0],[0]])
            # self.cnsts1 = np.linalg.lstsq(m1,y1)[0]

            # m2 = np.array([ [ (self.t_peak+self.t_fall)**3, (self.t_peak+self.t_fall)**2, (self.t_peak+self.t_fall), 1], \
            #                 [ self.t_peak**3              , self.t_peak**2              , self.t_peak              , 1], \
            #                 [ 3*self.t_peak**2            , 2*self.t_peak               , 1                        , 0], \
            #                 [ 6*(self.t_peak+self.t_fall) , 2                           , 0                        , 0] ])
            # y2 = np.array([[0.5],[self.peak_torque],[0],[0]])
            # self.cnsts2 = np.linalg.lstsq(m2,y2)[0]

            self.a1 = (2 * (onset_torque - self.peak_torque)) / (self.t_rise ** 3)
            self.b1 = (3 * (self.peak_torque - onset_torque) * (self.t_peak + t0)) / (self.t_rise ** 3)
            self.c1 = (6 * (onset_torque - self.peak_torque) * self.t_peak * t0) / (self.t_rise ** 3)
            self.d1 = (self.t_peak ** 3 * onset_torque - 3 * t0 * self.t_peak ** 2 * onset_torque + 3 * t0 ** 2 * self.t_peak * self.peak_torque - t0 ** 3 * self.peak_torque) / (self.t_rise ** 3)

            self.a2 = (self.peak_torque - onset_torque) / (2 * self.t_fall ** 3)
            self.b2 = (3 * (onset_torque - self.peak_torque) * t1) / (2 * self.t_fall ** 3)
            self.c2 = (3 * (self.peak_torque - onset_torque) * (- self.t_peak ** 2 + 2 * t1 * self.t_peak)) / (2 * self.t_fall ** 3)
            self.d2 = (2 * self.peak_torque * t1 ** 3 - 6 * self.peak_torque * t1 ** 2 * self.t_peak + 3 * self.peak_torque * t1 * self.t_peak ** 2 + 3 * onset_torque * t1 * self.t_peak ** 2 - 2 * onset_torque * t_peak ** 3) / (2 * self.t_fall ** 3)

        else:
            print('One of the Collins parameters is not set:' + \
                '\n t_rise           : ' + str(self.t_rise) + \
                '\n t_fall           : ' + str(self.t_fall) + \
                '\n t_peak           : ' + str(self.t_peak) + \
                '\n weight           : ' + str(self.weight) + \
                '\n peak_torque_norm : ' + str(self.peak_torque_norm))


    def run_collins_profile(self):
        ### Update Data.
        self.read_data()

        # self.current = 5000
        # # fxSetGains(self.devId, 100, 32, 0, 0, 0, 0)
        # # sleep(0.5)
        # for i in range(30):
        #     fxSendMotorCommand(self.devId, FxCurrent, self.current)
        #     sleep(0.1)
        # # fxSendMotorCommand(self.devId, FxNone, 0)
        # # sleep(0.5)
        
        # self.current = 4000
        # fxSendMotorCommand(self.devId, FxCurrent, self.current)
        # sleep(0.1)

        ### Early Stance.
        if (self.percent_gait >= 0 and self.percent_gait <= self.t_peak - self.t_rise):
            # print('Stage 1 ...')

            # ### Current Controol.     Current just enough to keep a small tension in the cable.
            # fxSetGains(self.devId, 100, 32, 0, 0, 0, 0)
            # # self.tau = 0
            # self.current = NO_SLACK_CURRENT
            # fxSendMotorCommand(self.devId, FxCurrent, self.current * self.side)

            ### Position Control.
            fxSetGains(self.devId, 175, 50, 0, 0, 0, 0)
            motorAngle = np.floor(np.polyval(self.ank_mot_coeffs, self.ankleTicksRaw) - self.side * self.magnitude - (self.kinematicCoeffs[0]*self.ankleVel_filt[0] + self.kinematicCoeffs[1]))
            fxSendMotorCommand(self.devId, FxPosition, motorAngle)

            # print('percent_gait: ', self.percent_gait, ';\tcurrent: ', self.current)

        ### Ascending Curve.
        elif (self.percent_gait > self.t_peak - self.t_rise and self.percent_gait <= self.t_peak):
            # print('Stage 2 ...')

            ### Current Control.
            fxSetGains(self.devId, 100, 32, 0, 0, 0, 0)
            # a, b, c, d = self.cnsts1[:,0]
            self.tau = self.a1 * pow(self.percent_gait, 3) + self.b1 * pow(self.percent_gait, 2) + self.c1 * self.percent_gait + self.d1
            self.current = A_TO_MA(self.ankle_torque_to_current(NM_TO_MNM(self.tau)))
            self.current = max(min(self.current, PEAK_CURRENT), NO_SLACK_CURRENT)
            fxSendMotorCommand(self.devId, FxCurrent, self.current * self.side)

#             ### Position Control.
#             fxSetGains(self.devId, 175, 50, 0, 0, 0, 0)
#             motorAngle = np.floor(np.polyval(self.ank_mot_coeffs, self.ankleTicksRaw) - self.side * self.magnitude - (self.kinematicCoeffs[0]*self.ankleVel_filt[0] + self.kinematicCoeffs[1]))
#             fxSendMotorCommand(self.devId, FxPosition, motorAngle)

            # print('percent_gait: ', self.percent_gait, ';\tcurrent: ', self.current)

        ### Descending Curve.
        elif (self.percent_gait > self.t_peak and self.percent_gait <= self.t_peak + self.t_fall):
            # print('Stage 3 ...')

            ### Current Control.
            fxSetGains(self.devId, 100, 32, 0, 0, 0, 0)
            # a, b, c, d = self.cnsts2[:,0]
            self.tau = self.a2 * pow(self.percent_gait, 3) + self.b2 * pow(self.percent_gait, 2) + self.c2 * self.percent_gait + self.d2
            self.current = A_TO_MA(self.ankle_torque_to_current(NM_TO_MNM(self.tau)))
            self.current = max(min(self.current, PEAK_CURRENT), NO_SLACK_CURRENT)
            fxSendMotorCommand(self.devId, FxCurrent, self.current * self.side)

#             ### Position Control.
#             fxSetGains(self.devId, 175, 50, 0, 0, 0, 0)
#             motorAngle = np.floor(np.polyval(self.ank_mot_coeffs, self.ankleTicksRaw) - self.side * self.magnitude - (self.kinematicCoeffs[0]*self.ankleVel_filt[0] + self.kinematicCoeffs[1]))
#             fxSendMotorCommand(self.devId, FxPosition, motorAngle)

            # print('percent_gait: ', self.percent_gait, ';\tcurrent: ', self.current)

        ### Late Stance.
        elif (self.percent_gait > self.t_peak + self.t_fall):
            # print('Stage 4 ...')
            
            # ### Current Controol.     Current just enough to keep a small tension in the cable.
            # fxSetGains(self.devId, 100, 32, 0, 0, 0, 0)
            # # self.tau = 0
            # self.current = NO_SLACK_CURRENT
            # fxSendMotorCommand(self.devId, FxCurrent, self.current * self.side)
            
            ### Position Control.
            fxSetGains(self.devId, 175, 50, 0, 0, 0, 0)
            motorAngle = np.floor(np.polyval(self.ank_mot_coeffs, self.ankleTicksRaw) - self.side * self.magnitude - (self.kinematicCoeffs[0]*self.ankleVel_filt[0] + self.kinematicCoeffs[1]))
            fxSendMotorCommand(self.devId, FxPosition, motorAngle)

            # print('percent_gait: ', self.percent_gait, ';\tcurrent: ', self.current)


    def percent_gait_calc(self):
        ### If self.expected_duration is not updated (= -1), no update on percent_gait.
        if (self.expected_duration != -1):
            self.percent_gait = 100 * (self.current_time - self.heelstrike_timestamp_current) / self.expected_duration
        ### If percent_gait is over 100, but still does not detect heel strike, hold it to 100.
        if (self.percent_gait > 100):
            self.percent_gait = 100

    ### Called when Heel Strike is detected and new stride begins.
    def update_expected_duration(self):
        ### Calculate current stride duration.
        self.current_duration = self.heelstrike_timestamp_current - self.heelstrike_timestamp_previous

        ### If it is the first time running just record the timestamp.
        if (self.heelstrike_timestamp_previous == -1):
            self.heelstrike_timestamp_previous = self.heelstrike_timestamp_current
            return
        
        # If not all values have been replaced.
        if (-1 in self.past_stride_times):
            self.past_stride_times.insert(0, self.current_duration)     ### Insert the new value at the beginning
            self.past_stride_times.pop()        ### Remove the last value.
        elif ((self.current_duration <= 1.5 * max(self.past_stride_times)) and (self.current_duration >= 0.5 * min(self.past_stride_times))):   ### self.expected_duration only update after NUM_GAIT_TIMES_TO_AVERAGE strides have been completed.
            self.past_stride_times.insert(0, self.current_duration)
            self.past_stride_times.pop()
            self.expected_duration = sum(self.past_stride_times) / len(self.past_stride_times);  ### Average to the past stride time.


    def HeelStrike_Detect(self):
        triggered = False
        armed_time = 0

        ### Condition 1: gyroZ is over a threshold for a fixed time period.
        if ((self.gyroz >= self.segmentation_arm_threshold) and (not self.heelstrike_armed)):
            self.heelstrike_armed = True
            self.armed_timestamp = self.current_time

        if self.armed_timestamp != -1:  ### != -1 means gyroZ is over threshold and armed.
            armed_time = self.current_time - self.armed_timestamp

        ### Condition 2: gyroZ is below another threshold. Unarmed.
        if (self.heelstrike_armed and (self.gyroz <= self.segmentation_trigger_threshold)):
            self.heelstrike_armed = False
            self.armed_timestamp = -1
            if (armed_time > ARMED_DURATION_PERCENT / 100 * self.expected_duration):
                triggered = True
                self.num_gait += 1
                self.num_gait_in_block += 1
                if self.side == 1:
                    print('Left Heel Strike Detected! Num: ', self.num_gait)
                else:
                    print('Right Heel Strike Detected! Num: ', self.num_gait)
                # self.HeelStrikeTime.append(self.current_time)

        self.segmentation_trigger = triggered
    

    def zero_boot(self):
        print('Tightening the Boot...')
        fxSetGains(self.devId, 100, 32, 0, 0, 0, 0)
        sleep(0.5)
        fxSendMotorCommand(self.devId, FxCurrent, ZEROING_CURRENT * self.side)       ### Tighten the belt.
        sleep(3)
        self.zero_encoders()
        fxSendMotorCommand(self.devId, FxNone, 0)
    

    def lpfilter(self, x, ypast, a, b):
        # "send it last 2 filtered points and last 3 unfiltered points. About a 20 Hz filter (depends on sampling frequency)"
        y = -(a[1]*ypast[0] + a[2]*ypast[1]) + b[0]*x[0] + b[1]*x[1] + b[2]*x[2]
        return y
    

    def printStatus(self):
        clearTerminal()
        print('Current Time:        ', self.current_time)
        # print('Percent Gait:        ', self.percent_gait)
        # print('Armed Time:          ', self.armed_timestamp)
        print('Expected Duration:   ', self.expected_duration)
        print('Past Stride Period:  ', self.past_stride_times)
        # print('Current Heelstrike:  ', self.heelstrike_timestamp_current)
        # print('Previous Heelstrike: ', self.heelstrike_timestamp_previous)
        print('Current sent:        ', self.current)
        print('Motor Current:       ', self.motorCurrent)
        # print('wm_wa:               ', self.wm_wa)
        print('HS Number Detected:  ', self.num_gait)
        

    
    def current_control(self, current, time):
        time = time * 10
        fxSetGains(self.devId, 100, 32, 0, 0, 0, 0)
        sleep(0.5)
        for i in range(time):
            fxSendMotorCommand(self.devId, FxCurrent, current * self.side)
            sleep(0.1)
        fxSendMotorCommand(self.devId, FxNone, 0)
        sleep(0.5)
        

    
    ### Clean the ExoBoot when finish.
    def clean(self):
        fxSendMotorCommand(self.devId, FxNone, 0)
        sleep(0.5)
        fxClose(self.devId)


        

                

