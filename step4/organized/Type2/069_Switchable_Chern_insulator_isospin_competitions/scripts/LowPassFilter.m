function [FilteredImage] = LowPassFilter(Data, height, Pad_Or_Not)

if Pad_Or_Not == 1
    z = Data.z;
    [p, q] = size(z);
    [padded_data, original_coords] = GaussianPadding(z, 1);
    [rows, cols] = size(padded_data);

    dx = (Data.x(2) - Data.x(1)) / (q - 1);
    dy = (Data.y(1) - Data.y(2)) / (p - 1);
    dkx = 2 * pi / dx;
    dky = 2 * pi / dy;
    kx = zeros(rows, cols);
    ky = zeros(rows, cols);
    w = zeros(rows, cols);

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
    
    fftData = fftshift(fft2(padded_data));
    kz = 2 * pi / height;
    k = sqrt(kx .^ 2 + ky .^ 2);
    flagMatrix = k < kz;
    w = (1 + cos(k .* (height / 2))) .* 0.5 .* flagMatrix;
    %w= flagMatrix;
    fftDataF = fftData .* w;
    zfiltered = ifft2(ifftshift(fftDataF));
    
    FilteredImage = Data;
    FilteredImage.z = zfiltered(original_coords(1):original_coords(2), original_coords(3):original_coords(4));
    
else
    z = Data.z;
    [rows , cols]= size(z); 
    kx = zeros(rows, cols);
    ky = zeros(rows, cols);
    dx = (Data.x(2) - Data.x(1)) / (cols - 1);
    dy = (Data.y(1) - Data.y(2)) / (rows - 1);
    dkx = 2 * pi / dx;
    dky = 2 * pi / dy;
        
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
    
    fftData = fftshift(fft2(z));
    kz = 2 * pi / height;
    k = sqrt(kx .^ 2 + ky .^ 2);
    flagMatrix = k < kz;
    w = (1 + cos(k .* (height / 2))) .* 0.5 .* flagMatrix;
    fftDataF = fftData .* w;
    FilteredImage = Data;
    FilteredImage.z = ifft2(ifftshift(fftDataF));
end
end