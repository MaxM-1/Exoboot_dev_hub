import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def Losing_Data_Checking(Data):
    maxLength = 0
    Time = Data['state_time'].values
    for i in range(Time.shape[0] - 1):
        if maxLength < (Time[i+1] - Time[i]):
            maxLength = Time[i+1] - Time[i]
            t = Time[i]
    print(maxLength)
    print(t)


def Time_Extract(Data):
    time = Data['state_time'].values   ### unit: ms.
    init_time = time[0]
    time = (time - init_time) / 1000   ### Convert to seconds.
    print('Time Length: ', time[-1])
    return time


def Data_Extract(Data, data_name):
    data = Data[data_name].values
    return data


if __name__ == '__main__':
    DataL = pd.read_csv('left_data.csv')
    DataR = pd.read_csv('right_data.csv')

    plt.figure()

    ### Gyro Z.
    plt.plot(DataL['state_time'].values, DataL['gyroz'].values,'b')
    # plt.plot(DataR['state_time'].values, DataR['gyroz'].values * -1,'r')

    ### Ankle Angle.
    plt.plot(DataL['state_time'].values, DataL['ank_ang'].values,'r--')
    # plt.plot(DataR['state_time'].values, DataR['ank_ang'].values,'r')

    plt.show()

    # Losing_Data_Checking(Data)

    # Time = Data['state_time'].values
    # Time = (Time - Time[0]) / 1000

    # gyroZ = Data['gyroz'].values
    # Current = Data['mot_cur'].values

    # print('Max Current: ', max(Current))

    # MotorAngle = Data['mot_ang'].values
    # MotorAngle = (MotorAngle - MotorAngle[0]) * 0.02197

    # plt.figure()
    # plt.plot(Time, gyroZ)
    # # plt.plot(Time, Current, 'o-')
    # # plt.plot(Time, MotorAngle)
    # # plt.hlines(800, Time[0], Time[-1], 'r', '--')
    # plt.xlabel('Time (s)')
    # # plt.ylabel('Current (mA)')
    # plt.show()




    

