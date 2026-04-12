function [int] = InterpIntegrate(data, angle, amplitude)
%This algorithm will integrate the input dataset along given angle defined
%counterclockwise from the x axis when plotted. The bottom side and the
%left side of the image are assumed to be zero boundary condition. 

%This algorithm uses 2 dimensional interpolation method. For each pixel
%that needs integration, draw a line back to the left / bottom side of the
%iimage, sampling the line and integrate. The resulting integrated image 
%will have the same dimension as original image. For now this algorithm 
%only works for inegration angles of 0 to 90 degrees. 

data.z = data.z/amplitude;

[rows, cols] = size(data.z);

%Get the coordinate matrix 
xgrid = linspace(data.x(1),data.x(2),rows);
dx = (data.x(2) - data.x(1))/rows;

ygrid = linspace(data.y(2),data.y(1),cols);
dy = (data.y(1) - data.y(2))/cols;

[X,Y] = meshgrid(xgrid, ygrid);

int = data;

if angle == 90
    int.z = cumtrapz(dy, data.z, 2);
elseif angle == 0
    int.z = cumtrapz(dx, data.z, 1);
elseif angle > 0 && angle < 90
    %slope of the line of integration
    m = tand(angle);

    %First, lets find the x intercept for all the points
    Xint = X - Y./m;
    Yint = Y - m.*X;
    
    int.z = zeros(rows, cols);
    for i = 1 : rows
        i %Algorithm is slow, so this prints out the row number to give a
          %sense of the progress made so far
        for j = 1 : cols
            x1 = X(j,i);
            y1 = Y(j,i);
            
            xint = Xint(j,i);
            if xint < 0
                xint = 0;
            end
            yint = Yint(j,i);
            if yint < 0
                yint = 0;
            end
            
            numofpt = round(sqrt(((x1-xint)/dx)^2+((y1-yint)/dy)^2));
            
            if numofpt <= 1
                int.z(i,j) = 0;
            else
                x_interp = linspace(xint,x1,numofpt);
                y_interp = linspace(yint,y1,numofpt);

                interpline = interp2(X, Y, data.z', x_interp, y_interp, 'cubic',0);
                interpixel_distance = sqrt(((x_interp(2)-x_interp(1)))^2+((y_interp(2)-y_interp(1)))^2);
                int.z(i,j) = trapz(interpline) * interpixel_distance;
            end
        end
    end
end
end