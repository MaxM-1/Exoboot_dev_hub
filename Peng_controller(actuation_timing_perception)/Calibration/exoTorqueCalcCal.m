% # DISTRIBUTION STATEMENT A. Approved for public release. Distribution is unlimited.
% #
% # This material is based upon work supported by the Under Secretary of Defense for Research and Engineering under Air Force Contract No. FA8702-15-D-0001. Any opinions, findings, conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the Under Secretary of Defense for Research and Engineering.
% #
% # � 2020 Massachusetts Institute of Technology.
% #
% # The software/firmware is provided to you on an As-Is basis
% #
% # Delivered to the U.S. Government with Unlimited Rights, as defined in DFARS Part 252.227-7013 or 7014 (Feb 2014). Notwithstanding any copyright notice, U.S. Government rights in this work are defined by DFARS 252.227-7013 or DFARS 252.227-7014 as detailed above. Use of this work other than as specifically authorized by the U.S. Government may violate any copyrights that exist in this work.
% #
% # P. Stegall 2020

clear;
close all;
clc;

path = '/Users/xypeng/Desktop/20Winter/Research/Project Code/ExoBoot_Perception/Raspberry Pi 4/Calibration/';
filenameL = 'left_boot_calib_new.csv';
filenameR = 'right_boot_calib_new.csv';

% [coeffL, uniqueAnkleL] =  exoTorqueCalPlan([path, filenameL], 1);
[coeffR, uniqueAnkleR] =  exoTorqueCalPlan([path, filenameR], -1);


hold off;

figure; 
plot( uniqueAnkleL, 5 * coeffL(1) .* uniqueAnkleL.^4 + 4 * coeffL(2) .* uniqueAnkleL.^3 + 3 * coeffL(3) .* uniqueAnkleL.^2 + 2 * coeffL(4) .* uniqueAnkleL + coeffL(5));

% figure; 
% plot( uniqueAnkleR, 5 * coeffR(1) .* uniqueAnkleR.^4 + 4 * coeffR(2) .* uniqueAnkleR.^3 + 3 * coeffR(3) .* uniqueAnkleR.^2 + 2 * coeffR(4) .* uniqueAnkleR + coeffR(5));
 





%%
function [p5, uniqueAnkle] =  exoTorqueCalPlan(filename, dir)
    data = readtable(filename);
    
    % plot the original data.
    figure;
    plot(data.ank_ang, data.mot_ang);
    xlabel('Original Ankle Angle');
    ylabel('Original Encoder Angle');
    hold on;

    time = (data.state_time - data.state_time(9)) / 1000;

    numIdxOneSecond = find(time > 1, 1) - find(time > 0, 1);
    acclThresh = 200;
    startIdx = 1;
    for i = 1:(length(time) - numIdxOneSecond)
        if (numIdxOneSecond == sum(data.mot_acc(i:(i+numIdxOneSecond)) < acclThresh))
            startIdx = i;
            break;
        end
    end


    % use cftool
    [val stopIdx] = max(dir * data.mot_ang);
    clear angle;
    ankleAngle = data.ank_ang(startIdx:stopIdx);
    motorAngle = data.mot_ang(startIdx:stopIdx);
    
    fprintf('startIdx: %.1f', startIdx);
    fprintf('stopIdx: %.1f', stopIdx);
    
    figure; 
    plot(dir * (ankleAngle - ankleAngle(1)), dir * (motorAngle - motorAngle(1)))
    xlabel('Chosen Ankle Angle');
    ylabel('Chosen Encoder Angle');
    hold on;


    [uniqueAnkle uniqueIdx] = unique(ankleAngle);
    uniqueMotor = motorAngle(uniqueIdx);
    
    [p1] = polyfit(uniqueAnkle(1:floor(end/2)), uniqueMotor(1:floor(end/2)),  1);
    [p5] = polyfit(uniqueAnkle, uniqueMotor,  5);
    
    % Fitted plot.
    figure;
    plot(uniqueAnkle, uniqueMotor); hold on;
    plot(uniqueAnkle, polyval(p5, uniqueAnkle));
    
    % omega_m/omega_a
    J5 = 5 * p5(1) .* uniqueAnkle.^4 + 4 * p5(2) .* uniqueAnkle.^3 + 3 * p5(3) .* uniqueAnkle.^2 + 2 * p5(4) .* uniqueAnkle + p5(5);
    coeff = 1./J5;
    J1 = p1(1);
%     figure; plot (uniqueAnkle, J5)
end

%%
function [coeff, uniqueAnkle] =  exoTorqueCal(filename)
    data = readtable(filename);

    time = (data.StateTime - data.StateTime(9))/1000;

    numIdxOneSecond = find(time > 1, 1) - find(time > 0, 1);
    acclThresh = 50;
    startIdx = 1;
    for i = 1:(length(time) - numIdxOneSecond)
        if (numIdxOneSecond == sum(data.motorAcceleration(i:(i+numIdxOneSecond)) < acclThresh))
            startIdx = i;
            break;

        end
    end


%     figure; plot( data.AnkleAngle(startIdx:end), data.MotorAngle(startIdx:end))
%     figure; plot(data.AnkleAngle(startIdx:(end-1)), diff(data.AnkleAngle(startIdx:end))./ diff(data.MotorAngle(startIdx:end)))
%     figure; plot(time(startIdx:end), data.AnkleAngle(startIdx:end), time(startIdx:end), data.MotorAngle(startIdx:end), time(startIdx:end), data.motorVelocity(startIdx:end), time(startIdx:end), data.motorAcceleration(startIdx:end))


    % use cftool
    [val stopIdx] = max(data.MotorAngle);
    clear angle;
    ankleAngle = data.AnkleAngle(startIdx:stopIdx);
    motorAngle = data.MotorAngle(startIdx:stopIdx);
    
%     figure; 
    plot(ankleAngle- ankleAngle(1), motorAngle - motorAngle(1))
    hold on;
    %

    [uniqueAnkle uniqueIdx] = unique(ankleAngle);
    uniqueMotor = motorAngle(uniqueIdx);
    
    [p1] = polyfit(uniqueAnkle(1:floor(end/2)), uniqueMotor(1:floor(end/2)),  1);
    [p5] = polyfit(uniqueAnkle, uniqueMotor,  5);
    
    % omega_m/omega_a
    J5 = 5 * p5(1) .* uniqueAnkle.^4 + 4 * p5(2) .* uniqueAnkle.^3 + 3 * p5(3) .* uniqueAnkle.^2 + 2 * p5(4) .* uniqueAnkle + p5(5);
    coeff = 1./J5;
    J1 = p1(1)
%     figure; plot (uniqueAnkle, J5)
end












