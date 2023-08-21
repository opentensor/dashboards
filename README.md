
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

### Secrets
This component needs an environtment variable called `WANDB_API_KEY` with a working api key to communicate with [wandb](https://docs.wandb.ai/).

# Validators
This repo contains a streamlit [dashboard]([url](https://opendashboard-v110.streamlit.app/)) which can be used to inspect and analyze the live network. It works by pulling validator data from [wandb](https://wandb.ai/opentensor-dev/openvalidators?workspace=default) and using this data for **metric tracking** and **interactive data visualizations**.

## Screenshots

*Overview metrics and run selection* - Total participants and contributed knowledge are displayed as metrics at the top of the app. This shows the total dataset size and growth rate. By selecting one or more runs from the table, the app will download the respective source data from wandb or load from local storage.
![Screenshot 2023-07-27 at 13 29 46](https://github.com/opentensor/dashboards/assets/6709103/f54b963e-b0c7-4333-be8c-800743ecf220)


*UID health* - One or more UIDs can be inspected in terms of their succesful response rate, diversity of responses and uniqueness within the network. Leaderboards of top-performing UIDs are also included.
![Screenshot 2023-07-27 at 13 37 13](https://github.com/opentensor/dashboards/assets/6709103/e5b230f2-a21d-4e3e-9767-c787ec06944a)

![Screenshot 2023-07-27 at 13 37 18](https://github.com/opentensor/dashboards/assets/6709103/3b8cfe30-14a6-4493-adda-41c4f82c1025)

*Completions* - Individual completions can be analyzed. Leaderboards can be viewed based on rate or reward, and completion length-and-time statistics are shown. Taken together, these figures allow the reward mechanism to be better understood.
![Screenshot 2023-07-27 at 13 38 19](https://github.com/opentensor/dashboards/assets/6709103/fa7f8f60-425e-4963-98a7-f8bd3641c3dc)

![Screenshot 2023-07-27 at 13 39 01](https://github.com/opentensor/dashboards/assets/6709103/968253ad-b869-46c7-adef-bdefc5ccfc33)


# Metagraph
This repo contains a WIP streamlit dashboard for inspecting the bittensor blockchain. It uses the `multigraph.py` script to pull metagraph snapshots from subtensor and then constructs a dataframe from these snapshots. **If you are running this in dev mode, be sure to run the following command to build a local database**:

```
python multigraph.py
```
By default, it creates a database for netuid 1.


To run the metagraph dashboard:
```
streamlit run metadash.py
```

## Screenshots

------
*Overview metrics and block range selection* - Current block, register cost and network size. A warning is displayed when the dashboard is out of date. By default this is when the source data has staleness of more than 100 blocks.
![Screenshot 2023-07-28 at 16 55 32](https://github.com/opentensor/dashboards/assets/6709103/9844a123-4021-4551-b85f-2690431b9c6c)


*Update metagraph data II* - When the button is clicked, a background script is run which pulls recent data. 
![Screenshot 2023-07-28 at 17 02 31](https://github.com/opentensor/dashboards/assets/6709103/6184b215-9d33-4e1e-8f49-4d868ce2e3df)


*Overview of network* - Hotkey churn and network occupancy of validator and miner slots are shown.
![Screenshot 2023-07-28 at 16 55 42](https://github.com/opentensor/dashboards/assets/6709103/2b8e0e20-936f-4065-979e-c60fc3a8f75a)
![Screenshot 2023-07-28 at 16 55 51](https://github.com/opentensor/dashboards/assets/6709103/62873107-9fb9-4433-9f2d-29b59c5c8a75)

*Miner activity animations* - Highly customizable animations can be made which show the evolution of metrics such as emission and incentive for miners, grouped by coldkey.

![Screenshot 2023-07-28 at 16 57 46](https://github.com/opentensor/dashboards/assets/6709103/590af29c-3aaf-4cf6-976b-20f959568935)
![Screenshot 2023-07-28 at 16 58 00](https://github.com/opentensor/dashboards/assets/6709103/6bf98869-8ab8-42c7-a12a-26408c88889e)

*Miner groups* - Miners are grouped by cold key and the number of hotkeys or IPs in possession of the group can be traced over time.

![Screenshot 2023-07-28 at 17 00 05](https://github.com/opentensor/dashboards/assets/6709103/4f685532-08d2-4122-bd07-36e81c772f87)

*Miner rewards* - Trace data is shown to track group performace over time. Miners belonging to the same hotkey are automatically grouped by color.

![Screenshot 2023-07-28 at 17 01 40](https://github.com/opentensor/dashboards/assets/6709103/4e18635d-3469-4dce-8cd0-7ecdbf3b4398)

![Screenshot 2023-07-28 at 16 59 23](https://github.com/opentensor/dashboards/assets/6709103/80d5c1a1-4fca-4280-ad10-3a82f5b4b54b)

*Validator activity animations* - Highly customizable animations can be made which show the evolution of metrics such as emission and incentive for miners, grouped by coldkey.

![Screenshot 2023-07-28 at 17 00 45](https://github.com/opentensor/dashboards/assets/6709103/5f0e5742-d003-4caf-97f7-84c02c975518)

*Block introspection* - Full metagraph state at selected block.

<img width="1721" alt="Screenshot 2023-08-02 at 11 12 43" src="https://github.com/opentensor/dashboards/assets/6709103/67942753-b44a-4c85-96e3-6efc11d3f008">



**Feature list**:
- Stake, incentive, dividends by block/time 💰
- Weights and consensus 💪
- Churn and registration rate 🚦
- Clustering of hotkeys based on shared coldkeys and IPs 🥊
- Clustering of hotkeys based on weights and correlations between stake 📈
- Connectivity embedding of metagraph snapshots ➡️
- All of the above for user-selected UIDs/hotkeys 🧔
- Full block introspection 🗄️


## Known Bug

There are compatibilty issues with protobuf, which cause errors sucha as
```
2023-07-28 23:20:04.943 Uncaught app exception
Traceback (most recent call last):
  File "/home/steffen/dashboards/env/lib/python3.8/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 552, in _run_script
    exec(code, module.__dict__)
  File "/home/steffen/dashboards/metadash.py", line 24, in <module>
    import bittensor
  File "/home/steffen/bittensor/bittensor/__init__.py", line 170, in <module>
    import bittensor._proto.bittensor_pb2 as proto
  File "/home/steffen/bittensor/bittensor/_proto/bittensor_pb2.py", line 32, in <module>
    _descriptor.EnumValueDescriptor(
  File "/home/steffen/dashboards/env/lib/python3.8/site-packages/google/protobuf/descriptor.py", line 796, in __new__
    _message.Message._CheckCalledFromGeneratedFile()
TypeError: Descriptors cannot not be created directly.
If this call came from a _pb2.py file, your generated code is out of date and must be regenerated with protoc >= 3.19.0.
If you cannot immediately regenerate your protos, some other possible workarounds are:
 1. Downgrade the protobuf package to 3.20.x or lower.
 2. Set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python (but this will use pure-Python parsing and will be much slower).

More information: https://developers.google.com/protocol-buffers/docs/news/2022-05-06#python-updates
```
If this happens, you can export the recommended variable and rerun
```
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python streamlit run metadash.py
```

### Possible fix

Since the original source of this bugfix is the conflicts between the requirements:
```
ERROR: Cannot install -r /mount/src/dashboards/requirements.txt (line 1), -r /mount/src/dashboards/requirements.txt (line 10) and -r /mount/src/dashboards/requirements.txt (line 3) because these package versions have conflicting dependencies.

The conflict is caused by:
    streamlit 1.23.1 depends on protobuf<5 and >=3.20
    wandb 0.15.3 depends on protobuf!=4.21.0, <5 and >=3.15.0; python_version == "3.9" and sys_platform == "linux"
    bittensor 5.3.3 depends on protobuf==3.19.5
To fix this you could try to:
1. loosen the range of package versions you've specified
2. remove package versions to allow pip attempt to solve the dependency conflict

ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/#dealing-with-dependency-conflicts
```

We can fix this by aligning the requirements so that everyone has a common range of protobuf package versions to work with...
