
import json
import sys

# Configuration
PROJECT_NAME = "Reference: Socio-Economic Model (Complex)"
PROJECT_DESCRIPTION = """Complex DAG demonstrating categorical logic, formula lookups, logits (softmax), and tail replacement.

Features:
- Exogenous variables (Region, Age)
- Conditional distributions (Education | Region)
- Latent variables (Skill)
- Softmax logic for categorical selection (Occupation)
- Lognormal income with semantic offsets
- Pareto tail replacement for high earners
M
Model:
Region -> Education -> Skill -> Occupation -> Income
"""

def create_dag_payload():
    return {
        "nodes": [
            # ---------------------------------------------------------
            # Exogenous
            # ---------------------------------------------------------
            {
                "id": "region",
                "name": "Region",
                "kind": "stochastic",
                "dtype": "string",
                "scope": "row",
                "distribution": {
                    "type": "categorical",
                    "params": {
                        "categories": ["North", "Center", "South"],
                        "probs": [0.3, 0.4, 0.3]
                    }
                }
            },
            {
                "id": "age",
                "name": "Age",
                "kind": "stochastic",
                "dtype": "int",
                "scope": "row",
                "distribution": {
                    "type": "normal",
                    "params": { "mu": 40, "sigma": 10 }
                },
                "post_processing": {
                    "clip_min": 18,
                    "clip_max": 65,
                    "round_decimals": 0
                }
            },
            
            # ---------------------------------------------------------
            # Education (Conditional on Region)
            # ---------------------------------------------------------
            {
                "id": "education_years",
                "name": "Education Years",
                "kind": "stochastic",
                "dtype": "int",
                "scope": "row",
                "distribution": {
                    "type": "normal",
                    "params": {
                        "mu": "region_education_mu[region]",
                        "sigma": 2
                    }
                },
                "post_processing": {
                    "clip_min": 0,
                    "round_decimals": 0
                }
            },
            
            # ---------------------------------------------------------
            # Skill (Latent)
            # ---------------------------------------------------------
            {
                "id": "skill",
                "name": "Skill Level",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {
                    "type": "normal",
                    "params": {
                        "mu": "0.5 * education_years + region_skill_effect[region]",
                        "sigma": 1
                    }
                }
            },
            
            # ---------------------------------------------------------
            # Occupation (Softmax Logic)
            # ---------------------------------------------------------
            {
                "id": "logit_low",
                "name": "Logit (LowSkill)",
                "kind": "deterministic",
                "dtype": "float",
                "scope": "row",
                "formula": "-1.5 - 1.0 * skill"
            },
            {
                "id": "logit_mid",
                "name": "Logit (MidSkill)",
                "kind": "deterministic",
                "dtype": "float",
                "scope": "row",
                "formula": "0.0 + 0.5 * skill"
            },
            {
                "id": "logit_high",
                "name": "Logit (HighSkill)",
                "kind": "deterministic",
                "dtype": "float",
                "scope": "row",
                "formula": "-0.5 + 1.2 * skill"
            },
            {
                "id": "exp_sum", 
                "name": "Sum Exp Logits",
                "kind": "deterministic",
                "dtype": "float",
                "scope": "row",
                "formula": "exp(logit_low) + exp(logit_mid) + exp(logit_high)"
            },
            {
                "id": "prob_low",
                "name": "P(LowSkill)",
                "kind": "deterministic",
                "dtype": "float",
                "scope": "row",
                "formula": "exp(logit_low) / exp_sum"
            },
            {
                "id": "prob_mid",
                "name": "P(MidSkill)",
                "kind": "deterministic",
                "dtype": "float",
                "scope": "row",
                "formula": "exp(logit_mid) / exp_sum"
            },
            {
                "id": "u_occ",
                "name": "U(Occupation)",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": { "type": "uniform", "params": { "low": 0, "high": 1 } }
            },
            {
                "id": "occupation",
                "name": "Occupation",
                "kind": "deterministic",
                "dtype": "string",
                "scope": "row",
                "formula": "if_else(u_occ < prob_low, 'LowSkill', if_else(u_occ < (prob_low + prob_mid), 'MidSkill', 'HighSkill'))"
            },
            
            # ---------------------------------------------------------
            # Family Income
            # ---------------------------------------------------------
            {
                "id": "family_income",
                "name": "Family Income",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {
                    "type": "lognormal",
                    "params": {
                        "mean": "9.5 + 0.08 * education_years + region_income_shift[region]",
                        "sigma": 0.6
                    }
                },
                "post_processing": { "round_decimals": 2 }
            },
            
            # ---------------------------------------------------------
            # Individual Income
            # ---------------------------------------------------------
            {
                "id": "raw_income",
                "name": "Raw Individual Income",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {
                    "type": "lognormal",
                    "params": {
                        "mean": "8.8 + 0.35 * skill + occupation_effect[occupation] + 0.25 * log(family_income) + 0.015 * (age - 40)",
                        "sigma": 0.7
                    }
                }
            },
            {
                "id": "pareto_tail",
                "name": "Pareto Tail",
                "kind": "stochastic",
                "dtype": "float",
                "scope": "row",
                "distribution": {
                    "type": "scipy.pareto",
                    "params": {
                        "b": 2.5,
                        "scale": 150000
                    }
                }
            },
            {
                "id": "individual_income",
                "name": "Final Individual Income",
                "kind": "deterministic",
                "dtype": "float",
                "scope": "row",
                "formula": "if_else(raw_income > 150000, pareto_tail, raw_income)",
                "post_processing": { "round_decimals": 2 }
            }
        ],
        "edges": [
            # Region -> Education
            {"source": "region", "target": "education_years"},
            
            # Education + Region -> Skill
            {"source": "education_years", "target": "skill"},
            {"source": "region", "target": "skill"},
            
            # Skill -> Logits
            {"source": "skill", "target": "logit_low"},
            {"source": "skill", "target": "logit_mid"},
            {"source": "skill", "target": "logit_high"},
            
            # Logits -> Exp Sum
            {"source": "logit_low", "target": "exp_sum"},
            {"source": "logit_mid", "target": "exp_sum"},
            {"source": "logit_high", "target": "exp_sum"},
            
            # Logits + Exp Sum -> Probs
            {"source": "logit_low", "target": "prob_low"},
            {"source": "exp_sum", "target": "prob_low"},
            {"source": "logit_mid", "target": "prob_mid"},
            {"source": "exp_sum", "target": "prob_mid"},
            
            # Probs + U + Logits(implicit in cutoff) -> Occupation
            {"source": "prob_low", "target": "occupation"},
            {"source": "prob_mid", "target": "occupation"},
            {"source": "u_occ", "target": "occupation"},
            
            # Education + Region -> Family Income
            {"source": "education_years", "target": "family_income"},
            {"source": "region", "target": "family_income"},
            
            # Age + Family + Skill + Occupation -> Raw Income
            {"source": "age", "target": "raw_income"},
            {"source": "family_income", "target": "raw_income"},
            {"source": "skill", "target": "raw_income"},
            {"source": "occupation", "target": "raw_income"},
            
            # Raw + Pareto -> Final
            {"source": "raw_income", "target": "individual_income"},
            {"source": "pareto_tail", "target": "individual_income"}
        ],
        "context": {
            "region_education_mu": {
                "North": 14,
                "Center": 13,
                "South": 11
            },
            "region_skill_effect": {
                "North": 0.5,
                "Center": 0.0,
                "South": -0.5
            },
            "region_income_shift": {
                "North": 0.3,
                "Center": 0.0,
                "South": -0.4
            },
            "occupation_effect": {
                "LowSkill": -0.6,
                "MidSkill": 0.0,
                "HighSkill": 0.7
            }
        },
        "metadata": {
            "sample_size": 1000,
            "seed": 42
        }
    }

if __name__ == "__main__":
    project_payload = {
        "name": PROJECT_NAME,
        "description": PROJECT_DESCRIPTION,
        "dag_definition": create_dag_payload()
    }
    print(json.dumps(project_payload, indent=2))
