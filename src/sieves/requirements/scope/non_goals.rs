use anyhow::{anyhow, Context, Result};
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, Write};

use crate::llm;
use crate::mutation::json_write::set_value_at_path;
use crate::sieves::requirements::artifact::{
    Inconsistency,
    NonGoal,
    PendingClarification,
    RequirementsArtifact,
};
use crate::sieves::requirements::io::{load_requirements, save_requirements};
use crate::sieves::requirements::validator::validate_requirements_artifact;

const QUESTION_SYSTEM_PROMPT: &str =
    include_str!("prompts/non_goals_question_system.txt");
const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/non_goals_extract_system.txt");
const NON_GOALS_CLARIFICATION_ID: &str = "scope.non_goals";
const NON_GOALS_SIEVE_ID: &str = "requirements.scope.non_goals";

#[derive(Debug, Deserialize)]
struct ClarificationQuestion {
    question: String,
}

#[derive(Debug, Deserialize)]
struct NonGoalsExtraction {
    non_goals: Vec<ExtractedNonGoal>,
    no_non_goals_declared: bool,
    detected_inconsistencies: Vec<DetectedInconsistency>,
}

#[derive(Debug, Deserialize)]
struct ExtractedNonGoal {
    kind: String,
    text: String,
}

#[derive(Debug, Deserialize)]
struct DetectedInconsistency {
    id: String,
    message: String,
}

pub fn run_non_goals_scope() -> Result<()> {
    let artifact = load_requirements().context("failed to load requirements artifact")?;

    let clarification = find_pending_clarification(&artifact, NON_GOALS_CLARIFICATION_ID)?;
    let question = generate_non_goals_question(&artifact, &clarification)?;

    println!("Current question:");
    println!("{question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact = update_non_goals(artifact, &clarification, answer.trim())?;

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

fn generate_non_goals_question(
    artifact: &RequirementsArtifact,
    clarification: &PendingClarification,
) -> Result<String> {
    let prompt_input = json!({
        "clarification": clarification,
        "current_value": artifact.scope.non_goals,
        "relevant_context": {
            "intent": artifact.intent,
            "product": artifact.product,
            "scope": {
                "capability_categories": artifact.scope.capability_categories,
                "explicit_constraints": artifact.scope.explicit_constraints,
            }
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate non-goals clarification question")?;

    let generated: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if generated.question.trim().is_empty() {
        anyhow::bail!("generated non-goals question must not be empty");
    }

    Ok(generated.question)
}

pub fn update_non_goals(
    artifact: RequirementsArtifact,
    clarification: &PendingClarification,
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before non-goals update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    let prompt_input = json!({
        "clarification": clarification,
        "user_answer": user_answer,
        "current_value": artifact.scope.non_goals,
        "relevant_context": {
            "intent": artifact.intent,
            "product": artifact.product,
            "scope": {
                "capability_categories": artifact.scope.capability_categories,
                "explicit_constraints": artifact.scope.explicit_constraints,
            }
        }
    });

    let extraction_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract non-goals")?;

    let extraction: NonGoalsExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match NonGoalsExtraction schema")?;

    apply_non_goals_extraction(artifact, &extraction)
}

fn apply_non_goals_extraction(
    artifact: RequirementsArtifact,
    extraction: &NonGoalsExtraction,
) -> Result<RequirementsArtifact> {
    validate_non_goals_extraction(extraction)?;

    if extraction.non_goals.is_empty()
        && !extraction.no_non_goals_declared
        && extraction.detected_inconsistencies.is_empty()
    {
        anyhow::bail!("non-goals answer did not clarify non_goals");
    }

    let mut artifact_value = serde_json::to_value(&artifact)
        .context("failed to convert requirements artifact to JSON value")?;

    if !extraction.non_goals.is_empty() {
        let non_goals: Vec<NonGoal> = extraction
            .non_goals
            .iter()
            .map(|item| NonGoal {
                kind: item.kind.clone(),
                text: item.text.clone(),
            })
            .collect();

        set_value_at_path(
            &mut artifact_value,
            &["scope".to_string(), "non_goals".to_string()],
            serde_json::to_value(non_goals)
                .context("failed to serialize non_goals")?,
        )
        .context("failed to set scope.non_goals")?;
    }

    if !extraction.detected_inconsistencies.is_empty() {
        let inconsistencies = artifact_value
            .get_mut("inconsistencies")
            .and_then(Value::as_array_mut)
            .ok_or_else(|| anyhow!("inconsistencies must be an array"))?;

        for detected in &extraction.detected_inconsistencies {
            let built = build_non_goals_inconsistency(detected)?;
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
    .context("failed to set maturity after non-goals update")?;

    if extraction.detected_inconsistencies.is_empty()
        && (!extraction.non_goals.is_empty() || extraction.no_non_goals_declared)
    {
        let _removed = remove_pending_clarification_by_id(
            &mut artifact_value,
            NON_GOALS_CLARIFICATION_ID,
        )?;
    }

    let updated_artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&updated_artifact)
        .context("non-goals update produced invalid requirements artifact")?;

    validate_non_goals_result(&updated_artifact, extraction)?;

    Ok(updated_artifact)
}

fn validate_non_goals_extraction(extraction: &NonGoalsExtraction) -> Result<()> {
    const ALLOWED_NON_GOAL_KINDS: &[&str] = &["permanent", "release", "deferred"];

    for (index, item) in extraction.non_goals.iter().enumerate() {
        if item.kind.trim().is_empty() {
            anyhow::bail!("non_goals[{index}].kind must not be empty");
        }
        if !ALLOWED_NON_GOAL_KINDS.contains(&item.kind.as_str()) {
            anyhow::bail!(
                "non_goals[{index}].kind must be one of {:?}, got {:?}",
                ALLOWED_NON_GOAL_KINDS,
                item.kind
            );
        }
        if item.text.trim().is_empty() {
            anyhow::bail!("non_goals[{index}].text must not be empty");
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

    if extraction.no_non_goals_declared {
        if !extraction.non_goals.is_empty() {
            anyhow::bail!(
                "no_non_goals_declared=true requires non_goals to be empty"
            );
        }
        if !extraction.detected_inconsistencies.is_empty() {
            anyhow::bail!(
                "no_non_goals_declared=true requires detected_inconsistencies to be empty"
            );
        }
    }

    if !extraction.non_goals.is_empty() && extraction.no_non_goals_declared {
        anyhow::bail!(
            "non_goals non-empty requires no_non_goals_declared=false"
        );
    }

    Ok(())
}

fn build_non_goals_inconsistency(detected: &DetectedInconsistency) -> Result<Inconsistency> {
    if detected.id.trim().is_empty() {
        anyhow::bail!("detected inconsistency id must not be empty");
    }
    if detected.message.trim().is_empty() {
        anyhow::bail!("detected inconsistency message must not be empty");
    }

    Ok(Inconsistency {
        id: format!("scope.non_goals.{}", detected.id),
        stage: "scope".to_string(),
        sieve: NON_GOALS_SIEVE_ID.to_string(),
        severity: "blocking".to_string(),
        target_paths: vec![vec!["scope".to_string(), "non_goals".to_string()]],
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

fn validate_non_goals_result(
    artifact: &RequirementsArtifact,
    extraction: &NonGoalsExtraction,
) -> Result<()> {
    if !extraction.non_goals.is_empty() && artifact.scope.non_goals.is_empty() {
        anyhow::bail!("non-goals update must populate scope.non_goals");
    }

    if extraction.no_non_goals_declared && !artifact.scope.non_goals.is_empty() {
        anyhow::bail!(
            "no_non_goals_declared=true requires scope.non_goals to remain empty"
        );
    }

    let has_pending = artifact
        .pending_clarifications
        .iter()
        .any(|item| item.id == NON_GOALS_CLARIFICATION_ID);

    if extraction.detected_inconsistencies.is_empty()
        && (!extraction.non_goals.is_empty() || extraction.no_non_goals_declared)
        && has_pending
    {
        anyhow::bail!(
            "non_goals pending clarification must be removed after successful update"
        );
    }

    if !extraction.detected_inconsistencies.is_empty() {
        if !has_pending {
            anyhow::bail!(
                "non_goals pending clarification must remain when inconsistencies exist"
            );
        }
        if !artifact
            .inconsistencies
            .iter()
            .any(|item| item.sieve == NON_GOALS_SIEVE_ID)
        {
            anyhow::bail!(
                "non-goals inconsistencies must be appended with matching sieve"
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
                id: NON_GOALS_CLARIFICATION_ID.to_string(),
                target_path: vec!["scope".to_string(), "non_goals".to_string()],
                question: "有没有明确不做的范围？".to_string(),
                sieve: NON_GOALS_SIEVE_ID.to_string(),
            }],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn normal_non_goals_accepted() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![
                ExtractedNonGoal {
                    kind: "release".to_string(),
                    text: "首版不开发移动端应用".to_string(),
                },
                ExtractedNonGoal {
                    kind: "deferred".to_string(),
                    text: "暂不支持跨校交易".to_string(),
                },
            ],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert_eq!(updated.scope.non_goals[0].kind, "release");
        assert_eq!(updated.scope.non_goals[1].kind, "deferred");
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
        assert!(updated.inconsistencies.is_empty());
    }

    #[test]
    fn no_non_goals_declared_is_valid_completion() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![],
            no_non_goals_declared: true,
            detected_inconsistencies: vec![],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated.scope.non_goals.is_empty());
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
        assert!(updated.inconsistencies.is_empty());
    }

    #[test]
    fn uncertain_absence_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "ambiguous_non_goal_commitment".to_string(),
                message: "用户没有说明该非目标是永久排除、当前版本排除，还是暂缓考虑，需要进一步澄清。".to_string(),
            }],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
        let inconsistency = updated
            .inconsistencies
            .iter()
            .find(|item| item.sieve == NON_GOALS_SIEVE_ID)
            .expect("must have inconsistency");
        assert_eq!(inconsistency.severity, "blocking");
    }

    #[test]
    fn functional_requirement_answer_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "functional_requirement_instead_of_non_goal".to_string(),
                message: "用户回答主要描述功能或能力，而不是明确不做或暂不支持的范围。".to_string(),
            }],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == NON_GOALS_SIEVE_ID && item.severity == "blocking"));
    }

    #[test]
    fn explicit_constraint_answer_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "explicit_constraint_instead_of_non_goal".to_string(),
                message: "用户回答更像必须遵守的禁止性约束，而不是产品非目标。".to_string(),
            }],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == NON_GOALS_SIEVE_ID && item.severity == "blocking"));
    }

    #[test]
    fn mixed_valid_non_goal_and_inconsistency_keeps_pending() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![ExtractedNonGoal {
                kind: "release".to_string(),
                text: "不开发移动端应用".to_string(),
            }],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "explicit_constraint_instead_of_non_goal".to_string(),
                message: "用户回答中包含禁止性约束，应作为 explicit_constraints 处理，而不是 non_goals。".to_string(),
            }],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert_eq!(updated.scope.non_goals[0].kind, "release");
        assert_eq!(updated.scope.non_goals[0].text, "不开发移动端应用");
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == NON_GOALS_SIEVE_ID && item.severity == "blocking"));
    }

    #[test]
    fn permanent_non_goal_accepted() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![ExtractedNonGoal {
                kind: "permanent".to_string(),
                text: "原则上不支持校外用户交易".to_string(),
            }],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert_eq!(updated.scope.non_goals[0].kind, "permanent");
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
    }

    #[test]
    fn deferred_non_goal_accepted() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![ExtractedNonGoal {
                kind: "deferred".to_string(),
                text: "暂时不开发移动端应用，后续再考虑".to_string(),
            }],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert_eq!(updated.scope.non_goals[0].kind, "deferred");
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
    }

    #[test]
    fn invalid_kind_rejected() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![ExtractedNonGoal {
                kind: "temporary".to_string(),
                text: "不开发移动端应用".to_string(),
            }],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_non_goals_extraction(artifact, &extraction)
            .expect_err("invalid kind should fail");
        assert!(err.to_string().contains("non_goals[0].kind must be one of"));
    }

    #[test]
    fn empty_kind_rejected() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![ExtractedNonGoal {
                kind: "".to_string(),
                text: "不开发移动端应用".to_string(),
            }],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_non_goals_extraction(artifact, &extraction)
            .expect_err("empty kind should fail");
        assert!(err.to_string().contains("non_goals[0].kind must not be empty"));
    }

    #[test]
    fn empty_text_rejected() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![ExtractedNonGoal {
                kind: "release".to_string(),
                text: "".to_string(),
            }],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_non_goals_extraction(artifact, &extraction)
            .expect_err("empty text should fail");
        assert!(err.to_string().contains("non_goals[0].text must not be empty"));
    }

    #[test]
    fn ambiguous_commitment_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "ambiguous_non_goal_commitment".to_string(),
                message: "用户没有说明该非目标是永久排除、当前版本排除，还是暂缓考虑，需要进一步澄清。".to_string(),
            }],
        };

        let updated =
            apply_non_goals_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == NON_GOALS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == NON_GOALS_SIEVE_ID && item.severity == "blocking"));
    }

    #[test]
    fn no_declared_true_with_non_empty_non_goals_rejected() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![ExtractedNonGoal {
                kind: "release".to_string(),
                text: "不开发移动端应用".to_string(),
            }],
            no_non_goals_declared: true,
            detected_inconsistencies: vec![],
        };

        let err = apply_non_goals_extraction(artifact, &extraction)
            .expect_err("invalid extraction should fail");
        assert!(err
            .to_string()
            .contains("no_non_goals_declared=true requires non_goals to be empty"));
    }

    #[test]
    fn no_declared_true_with_inconsistencies_rejected() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![],
            no_non_goals_declared: true,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "vague_non_goal".to_string(),
                message: "用户回答过于宽泛，无法形成可执行的非目标边界。".to_string(),
            }],
        };

        let err = apply_non_goals_extraction(artifact, &extraction)
            .expect_err("invalid extraction should fail");
        assert!(err.to_string().contains(
            "no_non_goals_declared=true requires detected_inconsistencies to be empty"
        ));
    }

    #[test]
    fn empty_extraction_rejected() {
        let artifact = base_artifact();
        let extraction = NonGoalsExtraction {
            non_goals: vec![],
            no_non_goals_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_non_goals_extraction(artifact, &extraction)
            .expect_err("empty extraction should fail");
        assert!(err
            .to_string()
            .contains("non-goals answer did not clarify non_goals"));
    }
}
