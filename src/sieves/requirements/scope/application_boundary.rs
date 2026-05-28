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
use crate::sieves::requirements::validator::validate_requirements_artifact;

const QUESTION_SYSTEM_PROMPT: &str =
    include_str!("prompts/application_boundary_question_system.txt");
const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/application_boundary_extract_system.txt");

const APPLICATION_TYPE_CLARIFICATION_ID: &str = "product.application_type";
const TARGET_PLATFORMS_CLARIFICATION_ID: &str = "product.target_platforms";
const APPLICATION_BOUNDARY_SIEVE_ID: &str =
    "requirements.scope.application_boundary";

const ALLOWED_APPLICATION_TYPES: &[&str] = &[
    "桌面应用",
    "Web 应用",
    "移动应用",
    "CLI 工具",
    "浏览器扩展",
    "编辑器插件",
    "服务端服务",
];

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
struct ApplicationBoundaryExtraction {
    application_type: Vec<String>,
    target_platforms: Vec<String>,
    detected_inconsistencies: Vec<DetectedInconsistency>,
}

#[derive(Debug, Deserialize)]
struct DetectedInconsistency {
    id: String,
    message: String,
}

pub fn run_application_boundary_scope() -> Result<()> {
    let artifact = load_requirements().context("failed to load requirements artifact")?;

    let mut clarifications = Vec::new();
    if let Some(item) =
        find_pending_clarification_optional(&artifact, APPLICATION_TYPE_CLARIFICATION_ID)
    {
        clarifications.push(item);
    }
    if let Some(item) =
        find_pending_clarification_optional(&artifact, TARGET_PLATFORMS_CLARIFICATION_ID)
    {
        clarifications.push(item);
    }

    if clarifications.is_empty() {
        anyhow::bail!("application boundary pending clarifications not found");
    }

    let question = generate_application_boundary_question(&artifact, &clarifications)?;

    println!("Current question:");
    println!("{question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact =
        update_application_boundary(artifact, &clarifications, answer.trim())?;

    save_requirements(&updated_artifact).context("failed to save requirements artifact")?;

    println!();
    println!("Saved requirements artifact:");
    println!("{}", serde_json::to_string_pretty(&updated_artifact)?);

    Ok(())
}

fn find_pending_clarification_optional(
    artifact: &RequirementsArtifact,
    id: &str,
) -> Option<PendingClarification> {
    artifact
        .pending_clarifications
        .iter()
        .find(|item| item.id == id)
        .cloned()
}

fn generate_application_boundary_question(
    artifact: &RequirementsArtifact,
    clarifications: &[PendingClarification],
) -> Result<String> {
    let prompt_input = json!({
        "clarifications": clarifications,
        "current_value": {
            "application_type": artifact.product.application_type,
            "target_platforms": artifact.product.target_platforms,
        },
        "relevant_context": {
            "intent": artifact.intent,
            "product": {
                "target_users": artifact.product.target_users,
            }
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate application boundary clarification question")?;

    let question: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if question.question.trim().is_empty() {
        anyhow::bail!("generated application boundary question must not be empty");
    }

    Ok(question.question)
}

pub fn update_application_boundary(
    artifact: RequirementsArtifact,
    clarifications: &[PendingClarification],
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before application boundary update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    if clarifications.is_empty() {
        anyhow::bail!("application boundary pending clarifications not found");
    }

    let prompt_input = json!({
        "clarifications": clarifications,
        "user_answer": user_answer,
        "current_value": {
            "application_type": artifact.product.application_type,
            "target_platforms": artifact.product.target_platforms,
        },
        "relevant_context": {
            "intent": artifact.intent,
            "product": {
                "target_users": artifact.product.target_users,
            }
        }
    });

    let extraction_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract application boundary")?;

    let extraction: ApplicationBoundaryExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match ApplicationBoundaryExtraction schema")?;

    apply_application_boundary_extraction(artifact, &extraction)
}

fn apply_application_boundary_extraction(
    artifact: RequirementsArtifact,
    extraction: &ApplicationBoundaryExtraction,
) -> Result<RequirementsArtifact> {
    validate_application_boundary_extraction(&extraction)?;

    if extraction.application_type.is_empty()
        && extraction.target_platforms.is_empty()
        && extraction.detected_inconsistencies.is_empty()
    {
        anyhow::bail!(
            "application boundary answer did not clarify application_type or target_platforms"
        );
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

    if !extraction.target_platforms.is_empty() {
        set_value_at_path(
            &mut artifact_value,
            &["product".to_string(), "target_platforms".to_string()],
            serde_json::to_value(&extraction.target_platforms)
                .context("failed to serialize target_platforms")?,
        )
        .context("failed to set product.target_platforms")?;
    }

    if extraction.detected_inconsistencies.is_empty() {
        if !extraction.application_type.is_empty() {
            let _removed = remove_pending_clarification_by_id(
                &mut artifact_value,
                APPLICATION_TYPE_CLARIFICATION_ID,
            )?;
        }

        if !extraction.target_platforms.is_empty() {
            let _removed = remove_pending_clarification_by_id(
                &mut artifact_value,
                TARGET_PLATFORMS_CLARIFICATION_ID,
            )?;
        }
    }

    let mut updated_artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    if !extraction.detected_inconsistencies.is_empty() {
        for detected in &extraction.detected_inconsistencies {
            updated_artifact
                .inconsistencies
                .push(build_application_boundary_inconsistency(detected)?);
        }
    }

    updated_artifact.maturity = "scope".to_string();

    validate_requirements_artifact(&updated_artifact)
        .context("application boundary update produced invalid requirements artifact")?;

    validate_application_boundary_result(&updated_artifact, &extraction)?;

    Ok(updated_artifact)
}

fn build_application_boundary_inconsistency(
    detected: &DetectedInconsistency,
) -> Result<Inconsistency> {
    if detected.id.trim().is_empty() {
        anyhow::bail!("detected inconsistency id must not be empty");
    }
    if detected.message.trim().is_empty() {
        anyhow::bail!("detected inconsistency message must not be empty");
    }

    Ok(Inconsistency {
        id: format!("scope.application_boundary.{}", detected.id),
        stage: "scope".to_string(),
        sieve: APPLICATION_BOUNDARY_SIEVE_ID.to_string(),
        severity: "blocking".to_string(),
        target_paths: vec![
            vec!["product".to_string(), "application_type".to_string()],
            vec!["product".to_string(), "target_platforms".to_string()],
        ],
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

fn validate_application_boundary_extraction(
    extraction: &ApplicationBoundaryExtraction,
) -> Result<()> {
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
            anyhow::bail!(
                "detected_inconsistencies[{index}].message must not be empty"
            );
        }
    }

    Ok(())
}

fn validate_application_boundary_result(
    artifact: &RequirementsArtifact,
    extraction: &ApplicationBoundaryExtraction,
) -> Result<()> {
    if !extraction.application_type.is_empty() && artifact.product.application_type.is_empty() {
        anyhow::bail!("application boundary update must populate product.application_type");
    }

    if !extraction.target_platforms.is_empty() && artifact.product.target_platforms.is_empty() {
        anyhow::bail!("application boundary update must populate product.target_platforms");
    }

    if extraction.detected_inconsistencies.is_empty() {
        if !extraction.application_type.is_empty()
            && artifact
                .pending_clarifications
                .iter()
                .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID)
        {
            anyhow::bail!(
                "application_type pending clarification must be removed after successful update"
            );
        }

        if !extraction.target_platforms.is_empty()
            && artifact
                .pending_clarifications
                .iter()
                .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID)
        {
            anyhow::bail!(
                "target_platforms pending clarification must be removed after successful update"
            );
        }
    } else {
        if !extraction.application_type.is_empty()
            && !artifact
                .pending_clarifications
                .iter()
                .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID)
        {
            anyhow::bail!(
                "application_type pending clarification must remain when inconsistencies exist"
            );
        }

        if !extraction.target_platforms.is_empty()
            && !artifact
                .pending_clarifications
                .iter()
                .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID)
        {
            anyhow::bail!(
                "target_platforms pending clarification must remain when inconsistencies exist"
            );
        }
    }

    if !extraction.detected_inconsistencies.is_empty() && artifact.inconsistencies.is_empty() {
        anyhow::bail!(
            "application boundary update must append inconsistencies when detected_inconsistencies is non-empty"
        );
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
            pending_clarifications: vec![
                PendingClarification {
                    id: APPLICATION_TYPE_CLARIFICATION_ID.to_string(),
                    target_path: vec!["product".to_string(), "application_type".to_string()],
                    question: "应用类型是什么？".to_string(),
                    sieve: APPLICATION_BOUNDARY_SIEVE_ID.to_string(),
                },
                PendingClarification {
                    id: TARGET_PLATFORMS_CLARIFICATION_ID.to_string(),
                    target_path: vec!["product".to_string(), "target_platforms".to_string()],
                    question: "目标平台有哪些？".to_string(),
                    sieve: APPLICATION_BOUNDARY_SIEVE_ID.to_string(),
                },
            ],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn extraction_allows_valid_labels() {
        let extraction = ApplicationBoundaryExtraction {
            application_type: vec!["桌面应用".to_string(), "CLI 工具".to_string()],
            target_platforms: vec![
                "macOS".to_string(),
                "Windows".to_string(),
                "VS Code".to_string(),
                "JetBrains".to_string(),
            ],
            detected_inconsistencies: vec![],
        };

        validate_application_boundary_extraction(&extraction)
            .expect("valid labels should pass");
    }

    #[test]
    fn extraction_rejects_invalid_application_type_label() {
        let extraction = ApplicationBoundaryExtraction {
            application_type: vec!["桌面端".to_string()],
            target_platforms: vec![],
            detected_inconsistencies: vec![],
        };

        let err = validate_application_boundary_extraction(&extraction)
            .expect_err("invalid application_type should fail");
        assert!(err.to_string().contains("application_type[0] must be one of"));
    }

    #[test]
    fn extraction_rejects_invalid_target_platform_label() {
        let extraction = ApplicationBoundaryExtraction {
            application_type: vec![],
            target_platforms: vec!["Mac".to_string()],
            detected_inconsistencies: vec![],
        };

        let err = validate_application_boundary_extraction(&extraction)
            .expect_err("invalid target_platform should fail");
        assert!(err.to_string().contains("target_platforms[0] must be one of"));
    }

    #[test]
    fn converts_detected_inconsistency_to_blocking_inconsistency() {
        let detected = DetectedInconsistency {
            id: "cli_mobile_platform_conflict".to_string(),
            message: "CLI 工具通常不以 iOS/Android 作为直接运行平台，需要进一步澄清目标运行环境。".to_string(),
        };

        let converted = build_application_boundary_inconsistency(&detected)
            .expect("conversion should pass");

        assert_eq!(
            converted.id,
            "scope.application_boundary.cli_mobile_platform_conflict"
        );
        assert_eq!(converted.stage, "scope");
        assert_eq!(converted.sieve, APPLICATION_BOUNDARY_SIEVE_ID);
        assert_eq!(converted.severity, "blocking");
        assert!(converted.requires_clarification);
        assert_eq!(converted.target_paths.len(), 2);
    }

    #[test]
    fn partial_completion_removes_only_relevant_pending_clarification() {
        let artifact = base_artifact();
        let mut value = serde_json::to_value(&artifact).expect("artifact to value");

        let removed_application_type =
            remove_pending_clarification_by_id(&mut value, APPLICATION_TYPE_CLARIFICATION_ID)
                .expect("remove should succeed");

        assert!(removed_application_type);

        let updated: RequirementsArtifact =
            serde_json::from_value(value).expect("value to artifact");

        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID));
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID));
    }

    #[test]
    fn keeps_pending_when_inconsistency_exists_even_if_fields_written() {
        let artifact = base_artifact();
        let extraction = ApplicationBoundaryExtraction {
            application_type: vec!["CLI 工具".to_string()],
            target_platforms: vec!["iOS".to_string(), "Android".to_string()],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "cli_mobile_platform_conflict".to_string(),
                message: "CLI 工具通常不以 iOS/Android 作为直接运行平台，需要进一步澄清目标运行环境。".to_string(),
            }],
        };

        let updated = apply_application_boundary_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert_eq!(
            updated.product.application_type,
            vec!["CLI 工具".to_string()]
        );
        assert_eq!(
            updated.product.target_platforms,
            vec!["iOS".to_string(), "Android".to_string()]
        );
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == APPLICATION_BOUNDARY_SIEVE_ID
                && item.severity == "blocking"));
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID));
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID));
    }

    #[test]
    fn removes_only_application_type_pending_when_only_application_type_clarified_without_inconsistency() {
        let artifact = base_artifact();
        let extraction = ApplicationBoundaryExtraction {
            application_type: vec!["桌面应用".to_string()],
            target_platforms: vec![],
            detected_inconsistencies: vec![],
        };

        let updated = apply_application_boundary_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID));
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID));
    }

    #[test]
    fn removes_only_target_platforms_pending_when_only_target_platforms_clarified_without_inconsistency() {
        let artifact = base_artifact();
        let extraction = ApplicationBoundaryExtraction {
            application_type: vec![],
            target_platforms: vec!["Windows".to_string(), "macOS".to_string()],
            detected_inconsistencies: vec![],
        };

        let updated = apply_application_boundary_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID));
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID));
    }

    #[test]
    fn removes_both_pending_when_both_fields_clarified_without_inconsistency() {
        let artifact = base_artifact();
        let extraction = ApplicationBoundaryExtraction {
            application_type: vec!["桌面应用".to_string()],
            target_platforms: vec!["Windows".to_string(), "macOS".to_string()],
            detected_inconsistencies: vec![],
        };

        let updated = apply_application_boundary_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == APPLICATION_TYPE_CLARIFICATION_ID));
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == TARGET_PLATFORMS_CLARIFICATION_ID));
    }
}
