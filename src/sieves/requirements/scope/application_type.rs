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
    include_str!("prompts/application_type_question_system.txt");
const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/application_type_extract_system.txt");

const APPLICATION_TYPE_CLARIFICATION_ID: &str = "product.application_type";
const APPLICATION_TYPE_SIEVE_ID: &str = "requirements.scope.application_type";

const ALLOWED_APPLICATION_TYPES: &[&str] = &[
    "桌面应用",
    "Web 应用",
    "移动应用",
    "CLI 工具",
    "浏览器扩展",
    "编辑器插件",
    "服务端服务",
];

#[derive(Debug, Deserialize)]
struct ClarificationQuestion {
    question: String,
}

#[derive(Debug, Deserialize)]
struct ApplicationTypeExtraction {
    application_type: Vec<String>,
    detected_inconsistencies: Vec<DetectedInconsistency>,
}

#[derive(Debug, Deserialize)]
struct DetectedInconsistency {
    id: String,
    message: String,
}

pub fn run_application_type_scope() -> Result<()> {
    run_application_type_scope_with_context(ScopeSieveRunContext::pending_clarification(
        APPLICATION_TYPE_CLARIFICATION_ID,
    ))
}

pub fn run_application_type_scope_with_context(
    context: ScopeSieveRunContext,
) -> Result<()> {
    require_pending_clarification_trigger(&context, APPLICATION_TYPE_CLARIFICATION_ID)?;

    let artifact = load_requirements().context("failed to load requirements artifact")?;
    let clarification = find_pending_clarification(&artifact, APPLICATION_TYPE_CLARIFICATION_ID)?;

    let question = generate_application_type_question(&artifact, &clarification)?;

    println!("Current question:");
    println!("{question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact = update_application_type(artifact, &clarification, answer.trim())?;

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

fn generate_application_type_question(
    artifact: &RequirementsArtifact,
    clarification: &PendingClarification,
) -> Result<String> {
    let prompt_input = json!({
        "clarification": clarification,
        "current_value": artifact.product.application_type,
        "relevant_context": {
            "intent": artifact.intent,
            "product": {
                "target_users": artifact.product.target_users,
                "target_platforms": artifact.product.target_platforms,
            }
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate application type clarification question")?;

    let generated: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if generated.question.trim().is_empty() {
        anyhow::bail!("generated application type question must not be empty");
    }

    Ok(generated.question)
}

pub fn update_application_type(
    artifact: RequirementsArtifact,
    clarification: &PendingClarification,
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before application type update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    let prompt_input = json!({
        "clarification": clarification,
        "user_answer": user_answer,
        "current_value": artifact.product.application_type,
        "relevant_context": {
            "intent": artifact.intent,
            "product": {
                "target_users": artifact.product.target_users,
                "target_platforms": artifact.product.target_platforms,
            }
        }
    });

    let extraction_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract application_type")?;

    let extraction: ApplicationTypeExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match ApplicationTypeExtraction schema")?;

    apply_application_type_extraction(artifact, &extraction)
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

fn validate_application_type_extraction(extraction: &ApplicationTypeExtraction) -> Result<()> {
    for (index, item) in extraction.application_type.iter().enumerate() {
        if item.trim().is_empty() {
            anyhow::bail!("application_type[{index}] must not be empty");
        }
        if !ALLOWED_APPLICATION_TYPES.contains(&item.as_str()) {
            anyhow::bail!(
                "application_type[{index}] must be one of {:?}, got {:?}",
                ALLOWED_APPLICATION_TYPES,
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

fn apply_application_type_extraction(
    artifact: RequirementsArtifact,
    extraction: &ApplicationTypeExtraction,
) -> Result<RequirementsArtifact> {
    validate_application_type_extraction(extraction)?;

    if extraction.application_type.is_empty() && extraction.detected_inconsistencies.is_empty() {
        anyhow::bail!("application type answer did not clarify application_type");
    }

    let mut artifact_value = serde_json::to_value(&artifact)
        .context("failed to convert requirements artifact to JSON value")?;

    if !extraction.application_type.is_empty() {
        set_value_at_path(
            &mut artifact_value,
            &["product".to_string(), "application_type".to_string()],
            serde_json::to_value(&extraction.application_type)
                .context("failed to serialize application_type")?,
        )
        .context("failed to set product.application_type")?;
    }

    if !extraction.detected_inconsistencies.is_empty() {
        let inconsistencies = artifact_value
            .get_mut("inconsistencies")
            .and_then(Value::as_array_mut)
            .ok_or_else(|| anyhow!("inconsistencies must be an array"))?;

        for detected in &extraction.detected_inconsistencies {
            inconsistencies.push(
                serde_json::to_value(build_application_type_inconsistency(detected)?)
                    .context("failed to serialize inconsistency")?,
            );
        }
    }

    if !extraction.application_type.is_empty() && extraction.detected_inconsistencies.is_empty() {
        remove_pending_clarification_by_id(&mut artifact_value, APPLICATION_TYPE_CLARIFICATION_ID)?;
    }

    set_value_at_path(
        &mut artifact_value,
        &["maturity".to_string()],
        Value::String("scope".to_string()),
    )
    .context("failed to set maturity after application type update")?;

    let updated_artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&updated_artifact)
        .context("application type update produced invalid requirements artifact")?;

    validate_application_type_result(&updated_artifact, extraction)?;

    Ok(updated_artifact)
}

fn build_application_type_inconsistency(detected: &DetectedInconsistency) -> Result<Inconsistency> {
    if detected.id.trim().is_empty() {
        anyhow::bail!("detected inconsistency id must not be empty");
    }
    if detected.message.trim().is_empty() {
        anyhow::bail!("detected inconsistency message must not be empty");
    }

    Ok(Inconsistency {
        id: format!("scope.application_type.{}", detected.id),
        stage: "scope".to_string(),
        sieve: APPLICATION_TYPE_SIEVE_ID.to_string(),
        severity: "blocking".to_string(),
        target_paths: vec![vec!["product".to_string(), "application_type".to_string()]],
        message: detected.message.clone(),
        requires_clarification: true,
    })
}

fn validate_application_type_result(
    artifact: &RequirementsArtifact,
    extraction: &ApplicationTypeExtraction,
) -> Result<()> {
    if !extraction.application_type.is_empty() && artifact.product.application_type.is_empty() {
        anyhow::bail!("application type update must populate product.application_type");
    }

    let has_pending = artifact
        .pending_clarifications
        .iter()
        .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID);

    if extraction.detected_inconsistencies.is_empty() && !extraction.application_type.is_empty() && has_pending {
        anyhow::bail!("application_type pending clarification must be removed after successful update");
    }

    if !extraction.detected_inconsistencies.is_empty() {
        if !has_pending {
            anyhow::bail!("application_type pending clarification must remain when inconsistencies exist");
        }
        if !artifact
            .inconsistencies
            .iter()
            .any(|item| item.sieve == APPLICATION_TYPE_SIEVE_ID)
        {
            anyhow::bail!("application_type inconsistencies must be appended with matching sieve");
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
                id: APPLICATION_TYPE_CLARIFICATION_ID.to_string(),
                target_path: vec!["product".to_string(), "application_type".to_string()],
                question: "应用类型是什么？".to_string(),
                sieve: APPLICATION_TYPE_SIEVE_ID.to_string(),
            }],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn valid_application_type_writes_field_and_removes_pending() {
        let artifact = base_artifact();
        let extraction = ApplicationTypeExtraction {
            application_type: vec!["Web 应用".to_string()],
            detected_inconsistencies: vec![],
        };

        let updated = apply_application_type_extraction(artifact, &extraction)
            .expect("update should succeed");
        assert_eq!(updated.product.application_type, vec!["Web 应用".to_string()]);
        assert!(updated
            .pending_clarifications
            .iter()
            .all(|item| item.id != APPLICATION_TYPE_CLARIFICATION_ID));
        assert_eq!(updated.maturity, "scope");
    }

    #[test]
    fn unclear_answer_keeps_pending_and_appends_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = ApplicationTypeExtraction {
            application_type: vec![],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "unclear_application_type".to_string(),
                message: "用户没有明确说明应用形态，需要进一步澄清。".to_string(),
            }],
        };

        let updated = apply_application_type_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.id == "scope.application_type.unclear_application_type" && item.sieve == APPLICATION_TYPE_SIEVE_ID));
    }

    #[test]
    fn wrong_layer_target_platform_answer_keeps_pending_and_appends_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = ApplicationTypeExtraction {
            application_type: vec![],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "target_platforms_instead_of_application_type".to_string(),
                message: "用户回答更像目标平台，而不是应用形态，需要进一步澄清应用形态。".to_string(),
            }],
        };

        let updated = apply_application_type_extraction(artifact, &extraction)
            .expect("update should succeed");
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.id == "scope.application_type.target_platforms_instead_of_application_type"));
    }

    #[test]
    fn empty_extraction_without_inconsistency_rejected() {
        let artifact = base_artifact();
        let extraction = ApplicationTypeExtraction {
            application_type: vec![],
            detected_inconsistencies: vec![],
        };

        let err = apply_application_type_extraction(artifact, &extraction)
            .expect_err("empty extraction should fail");
        assert_eq!(
            err.to_string(),
            "application type answer did not clarify application_type"
        );
    }

    #[test]
    fn invalid_application_type_label_rejected() {
        let extraction = ApplicationTypeExtraction {
            application_type: vec!["桌面端".to_string()],
            detected_inconsistencies: vec![],
        };

        let err = validate_application_type_extraction(&extraction)
            .expect_err("invalid label should fail");
        assert!(err.to_string().contains("application_type[0] must be one of"));
    }

    #[test]
    fn mismatched_context_trigger_rejected() {
        let context = ScopeSieveRunContext::pending_clarification("product.target_platforms");
        let err = require_pending_clarification_trigger(&context, APPLICATION_TYPE_CLARIFICATION_ID)
            .expect_err("mismatched trigger should fail");
        assert_eq!(
            err.to_string(),
            "invalid pending clarification trigger: expected product.application_type, got product.target_platforms"
        );
    }
}
