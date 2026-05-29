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
use crate::sieves::requirements::io::{load_requirements, save_requirements};
use crate::sieves::requirements::scope::context::{
    require_pending_clarification_trigger,
    ScopeSieveRunContext,
};
use crate::sieves::requirements::validator::validate_requirements_artifact;

const QUESTION_SYSTEM_PROMPT: &str =
    include_str!("prompts/target_platforms_question_system.txt");
const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/target_platforms_extract_system.txt");

const TARGET_PLATFORMS_CLARIFICATION_ID: &str = "product.target_platforms";
const TARGET_PLATFORMS_SIEVE_ID: &str = "requirements.scope.target_platforms";

const ALLOWED_TARGET_PLATFORMS: &[&str] = &[
    "macOS",
    "Windows",
    "Linux",
    "Web",
    "iOS",
    "Android",
    "Chrome",
    "Firefox",
    "Edge",
    "Safari",
    "VS Code",
    "JetBrains",
];

#[derive(Debug, Deserialize)]
struct ClarificationQuestion {
    question: String,
}

#[derive(Debug, Deserialize)]
struct TargetPlatformsExtraction {
    target_platforms: Vec<String>,
    detected_inconsistencies: Vec<DetectedInconsistency>,
}

#[derive(Debug, Deserialize)]
struct DetectedInconsistency {
    id: String,
    message: String,
}

pub fn run_target_platforms_scope() -> Result<()> {
    run_target_platforms_scope_with_context(ScopeSieveRunContext::pending_clarification(
        TARGET_PLATFORMS_CLARIFICATION_ID,
    ))
}

pub fn run_target_platforms_scope_with_context(
    context: ScopeSieveRunContext,
) -> Result<()> {
    require_pending_clarification_trigger(&context, TARGET_PLATFORMS_CLARIFICATION_ID)?;

    let artifact = load_requirements().context("failed to load requirements artifact")?;
    let clarification = find_pending_clarification(&artifact, TARGET_PLATFORMS_CLARIFICATION_ID)?;

    let question = generate_target_platforms_question(&artifact, &clarification)?;

    println!("Current question:");
    println!("{question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact = update_target_platforms(artifact, &clarification, answer.trim())?;

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

fn generate_target_platforms_question(
    artifact: &RequirementsArtifact,
    clarification: &PendingClarification,
) -> Result<String> {
    let prompt_input = json!({
        "clarification": clarification,
        "current_value": artifact.product.target_platforms,
        "relevant_context": {
            "intent": artifact.intent,
            "product": {
                "target_users": artifact.product.target_users,
                "application_type": artifact.product.application_type,
            }
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate target platforms clarification question")?;

    let generated: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if generated.question.trim().is_empty() {
        anyhow::bail!("generated target platforms question must not be empty");
    }

    Ok(generated.question)
}

pub fn update_target_platforms(
    artifact: RequirementsArtifact,
    clarification: &PendingClarification,
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before target platforms update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    let prompt_input = json!({
        "clarification": clarification,
        "user_answer": user_answer,
        "current_value": artifact.product.target_platforms,
        "relevant_context": {
            "intent": artifact.intent,
            "product": {
                "target_users": artifact.product.target_users,
                "application_type": artifact.product.application_type,
            }
        }
    });

    let extraction_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract target_platforms")?;

    let extraction: TargetPlatformsExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match TargetPlatformsExtraction schema")?;

    apply_target_platforms_extraction(artifact, &extraction)
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
    pending.retain(|item| item.get("id").and_then(Value::as_str) != Some(id));

    if pending.len() == original_len {
        anyhow::bail!(
            "pending clarification {:?} was not removed because it was not found",
            id
        );
    }

    Ok(())
}

fn validate_target_platforms_extraction(
    extraction: &TargetPlatformsExtraction,
) -> Result<()> {
    for (index, item) in extraction.target_platforms.iter().enumerate() {
        if item.trim().is_empty() {
            anyhow::bail!("target_platforms[{index}] must not be empty");
        }
        if !ALLOWED_TARGET_PLATFORMS.contains(&item.as_str()) {
            anyhow::bail!(
                "target_platforms[{index}] must be one of {:?}, got {:?}",
                ALLOWED_TARGET_PLATFORMS,
                item
            );
        }
    }

    for (index, item) in extraction.detected_inconsistencies.iter().enumerate() {
        if item.id.trim().is_empty() {
            anyhow::bail!("detected_inconsistencies[{index}].id must not be empty");
        }
        if item.message.trim().is_empty() {
            anyhow::bail!("detected_inconsistencies[{index}].message must not be empty");
        }
    }

    Ok(())
}

fn apply_target_platforms_extraction(
    artifact: RequirementsArtifact,
    extraction: &TargetPlatformsExtraction,
) -> Result<RequirementsArtifact> {
    validate_target_platforms_extraction(extraction)?;

    if extraction.target_platforms.is_empty() && extraction.detected_inconsistencies.is_empty() {
        anyhow::bail!("target platforms answer did not clarify target_platforms");
    }

    let mut artifact_value = serde_json::to_value(&artifact)
        .context("failed to convert requirements artifact to JSON value")?;

    if !extraction.target_platforms.is_empty() {
        set_value_at_path(
            &mut artifact_value,
            &["product".to_string(), "target_platforms".to_string()],
            serde_json::to_value(&extraction.target_platforms)
                .context("failed to serialize target_platforms")?,
        )
        .context("failed to set product.target_platforms")?;
    }

    if !extraction.detected_inconsistencies.is_empty() {
        let inconsistencies = artifact_value
            .get_mut("inconsistencies")
            .and_then(Value::as_array_mut)
            .ok_or_else(|| anyhow!("inconsistencies must be an array"))?;

        for detected in &extraction.detected_inconsistencies {
            inconsistencies.push(
                serde_json::to_value(build_target_platforms_inconsistency(detected)?)
                    .context("failed to serialize inconsistency")?,
            );
        }
    }

    if !extraction.target_platforms.is_empty() && extraction.detected_inconsistencies.is_empty() {
        remove_pending_clarification_by_id(&mut artifact_value, TARGET_PLATFORMS_CLARIFICATION_ID)?;
    }

    set_value_at_path(
        &mut artifact_value,
        &["maturity".to_string()],
        Value::String("scope".to_string()),
    )
    .context("failed to set maturity after target platforms update")?;

    let updated_artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&updated_artifact)
        .context("target platforms update produced invalid requirements artifact")?;

    validate_target_platforms_result(&updated_artifact, extraction)?;

    Ok(updated_artifact)
}

fn build_target_platforms_inconsistency(
    detected: &DetectedInconsistency,
) -> Result<Inconsistency> {
    if detected.id.trim().is_empty() {
        anyhow::bail!("detected inconsistency id must not be empty");
    }
    if detected.message.trim().is_empty() {
        anyhow::bail!("detected inconsistency message must not be empty");
    }

    Ok(Inconsistency {
        id: format!("scope.target_platforms.{}", detected.id),
        stage: "scope".to_string(),
        sieve: TARGET_PLATFORMS_SIEVE_ID.to_string(),
        severity: "blocking".to_string(),
        target_paths: vec![vec!["product".to_string(), "target_platforms".to_string()]],
        message: detected.message.clone(),
        requires_clarification: true,
    })
}

fn validate_target_platforms_result(
    artifact: &RequirementsArtifact,
    extraction: &TargetPlatformsExtraction,
) -> Result<()> {
    if !extraction.target_platforms.is_empty() && artifact.product.target_platforms.is_empty() {
        anyhow::bail!("target platforms update must populate product.target_platforms");
    }

    let has_pending = artifact
        .pending_clarifications
        .iter()
        .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID);

    if extraction.detected_inconsistencies.is_empty() && !extraction.target_platforms.is_empty() && has_pending {
        anyhow::bail!("target_platforms pending clarification must be removed after successful update");
    }

    if !extraction.detected_inconsistencies.is_empty() {
        if !has_pending {
            anyhow::bail!("target_platforms pending clarification must remain when inconsistencies exist");
        }
        if !artifact
            .inconsistencies
            .iter()
            .any(|item| item.sieve == TARGET_PLATFORMS_SIEVE_ID)
        {
            anyhow::bail!("target_platforms inconsistencies must be appended with matching sieve");
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
                target_users: vec!["学生".to_string()],
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
                id: TARGET_PLATFORMS_CLARIFICATION_ID.to_string(),
                target_path: vec!["product".to_string(), "target_platforms".to_string()],
                question: "目标平台有哪些？".to_string(),
                sieve: TARGET_PLATFORMS_SIEVE_ID.to_string(),
            }],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn valid_target_platforms_writes_field_and_removes_pending() {
        let artifact = base_artifact();
        let extraction = TargetPlatformsExtraction {
            target_platforms: vec!["Web".to_string()],
            detected_inconsistencies: vec![],
        };

        let updated = apply_target_platforms_extraction(artifact, &extraction)
            .expect("update should succeed");
        assert_eq!(updated.product.target_platforms, vec!["Web".to_string()]);
        assert!(updated
            .pending_clarifications
            .iter()
            .all(|item| item.id != TARGET_PLATFORMS_CLARIFICATION_ID));
        assert_eq!(updated.maturity, "scope");
    }

    #[test]
    fn unclear_answer_keeps_pending_and_appends_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = TargetPlatformsExtraction {
            target_platforms: vec![],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "unclear_target_platforms".to_string(),
                message: "用户没有明确说明目标平台，需要进一步澄清。".to_string(),
            }],
        };

        let updated = apply_target_platforms_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.id == "scope.target_platforms.unclear_target_platforms" && item.sieve == TARGET_PLATFORMS_SIEVE_ID));
    }

    #[test]
    fn wrong_layer_application_type_answer_keeps_pending_and_appends_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = TargetPlatformsExtraction {
            target_platforms: vec![],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "application_type_instead_of_target_platforms".to_string(),
                message: "用户回答更像应用形态，而不是目标平台，需要进一步澄清目标平台。".to_string(),
            }],
        };

        let updated = apply_target_platforms_extraction(artifact, &extraction)
            .expect("update should succeed");
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.id == "scope.target_platforms.application_type_instead_of_target_platforms"));
    }

    #[test]
    fn empty_extraction_without_inconsistency_rejected() {
        let artifact = base_artifact();
        let extraction = TargetPlatformsExtraction {
            target_platforms: vec![],
            detected_inconsistencies: vec![],
        };

        let err = apply_target_platforms_extraction(artifact, &extraction)
            .expect_err("empty extraction should fail");
        assert_eq!(
            err.to_string(),
            "target platforms answer did not clarify target_platforms"
        );
    }

    #[test]
    fn invalid_platform_label_rejected() {
        let extraction = TargetPlatformsExtraction {
            target_platforms: vec!["Mac".to_string()],
            detected_inconsistencies: vec![],
        };

        let err = validate_target_platforms_extraction(&extraction)
            .expect_err("invalid label should fail");
        assert!(err.to_string().contains("target_platforms[0] must be one of"));
    }

    #[test]
    fn mismatched_context_trigger_rejected() {
        let context = ScopeSieveRunContext::pending_clarification("product.application_type");
        let err = require_pending_clarification_trigger(&context, TARGET_PLATFORMS_CLARIFICATION_ID)
            .expect_err("mismatched trigger should fail");
        assert_eq!(
            err.to_string(),
            "invalid pending clarification trigger: expected product.target_platforms, got product.application_type"
        );
    }
}
