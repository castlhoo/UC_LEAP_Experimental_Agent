function [OutputX, OutputY, Output] = DirectionalIntegral(file_number) 
    %file_numbe = file NO. in datavault , for example, 09648
    %angle = the angle (in degrees) for tuning fork oscillation starts from +y 
    %axis, clockwise as positive. The angle from tunning fork fitting can apply 
    %directly here.
    %amplitude = the amplitude of tuning fork oscillations (in um)
    %offset = the offset provided by Tuning Fork Fitting and Error. If
    %information of angle and amplitude are not obtained through Tuning
    %Fork Fitting and Error, Enter 0
    %conversion_factor = the conversion factor from Voltage data to distance (um/V)
    %TFGain = Tuning Fork Gain

    x = inputdlg({'Angle (degrees)','Amplitude (um)','Offset (if not clear, enter 0)','Conversion Factor (um/V)','Tuning Fork Gain'},...
              'Please Enter information from Tuning Fork Calibration',[1,100]); 
    arguments = str2num(char(x));
    angle = arguments(1);
    amplitude = arguments(2);
    offset = arguments(3); 
    conversion_factor = arguments(4); 
    TFGain = arguments(5); 
    
    
    %%%%Below is an example of input arguments%%%%
    %file_number = 09934;
    %angle = 29.3; % in degrees
    %amplitude = 0.1954; %in um
    %offset = 0.2685; 
    %conversion_factor = 5.36; %This is the conversion factor from Voltage data to distance (um/V)
    %TFGain = 500;
    
    %FOR NOW, this script only works for angles: 0~360 with top or bottom
    %as constant
    
    % Load the functions necessary for the script
    addpath(fullfile('..','Functions'))

    [dataset, Variable_Names, ~] = OpenDataVaultFile(file_number);
    tf = 0;
    while tf == 0
        [yindx,tf] = listdlg('PromptString', 'Please Select TF Y Quadrature Data','SelectionMode','single','ListString',Variable_Names);
        if tf == 0
            answer = questdlg('TF X Quadrature Data Not Selected. Please Select Again.', ...
                'Warning', ...
                'OK','Cancel','OK');
            switch answer
                case 'Cancel'
                    return
                case ''
                    return
            end
        end
    end

    tf = 0;
    exitflag = 0;
    while tf == 0 && exitflag == 0
        [xindx,tf] = listdlg('PromptString', 'Please Select TF X Quadrature Data','SelectionMode','single','ListString',Variable_Names);
        if tf == 0
            answer = questdlg('TF X Quadrature Data Not Selected. Proceed without rotation?', ...
                'Warning', ...
                'Yes','No, Select Again','Exit');
            switch answer
                case 'Yes'
                    exitflag = 1;
                case 'No, Select Again'
                    exitflag = 0;
                case 'Exit'
                    return
                case ''
                    return
            end
        end
    end

    trace = dataset(dataset(:,1) == 0,:);

    l= max(dataset(:,2))+1;

    DataX = transpose(reshape(trace(:,4),l,[])) .* conversion_factor;
    DataY = transpose(reshape(trace(:,5),l,[])) .* conversion_factor;
    YQuad = transpose(reshape(trace(:,yindx),l,[]));

    switch exitflag
        case 1
            Data = YQuad;
            PData = Data;
            XCOOR = DataX;
            YCOOR = DataY;
        case 0
            XQuad = transpose(reshape(trace(:,xindx),l,[]));
            [PhaseAngle, Data, RotationResidual] = PhaseRotation(XQuad, YQuad);
    end


    [m, n] = size(Data);

    if m < 6 || n < 6
        waitfor(errordlg('Input Matrix Dimension Too Small','Input Error'));
        return;
    end

    tf = 0;
    Edges = {'top','bottom','left','right'};
    [edge,tf] = listdlg('PromptString', 'Please Select The Edge With 0 Field','SelectionMode','single','ListString',Edges);
    if tf == 0
        answer = questdlg('No Selection Recorded. Please Select Again.', ...
            'Warning', ...
            'OK','Cancel','OK');
        switch answer
            case 'Cancel'
                return
            case ''
                return
        end
    end

    switch edge
        case 1
            if angle == 0  || angle == 180
                errordlg('Unable to Compute','Input Error')
                return;
            elseif 0 < angle < 180
                [XCOOR, YCOOR, rawResult, dl, PData] = MatrixIntegrate(Data, DataX, DataY, angle + 180, amplitude);
                Result = rawResult .* (-1);
            elseif 180 < angle < 360
                [XCOOR, YCOOR, Result, dl, PData] = MatrixIntegrate(Data, DataX, DataY, angle, amplitude);
            else
                errordlg('Have not Developed','Input Error')
                return;
            end
            [p, q] = size(Result);
            x2 = round(-p * tand(angle));
            y2 = 0;
            y1 = 0;
            x1 = x2 + q;
            x = [0, q, x1, x2];
            y = [p, p, y1, y2];
            Mask = poly2mask(x, y, p, q);
            RawOutput = Result .* Mask;
        case 2
            if angle == 0  || angle == 180
                Result = NewMatrixIntegrate(Data, DataX, DataY, angle, amplitude);
                errordlg('Unable to Compute','Input Error')
                return;
            elseif 0 < angle < 180
                [XCOOR, YCOOR, Result, dl, PData] = MatrixIntegrate(Data, DataX, DataY, angle, amplitude);
            elseif 180 < angle < 360
                [XCOOR, YCOOR, rawResult, dl, PData] = MatrixIntegrate(Data, DataX, DataY, angle - 180, amplitude);
                Result = rawResult .* (-1);
            else
                errordlg('Have not Developed','Input Error')
                return;
            end
            [p, q] = size(Result);        
            x2 = round(p / tand(90 - angle));
            y2 = p;
            y1 = p;
            x1 = x2 + q;
            x = [0, q, x1, x2];
            y = [0, 0, y1, y2];
            Mask = poly2mask(x, y, p, q);
            RawOutput = Result .* Mask;
        otherwise
            errordlg('Have not Developed','Input Error')
            return;
    end
    Output = RawOutput ./ TFGain;
    OutputX = XCOOR;
    OutputY = YCOOR;
    
    figure
    subplot(2,3,5)
    pcolor(DataX, DataY, Data);
    % pcolor(XCOOR,YCOOR,CorrectedPData);
    shading flat
    axis equal
    colorbar
    title('Rotated TF Data Before Integration')


    % [FX, FY] = gradient(Result * amplitude, dl);
    % Derivative = FX * sind(angle) + FY * cosd(angle);

    subplot(2,3,[3 6])
    pcolor(DataX, DataY, RotationResidual);
    shading flat
    axis equal
    colorbar
    title(['Residual After ' num2str(rad2deg(PhaseAngle)) ' Degrees Integration'])

    subplot(2,3,1)
    pcolor(DataX, DataY, YQuad);
    shading flat
    axis equal
    colorbar
    title('Y Quadrature Before Phase Rotation')

    subplot(2,3,4)
    pcolor(DataX, DataY, XQuad);
    shading flat
    axis equal
    colorbar
    title('X Quadrature Before Phase Rotation')

    subplot(2,3,2)
    pcolor(XCOOR, YCOOR, Output);
    shading flat
    axis equal
    colorbar
    title(['After ' num2str(angle) ' Degrees Integration,'])
end



