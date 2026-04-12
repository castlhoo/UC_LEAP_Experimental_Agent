function [ the_data ] = OpenDataVaultFile2( file_number )

try
    the_data = readmatrix(file_number);
catch
    
end

end
