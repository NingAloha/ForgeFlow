use anyhow::{Context, Result};

use crate::llm;
use crate::mutation::json_write::set_value_at_path;
use crate::mutation::operations::{apply_operations, OperationSet};
use crate::sieves::requirements::artifact::{
    PendingClarification,
    RequirementsArtifact,
};
use crate::sieves::requirements::io::load_requirements_example_as_value;
use crate::sieves::requirements::validator::validate_requirements_artifact;

const SYSTEM_PROMPT: &str = include_str!("prompts/capture_system.txt");

const INTENT_CAPTURE_ALLOWED_PATHS: &[&[&str]] = &[
    &["intent", "raw_input"],
    &["intent", "goal"],
    &["intent", "domain"],
];

pub fn capture_intent(user_input: &str) -> Result<RequirementsArtifact> {
    if user_input.trim().is_empty() {
        anyhow::bail!("user_input must not be empty");
    }

    let operation_value = llm::call_llm_json(SYSTEM_PROMPT, user_input)
        .context("failed to capture requirements intent operations")?;

    let operation_set: OperationSet = serde_json::from_value(operation_value)
        .context("LLM JSON does not match OperationSet schema")?;

    let mut artifact_value = load_requirements_example_as_value()
        .context("failed to load requirements example template")?;

    apply_operations(
        &mut artifact_value,
        &operation_set,
        INTENT_CAPTURE_ALLOWED_PATHS,
    )
    .context("failed to apply intent capture operations")?;

    set_fixed_intent_fields(&mut artifact_value)?;

    let artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&artifact)
        .context("intent capture produced invalid requirements artifact")?;

    validate_intent_capture_result(&artifact)?;

    Ok(artifact)
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
            id: "scope.constraints".to_string(),
            target_path: vec!["scope".to_string(), "constraints".to_string()],
            question: "是否有明确约束？".to_string(),
            sieve: "requirements.scope.constraints".to_string(),
        },
        PendingClarification {
            id: "scope.non_goals".to_string(),
            target_path: vec!["scope".to_string(), "non_goals".to_string()],
            question: "是否有明确不做或暂不支持的范围？".to_string(),
            sieve: "requirements.scope.non_goals".to_string(),
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mutation::operations::{
        validate_operation_paths,
        ArtifactOperation,
        OperationSet,
    };
    use crate::sieves::requirements::io::load_requirements_example_as_value;

    #[test]
    fn rejects_pending_clarifications_path_in_intent_capture() {
        let op_set = OperationSet {
            operations: vec![ArtifactOperation::Set {
                path: vec!["pending_clarifications".to_string()],
                value: serde_json::json!([]),
            }],
        };

        let err = validate_operation_paths(&op_set, INTENT_CAPTURE_ALLOWED_PATHS)
            .expect_err("path should be rejected");
        assert_eq!(
            err.to_string(),
            "operation path pending_clarifications is not allowed"
        );
    }

    #[test]
    fn rejects_product_target_users_path_in_intent_capture() {
        let op_set = OperationSet {
            operations: vec![ArtifactOperation::Set {
                path: vec!["product".to_string(), "target_users".to_string()],
                value: serde_json::json!(["学生"]),
            }],
        };

        let err = validate_operation_paths(&op_set, INTENT_CAPTURE_ALLOWED_PATHS)
            .expect_err("path should be rejected");
        assert_eq!(
            err.to_string(),
            "operation path product.target_users is not allowed"
        );
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
