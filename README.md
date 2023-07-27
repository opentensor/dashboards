<div align="left">

# **Dashboards** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/realbittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 
---
Opentensor Dashboards, made with streamlit. The goal of this repo is to provide a means to visually introspect and quickly analyze key components of the bittensor network, namely the blockchain and AI layers. Furthermore, the dashboard are designed to be useful to beginners and experts alike so that the entire community can benefit from and learn more about the dynamic and decentralized bittensor marketplace. for complete beginners, we refer you to the [bittensor repo](https://github.com/opentensor/bittensor) and [official docs](https://bittensor.com/documentation/intro/index).

Repo contents:
1. [openvalidators](#validators) dashboard
2. [openmetagraph](#metagraph) dashboard

## Design Overview

Both the constantly growing bittensor [blockchain](https://polkadot.js.org/apps/#/chainstate) and the openvalidators [community wandb project](https://wandb.ai/opentensor-dev/openvalidators?workspace=default) produce many GB per day.  Storing, analyzing and visualizing such a large volume of data can be challenging, and in acknowledgement of this fact there are ongoing developments to the repo in the following way, which aligns with typical use-cases while remaining within reasonable data limits and performance expectations.

- Recent data (24-48 hours) is stored in high resolution (raw) format. This is suitable for full introspection.
- Historical data (30-90 days) is stored in low resolution (aggregated) format. This is suitable for high-level trend analysis.

## Getting Started

To install:
```
pip install -e .
```

To run a dashboard:
```
streamlit run dashboard.py
```
Alternatively, you can [deploy the app for free on streamlit](https://blog.streamlit.io/host-your-streamlit-app-for-free/), but be warned that the app is limited to 1GB of RAM.


# Validators
This repo contains a streamlit [dashboard]([url](https://opendashboard-v110.streamlit.app/)) which can be used to inspect and analyze the live network. It works by pulling validator data from [wandb](https://wandb.ai/opentensor-dev/openvalidators?workspace=default) and using this data for **metric tracking** and **interactive data visualizations**.

## Screenshots

------
*Overview metrics and run selection* - Total participants and contributed knowledge are displayed as metrics at the top of the app. This shows the total dataset size and growth rate. By selecting one or more runs from the table, the app will download the respective source data from wandb or load from local storage.
![Screenshot 2023-07-27 at 13 29 46](https://github.com/opentensor/dashboards/assets/6709103/f54b963e-b0c7-4333-be8c-800743ecf220)


------
*UID health* - One or more UIDs can be inspected in terms of their succesful response rate, diversity of responses and uniqueness within the network. Leaderboards of top-performing UIDs are also included.
![Screenshot 2023-07-27 at 13 37 13](https://github.com/opentensor/dashboards/assets/6709103/e5b230f2-a21d-4e3e-9767-c787ec06944a)

![Screenshot 2023-07-27 at 13 37 18](https://github.com/opentensor/dashboards/assets/6709103/3b8cfe30-14a6-4493-adda-41c4f82c1025)

------
*Completions* - Individual completions can be analyzed. Leaderboards can be viewed based on rate or reward, and completion length-and-time statistics are shown. Taken together, these figures allow the reward mechanism to be better understood.
![Screenshot 2023-07-27 at 13 38 19](https://github.com/opentensor/dashboards/assets/6709103/fa7f8f60-425e-4963-98a7-f8bd3641c3dc)

![Screenshot 2023-07-27 at 13 39 01](https://github.com/opentensor/dashboards/assets/6709103/968253ad-b869-46c7-adef-bdefc5ccfc33)


# Metagraph
This repo contains a WIP streamlit dashboard for inspecting the bittensor blockchain. It uses the `multigraph.py` script to pull metagraph snapshots from subtensor and then constructs a dataframe from these snapshots. 

## Screenshots

------
*Overview metrics and block range selection* - Current block, register cost and network size.
![Screenshot 2023-07-27 at 16 52 38](https://github.com/opentensor/dashboards/assets/6709103/943ccf97-1d9d-4f13-bc86-eaa1eafbdef4)



**Feature list**:
- Stake, incentive, dividends by block/time 💰
- Weights and consensus 💪
- Churn and registration rate 🚦
- Clustering of hotkeys based on shared coldkeys and IPs 🥊
- Clustering of hotkeys based on weights and correlations between stake 📈
- Connectivity embedding of metagraph snapshots ➡️
- All of the above for user-selected UIDs/hotkeys 🧔
- Full block introspection 🗄️
