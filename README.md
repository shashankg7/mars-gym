# MARS-Gym: A Gym framework to model, train, and evaluate recommendationsystems for marketplaces

Framework Code for the RecSys 2020 entitled 'MARS-Gym: A Gym framework to model, train, and evaluate recommendationsystems for marketplaces'. 

![MDP](images/img1.jpg)

MARS-Gym(MArketplaceRecommenderSystems Gym), a benchmark framework for modeling, training, and evaluating RL-based recommender systems for marketplaces. Three main components composesthe framework. The first one is a highly customizable module where the consumer can ingest and process a massiveamount of data for learning using spark jobs. We designed the second component for training purposes. It holdsan extensible module built on top of PyTorch to design learning architectures. It also possesses an OpenAI’s Gym environment that ingests the processed dataset to run a multi-agent system that simulates the targeted marketplace. Finally, the last component is an evaluation module that provides a set of distinct perspectives on theagent’s performance. It presents not only traditional recommendation metrics but also off-policy evaluation metrics, toaccount for the bias induced from the historical data representation of marketplace dynamics. Finally, it also presentsfairness indicators to analyze the long-term impact of such recommenders in the ecosystem concerning sensitive attributes. This component is powered by a user-friendly interface to facilitate the analysis and comparison betweenagents

![Framework](images/img2.jpg)


## Dependencies and Requirements

- python=3.6.7
- pandas=0.25.1
- pyarrow=0.15.0
- matplotlib=2.2.2
- scipy=1.3.1
- numpy=1.17.0
- seaborn=0.8.1
- scikit-learn=0.21.2
- pytorch=1.2.0
- tensorboardx=1.6
- luigi=2.7.5
- tqdm=4.33
- requests=2.18.4
- jupyterlab=1.0.2
- ipywidgets=7.5.1
- diskcache=3.0.6
- pyspark=2.4.3
- psutil=5.2.2
- category_encoders
- plotly=4.4.1
- imbalanced-learn==0.4.3
- torchbearer==0.5.1
- pytorch-nlp==0.4.1
- unidecode==1.1.1
- streamlit==0.52.2
- dask[dataframe]==2.12.0
- gym==0.15.4
- google-cloud-storage==1.26.0

### Install

```bash
conda env create -f environment.yml
conda activate mars-gym
```

## Usage

### Simulate Example

```bash

PYTHONPATH="." luigi --module MODULE --project PROJECT \
--n-factors N_FACTORS --learning-rate LR --optimizer OPTIMIZER \
--epochs EPOCHS --obs-batch-size OBS_BATCH \
--batch-size BATCH_SIZE --num-episodes NUM_EP \
--bandit-policy BANDIT --bandit-policy-params BANDIT_PARAMS  

```

### Evaluate Example

```bash

PYTHONPATH="." luigi --module MODULE --model-task-class MODEL_CLASS \
 --model-task-id MODEL_TASK_ID --fairness-columns "[]" \
 --direct-estimator-class DE_CLASS
```

#### Evaluation Module

```bash

streamlit run tools/eval_viz/app.py
```

## Cite
Please cite the associated paper for this work if you use this code:


```
@article{santana2020mars,
  title={MARS-Gym: A Gym framework to model, train, and evaluate recommendationsystems for marketplaces},
  author={Marlesson R. O. de Santana and
          Luckeciano C. Melo and
          Fernando H. F. Camargo and
          Bruno Brandão and
          Renan Oliveira and
          Sandor Caetano and
          Anderson Soares},
  journal={},
  year={2020}
}
```

## License

Copyright ---

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.