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
devId_left = fxOpen(portList[0], baudRate, logLevel = 6)
fxStartStreaming(devId_left, frequency=100, shouldLog=True)
appType_left = fxGetAppType(devId_left)

devId_right = fxOpen(portList[1], baudRate, logLevel = 6)
fxStartStreaming(devId_right, frequency=100, shouldLog=True)
appType_right = fxGetAppType(devId_right)



sleep(0.1)



try:


    ### Read Only.
    # time = 20
    time_step = 0.1

    while True:
        # totalLoopCount = int(time / time_step)
        # for i in range(totalLoopCount):
        # printLoopCount(i, totalLoopCount)
        sleep(time_step)
        clearTerminal()
        
        print('Left: ')
        myData_left = fxReadDevice(devId_left)
        printDevice(myData_left, appType_left)
        print('Ankle Angle:    ', myData_left.ank_ang)
        print('Ankle Velocity:    ', myData_left.ank_vel)
        
        print('\n')
        print('Right: ')
        myData_right = fxReadDevice(devId_right)
        printDevice(myData_right, appType_right)
        print('Ankle Angle:    ', myData_right.ank_ang)
        print('Ankle Velocity:    ', myData_right.ank_vel)


except KeyboardInterrupt:
    print('keyboarInterrupt has been caught.')

print('Outside the loop...')

### Disconnect from a FlexSEA device with the given device ID.
fxClose(devId_left)     ### fxClose takes around 1.5 s to execute.
fxClose(devId_right)