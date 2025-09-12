import os, sys
from time import time, sleep
import numpy as np
from scipy.signal import butter, lfilter

from flexseapython.pyFlexsea import *
from flexseapython.fxUtil import *

scriptPath = os.path.dirname(os.path.abspath(__file__))
fpath = scriptPath + '/flexseapython/com.txt'
portList, baudRate = loadPortsFromFile(fpath)
baudRate = int(baudRate)
print('Using portList:\t', portList)
print('Using baud rate:', baudRate)

### Establish a connection with a FlexSEA device.
devId_left = fxOpen(portList[0], baudRate, logLevel = 6)
fxStartStreaming(devId_left, frequency=100, shouldLog=False)
fxSetGains(devId_left, 175, 50, 0, 0, 0, 0)

devId_right = fxOpen(portList[1], baudRate, logLevel = 6)
fxStartStreaming(devId_right, frequency=100, shouldLog=False)



## Low pass filter function
def lpfilter(x,ypast,a,b):
    # "send it last 2 filtered points and last 3 unfiltered points. About a 20 Hz filter (depends on sampling frequency)"
    y = -(a[1]*ypast[0] + a[2]*ypast[1]) + b[0]*x[0] + b[1]*x[1] + b[2]*x[2]
    return y
    


direction_L = 1   # Left:1; Right:-1;
direction_R = -1
magnitude = 8000 # The magnitude for enough slack.

### Coefficients
coeff_L = [-6.985276884624736e-14, 1.273622971499345e-09, -9.017611894231802e-06, 0.030573702252110, -33.653985267845040, 0] ### Left Boot
coeff_R = [-5.330907956856061e-14, 1.215396573820272e-09, -1.093486346822073e-05, 0.048942600274828, -95.500006854492640, 0] ### Right Boot

samplingFreq = 500
b, a = butter(2, 12/(samplingFreq/2), 'low')

ankleVel_L = [0.0]*3
ankleVel_filt_L = [0.0]*3 
ankleVel_R = [0.0]*3
ankleVel_filt_R = [0.0]*3 

kinematicCoeffs = np.array([-500, 0])

def zero_boot(devId, side):
    fxSetGains(devId, 100, 32, 0, 0, 0, 0)
    sleep(0.5)
    if side == 1:
        fxSendMotorCommand(devId, FxCurrent, 1300)       ### Tighten the belt.
    if side == -1:
        fxSendMotorCommand(devId, FxCurrent, -1300)       ### Tighten the belt.

def check_encoder(devId, coeffs):
    angleCheck = 0
    while angleCheck == 0:
        for i in range(0,3):    ### Check initial encoder angle three times.
            actPackState = fxReadDevice(devId)
            initialAngle = actPackState.mot_ang
            print('Encoder check ' + str(i) + ':' + str(initialAngle))
        actPackState = fxReadDevice(devId)
        initialAngle = actPackState.ank_ang
        initialMotor = actPackState.mot_ang
        initialMotor_des = np.floor(np.polyval(coeffs, initialAngle))    # calculate desired motor position from polynomial coefficients
        zeroing = initialMotor - initialMotor_des  # calculate difference between current motor position and desired motor position
        coeffs[-1] = coeffs[-1] + zeroing   # shift coefficients to meet current motor encoder value
        initialMotor_shift = np.floor(np.polyval(coeffs, initialAngle))     # check the interpolation worked correctly

        print('Initial Angle: ' + str(initialAngle))
        print('Initial Motor Actual: ' + str(initialMotor))
        print('Initial Motor Desired: ' + str(initialMotor_des))
        print('Offset to zero: ' + str(zeroing))
        print('Initial Motor: ' + str(initialMotor) + ', Initial Motor Desired (shifted): ' + str(initialMotor_shift))
        check = input("Is this correct? ")
        if check == 'y':
            angleCheck=1
            input('Press Enter to Continue...')
            fxSendMotorCommand(devId, FxNone, 0)
        else:
            angleCheck=0  
    return coeffs

print('!!!Make sure the belts are tightening before the encoder checking!!!')

input('Please Stand Still and Do NOT Move while Calibrating...')
print('Tighten the Left Boot...')
zero_boot(devId_left, 1)
print('Setting controller to position...')
fxSetGains(devId_left, 175, 50, 0, 0, 0, 0)
sleep(0.5)
print('Encoder Checking for Left Boot...')
coeff_L = check_encoder(devId_left, coeff_L)


input('Please Stand Still and Do NOT Move while Calibrating...')
print('Tighten the Right Boot...')
zero_boot(devId_right, -1)
print('Setting controller to position...')
fxSetGains(devId_right, 175, 50, 0, 0, 0, 0)
sleep(0.5)
print('Encoder Checking for Right Boot...')
coeff_R = check_encoder(devId_right, coeff_R)


### Start Position Control.
fxSetGains(devId_left, 175, 50, 0, 0, 0, 0)
fxSetGains(devId_right, 175, 50, 0, 0, 0, 0)
sleep(0.5)

try:

    while True:

        ### Left Boot.

        actPackState_L = fxReadDevice(devId_left)
        ankleAngle_L = actPackState_L.ank_ang
        ankleVelocity_L = actPackState_L.ank_vel

        # filter the velocity 
        # 0 is newest value, 1 is middle, 2 is oldest value
        ankleVel_L.pop() # remove last index
        ankleVel_L.insert(0, ankleVelocity_L) # add new value to index 0
        y_new = lpfilter(ankleVel_L, ankleVel_filt_L, a, b)
        ankleVel_filt_L.pop()
        ankleVel_filt_L.insert(0,y_new)

        motorAngle_L = int(np.polyval(coeff_L, ankleAngle_L) - direction_L * magnitude - (kinematicCoeffs[0]*ankleVel_filt_L[0] + kinematicCoeffs[1]))



        ### Right Boot.

        actPackState_R = fxReadDevice(devId_right)
        ankleAngle_R = actPackState_R.ank_ang
        ankleVelocity_R = actPackState_R.ank_vel

        # filter the velocity 
        # 0 is newest value, 1 is middle, 2 is oldest value
        ankleVel_R.pop() # remove last index
        ankleVel_R.insert(0, ankleVelocity_R) # add new value to index 0
        y_new = lpfilter(ankleVel_R, ankleVel_filt_R, a, b)
        ankleVel_filt_R.pop()
        ankleVel_filt_R.insert(0,y_new)

        motorAngle_R = int(np.polyval(coeff_R, ankleAngle_R) - direction_R * magnitude - (kinematicCoeffs[0]*ankleVel_filt_R[0] + kinematicCoeffs[1]))


        fxSendMotorCommand(devId_left, FxPosition, motorAngle_L)
        fxSendMotorCommand(devId_right, FxPosition, motorAngle_R)

        sleep(0.001)


except KeyboardInterrupt:
    print('keyboarInterrupt has been caught.')

print('Outside the loop...')


# When we exit we want the motor to be off
fxSendMotorCommand(devId_left, FxNone, 0)
fxSendMotorCommand(devId_right, FxNone, 0)
sleep(0.5)


### Disconnect from a FlexSEA device with the given device ID.
fxClose(devId_left)     ### fxClose takes around 1.5 s to execute.
fxClose(devId_right)




