function [Magnetization] = ConvertBtoMoment(A, height, SQUID_Diameter, Pad_Or_Not)
%Pad_Or_Not: 1-pad, 0-not_pad
Bfield = A.z;
switch Pad_Or_Not
    case 1
        [p, q] = size(Bfield);
        [paddedBfield, original_coords] = GaussianPadding(Bfield, 1);
        [rows, cols] = size(paddedBfield);
        
        fftBfield = fftshift(fft2(paddedBfield)) / (rows * cols);
        dx = (A.x(2) - A.x(1)) / (q - 1);
        dy = (A.y(1) - A.y(2)) / (p - 1);
        dkx = 2 * pi / dx;
        dky = 2 * pi / dy;

        w = zeros(rows, cols);
        kz = min (2 * pi / height, 3.83 * 2 / SQUID_Diameter);
        sigma = zeros(rows, cols);
        miu = 4 * pi * 10 ^ (-7);
        
        kx = zeros(rows, cols);
        ky = zeros(rows, cols);
        
        %For even number of columns
        if mod(cols,2) == 0
            for m = 1:rows
                kx(m, :) = (-cols/2:cols/2-1) * dkx / cols;
            end
        else %for odd number of columns
            for m = 1:rows
                kx(m, :) = (-(cols-1)/2:(cols-1)/2) * dkx / cols;
            end
        end
        
        %For even number of rows
        if mod(rows, 2) == 0
            for n = 1:cols
                ky(:, n) = (-rows/2:rows/2-1) * dky / rows;
            end
        else %for odd number of rows
            for n = 1:cols
                ky(:, n) = (-(rows-1)/2:(rows-1)/2) * dky / rows;
            end 
        end
        
        for m = 1 : rows
            for n = 1 : cols
                k = sqrt(kx(m, n) ^ 2 + ky(m, n) ^ 2);
                if k < kz && k > 0
                    w(m, n) = (1 + cos(k * height / 2)) * 0.5;
                else
                    w(m, n) = 0;
                end
                hfunc = besselj(1, k * (SQUID_Diameter / 2)) / (k * (SQUID_Diameter / 2) / 2);
                sigma(m, n) = w(m, n) * fftBfield(m, n) * hfunc / (miu * k * exp(-k * height) / 2);
            end
        end
        sigma(isnan(sigma)) = 0; %WHAT SHOULD IT BE?
        M = real(ifft2(ifftshift(sigma)) * (rows * cols));
        Magnetization.z = M(original_coords(1):original_coords(2), original_coords(3):original_coords(4));
        Magnetization.x = A.x;
        Magnetization.y = A.y;
        Magnetization.X = A.X;
        Magnetization.Y = A.Y;
        % I = ones(p, q);
        % I(1:end,2:end-1)=0;
        % MI = Magnetization.*I;
        % edge = reshape(MI,1,[]);
        % avg = sum(edge)/(2 * p);
        % Magnetization = Magnetization - avg;
    case 0
        [rows, cols] = size(Bfield);
        xaxis = linspace(A.x(1), A.x(2), cols);
        yaxis = linspace(A.y(2), A.y(1), rows);
        [BfieldX, BfieldY] = meshgrid(xaxis, yaxis);
        dx = (A.x(2) - A.x(1)) / (cols - 1);
        dy = (A.y(1) - A.y(2)) / (rows - 1);
        dkx = 2 * pi / dx;
        dky = 2 * pi / dy;
        fftBfield = fftshift(fft2(Bfield)) / (rows * cols);
        kx = zeros(rows, cols);
        ky = zeros(rows, cols);
        w = zeros(rows, cols);
        kz = min (2 * pi / height, 3.83 * 2 / SQUID_Diameter);
        sigma = zeros(rows, cols);
        miu = 4 * pi * 10 ^ (-7);
        
        %For even number of columns
        if mod(cols,2) == 0
            for m = 1:rows
                kx(m, :) = (-cols/2:cols/2-1) * dkx / cols;
            end
        else %for odd number of columns
            for m = 1:rows
                kx(m, :) = (-(cols-1)/2:(cols-1)/2) * dkx / cols;
            end
        end
        
        %For even number of rows
        if mod(rows, 2) == 0
            for n = 1:cols
                ky(:, n) = (-rows/2:rows/2-1) * dky / rows;
            end
        else %for odd number of rows
            for n = 1:cols
                ky(:, n) = (-(rows-1)/2:(rows-1)/2) * dky / rows;
            end 
        end
        
        for m = 1 : rows
            for n = 1 : cols
                k = sqrt(kx(m, n) ^ 2 + ky(m, n) ^ 2);
                if k < kz && k > 0
                    w(m, n) = (1 + cos(k * height / 2)) * 0.5;
                else
                    w(m, n) = 0;
                end
                hfunc = besselj(1, k * (SQUID_Diameter / 2)) / (k * (SQUID_Diameter / 2) / 2);
                sigma(m, n) = w(m, n) * fftBfield(m, n) * hfunc / (miu * k * exp(-k * height) / 2);
            end
        end
        sigma(isnan(sigma)) = 0; %WHAT SHOULD IT BE
        sigma(isinf(sigma)) = 0;
        Magnetization.z = real(ifft2(ifftshift(sigma)) * (rows * cols));
        Magnetization.x = A.x;
        Magnetization.y = A.y;
        Magnetization.X = BfieldX;
        Magnetization.Y = BfieldY;
        % avg = (mean(Magnetization(:, end)) + mean(Magnetization(:, 1)))/2;
        % Magnetization = Magnetization - avg;
end
end
 
% function [Magnetization] = ConvertBtoMoment(A, height, SQUID_Diameter, Pad_Or_Not)
% %Pad_Or_Not: 1-pad, 0-not_pad
% Bfield = A.z;
% switch Pad_Or_Not
%     case 1
%         [p, q] = size(Bfield);
%         [paddedBfield, original_coords] = GaussianPadding(Bfield);
%         [rows, cols] = size(paddedBfield);
%         
%         fftBfield = fftshift(fft2(paddedBfield)) / (rows * cols);
%         dx = (A.x(2) - A.x(1)) / (q - 1);
%         dy = (A.y(1) - A.y(2)) / (p - 1);
%         dkx = 2 * pi / dx;
%         dky = 2 * pi / dy;
%         kx = zeros(rows, cols);
%         ky = zeros(rows, cols);
%         w = zeros(rows, cols);
%         kz = 2 * pi / sqrt(SQUID_Diameter ^ 2);
%         sigma = zeros(rows, cols);
%         miu = 4 * pi * 10 ^ (-7);
%         
%         for m = 1:cols
%             kx(1 : rows, m) = (m - 1 - cols / 2) * dkx / cols;
%         end
%         for n = 1:rows
%             ky(n, 1 : cols) = (n - 1 - rows / 2) * dky / rows;
%         end
%         
%         
%         for m = 1 : rows
%             for n = 1 : cols
%                 k = sqrt(kx(m, n) ^ 2 + ky(m, n) ^ 2);
%                 if k < kz && k > 0
%                     w(m, n) = (1 + cos(k * height / 2)) * 0.5;
%                     %w(m, n) = 1;
%                 else
%                     w(m, n) = 0;
%                 end
%                 sigma(m, n) = w(m, n) * fftBfield(m, n) / (miu * k * exp(-k * height) / 2);
%             end
%         end
%         
%         sigma(isnan(sigma)) = 0; %WHAT SHOULD IT BE?
%         M = real(ifft2(ifftshift(sigma)) * (rows * cols));
%         Magnetization.z = M(original_coords(1):original_coords(2), original_coords(3):original_coords(4));
%         Magnetization.x = A.x;
%         Magnetization.y = A.y;
%         Magnetization.X = A.X;
%         Magnetization.Y = A.Y;
%         % I = ones(p, q);
%         % I(1:end,2:end-1)=0;
%         % MI = Magnetization.*I;
%         % edge = reshape(MI,1,[]);
%         % avg = sum(edge)/(2 * p);
%         % Magnetization = Magnetization - avg;
%     case 0
%         [rows, cols] = size(Bfield);
%         xaxis = linspace(A.x(1), A.x(2), cols);
%         yaxis = linspace(A.y(2), A.y(1), rows);
%         [BfieldX, BfieldY] = meshgrid(xaxis, yaxis);
%         dx = (A.x(2) - A.x(1)) / (cols - 1);
%         dy = (A.y(1) - A.y(2)) / (rows - 1);
%         dkx = 2 * pi / dx;
%         dky = 2 * pi / dy;
%         fftBfield = fftshift(fft2(Bfield)) / (rows * cols);
%         kx = zeros(rows, cols);
%         ky = zeros(rows, cols);
%         w = zeros(rows, cols);
%         kz = 2 * pi / sqrt(SQUID_Diameter ^ 2);
%         sigma = zeros(rows, cols);
%         miu = 4 * pi * 10 ^ (-7);
%         
%         
%         for m = 1:cols
%             kx(1 : rows, m) = (m - 1 - cols / 2) * dkx / cols;
%         end
%         for n = 1:rows
%             ky(n, 1 : cols) = (n - 1 - rows / 2) * dky / rows;
%         end
%         
%         
%         for m = 1 : rows
%             for n = 1 : cols
%                 k = sqrt(kx(m, n) ^ 2 + ky(m, n) ^ 2);
%                 if k < kz && k > 0
%                     %w(m, n) = (1 + cos(k * height / 2)) * 0.5;
%                     w(m,n) = 1;
%                 else
%                     w(m, n) = 0;
%                 end
%                 %         w = ones(rows, cols);
%                 sigma(m, n) = w(m, n) * fftBfield(m, n) / (miu * k * exp(-k * height) / 2);
%             end
%         end
%         sigma(isnan(sigma)) = 0; %WHAT SHOULD IT BE?
%         Magnetization.z = real(ifft2(ifftshift(sigma)) * (rows * cols));
%         Magnetization.x = A.x;
%         Magnetization.y = A.y;
%         Magnetization.X = BfieldX;
%         Magnetization.Y = BfieldY;
%         % avg = (mean(Magnetization(:, end)) + mean(Magnetization(:, 1)))/2;
%         % Magnetization = Magnetization - avg;
% end
% end
