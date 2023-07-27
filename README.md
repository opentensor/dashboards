<div align="left">

# **Dashboards** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/realbittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 
---
Opentensor Dashboards. The goal of this repo is to provide a means to visually introspect and quickly analyze key components of the bittensor network, namely the blockchain and AI layers. Furthermore, the dashboard are designed to be useful to beginners and experts alike so that the entire community can benefit from and learn more about the dynamic and decentralized bittensor marketplace. for complete beginners, we refer you to the [bittensor repo](https://github.com/opentensor/bittensor) and [official docs](https://bittensor.com/documentation/intro/index).

Repo contents:
1. [openvalidators](#validators) dashboard
2. [openmetagraph](#metagraph) dashboard

# Design Overview and Ongoing Development

Both the constantly growing bittensor [blockchain](https://polkadot.js.org/apps/#/chainstate) and the openvalidators [community wandb project](https://wandb.ai/opentensor-dev/openvalidators?workspace=default) produce many GB per day. Storing, analyzing and visualizing such a large volume of data can be challenging, and in acknowledgement of this fact we are enhancing the repo in the following way, which aligns with typical use-cases while remaining within reasonable data limits and performance expectations.

- Recent data (24-48 hours) is stored in high resolution (raw) format. This is suitable for full introspection.
- Historical data (14-30 days) is stored in low resolution (aggregated) format. This is suitable for high-level trend analysis.

# Validators
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


## Screenshots
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


## Metagraph
