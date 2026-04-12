function [XCOOR, YCOOR, data, dl, ProcessedData] = MatrixIntegrate( rawData, rawDataX, rawDataY, angle, amplitude )
%This algorithm will integrate the input dataset along given angle with
%given dx interval. The bottom row of the matrix is considered x axis and
%the leftmost column of the matrix is considered y axis. 

%Extrapolating to make each interpixel distance of x and y direction equal
%Should Probably discard edges
rawData = rawData / amplitude;
[rows, cols] = size(rawData);
dx = rawDataX(3, 2) - rawDataX(3, 1);
dy = rawDataY(5, 2) - rawDataY(4, 2);
switch angle
    case 0
        data = cumtrapz(dy, rawData, 1);
    case 90
        data = cumtrapz(dx, rawData, 2);
    otherwise
        if dx ~= dy
            if dx < dy
                ratio = dy / dx;
                ProcessedData = zeros(1 + round(ratio * (rows - 1)), cols);
                y = linspace(0, rows - 1, rows);
                yex = linspace(0, rows - 1, 1 + round(ratio * (rows - 1)));
                for i = 1 : cols
                    ProcessedData(: , i) = interp1( y, rawData(: , i), yex );
                end
                dr = dx;
            else
                ratio = dx / dy;
                ProcessedData = zeros(rows, 1 + round(ratio * (cols - 1)));
                x = linspace(0, cols - 1, cols);
                xex = linspace(0, cols - 1, 1 + round(ratio * (cols - 1)));
                for i = 1 : rows
                    ProcessedData(i , :) = interp1( x, rawData(i , :), xex );
                end
                dr = dy;
            end
        else
            ProcessedData = rawData;
            dr = dx;
        end
        [rows, cols] = size(ProcessedData);
        
        % %Padding the image with 0s
        % prows = rows * 3;
        % pcols = cols * 3;
        % paddedData = zeros(prows, pcols);
        % paddedData(rows + 1 : 2 * rows, cols + 1 : 2 * cols) = ProcessedData;
        
        %Rotate image by an angle
        rotatedData = imrotate(ProcessedData, (-1) * angle, 'bicubic', 'loose');
        
        %Integrate the image along Y axis
        dl = dr / cosd(angle);
        %dl = dr; %this had worked well but not sure whether interpixel
        %distance changed after rotation
        IntegrateData = cumtrapz(dl, rotatedData, 1);
        % IntegrateData = rotatedData;
        %Rotate Data Back and crop
        backData = imrotate(IntegrateData, angle, 'bicubic', 'loose');
        [r, c] = size(backData);
        ystart = floor((r - rows) / 2) + 1;
        xstart = floor((c - cols) / 2) + 1;
        data = backData(ystart : ystart + rows - 1, xstart: xstart + cols - 1);
        [XCOOR, YCOOR] = meshgrid(0:(cols-1), 0:(rows-1));
        XCOOR = XCOOR .* dr;
        YCOOR = YCOOR .* dr;
end
end