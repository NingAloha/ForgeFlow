use anyhow::{anyhow, Context, Result};
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, Write};

use crate::llm;
use crate::mutation::json_write::set_value_at_path;
use crate::sieves::requirements::artifact::{
    Constraint,
    Inconsistency,
    PendingClarification,
    RequirementsArtifact,
};
use crate::sieves::requirements::io::{load_requirements, save_requirements};
use crate::sieves::requirements::validator::validate_requirements_artifact;

const QUESTION_SYSTEM_PROMPT: &str =
    include_str!("prompts/explicit_constraints_question_system.txt");
const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/explicit_constraints_extract_system.txt");
const EXPLICIT_CONSTRAINTS_CLARIFICATION_ID: &str =
    "scope.explicit_constraints";
const EXPLICIT_CONSTRAINTS_SIEVE_ID: &str =
    "requirements.scope.explicit_constraints";

const ALLOWED_CONSTRAINT_KINDS: &[&str] = &[
    "technical",
    "platform",
    "policy",
    "resource",
    "performance",
    "integration",
    "data",
    "business",
    "other",
];

#[derive(Debug, Deserialize)]
struct ClarificationQuestion {
    question: String,
}

#[derive(Debug, Deserialize)]
struct ExplicitConstraintsExtraction {
    explicit_constraints: Vec<ExtractedConstraint>,
    no_explicit_constraints_declared: bool,
    detected_inconsistencies: Vec<DetectedInconsistency>,
}

#[derive(Debug, Deserialize)]
struct ExtractedConstraint {
    kind: String,
    text: String,
}

#[derive(Debug, Deserialize)]
struct DetectedInconsistency {
    id: String,
    message: String,
}

pub fn run_explicit_constraints_scope() -> Result<()> {
    let artifact = load_requirements().context("failed to load requirements artifact")?;

    let clarification = find_pending_clarification(
        &artifact,
        EXPLICIT_CONSTRAINTS_CLARIFICATION_ID,
    )?;

    let question = generate_explicit_constraints_question(&artifact, &clarification)?;

    println!("Current question:");
    println!("{question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact =
        update_explicit_constraints(artifact, &clarification, answer.trim())?;

    save_requirements(&updated_artifact).context("failed to save requirements artifact")?;

    println!();
    println!("Saved requirements artifact:");
    println!("{}", serde_json::to_string_pretty(&updated_artifact)?);

    Ok(())
}

fn find_pending_clarification(
    artifact: &RequirementsArtifact,
    id: &str,
) -> Result<PendingClarification> {
    artifact
        .pending_clarifications
        .iter()
        .find(|item| item.id == id)
        .cloned()
        .ok_or_else(|| anyhow!("pending clarification {:?} not found", id))
}

fn generate_explicit_constraints_question(
    artifact: &RequirementsArtifact,
    clarification: &PendingClarification,
) -> Result<String> {
    let prompt_input = json!({
        "clarification": clarification,
        "current_value": artifact.scope.explicit_constraints,
        "relevant_context": {
            "intent": artifact.intent,
            "product": artifact.product,
            "scope": {
                "capability_categories": artifact.scope.capability_categories,
            }
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate explicit constraints clarification question")?;

    let generated: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if generated.question.trim().is_empty() {
        anyhow::bail!("generated explicit constraints question must not be empty");
    }

    Ok(generated.question)
}

pub fn update_explicit_constraints(
    artifact: RequirementsArtifact,
    clarification: &PendingClarification,
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before explicit constraints update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    let prompt_input = json!({
        "clarification": clarification,
        "user_answer": user_answer,
        "current_value": artifact.scope.explicit_constraints,
        "relevant_context": {
            "intent": artifact.intent,
            "product": artifact.product,
            "scope": {
                "capability_categories": artifact.scope.capability_categories,
            }
        }
    });

    let extraction_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract explicit constraints")?;

    let extraction: ExplicitConstraintsExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match ExplicitConstraintsExtraction schema")?;

    apply_explicit_constraints_extraction(artifact, &extraction)
}

fn apply_explicit_constraints_extraction(
    artifact: RequirementsArtifact,
    extraction: &ExplicitConstraintsExtraction,
) -> Result<RequirementsArtifact> {
    validate_explicit_constraints_extraction(extraction)?;

    if extraction.explicit_constraints.is_empty()
        && !extraction.no_explicit_constraints_declared
        && extraction.detected_inconsistencies.is_empty()
    {
        anyhow::bail!(
            "explicit constraints answer did not clarify explicit_constraints"
        );
    }

    let mut artifact_value = serde_json::to_value(&artifact)
        .context("failed to convert requirements artifact to JSON value")?;

    if !extraction.explicit_constraints.is_empty() {
        let constraints: Vec<Constraint> = extraction
            .explicit_constraints
            .iter()
            .map(|item| Constraint {
                kind: item.kind.clone(),
                text: item.text.clone(),
            })
            .collect();

        set_value_at_path(
            &mut artifact_value,
            &["scope".to_string(), "explicit_constraints".to_string()],
            serde_json::to_value(constraints)
                .context("failed to serialize explicit_constraints")?,
        )
        .context("failed to set scope.explicit_constraints")?;
    }

    if !extraction.detected_inconsistencies.is_empty() {
        let inconsistencies = artifact_value
            .get_mut("inconsistencies")
            .and_then(Value::as_array_mut)
            .ok_or_else(|| anyhow!("inconsistencies must be an array"))?;

        for detected in &extraction.detected_inconsistencies {
            let built = build_explicit_constraints_inconsistency(detected)?;
            inconsistencies.push(
                serde_json::to_value(built)
                    .context("failed to serialize inconsistency")?,
            );
        }
    }

    set_value_at_path(
        &mut artifact_value,
        &["maturity".to_string()],
        Value::String("scope".to_string()),
    )
    .context("failed to set maturity after explicit constraints update")?;

    if extraction.detected_inconsistencies.is_empty()
        && (!extraction.explicit_constraints.is_empty()
            || extraction.no_explicit_constraints_declared)
    {
        let _removed = remove_pending_clarification_by_id(
            &mut artifact_value,
            EXPLICIT_CONSTRAINTS_CLARIFICATION_ID,
        )?;
    }

    let updated_artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&updated_artifact)
        .context("explicit constraints update produced invalid requirements artifact")?;

    validate_explicit_constraints_result(&updated_artifact, extraction)?;

    Ok(updated_artifact)
}

fn validate_explicit_constraints_extraction(
    extraction: &ExplicitConstraintsExtraction,
) -> Result<()> {
    for (index, item) in extraction.explicit_constraints.iter().enumerate() {
        if item.kind.trim().is_empty() {
            anyhow::bail!("explicit_constraints[{index}].kind must not be empty");
        }
        if !ALLOWED_CONSTRAINT_KINDS.contains(&item.kind.as_str()) {
            anyhow::bail!(
                "explicit_constraints[{index}].kind must be one of {:?}, got {:?}",
                ALLOWED_CONSTRAINT_KINDS,
                item.kind
            );
        }
        if item.text.trim().is_empty() {
            anyhow::bail!("explicit_constraints[{index}].text must not be empty");
        }
    }

    for (index, item) in extraction.detected_inconsistencies.iter().enumerate() {
        if item.id.trim().is_empty() {
            anyhow::bail!("detected_inconsistencies[{index}].id must not be empty");
        }
        if item.message.trim().is_empty() {
            anyhow::bail!(
                "detected_inconsistencies[{index}].message must not be empty"
            );
        }
    }

    if extraction.no_explicit_constraints_declared {
        if !extraction.explicit_constraints.is_empty() {
            anyhow::bail!(
                "no_explicit_constraints_declared=true requires explicit_constraints to be empty"
            );
        }
        if !extraction.detected_inconsistencies.is_empty() {
            anyhow::bail!(
                "no_explicit_constraints_declared=true requires detected_inconsistencies to be empty"
            );
        }
    }

    if !extraction.explicit_constraints.is_empty() && extraction.no_explicit_constraints_declared {
        anyhow::bail!(
            "explicit_constraints non-empty requires no_explicit_constraints_declared=false"
        );
    }

    Ok(())
}

fn build_explicit_constraints_inconsistency(
    detected: &DetectedInconsistency,
) -> Result<Inconsistency> {
    if detected.id.trim().is_empty() {
        anyhow::bail!("detected inconsistency id must not be empty");
    }
    if detected.message.trim().is_empty() {
        anyhow::bail!("detected inconsistency message must not be empty");
    }

    Ok(Inconsistency {
        id: format!("scope.explicit_constraints.{}", detected.id),
        stage: "scope".to_string(),
        sieve: EXPLICIT_CONSTRAINTS_SIEVE_ID.to_string(),
        severity: "blocking".to_string(),
        target_paths: vec![vec!["scope".to_string(), "explicit_constraints".to_string()]],
        message: detected.message.clone(),
        requires_clarification: true,
    })
}

fn remove_pending_clarification_by_id(
    artifact_value: &mut Value,
    id: &str,
) -> Result<bool> {
    let pending = artifact_value
        .get_mut("pending_clarifications")
        .and_then(Value::as_array_mut)
        .ok_or_else(|| anyhow!("pending_clarifications must be an array"))?;

    let original_len = pending.len();
    pending.retain(|item| item.get("id").and_then(Value::as_str) != Some(id));

    Ok(pending.len() != original_len)
}

fn validate_explicit_constraints_result(
    artifact: &RequirementsArtifact,
    extraction: &ExplicitConstraintsExtraction,
) -> Result<()> {
    if !extraction.explicit_constraints.is_empty()
        && artifact.scope.explicit_constraints.is_empty()
    {
        anyhow::bail!(
            "explicit constraints update must populate scope.explicit_constraints"
        );
    }

    if extraction.no_explicit_constraints_declared
        && !artifact.scope.explicit_constraints.is_empty()
    {
        anyhow::bail!(
            "no_explicit_constraints_declared=true requires scope.explicit_constraints to remain empty"
        );
    }

    let has_pending = artifact.pending_clarifications.iter().any(|item| {
        item.id == EXPLICIT_CONSTRAINTS_CLARIFICATION_ID
    });

    if extraction.detected_inconsistencies.is_empty()
        && (!extraction.explicit_constraints.is_empty()
            || extraction.no_explicit_constraints_declared)
        && has_pending
    {
        anyhow::bail!(
            "explicit_constraints pending clarification must be removed after successful update"
        );
    }

    if !extraction.detected_inconsistencies.is_empty() {
        if !has_pending {
            anyhow::bail!(
                "explicit_constraints pending clarification must remain when inconsistencies exist"
            );
        }
        if !artifact
            .inconsistencies
            .iter()
            .any(|item| item.sieve == EXPLICIT_CONSTRAINTS_SIEVE_ID)
        {
            anyhow::bail!(
                "explicit constraints inconsistencies must be appended with matching sieve"
            );
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sieves::requirements::artifact::{Intent, Product, Scope};

    fn base_artifact() -> RequirementsArtifact {
        RequirementsArtifact {
            artifact_type: "requirements".to_string(),
            schema_version: "0.1".to_string(),
            maturity: "intent".to_string(),
            intent: Intent {
                raw_input: "做一个校园二手交易平台".to_string(),
                goal: "做一个校园二手交易平台".to_string(),
                domain: "校园二手交易".to_string(),
            },
            product: Product {
                target_users: vec!["大学生".to_string()],
                application_type: vec!["Web 应用".to_string()],
                target_platforms: vec!["Web".to_string()],
            },
            scope: Scope {
                capability_categories: vec!["商品交易".to_string()],
                explicit_constraints: vec![],
                non_goals: vec![],
            },
            functional_requirements: vec![],
            non_functional_requirements: vec![],
            external_interfaces: vec![],
            data_requirements: vec![],
            pending_clarifications: vec![PendingClarification {
                id: EXPLICIT_CONSTRAINTS_CLARIFICATION_ID.to_string(),
                target_path: vec![
                    "scope".to_string(),
                    "explicit_constraints".to_string(),
                ],
                question: "是否有其他明确约束？".to_string(),
                sieve: EXPLICIT_CONSTRAINTS_SIEVE_ID.to_string(),
            }],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn technical_constraint_accepted() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![ExtractedConstraint {
                kind: "technical".to_string(),
                text: "必须使用 React、PostgreSQL 和 Redis".to_string(),
            }],
            no_explicit_constraints_declared: false,
            detected_inconsistencies: vec![],
        };

        let updated = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert_eq!(updated.scope.explicit_constraints.len(), 1);
        assert_eq!(updated.scope.explicit_constraints[0].kind, "technical");
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == EXPLICIT_CONSTRAINTS_CLARIFICATION_ID));
        assert!(updated.inconsistencies.is_empty());
    }

    #[test]
    fn policy_and_data_constraints_accepted() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![
                ExtractedConstraint {
                    kind: "policy".to_string(),
                    text: "只能使用校内邮箱注册".to_string(),
                },
                ExtractedConstraint {
                    kind: "data".to_string(),
                    text: "交易记录至少保留一年".to_string(),
                },
            ],
            no_explicit_constraints_declared: false,
            detected_inconsistencies: vec![],
        };

        let updated = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert_eq!(updated.scope.explicit_constraints.len(), 2);
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == EXPLICIT_CONSTRAINTS_CLARIFICATION_ID));
    }

    #[test]
    fn no_explicit_constraints_declared_is_valid_completion() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![],
            no_explicit_constraints_declared: true,
            detected_inconsistencies: vec![],
        };

        let updated = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated.scope.explicit_constraints.is_empty());
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == EXPLICIT_CONSTRAINTS_CLARIFICATION_ID));
        assert!(updated.inconsistencies.is_empty());
    }

    #[test]
    fn vague_constraint_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![],
            no_explicit_constraints_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "vague_explicit_constraint".to_string(),
                message: "用户回答过于宽泛，无法形成可执行的明确约束。".to_string(),
            }],
        };

        let updated = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == EXPLICIT_CONSTRAINTS_CLARIFICATION_ID));
        let inconsistency = updated
            .inconsistencies
            .iter()
            .find(|item| item.sieve == EXPLICIT_CONSTRAINTS_SIEVE_ID)
            .expect("must have inconsistency");
        assert_eq!(inconsistency.severity, "blocking");
    }

    #[test]
    fn functional_requirement_answer_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![],
            no_explicit_constraints_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "functional_requirement_instead_of_constraint".to_string(),
                message: "用户回答主要描述功能或能力，而不是额外明确约束。".to_string(),
            }],
        };

        let updated = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == EXPLICIT_CONSTRAINTS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == EXPLICIT_CONSTRAINTS_SIEVE_ID));
    }

    #[test]
    fn non_goal_answer_produces_blocking_inconsistency_and_keeps_pending() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![],
            no_explicit_constraints_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "non_goal_instead_of_explicit_constraint".to_string(),
                message: "用户回答更像产品非目标，而不是额外显式约束，需要在 non_goals 层澄清。".to_string(),
            }],
        };

        let updated = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated.scope.explicit_constraints.is_empty());
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == EXPLICIT_CONSTRAINTS_CLARIFICATION_ID));
        let inconsistency = updated
            .inconsistencies
            .iter()
            .find(|item| {
                item.id
                    == "scope.explicit_constraints.non_goal_instead_of_explicit_constraint"
            })
            .expect("must have non-goal inconsistency");
        assert_eq!(inconsistency.sieve, EXPLICIT_CONSTRAINTS_SIEVE_ID);
        assert_eq!(inconsistency.severity, "blocking");
        assert!(inconsistency.requires_clarification);
    }

    #[test]
    fn uncertain_absence_produces_blocking_inconsistency_and_keeps_pending() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![],
            no_explicit_constraints_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "uncertain_explicit_constraints_absence".to_string(),
                message: "用户没有明确声明是否存在其他约束，需要进一步确认。".to_string(),
            }],
        };

        let updated = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == EXPLICIT_CONSTRAINTS_CLARIFICATION_ID));
        let inconsistency = updated
            .inconsistencies
            .iter()
            .find(|item| item.id == "scope.explicit_constraints.uncertain_explicit_constraints_absence")
            .expect("must have uncertainty inconsistency");
        assert_eq!(inconsistency.severity, "blocking");
        assert_eq!(inconsistency.sieve, EXPLICIT_CONSTRAINTS_SIEVE_ID);
    }

    #[test]
    fn invalid_kind_rejected() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![ExtractedConstraint {
                kind: "random".to_string(),
                text: "xxx".to_string(),
            }],
            no_explicit_constraints_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect_err("invalid kind should fail");
        assert!(err.to_string().contains("must be one of"));
    }

    #[test]
    fn no_declared_true_with_non_empty_constraints_rejected() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![ExtractedConstraint {
                kind: "technical".to_string(),
                text: "必须使用 React".to_string(),
            }],
            no_explicit_constraints_declared: true,
            detected_inconsistencies: vec![],
        };

        let err = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect_err("conflicting no_declared should fail");
        assert!(err
            .to_string()
            .contains("no_explicit_constraints_declared=true requires explicit_constraints to be empty"));
    }

    #[test]
    fn no_declared_true_with_inconsistencies_rejected() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![],
            no_explicit_constraints_declared: true,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "vague_explicit_constraint".to_string(),
                message: "x".to_string(),
            }],
        };

        let err = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect_err("no_declared with inconsistency should fail");
        assert!(err
            .to_string()
            .contains("no_explicit_constraints_declared=true requires detected_inconsistencies to be empty"));
    }

    #[test]
    fn empty_extraction_rejected() {
        let artifact = base_artifact();
        let extraction = ExplicitConstraintsExtraction {
            explicit_constraints: vec![],
            no_explicit_constraints_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_explicit_constraints_extraction(artifact, &extraction)
            .expect_err("empty extraction should fail");
        assert_eq!(
            err.to_string(),
            "explicit constraints answer did not clarify explicit_constraints"
        );
    }
}
