# Bath Photonics 2 Lab pieces

App pieces for Photonics 2 lab, Department of Physics, University of Bath. 

## Overview

This module aims to unify the device control and experiment automation in a single place, via the modular puzzlepiece GUI module.
This repository contains the basic pieces for buliding the experiments notebook with GUI. Pieces includes hardware communications and measurement modules for basic measurement routine. These pieces are designed for the use in the environment of Bath Photonics 2 Lab.

## Requirements

    - Python 3 (only tested with 3.11)
    - Ony tested with Windows 11
    - Depends on the pieces used, different python packages are reqiured. For most basic operation, it requires numpy, PyQT6, pyqtgraph, [puzzlepiece] (https://github.com/jdranczewski/puzzlepiece), and [datasets] (https://github.com/jdranczewski/dataset-suite). For a complete coverage of all the pieces, check out the full list of required packages in [requirement.txt] (https://github.com/kn920/BathPhotonics2Lab_pieces/blob/main/requirements.txt).
    - The installation of SDK toolkit / drivers for the hardware device is also required. For example: [Andor SDK] (https://andor.oxinst.com/products/software-development-kit/software-development-kit) for Andor spectrometer, [NI-DAQ mx](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html?srsltid=AfmBOoqbEq5yyNqCnhmd-JwMlmpyn1kLnu7DQ8Zt09DheyEcKw0iZ3aK#569353) for NI DAQ control, etc.



## Installion guide (in Bath Photonics 2 lab) 
This is the (very) detailed installation procedure that I have done. You do not have to follow all the steps.

1. Git pull this repository to the local drive of your PC (e.g., `C:/lab_automation/`) with
```
git clone https://github.com/kn920/BathPhotonics2Lab_pieces.git
```
2. (_Recommended but optional_) Create virtual envrionment for the automation programs in a folder that all users have access (e.g., `C:/lab_automation/`). To do this, open Windows PowerShell and run
```
python.exe -m venv venv
```
Then activate the environment with
```
C:/lab_automation/venv/Scripts/Activate.ps1
```

Note: If you have difficulty in running the codes on PowerShell, see [Windows PowerShell restriction] (#windows-powershell-restriction)
3. Install required python packages using `pip` with `requirement.txt` by
```
pip install -r requirement.txt
```


## Windows PowerShell restriction

If you experience an error with Windows PowerShell when running codes, something like:
```
File C:/lab_automation/venv/Scripts/Activate.ps1 cannot be loaded because the execution of scripts is disabled on this system. 
```
You can run this code on PowerShell to change the execution policy to allow running script (Do not require administrator permission):
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```



### Note to datasets
git clone https://github.com/jdranczewski/dataset-suite.git in document, and rename the folder to "datasets", and add .pth file in venv\Lib\site-packages

Usage: import datasets as ds

### Issues to be fixed
* Randomly happens a +- 1 count offset per pixels (Dark count?), independent to integration time, vs_speed and amp_mode settings
* Fire laser only when CCD integrating & threading