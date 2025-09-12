import os, sys
from time import time, sleep

from flexseapython.pyFlexsea import *
from flexseapython.fxUtil import *

scriptPath = os.path.dirname(os.path.abspath(__file__))
fpath = scriptPath + '/flexseapython/com.txt'
portList, baudRate = loadPortsFromFile(fpath)
baudRate = int(baudRate)
print('Using portList:\t', portList)
print('Using baud rate:', baudRate)

### Establish a connection with a FlexSEA device.
devId = fxOpen(portList[0], baudRate, logLevel = 6)
fxStartStreaming(devId, frequency=1000, shouldLog=True)
print('Setting controller to current...')
fxSetGains(devId, 100, 32, 0, 0, 0, 0)
# fxSetGains(devId, 40, 400, 0, 0, 0, 128)
sleep(0.5)

### Current Control.
# current = 2000

for i in range(1000):
    if i < 500:
        current = 30*i
        fxSendMotorCommand(devId, FxCurrent, current)
    if i >= 500:
        current = 30000 - 30*i
        fxSendMotorCommand(devId, FxCurrent, current)
    sleep(0.001)

    Exo_Data = fxReadDevice(devId)
    motorCurrent = Exo_Data.mot_cur


    print('Desired_Current: ', current, ';\tActual_Current: ', motorCurrent)

# When we exit we want the motor to be off
fxSendMotorCommand(devId, FxNone, 0)
sleep(0.5)

fxClose(devId)
