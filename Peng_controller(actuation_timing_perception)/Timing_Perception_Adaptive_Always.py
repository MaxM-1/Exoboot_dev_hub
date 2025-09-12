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
DELTA = 1
TOTAL_TRIAL = 55
TOTAL_SWEEP = 10


def main():

    ### Participant ID.
    participant_ID = str(sys.argv[1])   ### String

    ### Data Log.
    perception_data = {'Trial #':[], 'Sweep #':[], 'Delta':[], 'Reference Timing':[], 'Comparison Timing':[], 'Response':[], 'Catch Trial':[]}
    perception_left_stride_data = {'state_time':[], 'Actuation Timing (%)':[], 'Estimated Stride Duration':[], 'Actual Stride Duration':[]}
    perception_right_stride_data = {'state_time':[], 'Actuation Timing (%)':[], 'Estimated Stride Duration':[], 'Actual Stride Duration':[]}
    familiarization_left_data = {'state_time':[], 'Actuation Timing (%)':[], 'Estimated Stride Duration':[], 'Actual Stride Duration':[]}
    familiarization_right_data = {'state_time':[], 'Actuation Timing (%)':[], 'Estimated Stride Duration':[], 'Actual Stride Duration':[]}

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

    # leftBoot.zero_boot()
    # rightBoot.zero_boot()


    # ### Set Current Control Gains.
    # fxSetGains(leftBoot.devId, 100, 32, 0, 0, 0, 0)
    # fxSetGains(rightBoot.devId, 100, 32, 0, 0, 0, 0)
    # sleep(0.5)


    ### Set parameters.
    delT_prior = DELTA  ### Prior Test Delta T. 
    blockLength = 10     ### How many strides are there in a single trial.
    stopFlag = False

    Perception_DataLog_Flag = False
    Familiarization_DataLog_Flag = False

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

            Perception_DataLog_Flag = True
            ### The augmentation begins at the 10th stride.
            while(leftBoot.num_gait < 10):
                leftBoot.read_data()
                rightBoot.read_data()
                fxSendMotorCommand(leftBoot.devId, FxCurrent, 400)
                fxSendMotorCommand(rightBoot.devId, FxCurrent, -400)
                sleep(1 / leftBoot.frequency)
            
            ### The augmentation remains for 10 more strides.
            while(leftBoot.num_gait < 20):
                leftBoot.run_collins_profile()
                rightBoot.run_collins_profile()
                sleep(1 / leftBoot.frequency)

            print('Timing Perception Begins...')




            ### Adaptive Algorithm.
            reference_timing = t_onset
            init_comparison_timing = reference_timing - 3
            comparison_timing = init_comparison_timing
            adaptive_comparison_timing = init_comparison_timing
            catch_trial_flag = 1

            if reference_timing > comparison_timing:
                direction = 1   ### comparison < reference
            else:
                direction = -1  ### comparison > reference

            trial_num = 0
            sweep_num = 0
            
            print('\n\nTrial Number: ', trial_num+1, '      Sweep Number: ', int(sweep_num), '      Catch Trial: No', '\n\n')

            ### Left boot as the counting boot.
            current_left_gait = leftBoot.num_gait
            current_right_gait = rightBoot.num_gait

            left_num_gait_prev = leftBoot.num_gait
            right_num_gait_prev = rightBoot.num_gait
            
            perception_left_stride_data['state_time'].append(leftBoot.current_time)
            perception_left_stride_data['Actuation Timing (%)'].append(leftBoot.t_peak - leftBoot.t_rise)
            perception_left_stride_data['Estimated Stride Duration'].append(leftBoot.expected_duration)

            ### Generate [Timing_A, Timing_B]
            timing_list = [reference_timing, comparison_timing]
            random_num = random.randint(0,1)
            timing_A = timing_list[random_num]
            timing_B = timing_list[1-random_num]

            print('Timing A: ', timing_A, '...\n')

            ### Initialize with Timing A.
            leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=timing_A+t_rise, weight=user_weight, peak_torque_norm=peak_torque_norm)
            print('Left: Actuation Timing:', timing_A, 't_rise:', t_rise, 't_peak:', timing_A+t_rise, 't_fall:', t_fall)

            right_update_A = False
            left_update_B = False
            right_update_B = False
            right_update_back = False
            update = False
            response_update = False
            left_within_trial = True
            right_within_trial = False
            prev_response = None

            ### Termination Condition for the test.
            while trial_num < TOTAL_TRIAL and sweep_num < TOTAL_SWEEP and not stopFlag:

                ### In a Single Trial.
                leftBoot.run_collins_profile()
                rightBoot.run_collins_profile()

                ### Update the right boot.
                if rightBoot.num_gait > current_right_gait and not right_update_A:
                    rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=timing_A+t_rise, weight=user_weight, peak_torque_norm=peak_torque_norm)
                    print('Right: Actuation Timing:', timing_A, 't_rise:', t_rise, 't_peak:', timing_A+t_rise, 't_fall:', t_fall)
                    right_update_A = True
                    right_within_trial = True

                ### Instructions: 
                if not update and (leftBoot.num_gait - current_left_gait >= 0.5*blockLength):
                    print('\nTiming B: ', timing_B, '...\n')
                    update = True
                ### Change the timing after blockLength/2 strides in the first timing --- Timing B.
                if leftBoot.num_gait - current_left_gait >= 0.5*blockLength and not left_update_B:
                    leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=timing_B+t_rise, weight=user_weight, peak_torque_norm=peak_torque_norm)
                    print('Left: Actuation Timing:', timing_B, 't_rise:', t_rise, 't_peak:', timing_B+t_rise, 't_fall:', t_fall)
                    left_update_B = True
                    current_right_gait = rightBoot.num_gait

                if rightBoot.num_gait > current_right_gait and not right_update_B and left_update_B:
                    rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=timing_B+t_rise, weight=user_weight, peak_torque_norm=peak_torque_norm)
                    print('Right: Actuation Timing:', timing_B, 't_rise:', t_rise, 't_peak:', timing_B+t_rise, 't_fall:', t_fall)
                    right_update_B = True
                

                ### After the trial, update the timing to t_peak.
                if not response_update and leftBoot.num_gait - current_left_gait >= blockLength:
                    print('\n\nIs Timing A equal or different than Timing B ?\n\n')
                    leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
                    print('Left: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall)
                    response_update = True
                    right_update_back = True
                    left_within_trial = False
                    current_right_gait = rightBoot.num_gait
                
                if rightBoot.num_gait > current_right_gait and right_update_back:
                    rightBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=t_peak, weight=user_weight, peak_torque_norm=peak_torque_norm)
                    print('Right: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall)
                    right_update_back = False
                    right_within_trial = False

                
                if leftBoot.num_gait > left_num_gait_prev and left_within_trial:
                    perception_left_stride_data['Actual Stride Duration'].append(leftBoot.current_duration)
                    perception_left_stride_data['state_time'].append(leftBoot.current_time)
                    perception_left_stride_data['Actuation Timing (%)'].append(leftBoot.t_peak - leftBoot.t_rise)
                    perception_left_stride_data['Estimated Stride Duration'].append(leftBoot.expected_duration)
                    left_num_gait_prev = leftBoot.num_gait
                if rightBoot.num_gait > right_num_gait_prev and right_within_trial:
                    perception_right_stride_data['Actual Stride Duration'].append(rightBoot.current_duration)
                    perception_right_stride_data['state_time'].append(rightBoot.current_time)
                    perception_right_stride_data['Actuation Timing (%)'].append(rightBoot.t_peak - rightBoot.t_rise)
                    perception_right_stride_data['Estimated Stride Duration'].append(rightBoot.expected_duration)
                    right_num_gait_prev = rightBoot.num_gait
                

                sleep(1/leftBoot.frequency)

                try:
                    data = socket_con.recv(BUFSIZE)
                    response = int(data.decode('utf-8'))
                    
                    if (response == DIFFERENCE_RESPONSE) or (response == NO_DIFFERENCE_RESPONSE):

                        ### Log data.
                        perception_data['Trial #'].append(trial_num+1)
                        perception_data['Delta'].append(DELTA)
                        perception_data['Reference Timing'].append(reference_timing)
                        perception_data['Comparison Timing'].append(comparison_timing)
                        

                        ### If the current trial is the catch trial.
                        if catch_trial_flag == 0:
                            perception_data['Catch Trial'].append('Yes')
                            if response == DIFFERENCE_RESPONSE:
                                print('\nResponse: Different\n')
                                perception_data['Response'].append('Different')
                            if response == NO_DIFFERENCE_RESPONSE:
                                print('\nResponse: Equal\n')
                                perception_data['Response'].append('Equal')
                        ### If the current trial is not the catch trial, update the next comparison timing value.
                        else:
                            perception_data['Catch Trial'].append('No')
                            if response == DIFFERENCE_RESPONSE:
                                print('\nResponse: Different\n')
                                ### The comparison value should not cross the reference value.
                                if direction == 1 and adaptive_comparison_timing + direction * DELTA <= reference_timing:
                                    adaptive_comparison_timing += direction * DELTA
                                if direction == -1 and adaptive_comparison_timing + direction * DELTA >= reference_timing:
                                    adaptive_comparison_timing += direction * DELTA
                                perception_data['Response'].append('Different')
                            if response == NO_DIFFERENCE_RESPONSE:
                                print('\nResponse: Equal\n')
                                adaptive_comparison_timing -= direction * DELTA
                                perception_data['Response'].append('Equal')
                            
                            if response != prev_response and prev_response != None:
                                sweep_num += 0.5
                            prev_response = response

                        perception_data['Sweep #'].append(int(sweep_num))

                        ### Determine whether the next trial is 'catch trial' or not.
                        catch_trial_flag = random.randint(0,3)  ### (0,3)

                        ### The probability of the catch trial is 20%.
                        if catch_trial_flag == 0:
                            comparison_timing = reference_timing
                        else:
                            comparison_timing = adaptive_comparison_timing
                        
                        trial_num += 1
                        ### Trial 3: the first trial in the real test, reset.
                        if trial_num == 3:
                            catch_trial_flag = 1
                            comparison_timing = init_comparison_timing
                            adaptive_comparison_timing = init_comparison_timing
                            sweep_num = 1
                            prev_response = None


                        ### Wait for 8 strides before starting the next trial.
                        current_left_gait = leftBoot.num_gait
                        while(leftBoot.num_gait - current_left_gait < 8):
                            leftBoot.run_collins_profile()
                            rightBoot.run_collins_profile()
                            sleep(1 / leftBoot.frequency)

                        
                        ### Generate [Timing_A, Timing_B]
                        timing_list = [reference_timing, comparison_timing]
                        random_num = random.randint(0,1)
                        timing_A = timing_list[random_num]
                        timing_B = timing_list[1-random_num]

                        if catch_trial_flag == 0:
                            print('\n\nTrial Number: ', trial_num+1, '      Sweep Number: ', int(sweep_num), '      Catch Trial: Yes', '\n\n')
                        else:
                            print('\n\nTrial Number: ', trial_num+1, '      Sweep Number: ', int(sweep_num), '      Catch Trial: No', '\n\n')

                        print('Timing A: ', timing_A, '...\n')

                        current_left_gait = leftBoot.num_gait
                        current_right_gait = rightBoot.num_gait

                        leftBoot.init_collins_profile(t_rise=t_rise, t_fall=t_fall, t_peak=timing_A+t_rise, weight=user_weight, peak_torque_norm=peak_torque_norm)
                        print('Left: Actuation Timing:', timing_A, 't_rise:', t_rise, 't_peak:', timing_A+t_rise, 't_fall:', t_fall)
                        
                        left_update_B = False
                        right_update_A = False
                        right_update_B = False
                        update = False
                        response_update = False
                        left_within_trial = True

                    if int(data.decode('utf-8')) == STOP_SIGNAL: 
                        socket_con.send(bytes("Stop\n", 'utf-8'))
                        stopFlag = True
                        break
                
                except:
                    pass


        
        ### Familiarization Test Protocol.
        elif signal == PRIOR_TEST_BEGIN_SIGNAL:

            Familiarization_DataLog_Flag = True

            print('\nLeft: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall)
            print('Right: Actuation Timing:', t_peak-t_rise, 't_rise:', t_rise, 't_peak:', t_peak, 't_fall:', t_fall, '\n')

            familiarization_left_data['state_time'].append(leftBoot.current_time)
            familiarization_left_data['Actuation Timing (%)'].append(leftBoot.t_peak - leftBoot.t_rise)
            familiarization_left_data['Estimated Stride Duration'].append(leftBoot.expected_duration) 
            familiarization_right_data['state_time'].append(rightBoot.current_time)
            familiarization_right_data['Actuation Timing (%)'].append(rightBoot.t_peak - rightBoot.t_rise)
            familiarization_right_data['Estimated Stride Duration'].append(rightBoot.expected_duration)

            left_num_gait_prev = leftBoot.num_gait
            right_num_gait_prev = rightBoot.num_gait

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
                        print('Increase Timing')
                        delT_prior = abs(delT_prior)
                        current_left_num = leftBoot.num_gait
                        current_right_num = rightBoot.num_gait
                        update_left = True
                        update_right = True
                    if data == DECREASE_SIGNAL: 
                        print('Decrease Timing')
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

                ### Log Data every stride.
                if leftBoot.num_gait > left_num_gait_prev:
                    familiarization_left_data['Actual Stride Duration'].append(leftBoot.current_duration)
                    familiarization_left_data['state_time'].append(leftBoot.current_time)
                    familiarization_left_data['Actuation Timing (%)'].append(leftBoot.t_peak - leftBoot.t_rise)
                    familiarization_left_data['Estimated Stride Duration'].append(leftBoot.expected_duration)
                    left_num_gait_prev = leftBoot.num_gait
                if rightBoot.num_gait > right_num_gait_prev:
                    familiarization_right_data['Actual Stride Duration'].append(rightBoot.current_duration)        
                    familiarization_right_data['state_time'].append(rightBoot.current_time)
                    familiarization_right_data['Actuation Timing (%)'].append(rightBoot.t_peak - rightBoot.t_rise)
                    familiarization_right_data['Estimated Stride Duration'].append(rightBoot.expected_duration)
                    right_num_gait_prev = rightBoot.num_gait

                sleep(1 / leftBoot.frequency)

    
    except KeyboardInterrupt:
        print('keyboarInterrupt has been caught.')
    
    fxSendMotorCommand(leftBoot.devId, FxCurrent, 0)
    fxSendMotorCommand(rightBoot.devId, FxCurrent, 0)
    print('Outside the loop...')


    if Perception_DataLog_Flag == True:
        perception_left_stride_data['Actual Stride Duration'].append(leftBoot.current_duration)
        perception_right_stride_data['Actual Stride Duration'].append(rightBoot.current_duration)
        results = pd.DataFrame(compensate(perception_data))
        left_results = pd.DataFrame(compensate(perception_left_stride_data))
        right_results = pd.DataFrame(compensate(perception_right_stride_data))
        results.to_csv(participant_ID + '_TimingPerception_' + strftime("%Y-%m-%d_%Hh%Mm%Ss") +'.csv', sep=',')
        left_results.to_csv(participant_ID + '_TimingPerceptionStride_' + str(leftBoot.devId) + '_' + strftime("%Y-%m-%d_%Hh%Mm%Ss") +'.csv', sep=',')
        right_results.to_csv(participant_ID + '_TimingPerceptionStride_' + str(rightBoot.devId) + '_' + strftime("%Y-%m-%d_%Hh%Mm%Ss") +'.csv', sep=',')

    if Familiarization_DataLog_Flag == True:
        familiarization_left_data['Actual Stride Duration'].append(leftBoot.current_duration)
        familiarization_right_data['Actual Stride Duration'].append(rightBoot.current_duration) 
        left_results = pd.DataFrame(compensate(familiarization_left_data))
        right_results = pd.DataFrame(compensate(familiarization_right_data))
        left_results.to_csv(participant_ID + '_Familiarization_' + str(leftBoot.devId) + '_' + strftime("%Y-%m-%d_%Hh%Mm%Ss") +'.csv', sep=',')
        right_results.to_csv(participant_ID + '_Familiarization_' + str(rightBoot.devId) + '_' + strftime("%Y-%m-%d_%Hh%Mm%Ss") +'.csv', sep=',')

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
    return data


if __name__ == '__main__':
    main()