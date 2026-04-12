function [Bout] = convolveTFSig(Bin, d, amp, angle)
%UNTITLED Summary of this function goes here
%   Bin
%   inter_pixel_distance. Assumed to be the same in x and y direction
%   d - squid diameter
%   amp - tuning fork amplitude (not peak to peak)
%   angle - tuning fork oscillation angle from normal. 0 degrees is
%   vertical oscillation

%First, convolve the first with the tip diameter
%Algorithm assumes X and Y inter pixel distance is the same
inter_pixel_distance = Bin.X(1,2) - Bin.X(1,1);

Bin.z = conv2(Bin.z,fspecial('disk',d/inter_pixel_distance/2),'same');

dims = size(Bin.z);

% Bdata.z = Bin;
% Bdata.x = [0 dims(1)*inter_pixel_distance];
% Bdata.y = [0 dims(2)*inter_pixel_distance];
% 
% xgrid = linspace(Bdata.x(1),Bdata.x(2),dims(1));
% ygrid = linspace(Bdata.y(1),Bdata.y(2),dims(2));
% 
% [X,Y] = meshgrid(xgrid, ygrid);
% Bdata.X = X;
% Bdata.Y = Y;

Bout = Bin;

Bout.z = zeros(dims);

for i=1:dims(1)
    i
    for j=1:dims(2)
        x = i*inter_pixel_distance;
        y = j*inter_pixel_distance;
        
        p = [x y];

        Btf = InterpFourierComponent(Bin, p, amp, angle, 100);
        
        Bout.z(i,j) = Btf;
    end
end

end

