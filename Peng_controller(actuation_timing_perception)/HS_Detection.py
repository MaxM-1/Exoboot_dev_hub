import os, sys
import time
import pandas as pd
import socket

from Exo_Init import *



ZEROING_CURRENT = 1000      ### mA


### Android App Signal.
STOP_SIGNAL = 0
PRIOR_TEST_BEGIN_SIGNAL = 1
PERCEPTION_TEST_BEGIN_SIGNAL = 2
RECORD_SIGNAL = 3
INCREASE_SIGNAL = 4
DECREASE_SIGNAL = 5


def main():

    ### Boot Connection.
    print('\nBoot Connection...')
    scriptPath = os.path.dirname(os.path.abspath(__file__))
    fpath = scriptPath + '/flexseapython/com.txt'
    portList, baudRate = loadPortsFromFile(fpath)
    baudRate = int(baudRate)
    print('Using portList:\t', portList)
    print('Using baud rate:', baudRate)


    ### Boot Initialization. fxOpen and fxStartStreaming.
    leftBoot = ExoBoot(LEFT, portList[0], baudRate)
    rightBoot = ExoBoot(RIGHT, portList[1], baudRate)
    leftBoot.zero_boot()
    rightBoot.zero_boot()

    ### Set Current Control Gains.
    fxSetGains(leftBoot.devId, 100, 32, 0, 0, 0, 0)
    fxSetGains(rightBoot.devId, 100, 32, 0, 0, 0, 0)
    sleep(0.5)

    leftBoot.init_collins_profile(t_rise=25.3, t_fall=10.3 , t_peak=25.3+42, weight=75, peak_torque_norm=0.175)
    rightBoot.init_collins_profile(t_rise=25.3, t_fall=10.3 , t_peak=25.3+42, weight=75, peak_torque_norm=0.175)

    ### Trials begin.
    print('Starting Loop...')
    try:
        
        while True:  ### Press CTRL+C to stop the loop.  

            leftBoot.read_data()
            rightBoot.read_data()

            # leftBoot.run_collins_profile()
            # rightBoot.run_collins_profile()

            
            sleep(1 / leftBoot.frequency)
            # sleep(1 / rightBoot.frequency)


    except KeyboardInterrupt:
        print('keyboarInterrupt has been caught.')
    
    print('Outside the loop...')

    ### Clean.
    leftBoot.clean()
    rightBoot.clean()
    del leftBoot
    del rightBoot

    print('Trial Ends.')


if __name__ == '__main__':
    main()