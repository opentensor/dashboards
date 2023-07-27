<div align="center">

# **Dashboards** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/realbittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 
---
Opentensor Dashboards.

## Validators
This repo contains a streamlit [dashboard]([url](https://opendashboard-v110.streamlit.app/)) which can be used to inspect and analyze the live network. It works by pulling validator data from [wandb](https://wandb.ai/opentensor-dev/openvalidators?workspace=default) and using this data for **metric tracking** and **interactive data visualizations**.


To install:
```
pip install -e .
```

To run dashboard:
```
streamlit run dashboard.py
```
Alternatively, you can [deploy the app for free on streamlit](https://blog.streamlit.io/host-your-streamlit-app-for-free/), but be warned that the app is limited to 1GB of RAM.

### Screenshots
------
*Overview metrics and run selection*
![Screenshot 2023-07-27 at 13 29 46](https://github.com/opentensor/dashboards/assets/6709103/f54b963e-b0c7-4333-be8c-800743ecf220)


------
*UID health*
![Screenshot 2023-07-27 at 13 37 13](https://github.com/opentensor/dashboards/assets/6709103/e5b230f2-a21d-4e3e-9767-c787ec06944a)

![Screenshot 2023-07-27 at 13 37 18](https://github.com/opentensor/dashboards/assets/6709103/3b8cfe30-14a6-4493-adda-41c4f82c1025)

------
*Completions*
![Screenshot 2023-07-27 at 13 38 19](https://github.com/opentensor/dashboards/assets/6709103/fa7f8f60-425e-4963-98a7-f8bd3641c3dc)

![Screenshot 2023-07-27 at 13 39 01](https://github.com/opentensor/dashboards/assets/6709103/968253ad-b869-46c7-adef-bdefc5ccfc33)


## OpenMetagraph
