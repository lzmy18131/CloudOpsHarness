"""Evaluation package."""

from cloudops_harness.evaluation.dataset import dataset_stats, load_scenarios, validate_dataset
from cloudops_harness.evaluation.harness import run_experiment
from cloudops_harness.evaluation.metrics import aggregate, compare_paired, mcnemar_pvalue, paired_bootstrap
from cloudops_harness.evaluation.runners import SystemConfig, run_one_scenario
from cloudops_harness.evaluation.scenario_builder import build_dataset, save_dataset

__all__ = [
    "SystemConfig",
    "aggregate",
    "build_dataset",
    "compare_paired",
    "dataset_stats",
    "load_scenarios",
    "mcnemar_pvalue",
    "paired_bootstrap",
    "run_experiment",
    "run_one_scenario",
    "save_dataset",
    "validate_dataset",
]
