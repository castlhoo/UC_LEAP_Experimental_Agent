function [int] = Integrate( rawData, rawDataX, rawDataY, angle, amplitude )
%This algorithm will integrate the input dataset along given angle.
%The bottom row of the matrix is considered x axis and
%the leftmost column of the matrix is considered y axis. 

%This algorithm uses 2 dimensional interpolation method. For each pixel
%that needs integration, draw a line in the direction of integration,
%sampling the line at rate (3pt/pixel_in_x_direction) and integrate. The
%resulting integrated image will have the same dimension as original image.
%For now this algorithm only deals with bottom as zero, 0~90 degrees.
dx = rawDataX(3, 2) - rawDataX(3, 1);
dy = rawDataY(5, 2) - rawDataY(4, 2);
if angle == 0
    int = cumtrapz(dy, rawData, 1);
elseif angle == 90
    int = cumtrapz(dx, rawData, 2);
elseif angle == -90
    rawint = cumtrapz(dx, flip(rawData, 2), 2);
    int = flip(rawint, 2); 
elseif angle == 180
    rawint = cumtrapz(dy, flip(rawData, 1), 1);
    int = flip(rawint, 1);      
elseif angle > 0 && angle < 90
    int = InterpolateIntegrate( rawData, rawDataX, rawDataY, angle, amplitude );         
end
end