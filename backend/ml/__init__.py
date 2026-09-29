"""
Machine-learning core for RL-Cleanse.

Modules:
    metrics              the single metric implementation every method scores through
    reward_shaper        magnitude-aware streaming reward (master plan section 2.3)
    dqn_model            Q-network, DQN policy and the observation encoder
    experience_replay    seeded circular replay buffer
    rule_based_baseline  rule filter under the same online constraint
    calibrate_baseline   training-split grid search for the baseline
    train_dqn            training pipeline with validation-based selection
    evaluate_benchmarks  benchmark table and figures
"""
