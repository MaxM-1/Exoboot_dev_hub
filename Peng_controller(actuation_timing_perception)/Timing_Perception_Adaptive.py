import os, sys
from time import sleep, strftime, time
import pandas as pd
import socket
import random

from Exo_Init import *


### Android App Signal.
STOP_SIGNAL = 0
PRIOR_TEST_BEGIN_SIGNAL = 1
PERCEPTION_TEST_BEGIN_SIGNAL = 2
INCREASE_SIGNAL = 4
DECREASE_SIGNAL = 5
DIFFERENCE_RESPONSE = 6
NO_DIFFERENCE_RESPONSE = 7


### Control Parameters.
DELTA = 0.5
TOTAL_TRIAL = 30
TOTAL_SWEEP = 8


def main():

    ### Participant ID.
    participant_ID = str(sys.argv[1])   ### String

    ### Data Log.
    result_dict = {'Trial #':[], 'Sweep #':[], 'Delta':[], 'Reference Timing':[], 'Comparison Timing':[], 'Response':[]}

    ### Connected to Android App.
    HOST_IP = '35.6.181.198'    ### IP Address for RPi.
    HOST_PORT = 7654
    BUFSIZE = 1024
    ADDR = (HOST_IP, HOST_PORT)

    socket_to_app = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_to_app.bind(ADDR)
    socket_to_app.listen(1)

    print('Android App Connection...')
    socket_con, addr = socket_to_app.accept()
    print('Android App Connected Successfully!')


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


    ### Set parameters.
    delT_prior = 1  ### Prior Test Delta T.
    blockLength = 10     ### How many strides are there in a single trial.
    totalSweep = 8      ### Stops after 8 complete sweeps.
    stopFlag = False
    # limitSide = ['Right limit: ', 'Left limit: ']
    Direction_Change = False

    count = 0
    record_time = 0
    dataLog_Flag = False

    ### Set Collins Profile Parameters.
    t_onset = float(sys.argv[2])    ### Actuation Timing variable.
    user_weight = float(sys.argv[3])  ### kg.
    t_rise = 25.3   ### in percent.
    t_fall = 10.3   
    t_peak = t_rise + t_onset
    # t_peak = float(sys.argv[2])
    peak_torque_norm = 0.175 # Limited by the Dephy Boot Max current.

    print('\nInput parameter:')
    print('participant ID:', participant_ID)
    print('Actuation Timing:', t_onset, '%')
    print('User Weight:', user_weight, 'kg')
    
    ### Generate cnsts1 and cnsts2 for spline curve. 
    leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
    rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)

    ### Wait for Andriod App to send START command.
    print('\nReady to begin...')
    while True:
        data = socket_con.recv(BUFSIZE)
        signal = int(data.decode('utf-8'))
        if ((signal == PRIOR_TEST_BEGIN_SIGNAL) or (signal == PERCEPTION_TEST_BEGIN_SIGNAL)):
            break
    
    socket_con.send(bytes("Running\n", 'utf-8'))
    ### Set the socket to non-blockable.
    socket_con.setblocking(False)


    ### Trials begin.
    print('Starting Loop...')
    try:

        ### With Android Application Communication.

        ### Perception Test Protocol.
        if signal == PERCEPTION_TEST_BEGIN_SIGNAL:
            dataLog_Flag = True
            ### The sweep process will begin automatically after 10 seconds when strides are stable.
            # begin_time = time()
            # while (time() - begin_time < 10):
            
            ### The augmentation begins at the 10th stride.
            while(leftBoot.num_gait < 10):
                leftBoot.read_data()
                rightBoot.read_data()
                fxSendMotorCommand(leftBoot.devId, FxCurrent, 600)
                fxSendMotorCommand(rightBoot.devId, FxCurrent, -600)
                sleep(1 / leftBoot.frequency)

            print('Onset Timing Perception Begins...')




            ### Adaptive Algorithm.
            reference_timing = t_onset
            comparison_timing = reference_timing - 3

            if reference_timing > comparison_timing:
                direction = 1   ### comparison < reference
            else:
                direction = -1  ### comparison > reference

            trial_num = 0
            sweep_num = 0

            ### Termination Condition for the test.
            while trial_num < TOTAL_TRIAL and sweep_num < TOTAL_SWEEP and not stopFlag:
                

                ### In a single trial.
                print('\n\nTrial Number: ', trial_num, '\n\n')

                timing_vector = [reference_timing, comparison_timing]
                random_num = random.randint(0,1)


                t_onset_1 = timing_vector[random_num]
                t_peak_1 = t_rise + t_onset_1
                t_onset_2 = timing_vector[1-random_num]
                t_peak_2 = t_rise + t_onset_2
                print('The First Actuation Timing: ', t_onset_1, '...\n')
                
                ### Left boot as the counting boot.
                current_left_gait = leftBoot.num_gait
                current_right_gait = rightBoot.num_gait
                leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak_1, weight=user_weight, peak_torque_norm=peak_torque_norm)
                rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak_1, weight=user_weight, peak_torque_norm=peak_torque_norm)
                print('Left: Actuation Timing:', t_peak_1-t_rise, 't_rise:', t_rise, 't_peak:', t_peak_1, 't_fall:', t_fall)
                print('Right: Actuation Timing:', t_peak_1-t_rise, 't_rise:', t_rise, 't_peak:', t_peak_1, 't_fall:', t_fall)

                ### In a Single Trial.
                left_update = False
                right_update = False
                update = False
                while leftBoot.num_gait - current_left_gait < blockLength:
                    leftBoot.run_collins_profile()
                    rightBoot.run_collins_profile()

                    ### Instructions: 
                    if not update and (leftBoot.num_gait - current_left_gait >= 0.5*blockLength or rightBoot.num_gait - current_right_gait >= 0.5*blockLength):
                        print('\nThe First Actuation Timing: ', t_onset_2, '...\n')
                        update = True

                    ### Change the timing after blockLength/2 strides in the first timing.
                    if leftBoot.num_gait - current_left_gait >= 0.5*blockLength and not left_update:
                        leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak_2, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Left: Actuation Timing:', t_peak_2-t_rise, 't_rise:', t_rise, 't_peak:', t_peak_2, 't_fall:', t_fall)
                        left_update = True
                        current_right_gait = rightBoot.num_gait
                    if rightBoot.num_gait - current_right_gait > 0 and not right_update and left_update:
                        rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak_2, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Right: Actuation Timing:', t_peak_2-t_rise, 't_rise:', t_rise, 't_peak:', t_peak_2, 't_fall:', t_fall)
                        right_update = True

                    sleep(1/leftBoot.frequency)
                
                ### Power-off after the trial.
                fxSendMotorCommand(leftBoot.devId, FxCurrent, 0)
                fxSendMotorCommand(rightBoot.devId, FxCurrent, 0)
                
                ### Waiting for the Response to continue
                print('\nPlease tell if you can feel the difference of the two timing.\n')
                while True:

                    try:
                        data = socket_con.recv(BUFSIZE)
                        response = int(data.decode('utf-8'))
                        
                        if (response == DIFFERENCE_RESPONSE) or (response == NO_DIFFERENCE_RESPONSE):
                            
                            if response == DIFFERENCE_RESPONSE:
                                ### The comparison value should not cross the reference value.
                                if direction == 1 and comparison_timing + direction * DELTA < reference_timing:
                                    comparison_timing += direction * DELTA
                                if direction == -1 and comparison_timing + direction * DELTA > reference_timing:
                                    comparison_timing += direction * DELTA
                                result_dict['Response'].append('Difference')
                            if response == NO_DIFFERENCE_RESPONSE:
                                comparison_timing -= 3 * direction * DELTA
                                result_dict['Response'].append('No Difference')
                                sweep_num += 1
                            
                            ### Log data.
                            result_dict['Trial #'].append(trial_num+1)
                            result_dict['Sweep #'].append(sweep_num+1)
                            result_dict['Delta'].append(DELTA)
                            result_dict['Reference Timing'].append(reference_timing)
                            result_dict['Comparison Timing'].append(comparison_timing)

                            trial_num += 1

                            break
                    
                        if int(data.decode('utf-8')) == STOP_SIGNAL: 
                            socket_con.send(bytes("Stop\n", 'utf-8'))
                            stopFlag = True
                            break
                    
                    except:
                        pass


        
        ### Familiarization Test Protocol.
        elif signal == PRIOR_TEST_BEGIN_SIGNAL:
            print('\nLeft: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall)
            print('Right: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')

            update_left = False
            update_right = False
            while not stopFlag:  ### Press CTRL+C to stop the loop.  
                leftBoot.run_collins_profile()
                rightBoot.run_collins_profile()

                try:
                    ### Check if there is STOP command.
                    data = socket_con.recv(BUFSIZE)
                    data = int(data.decode('utf-8'))
                    if data == STOP_SIGNAL: 
                        socket_con.send(bytes("Stop\n", 'utf-8'))
                        stopFlag = True
                    if data == INCREASE_SIGNAL: 
                        delT_prior = abs(delT_prior)
                        current_left_num = leftBoot.num_gait
                        current_right_num = rightBoot.num_gait
                        update_left = True
                        update_right = True
                    if data == DECREASE_SIGNAL: 
                        delT_prior = - abs(delT_prior)
                        current_left_num = leftBoot.num_gait
                        current_right_num = rightBoot.num_gait
                        update_left = True
                        update_right = True

                except:
                    pass

                if stopFlag:
                    break
                
                if ((data == INCREASE_SIGNAL) or (data == DECREASE_SIGNAL)):
                    t_peak += delT_prior
                    data = 0
                
                if update_left:
                    if leftBoot.num_gait > current_left_num:
                        leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Left: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')
                        update_left = False
                if update_right:
                    if rightBoot.num_gait > current_right_num:
                        rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Right: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')
                        update_right = False

                sleep(1 / leftBoot.frequency)

    
    except KeyboardInterrupt:
        print('keyboarInterrupt has been caught.')
    
    fxSendMotorCommand(leftBoot.devId, FxCurrent, 0)
    fxSendMotorCommand(rightBoot.devId, FxCurrent, 0)
    print('Outside the loop...')


    if dataLog_Flag == True:
        results = pd.DataFrame(result_dict)
        results.to_csv(participant_ID + '_TimingPerception_' + strftime("%Y-%m-%d_%Hh%Mm%Ss") +'.csv', sep=',')

    ### Clean.
    leftBoot.clean()
    rightBoot.clean()
    del leftBoot
    del rightBoot
    
    socket_con.close()

    print('Trial Ends...')


def compensate(data):
    max_len = 0
    for key in data:
        if len(data[key]) > max_len:
            max_len = len(data[key])
    for key in data:
        if len(data[key]) < max_len:
            num = max_len - len(data[key])
            for i in range(num):
                data[key].append('0')


if __name__ == '__main__':
    main()