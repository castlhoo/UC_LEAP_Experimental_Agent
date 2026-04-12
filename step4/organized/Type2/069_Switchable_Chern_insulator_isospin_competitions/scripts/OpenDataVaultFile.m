function [ data ] = OpenDataVaultFile( file_number )
% Opens a data vault file by specifying the file number rather than the
% file name

%Path to datavault 

%Path to datavault 
path_id = fopen('Data_Vault_Path.txt');
data_vault_path = fgetl(path_id);

%Keep track of the original folder to return to after the function is run
curr_folder = cd;

%Change directory to the data vault path 
cd(data_vault_path);
dir_info = dir;

data = [];

for i = 1:length(dir_info)
    try
        number = str2num(dir_info(i).name(1:6));
    catch
        continue
    end
    
    if file_number == number
        file = dir_info(i).name;
        break
    end
end

try
    struct = h5read(file, '/DataVault');
    fields = fieldnames(struct);

    data = [];
    for i = 1:numel(fields)
        data = [data struct.(fields{i})];
    end
catch
    
end
    
cd(curr_folder);

end
