import os, sys
from time import sleep, strftime, time
import pandas as pd
import socket

from Exo_Init import *


### Android App Signal.
STOP_SIGNAL = 0
PRIOR_TEST_BEGIN_SIGNAL = 1
PERCEPTION_TEST_BEGIN_SIGNAL = 2
RECORD_SIGNAL = 3
INCREASE_SIGNAL = 4
DECREASE_SIGNAL = 5


def main():

    ### Participant ID.
    participant_ID = str(sys.argv[1])   ### String

    ### Data Log.
    left_data = {'state_time':[], 'Onset Timing (%)':[], 'Peak Timing (%)':[], 'Estimated Stride Duration':[], 'Actual Stride Duration':[]}
    right_data = {'state_time':[], 'Onset Timing (%)':[], 'Peak Timing (%)':[], 'Estimated Stride Duration':[], 'Actual Stride Duration':[]}


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
    delT_prior = 2  ### Prior Test Delta T.
    delT_perception = 2    ### Sweeping timing (in percentage).
    blockLength = 3     ### How many strides to maintain for each delT change.
    totalSweep = 8      ### Stops after 8 complete sweeps.
    stopFlag = False
    # limitSide = ['Right limit: ', 'Left limit: ']
    Direction_Change = False

    count = 0
    record_time = 0
    dataLog_Flag = False

    t_onset = float(sys.argv[2])    ### Actuation Timing variable.

    ### Set Collins Profile Parameters.
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
            begin_time = time()
            # while (time() - begin_time < 10):
            
            ### The augmentation begins at the 10th stride.
            while(leftBoot.num_gait < 10):
                leftBoot.read_data()
                rightBoot.read_data()
                fxSendMotorCommand(leftBoot.devId, FxCurrent, 600)
                fxSendMotorCommand(rightBoot.devId, FxCurrent, -600)
                sleep(1 / leftBoot.frequency)

            print('Onset Timing Perception Begins...')

            ### Log data.
            left_num_gait = leftBoot.num_gait
            right_num_gait = rightBoot.num_gait

            left_data['state_time'].append(leftBoot.current_time)
            left_data['Onset Timing (%)'].append(leftBoot.t_peak - leftBoot.t_rise)
            left_data['Peak Timing (%)'].append(leftBoot.t_peak)
            left_data['Estimated Stride Duration'].append(leftBoot.expected_duration)
            right_data['state_time'].append(rightBoot.current_time)
            right_data['Onset Timing (%)'].append(rightBoot.t_peak - rightBoot.t_rise)
            right_data['Peak Timing (%)'].append(rightBoot.t_peak)
            right_data['Estimated Stride Duration'].append(rightBoot.expected_duration)

            count_sweep = 0     ### Count the sweep number.
            leftBoot.num_gait_in_block = 1  ### Start a block.
            rightBoot.num_gait_in_block = 1
            
            button_update_left = False
            button_update_right = False
            natural_update_left = False
            natural_update_right = False

            print('\nLeft: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall)
            print('Right: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')

            while not stopFlag:  ### Press CTRL+C to stop the loop.  
                                
                leftBoot.run_collins_profile()
                rightBoot.run_collins_profile()
                    

                try:
                    ### Check if there is STOP command.
                    data = socket_con.recv(BUFSIZE)
                    if int(data.decode('utf-8')) == STOP_SIGNAL: 
                        socket_con.send(bytes("Stop\n", 'utf-8'))
                        stopFlag = True
                        # break
                    if (int(data.decode('utf-8')) == RECORD_SIGNAL) and (time() - record_time > 2):
                        count += 1
                        print('torque time recorded. [Total records:' + str(count) + ']')
                        socket_con.send(bytes("Recorded\n", 'utf-8'))
                        record_time = time()
                        Direction_Change = True
                        # break
                except:
                    pass

            
                ### Button is pressed here.
                if Direction_Change:
                    delT_perception = - delT_perception
                    t_peak += delT_perception
                    Direction_Change = False
                    count_sweep += 0.5  ### Each the direction changes, it's a half complete sweep.
                    ### update for both boots at their next steps.
                    button_update_left = True
                    button_update_right = True
                    current_left_block = leftBoot.num_gait_in_block
                    current_right_block = rightBoot.num_gait_in_block
                
                if button_update_left:
                    if leftBoot.num_gait_in_block > current_left_block:
                        leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Left: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')
                        leftBoot.num_gait_in_block = 1
                        button_update_left = False
                        natural_update_left = False
                if button_update_right:
                    if rightBoot.num_gait_in_block > current_right_block:
                        rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Right: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')
                        rightBoot.num_gait_in_block = 1
                        button_update_right = False
                        natural_update_right = False
                

                ### Natural Increase/Decrease after blockLength number of blocks.                   
                if ((leftBoot.num_gait_in_block > blockLength) or (rightBoot.num_gait_in_block > blockLength)) \
                            and (natural_update_left == False) and (natural_update_right == False) \
                            and (button_update_left == False) and (button_update_right == False):
                    t_peak += delT_perception
                    natural_update_left = True
                    natural_update_right = True
                
                if natural_update_left:
                    if leftBoot.num_gait_in_block > blockLength:
                        leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Left: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')
                        leftBoot.num_gait_in_block = 1
                        button_update_left = False
                        natural_update_left = False
                if natural_update_right:
                    if rightBoot.num_gait_in_block > blockLength:
                        rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Right: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')
                        rightBoot.num_gait_in_block = 1
                        button_update_right = False
                        natural_update_right = False

                ### The program should terminate after totalSweep number of complete sweeps.
                if count_sweep >= totalSweep:
                    stopFlag = True
                    ### Send STOP signal to Android app.
                    socket_con.send(bytes("Stop\n", 'utf-8'))
                
                ### log data.
                if leftBoot.num_gait > left_num_gait:
                    left_num_gait = left_num_gait + 1
                    left_data['Actual Stride Duration'].append(leftBoot.current_duration)
                    left_data['state_time'].append(leftBoot.current_time)
                    left_data['Onset Timing (%)'].append(leftBoot.t_peak - leftBoot.t_rise)
                    left_data['Peak Timing (%)'].append(leftBoot.t_peak)
                    left_data['Estimated Stride Duration'].append(leftBoot.expected_duration)     

                if rightBoot.num_gait > right_num_gait:   
                    right_num_gait = right_num_gait + 1         
                    right_data['Actual Stride Duration'].append(rightBoot.current_duration)        
                    right_data['state_time'].append(rightBoot.current_time)
                    right_data['Onset Timing (%)'].append(rightBoot.t_peak - rightBoot.t_rise)
                    right_data['Peak Timing (%)'].append(rightBoot.t_peak)
                    right_data['Estimated Stride Duration'].append(rightBoot.expected_duration)


                sleep(1 / leftBoot.frequency)
                # sleep(1 / rightBoot.frequency)
        
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
                # sleep(1 / rightBoot.frequency)


        # ### Without Android App Communication for testing.
        # while True:
        #     # leftBoot.read_data()
        #     # # print('Current Time: ', leftBoot.current_time)
        #     leftBoot.run_collins_profile()
        #     # # print('Current sent :       ', leftBoot.current,    'Current Received:    ', leftBoot.motorCurrent)
        #     sleep(1 / leftBoot.frequency)

        #     # leftBoot.current_control(7000, 3)
    
    except KeyboardInterrupt:
        print('keyboarInterrupt has been caught.')
    
    fxSendMotorCommand(leftBoot.devId, FxCurrent, 0)
    fxSendMotorCommand(rightBoot.devId, FxCurrent, 0)
    print('Outside the loop...')

    ### Write data in csv.
    left_data['Actual Stride Duration'].append(leftBoot.current_duration)
    right_data['Actual Stride Duration'].append(rightBoot.current_duration)


    compensate(left_data)
    compensate(right_data)

    if dataLog_Flag == True:
        left_results = pd.DataFrame(left_data)
        left_results.to_csv(participant_ID + '_Perception_' + str(leftBoot.devId) + '_' + strftime("%Y-%m-%d_%Hh%Mm%Ss") +'.csv', sep=',')
        right_results = pd.DataFrame(right_data)
        right_results.to_csv(participant_ID + '_Perception_' + str(rightBoot.devId) + '_' + strftime("%Y-%m-%d_%Hh%Mm%Ss") +'.csv', sep=',')

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