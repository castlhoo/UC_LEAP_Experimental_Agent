function [Output, coord] = GaussianPadding(Input, Even)
[rows, cols] = size(Input); 
sigma = 0.032 .* [rows cols];
onerows = rows + ceil(2 * sigma(1) + 1) * 2; 
onecols = cols + ceil(2 * sigma(2) + 1) * 2; 
prows = ceil(rows * 1.5);
pcols = ceil(cols * 1.5);

PaddedImage = padarray(Input,[ceil((prows - rows) / 2), ceil((pcols - cols) / 2)],'replicate','pre');
PaddedImage = padarray(PaddedImage,[(prows - (ceil((prows - rows) / 2 + rows))), (pcols - (ceil((pcols - cols) / 2 + cols)))],'replicate','post');
%Make even odd
oddityPadding = double(mod(size(PaddedImage), 2) == 0);
OddPaddedImage = padarray(PaddedImage, oddityPadding, 'replicate', 'post');

A = ones(onerows, onecols);
prePadA = zeros(prows + oddityPadding(1), pcols + oddityPadding(2));
prePadA(ceil((prows - onerows) / 2) + 1: (ceil((prows - onerows) / 2 + onerows)), ceil((pcols - onecols) / 2) + 1: (ceil((pcols - onecols) / 2 + onecols))) = A;

PadA = imgaussfilt(prePadA, sigma);
C = PadA(ceil((prows - rows) / 2) + 1: (ceil((prows - rows) / 2 + rows)), ceil((pcols - cols) / 2) + 1: (ceil((pcols - cols) / 2 + cols)));

PadInput = OddPaddedImage .* PadA;

B = PadInput(ceil((prows - rows) / 2) + 1: (ceil((prows - rows) / 2 + rows)), ceil((pcols - cols) / 2) + 1: (ceil((pcols - cols) / 2 + cols)));
Residual = abs(B - Input);

if abs(sum(sum(Residual))) < 1e-6
	Success = "Padding Successful!"
else
    Success = "Padding Failed"
end

coord = [ceil((prows - rows) / 2) + 1, (ceil((prows - rows) / 2 + rows)), ceil((pcols - cols) / 2) + 1, (ceil((pcols - cols) / 2 + cols))];
if exist('Even') & Even == 1
    Output = PadInput(1:end-1,1:end-1);    
else
    Output = PadInput;
end
end    


