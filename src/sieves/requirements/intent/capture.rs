use anyhow::{Context, Result};
use serde::Deserialize;

use crate::llm;
use crate::mutation::json_write::set_value_at_path;
use crate::sieves::requirements::artifact::{
    PendingClarification,
    RequirementsArtifact,
};
use crate::sieves::requirements::io::load_requirements_example_as_value;
use crate::sieves::requirements::validator::validate_requirements_artifact;

const SYSTEM_PROMPT: &str = include_str!("prompts/capture_system.txt");

#[derive(Debug, Deserialize)]
struct IntentCaptureExtraction {
    raw_input: String,
    goal: String,
    domain: String,
}

pub fn capture_intent(user_input: &str) -> Result<RequirementsArtifact> {
    if user_input.trim().is_empty() {
        anyhow::bail!("user_input must not be empty");
    }

    let extraction_value = llm::call_llm_json(SYSTEM_PROMPT, user_input)
        .context("failed to capture requirements intent extraction")?;

    let extraction: IntentCaptureExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match IntentCaptureExtraction schema")?;
    validate_intent_capture_extraction(&extraction, user_input)?;

    let mut artifact_value = load_requirements_example_as_value()
        .context("failed to load requirements example template")?;

    apply_intent_capture_extraction(&mut artifact_value, &extraction)?;

    set_fixed_intent_fields(&mut artifact_value)?;

    let artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&artifact)
        .context("intent capture produced invalid requirements artifact")?;

    validate_intent_capture_result(&artifact)?;

    Ok(artifact)
}

fn validate_intent_capture_extraction(
    extraction: &IntentCaptureExtraction,
    original_user_input: &str,
) -> Result<()> {
    if extraction.raw_input.trim().is_empty() {
        anyhow::bail!("intent capture extraction raw_input must not be empty");
    }
    if extraction.goal.trim().is_empty() {
        anyhow::bail!("intent capture extraction goal must not be empty");
    }
    if extraction.domain.trim().is_empty() {
        anyhow::bail!("intent capture extraction domain must not be empty");
    }
    if extraction.raw_input != original_user_input {
        anyhow::bail!("raw_input must match original user input");
    }

    Ok(())
}

fn apply_intent_capture_extraction(
    artifact_value: &mut serde_json::Value,
    extraction: &IntentCaptureExtraction,
) -> Result<()> {
    set_value_at_path(
        artifact_value,
        &["intent".to_string(), "raw_input".to_string()],
        serde_json::Value::String(extraction.raw_input.clone()),
    )
    .context("failed to set intent.raw_input")?;

    set_value_at_path(
        artifact_value,
        &["intent".to_string(), "goal".to_string()],
        serde_json::Value::String(extraction.goal.clone()),
    )
    .context("failed to set intent.goal")?;

    set_value_at_path(
        artifact_value,
        &["intent".to_string(), "domain".to_string()],
        serde_json::Value::String(extraction.domain.clone()),
    )
    .context("failed to set intent.domain")?;

    Ok(())
}

fn validate_intent_capture_result(artifact: &RequirementsArtifact) -> Result<()> {
    if artifact.maturity != "intent" {
        anyhow::bail!(
            "intent capture result maturity must be {:?}, got {:?}",
            "intent",
            artifact.maturity
        );
    }

    if artifact.intent.raw_input.trim().is_empty() {
        anyhow::bail!("intent.raw_input must not be empty");
    }

    if artifact.intent.goal.trim().is_empty() {
        anyhow::bail!("intent.goal must not be empty");
    }

    if artifact.intent.domain.trim().is_empty() {
        anyhow::bail!("intent.domain must not be empty");
    }

    if artifact.pending_clarifications.is_empty() {
        anyhow::bail!("intent capture must produce pending_clarifications");
    }

    Ok(())
}

fn set_fixed_intent_fields(
    artifact_value: &mut serde_json::Value,
) -> Result<()> {
    set_value_at_path(
        artifact_value,
        &["maturity".to_string()],
        serde_json::Value::String("intent".to_string()),
    )
    .context("failed to set maturity")?;

    let pending = build_scope_v0_pending_clarifications();
    set_value_at_path(
        artifact_value,
        &["pending_clarifications".to_string()],
        serde_json::to_value(pending).context("failed to serialize pending_clarifications")?,
    )
    .context("failed to set pending_clarifications")?;

    Ok(())
}

fn build_scope_v0_pending_clarifications() -> Vec<PendingClarification> {
    vec![
        PendingClarification {
            id: "product.target_users".to_string(),
            target_path: vec!["product".to_string(), "target_users".to_string()],
            question: "目标用户是谁？".to_string(),
            sieve: "requirements.scope.target_users".to_string(),
        },
        PendingClarification {
            id: "product.application_type".to_string(),
            target_path: vec!["product".to_string(), "application_type".to_string()],
            question: "应用类型是什么？".to_string(),
            sieve: "requirements.scope.application_boundary".to_string(),
        },
        PendingClarification {
            id: "product.target_platforms".to_string(),
            target_path: vec!["product".to_string(), "target_platforms".to_string()],
            question: "目标平台有哪些？".to_string(),
            sieve: "requirements.scope.application_boundary".to_string(),
        },
        PendingClarification {
            id: "scope.capability_categories".to_string(),
            target_path: vec!["scope".to_string(), "capability_categories".to_string()],
            question: "核心能力类别有哪些？".to_string(),
            sieve: "requirements.scope.capability_categories".to_string(),
        },
        PendingClarification {
            id: "scope.mandatory_constraints".to_string(),
            target_path: vec!["scope".to_string(), "mandatory_constraints".to_string()],
            question: "是否有其他强制约束？".to_string(),
            sieve: "requirements.scope.mandatory_constraints".to_string(),
        },
        PendingClarification {
            id: "scope.scope_exclusions".to_string(),
            target_path: vec!["scope".to_string(), "scope_exclusions".to_string()],
            question: "是否有明确排除在范围外的内容？".to_string(),
            sieve: "requirements.scope.scope_exclusions".to_string(),
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sieves::requirements::io::load_requirements_example_as_value;

    #[test]
    fn valid_typed_intent_extraction_accepted() {
        let mut value =
            load_requirements_example_as_value().expect("template should load");
        let extraction = IntentCaptureExtraction {
            raw_input: "设计一个ide".to_string(),
            goal: "设计一个集成开发环境".to_string(),
            domain: "软件开发工具".to_string(),
        };

        validate_intent_capture_extraction(&extraction, "设计一个ide")
            .expect("valid extraction should pass");
        apply_intent_capture_extraction(&mut value, &extraction)
            .expect("apply extraction should succeed");
        set_fixed_intent_fields(&mut value).expect("fixed fields should be set");

        let artifact: RequirementsArtifact =
            serde_json::from_value(value).expect("value to artifact");
        validate_intent_capture_result(&artifact).expect("result should be valid");

        assert_eq!(artifact.intent.raw_input, "设计一个ide");
        assert_eq!(artifact.intent.goal, "设计一个集成开发环境");
        assert_eq!(artifact.intent.domain, "软件开发工具");
        assert_eq!(artifact.maturity, "intent");
        assert!(!artifact.pending_clarifications.is_empty());
        assert!(artifact.product.target_users.is_empty());
        assert!(artifact.product.application_type.is_empty());
        assert!(artifact.product.target_platforms.is_empty());
        assert!(artifact.scope.capability_categories.is_empty());
        assert!(artifact.scope.mandatory_constraints.is_empty());
        assert!(artifact.scope.scope_exclusions.is_empty());
    }

    #[test]
    fn empty_raw_input_rejected() {
        let extraction = IntentCaptureExtraction {
            raw_input: "".to_string(),
            goal: "设计一个集成开发环境".to_string(),
            domain: "软件开发工具".to_string(),
        };

        let err = validate_intent_capture_extraction(&extraction, "设计一个ide")
            .expect_err("empty raw_input should fail");
        assert_eq!(
            err.to_string(),
            "intent capture extraction raw_input must not be empty"
        );
    }

    #[test]
    fn empty_goal_rejected() {
        let extraction = IntentCaptureExtraction {
            raw_input: "设计一个ide".to_string(),
            goal: "".to_string(),
            domain: "软件开发工具".to_string(),
        };

        let err = validate_intent_capture_extraction(&extraction, "设计一个ide")
            .expect_err("empty goal should fail");
        assert_eq!(
            err.to_string(),
            "intent capture extraction goal must not be empty"
        );
    }

    #[test]
    fn empty_domain_rejected() {
        let extraction = IntentCaptureExtraction {
            raw_input: "设计一个ide".to_string(),
            goal: "设计一个集成开发环境".to_string(),
            domain: "".to_string(),
        };

        let err = validate_intent_capture_extraction(&extraction, "设计一个ide")
            .expect_err("empty domain should fail");
        assert_eq!(
            err.to_string(),
            "intent capture extraction domain must not be empty"
        );
    }

    #[test]
    fn raw_input_mismatch_rejected() {
        let extraction = IntentCaptureExtraction {
            raw_input: "设计 IDE".to_string(),
            goal: "设计一个集成开发环境".to_string(),
            domain: "软件开发工具".to_string(),
        };

        let err = validate_intent_capture_extraction(&extraction, "设计一个ide")
            .expect_err("mismatch should fail");
        assert_eq!(err.to_string(), "raw_input must match original user input");
    }

    #[test]
    fn sets_fixed_intent_fields() {
        let mut value =
            load_requirements_example_as_value().expect("template should load");

        set_fixed_intent_fields(&mut value)
            .expect("fixed intent fields should be set");

        assert_eq!(value["maturity"], serde_json::json!("intent"));
        assert_eq!(
            value["pending_clarifications"]
                .as_array()
                .expect("pending_clarifications must be array")
                .len(),
            6
        );
    }
}
