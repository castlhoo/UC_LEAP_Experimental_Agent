function [A] = InterpDataLine(data, p1, p2, points)
%INTERPDATALINE Summary of this function goes here
%   data is a structure with data.z is the data matrix, and data.x and
%   data.y have x and y extents
%   p1 is [x1 y1]
%   p2 is [x2 y2]
%   points is the number of points to take in the interpolation

x = linspace(p1(1),p2(1),points);
y = linspace(p1(2),p2(2),points);

datasize = size(data.z);

xgrid = linspace(data.x(1),data.x(2),datasize(1));
ygrid = linspace(data.y(1),data.y(2),datasize(2));

[X,Y] = meshgrid(xgrid, ygrid);

z = interp2(X,Y,data.z',x,y,'linear',0);

A.x = sqrt((x-x(1)).^2+(y-y(1)).^2);
A.z = z;
end

