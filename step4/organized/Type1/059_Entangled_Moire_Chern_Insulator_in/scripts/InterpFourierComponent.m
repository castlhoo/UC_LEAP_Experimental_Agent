function [F] = InterpFourierComponent(data, p, amp, angle, points)
%INTERPDATALINE Summary of this function goes here
%   data is a structure with data.z is the data matrix, and data.x and
%   data.y have x and y extents, and data.X and data.Y have the grid
%   returns a linecut of the dataset with sinusoidal sampling around point
%   p with amplitude amp and angle angle

t = linspace(-pi, pi, points);

x = p(1) + amp*sin(t)*sind(angle);
y = p(2) + amp*sin(t)*cosd(angle);

datasize = size(data.z);

X = data.X;
Y = data.Y;

%X - xgrid
%Y - ygrid
%data.z - data
%x, y - points to sample
%'cubic' - interpolation algorithm
%0 - value to return when sampling outside of the grid
z = interp2(X,Y,data.z',x,y,'cubic',0);

%Use a trapezoidal integration algorithm. 
%Factor of two multiplication in front gives the peak to peak amplitude x
F = trapz(z.*sin(t)/pi)*2*pi/(points-1);
end

