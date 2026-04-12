function [data] = InterpolateIntegrate( rawData, rawDataX, rawDataY, angle, amplitude )
%This algorithm will integrate the input dataset along given angle.
%The bottom row of the matrix is considered x axis and
%the leftmost column of the matrix is considered y axis. 

%This algorithm uses 2 dimensional interpolation method. For each pixel
%that needs integration, draw a line in the direction of integration,
%sampling the line at rate (3pt/pixel_in_x_direction) and integrate. The
%resulting integrated image will have the same dimension as original image.
%For now this algorithm only deals with bottom as zero, 0~90 degrees.

rawData = rawData / amplitude;
ang = 90 - angle;   %ang = integration angle counterclockwise from x axis
[rows, cols] = size(rawData);
dx = rawDataX(3, 2) - rawDataX(3, 1);
dy = rawDataY(5, 2) - rawDataY(4, 2);

%Get the coordinate matrix
[XCOOR, YCOOR] = meshgrid(0:(cols-1), 0:(rows-1));
XCOOR = XCOOR .* dx;
YCOOR = YCOOR .* dy;

if ang == 90
    data = cumtrapz(dy, rawData, 1);
elseif ang == 0
    data = cumtrapz(dx, rawData, 2);
elseif ang > 0 && ang < 90
    CNT = 0;
    data = zeros(rows, cols);
    for i = 0 : rows - 1
        for j = 0 : cols - 1
            %for each pixel length in x direction, 3 sample points are needed
            delx = dx / 3; %number of points calculated in one pixel
            coord = [j * dx, i * dy];
            length = abs((min(coord(1),coord(2)/tand(ang))) / cosd(ang)); %length of the line w/ specified direction
            numofpt = round(length / delx) + 1;
            xcoords = linspace(max(0, (coord(1) - coord(2)/tand(ang))), coord(1), numofpt);
            ycoords = (tand(ang) .* (xcoords - coord(1))) + coord(2);
            ycoords(abs(ycoords)<1e-6) = 0;
            %ycoords = (tand(ang) .* (xcoords - xcoords(1)));
            interpline = interp2(XCOOR, YCOOR, rawData, xcoords, ycoords, 'cubic');
            interpixel_distance = abs((((max(0, (coord(1) - coord(2)/tand(ang))) - coord(1)) / (numofpt - 1)) / cosd(ang)));
            interpixel_distance(isinf(interpixel_distance)) = 0;
            interpixel_distance(isnan(interpixel_distance)) = 0;
            data(i + 1, j + 1) = trapz(interpline) * interpixel_distance;
            CNT = CNT + 1;
            CNTIJ = [i, j, CNT]
        end
    end
    
% elseif ang < 0 && ang > -90
%     CNT = 0;
%     data = zeros(rows, cols);
%     ymax = (rows - 1) * dy;
%     for i = 0 : rows - 1
%         for j = 0 : cols - 1
%             %for each pixel length in x direction, 3 sample points are needed
%             delx = dx / 3; %number of points calculated in one pixel
%             coord = [j * dx, i * dy];
%             length = abs((min(coord(1),(ymax - coord(2))/tand(-1 * ang))) / cosd(ang)); %length of the line w/ specified direction
%             numofpt = round(length / delx) + 1;
%             xcoords = linspace(max(0, (coord(1) - (ymax - coord(2))/tand(-1 * ang))), coord(1), numofpt);
%             ycoords = (tand(180 + ang) .* (xcoords - coord(1))) + coord(2);
%             ycoords(abs(ycoords)<1e-6) = 0;
%             ycoords(abs(ymax - ycoords)<1e-6) = 0;
%             %ycoords = (tand(ang) .* (xcoords - xcoords(1)));
%             interpline = interp2(XCOOR, YCOOR, rawData, xcoords, ycoords, 'cubic');
%             interpixel_distance = abs((((max(0, (coord(1) - (ymax - coord(2))/tand(-1 * ang))) - coord(1)) / (numofpt - 1)) / cosd(ang)));
%             interpixel_distance(isinf(interpixel_distance)) = 0;
%             interpixel_distance(isnan(interpixel_distance)) = 0;
%             data(i + 1, j + 1) = trapz(interpline) * interpixel_distance;
%             CNT = CNT + 1;
%             CNTIJ = [i, j, CNT]
%         end
%     end

elseif ang < 180 && ang > 90
    CNT = 0;
    data = zeros(rows, cols);
    xmax = (cols - 1) * dx;
    ymax = (rows - 1) * dy;
    for i = 0 : rows - 1
        for j = 0 : cols - 1
            %for each pixel length in x direction, 3 sample points are needed
            delx = dx / 3; %number of points calculated in one pixel
            coord = [j * dx, i * dy];
            length = abs((min(xmax - coord(1), coord(2)/tand(180 - ang))) / cosd(180 - ang)); %length of the line w/ specified direction
            numofpt = round(length / delx) + 1;
            xcoords = linspace(coord(1), min(xmax, (coord(1) + coord(2)/tand(-1 * ang))), numofpt);
            ycoords = (tand(ang) .* (xcoords - coord(1))) + coord(2);
            ycoords(abs(ycoords)<1e-6) = 0;
            ycoords(abs(ymax - ycoords)<1e-6) = 0;
            %ycoords = (tand(ang) .* (xcoords - xcoords(1)));
            interpline = interp2(XCOOR, YCOOR, rawData, xcoords, ycoords, 'cubic');
            interpixel_distance = abs((((coord(1) - min(xmax, (coord(1) +  coord(2)/tand(180 - ang)))) / (numofpt - 1)) / cosd(180 - ang)));
            interpixel_distance(isinf(interpixel_distance)) = 0;
            interpixel_distance(isnan(interpixel_distance)) = 0;
            data(i + 1, j + 1) = trapz(interpline) * interpixel_distance;
            CNT = CNT + 1;
            CNTIJ = [i, j, CNT]
        end
    end
end
end