# Bath Photonics 2 Lab Pieces

App pieces for the Photonics 2 Lab, Department of Physics, University of Bath.  

## Overview

This module aims to unify device control and experiment automation in a single place via the modular **puzzlepiece** GUI module.  
This repository contains the basic components (pieces) for building the experiment notebook with a GUI. The components include hardware communication and measurement modules for basic measurement routines. These pieces are designed for use in the Bath Photonics 2 Lab environment.  

## Requirements

- Python 3 (tested only with 3.11)  
- Tested only on Windows 11  
- Depending on the pieces used, different Python packages are required. For most basic operations, you need `numpy`, `PyQt6`, `pyqtgraph`, [puzzlepiece](https://github.com/jdranczewski/puzzlepiece), and [datasets](https://github.com/jdranczewski/dataset-suite). For full coverage of all components, see the complete list of required packages in [requirements.txt](https://github.com/kn920/BathPhotonics2Lab_pieces/blob/main/requirements.txt).  
- Installation of SDK toolkits/drivers for the hardware devices is also required. For example: [Andor SDK](https://andor.oxinst.com/products/software-development-kit/software-development-kit) for Andor spectrometers, [NI-DAQ<sup>TM</sup>mx](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html?srsltid=AfmBOoqbEq5yyNqCnhmd-JwMlmpyn1kLnu7DQ8Zt09DheyEcKw0iZ3aK#569353) for NI DAQ control, etc.  

## Installation Guide (Bath Photonics 2 Lab)  

This is the (very) detailed installation procedure I followed. You do not need to repeat every step.  

1. Clone this repository to the local drive of your PC (e.g., `C:/lab_automation/`):  
   ```bash
   git clone https://github.com/kn920/BathPhotonics2Lab_pieces.git
   ```

2. (_Recommended but optional_) Create a virtual environment for the automation programs in a folder accessible to all users (e.g., `C:/lab_automation/`). Open Windows PowerShell and run:  
   ```powershell
   python.exe -m venv venv
   ```
   Then activate the environment with:  
   ```powershell
   C:/lab_automation/venv/Scripts/Activate.ps1
   ```

   **Note:** If you encounter issues running code in PowerShell, see [Windows PowerShell Restriction](#windows-powershell-restriction).  

3. Install the required Python packages using `pip` and the `requirements.txt` file:  
   ```powershell
   pip install -r requirements.txt
   ```

4. Install the **datasets** package. Since [datasets](https://github.com/jdranczewski/dataset-suite) is not yet published on `pip`, clone it from GitHub into the same folder (e.g., `C:/lab_automation/`):  
   ```powershell
   git clone https://github.com/jdranczewski/dataset-suite
   ```
   Once done, rename the `dataset-suite` folder to `datasets`, then create a file `datasets.pth` in `C:/lab_automation/venv/Lib/site-packages` with the following content:  
   ```
   C:/lab_automation/datasets
   ```

5. (_Recommended but optional_) For convenience, you can create a PowerShell shortcut to activate the virtual environment. First, create a PowerShell profile for the current user by running:  
   ```powershell
   if (!(Test-Path -Path $PROFILE)) {
     New-Item -ItemType File -Path $PROFILE -Force
   }
   ```
   The profile file `Microsoft.PowerShell_profile.ps1` should appear in `\\myfiles\<user>\dos\WindowsPowerShell`.  
   Open this file and add:  
   ```powershell
   New-Alias venv C:\lab_automation\venv\Scripts\Activate.ps1
   ```
   Now, to activate the virtual environment, you can simply run:  
   ```powershell
   venv
   ```
   in Windows PowerShell.  

   **Note:** This shortcut only works for the current user. Each user account will need to set this up individually.  

## Windows PowerShell Restriction  

If you see an error in PowerShell such as:  
```
File C:/lab_automation/venv/Scripts/Activate.ps1 cannot be loaded because the execution of scripts is disabled on this system. 
```  
You can allow script execution (no administrator permission required) by running:  
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```  

## Related Projects  
