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
sleep(1)
### Start streaming data from a FlexSEA device.
print('Data Collection Starts!')
fxStartStreaming(devId, frequency=100, shouldLog=True)
sleep(0.1)


print('1. Please hold the shoe fully dorsiflexed.')
sleep(5)

print('2. Apply a motor current to tighten the strap...')
fxSetGains(devId, 100, 32, 0, 0, 0, 0)
sleep(0.5)
for i in range(30):
    fxSendMotorCommand(devId, FxCurrent, 1500)
    sleep(0.1)
sleep(2)
fxSendMotorCommand(devId, FxNone, 0)
sleep(0.5)

print('3. Gradually dorsiflex the shoe till it is fully dorsiflexed.')
sleep(10)

print('Data Collection Ends!')
### Disconnect from a FlexSEA device with the given device ID.
fxClose(devId)     ### fxClose takes around 1.5 s to execute.
