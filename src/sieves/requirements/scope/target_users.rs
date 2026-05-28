use anyhow::{anyhow, Context, Result};
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, Write};

use crate::llm;
use crate::mutation::json_write::set_value_at_path;
use crate::sieves::requirements::artifact::{
    Inconsistency,
    PendingClarification,
    RequirementsArtifact,
};
use crate::sieves::requirements::io::{
    load_requirements,
    save_requirements,
};
use crate::sieves::requirements::validator::validate_requirements_artifact;

const QUESTION_SYSTEM_PROMPT: &str =
    include_str!("prompts/target_users_question_system.txt");

const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/target_users_extract_system.txt");

const TARGET_USERS_CLARIFICATION_ID: &str = "product.target_users";
const TARGET_USERS_SIEVE_ID: &str = "requirements.scope.target_users";

#[derive(Debug, Deserialize)]
struct ClarificationQuestion {
    question: String,
}

#[derive(Debug, Deserialize)]
struct TargetUsersExtraction {
    target_users: Vec<String>,
    detected_inconsistencies: Vec<DetectedInconsistency>,
}

#[derive(Debug, Deserialize)]
struct DetectedInconsistency {
    id: String,
    message: String,
}

pub fn run_target_users_scope() -> Result<()> {
    let artifact = load_requirements()
        .context("failed to load requirements artifact")?;

    let clarification = find_pending_clarification(
        &artifact,
        TARGET_USERS_CLARIFICATION_ID,
    )?;

    let generated_question = generate_target_users_question(
        &artifact,
        &clarification,
    )?;

    println!("Current question:");
    println!("{generated_question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact = update_target_users(
        artifact,
        &clarification,
        answer.trim(),
    )?;

    save_requirements(&updated_artifact)
        .context("failed to save requirements artifact")?;

    println!();
    println!("Saved requirements artifact:");
    println!("{}", serde_json::to_string_pretty(&updated_artifact)?);

    Ok(())
}

fn generate_target_users_question(
    artifact: &RequirementsArtifact,
    clarification: &PendingClarification,
) -> Result<String> {
    let prompt_input = json!({
        "clarification": clarification,
        "current_value": artifact.product.target_users,
        "relevant_context": {
            "intent": artifact.intent
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate target users clarification question")?;

    let generated: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if generated.question.trim().is_empty() {
        anyhow::bail!("generated target users question must not be empty");
    }

    Ok(generated.question)
}

pub fn update_target_users(
    artifact: RequirementsArtifact,
    clarification: &PendingClarification,
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before target users update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    let prompt_input = json!({
        "clarification": clarification,
        "user_answer": user_answer,
        "current_value": artifact.product.target_users,
        "relevant_context": {
            "intent": artifact.intent
        }
    });

    let extraction_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract target users")?;

    let extraction: TargetUsersExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match TargetUsersExtraction schema")?;

    apply_target_users_extraction(artifact, &extraction)
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

fn remove_pending_clarification_by_id(
    artifact_value: &mut Value,
    id: &str,
) -> Result<()> {
    let pending = artifact_value
        .get_mut("pending_clarifications")
        .and_then(Value::as_array_mut)
        .ok_or_else(|| anyhow!("pending_clarifications must be an array"))?;

    let original_len = pending.len();

    pending.retain(|item| {
        item.get("id")
            .and_then(Value::as_str)
            != Some(id)
    });

    if pending.len() == original_len {
        anyhow::bail!(
            "pending clarification {:?} was not removed because it was not found",
            id
        );
    }

    Ok(())
}

fn validate_target_users_extraction(extraction: &TargetUsersExtraction) -> Result<()> {
    for (index, value) in extraction.target_users.iter().enumerate() {
        if value.trim().is_empty() {
            anyhow::bail!("target_users[{index}] must not be empty");
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

    Ok(())
}

fn apply_target_users_extraction(
    artifact: RequirementsArtifact,
    extraction: &TargetUsersExtraction,
) -> Result<RequirementsArtifact> {
    validate_target_users_extraction(extraction)?;

    if extraction.target_users.is_empty()
        && extraction.detected_inconsistencies.is_empty()
    {
        anyhow::bail!("target users answer did not clarify target_users");
    }

    let mut artifact_value = serde_json::to_value(&artifact)
        .context("failed to convert requirements artifact to JSON value")?;

    if !extraction.target_users.is_empty() {
        set_value_at_path(
            &mut artifact_value,
            &["product".to_string(), "target_users".to_string()],
            serde_json::to_value(&extraction.target_users)
                .context("failed to serialize target_users")?,
        )
        .context("failed to set product.target_users")?;
    }

    if !extraction.detected_inconsistencies.is_empty() {
        let inconsistencies = artifact_value
            .get_mut("inconsistencies")
            .and_then(Value::as_array_mut)
            .ok_or_else(|| anyhow!("inconsistencies must be an array"))?;

        for detected in &extraction.detected_inconsistencies {
            inconsistencies.push(
                serde_json::to_value(build_target_users_inconsistency(detected)?)
                    .context("failed to serialize inconsistency")?,
            );
        }
    }

    if !extraction.target_users.is_empty()
        && extraction.detected_inconsistencies.is_empty()
    {
        remove_pending_clarification_by_id(
            &mut artifact_value,
            TARGET_USERS_CLARIFICATION_ID,
        )?;
    }

    set_value_at_path(
        &mut artifact_value,
        &["maturity".to_string()],
        Value::String("scope".to_string()),
    )
    .context("failed to set maturity after target users update")?;

    let updated_artifact: RequirementsArtifact =
        serde_json::from_value(artifact_value)
            .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&updated_artifact)
        .context("target users update produced invalid requirements artifact")?;

    validate_target_users_result(&updated_artifact, extraction)?;

    Ok(updated_artifact)
}

fn build_target_users_inconsistency(
    detected: &DetectedInconsistency,
) -> Result<Inconsistency> {
    if detected.id.trim().is_empty() {
        anyhow::bail!("detected inconsistency id must not be empty");
    }
    if detected.message.trim().is_empty() {
        anyhow::bail!("detected inconsistency message must not be empty");
    }

    Ok(Inconsistency {
        id: format!("product.target_users.{}", detected.id),
        stage: "scope".to_string(),
        sieve: TARGET_USERS_SIEVE_ID.to_string(),
        severity: "blocking".to_string(),
        target_paths: vec![vec!["product".to_string(), "target_users".to_string()]],
        message: detected.message.clone(),
        requires_clarification: true,
    })
}

fn validate_target_users_result(
    artifact: &RequirementsArtifact,
    extraction: &TargetUsersExtraction,
) -> Result<()> {
    if !extraction.target_users.is_empty() && artifact.product.target_users.is_empty() {
        anyhow::bail!("target users update must populate product.target_users");
    }

    let has_pending = artifact
        .pending_clarifications
        .iter()
        .any(|item| item.id == TARGET_USERS_CLARIFICATION_ID);

    if extraction.detected_inconsistencies.is_empty()
        && !extraction.target_users.is_empty()
        && has_pending
    {
        anyhow::bail!("target users pending clarification must be removed after successful update");
    }

    if !extraction.detected_inconsistencies.is_empty() {
        if !has_pending {
            anyhow::bail!("target users pending clarification must remain when inconsistencies exist");
        }
        if !artifact
            .inconsistencies
            .iter()
            .any(|item| item.sieve == TARGET_USERS_SIEVE_ID)
        {
            anyhow::bail!("target users inconsistencies must be appended with matching sieve");
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
                raw_input: "设计一个ide".to_string(),
                goal: "设计一个集成开发环境".to_string(),
                domain: "软件开发工具".to_string(),
            },
            product: Product {
                target_users: vec![],
                application_type: vec![],
                target_platforms: vec![],
            },
            scope: Scope {
                capability_categories: vec![],
                mandatory_constraints: vec![],
                scope_exclusions: vec![],
            },
            functional_requirements: vec![],
            non_functional_requirements: vec![],
            external_interfaces: vec![],
            data_requirements: vec![],
            pending_clarifications: vec![PendingClarification {
                id: TARGET_USERS_CLARIFICATION_ID.to_string(),
                target_path: vec!["product".to_string(), "target_users".to_string()],
                question: "目标用户是谁？".to_string(),
                sieve: "requirements.scope.target_users".to_string(),
            }],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn extraction_allows_shared_qualifier_target_users() {
        let extraction = TargetUsersExtraction {
            target_users: vec![
                "有一定开发经验并掌握工业化开发流程的学生".to_string(),
                "有一定开发经验并掌握工业化开发流程的开发者".to_string(),
            ],
            detected_inconsistencies: vec![],
        };

        validate_target_users_extraction(&extraction)
            .expect("shared qualifier target users should be valid");
    }

    #[test]
    fn extraction_allows_propagated_reading_context_qualifier() {
        let extraction = TargetUsersExtraction {
            target_users: vec![
                "经常读书、写摘录和整理想法的个人用户".to_string(),
                "有读书摘录和想法整理需求的学生".to_string(),
                "有读书摘录和想法整理需求的研究者".to_string(),
            ],
            detected_inconsistencies: vec![],
        };

        validate_target_users_extraction(&extraction)
            .expect("propagated shared qualifier should be valid");
    }

    #[test]
    fn extraction_allows_identity_groups_without_forced_qualifier_merge() {
        let extraction = TargetUsersExtraction {
            target_users: vec!["程序员".to_string(), "老师".to_string()],
            detected_inconsistencies: vec![],
        };

        validate_target_users_extraction(&extraction)
            .expect("identity labels should remain independent user groups");
    }

    #[test]
    fn extraction_rejects_empty_result() {
        let extraction = TargetUsersExtraction {
            target_users: vec![],
            detected_inconsistencies: vec![],
        };

        let artifact = base_artifact();
        let err = apply_target_users_extraction(artifact, &extraction)
            .expect_err("empty extraction should fail");
        assert_eq!(err.to_string(), "target users answer did not clarify target_users");
    }

    #[test]
    fn removes_target_users_pending_clarification() {
        let artifact = base_artifact();
        let extraction = TargetUsersExtraction {
            target_users: vec!["学生".to_string()],
            detected_inconsistencies: vec![],
        };

        let updated = apply_target_users_extraction(artifact, &extraction)
            .expect("update should succeed");
        assert!(updated
            .pending_clarifications
            .iter()
            .all(|item| item.id != TARGET_USERS_CLARIFICATION_ID));
        assert_eq!(updated.maturity, "scope");
    }

    #[test]
    fn vague_answer_produces_blocking_inconsistency_and_keeps_pending() {
        let artifact = base_artifact();
        let extraction = TargetUsersExtraction {
            target_users: vec![],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "unclear_target_users".to_string(),
                message: "用户没有明确说明目标用户群体，需要进一步澄清。".to_string(),
            }],
        };

        let updated = apply_target_users_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == TARGET_USERS_CLARIFICATION_ID));
        let inconsistency = updated
            .inconsistencies
            .iter()
            .find(|item| item.sieve == TARGET_USERS_SIEVE_ID)
            .expect("must have inconsistency");
        assert_eq!(inconsistency.id, "product.target_users.unclear_target_users");
        assert_eq!(inconsistency.severity, "blocking");
        assert!(inconsistency.requires_clarification);
        assert_eq!(
            inconsistency.target_paths,
            vec![vec!["product".to_string(), "target_users".to_string()]]
        );
        assert_eq!(updated.maturity, "scope");
    }

    #[test]
    fn detected_inconsistency_with_empty_id_or_message_rejected() {
        let extraction = TargetUsersExtraction {
            target_users: vec![],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "".to_string(),
                message: "x".to_string(),
            }],
        };
        let err = validate_target_users_extraction(&extraction)
            .expect_err("empty inconsistency id should fail");
        assert!(err
            .to_string()
            .contains("detected_inconsistencies[0].id must not be empty"));
    }

    #[test]
    fn existing_unrelated_pending_items_remain() {
        let mut artifact = base_artifact();
        artifact.pending_clarifications.push(PendingClarification {
            id: "scope.capability_categories".to_string(),
            target_path: vec!["scope".to_string(), "capability_categories".to_string()],
            question: "核心能力类别有哪些？".to_string(),
            sieve: "requirements.scope.capability_categories".to_string(),
        });
        let extraction = TargetUsersExtraction {
            target_users: vec!["学生".to_string()],
            detected_inconsistencies: vec![],
        };

        let updated = apply_target_users_extraction(artifact, &extraction)
            .expect("update should succeed");
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == "scope.capability_categories"));
    }
}
