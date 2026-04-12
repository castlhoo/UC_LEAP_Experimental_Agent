# nanoSQUID-DataAnalysis

Data analysis functions written in MATLAB and Python to manipulate data saved in LabRAD's default data saving structure. 

Most central to the analysis written in these package is going from the raw data, which provides a voltage proportional to the local gradient of the magnetic field, to a magnetization density map. There are three main functions written into this analysis package: 

1. Using calibration datasets to extract information needed to determine the proportionality of the voltage to the local field (ie, determine the magnitude of the oscillation). 
2. Manipulate the dataset (data integration + FFT magnetization reversal). 
3. Simulation of gradient signal for understanding (simulate AC signal and take first harmonic)


# Installation-Instructions


1. Download ALL FOLDERS the Data Analysis Package from GitHub
2. Make sure that Matlab and Python are installed on this computer
3. Make sure that Data Vault is on this computer
4. Go to Data_Vault_Path.txt in the downloaded folder and enter the Data Vault location on this computer (no quotation marks)
5. Go to Folder_Path.txt and enter the location of the entire folder
6. Run AddFolderToPath.m in order to add the folder and all its subfolder to Matlab path
7. The Tuning Fork Fitting and Error function is run in python, texted on Python 2.7.16
8. All Matlab Functions are written and tested on Matlab R2019a
9. Until 11/27/2019, the Data Analysis Package contains:

*The following chart contains descriptions and required Matlab packages for all functions in "function" folder. The instructions for
 individual tool kits are in each folders.

Functions:
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
|	Name		|					Description					|Packages Required
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
|OpenDataVaultFile.m	|Opens designated hdf5 file from Data Vault and returns data    			|None
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
|MatrixIntegrate.m	|Integrate image along a given angle with a given amplitude				|image_toolbox
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
|PhaseRotation.m	|Rotate the x and y quadrature of the image						|None
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
|IntegrateAndMask.m	|Integrate image along a given angle with a given amplitude and apply mask on the	|None
|			|result											|
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
|HighPassFilter.m	|Apply High Pass Filter to the Data							|None
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
|TFScanDataProcessor.m	|Process the raw data from Data Vault and apply Low pass filter				|signal_toolbox
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
|ProcessDCData.m	|Required functions for TF Integration package, stretch the DC data from Data Vault the	|None
|			|same way the MatrixIntegrate do, in order to make it easier for residual calculation	|
|-----------------------|---------------------------------------------------------------------------------------|-----------------------
